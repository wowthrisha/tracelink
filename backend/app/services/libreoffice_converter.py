"""
LibreOffice headless DOCX → PDF conversion service.

Architecture decision — subprocess per conversion (not unoserver daemon)
─────────────────────────────────────────────────────────────────────────
Celery workers process one document at a time.  The per-conversion startup
cost (~1–3 s) is acceptable because DOCX processing is async (the user sees
a 202 immediately on upload) and the dominant latency is pdf2image rasterisation
that follows.

Subprocess isolation ensures memory used during conversion (large images,
embedded fonts) is fully released between tasks.  worker_max_tasks_per_child
in config.py further guards against accumulation in the parent process.

unoserver (persistent LibreOffice daemon) was evaluated but rejected:
  • Requires daemon lifecycle management and health-check/restart logic.
  • Port conflicts arise with multiple worker containers sharing a host.
  • Less battle-tested in production than the headless subprocess approach.

Security model
──────────────
  • subprocess.run() receives a list, never a shell string → no injection.
  • Input is written to a mkdtemp() directory with a random name.
  • Input filename is always 'input.docx', never user-supplied → no traversal.
  • Temp directory cleaned up unconditionally in a finally block.
  • Macros disabled via profile registry (MacroSecurityLevel=3, "Very High") written to
    the per-conversion lo_profile before LibreOffice starts — the former CLI flag
    --nomacroexecution was removed in LibreOffice 25.2.
  • Hard timeout at the subprocess level (default 60 s).
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from typing import Optional

logger = logging.getLogger(__name__)

# Default timeout for a single LibreOffice conversion subprocess.
# 60 s is generous; a 200-page DOCX typically converts in < 30 s.
_CONVERSION_TIMEOUT_SEC: int = 60

# XCU registry fragment that sets macro security to "Very High" (level 3).
# This prevents embedded macros from executing during headless conversion.
# Written into each conversion's isolated lo_profile before LibreOffice starts.
_MACRO_SECURITY_XCU = """\
<?xml version="1.0" encoding="UTF-8"?>
<oor:items xmlns:oor="http://openoffice.org/2001/registry"
           xmlns:xs="http://www.w3.org/2001/XMLSchema"
           xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <item oor:path="/org.openoffice.Office.Common/Security/Scripting">
    <prop oor:name="MacroSecurityLevel" oor:op="fuse">
      <value>3</value>
    </prop>
  </item>
</oor:items>
"""


class LibreOfficeError(Exception):
    """Base for all LibreOffice conversion errors."""


class LibreOfficeNotAvailableError(LibreOfficeError):
    """Raised when the libreoffice binary is not found on PATH."""


class LibreOfficeConversionError(LibreOfficeError):
    """Raised when LibreOffice exits with a non-zero return code."""


class LibreOfficeTimeoutError(LibreOfficeError):
    """Raised when the conversion subprocess exceeds the timeout."""


class LibreOfficeConverter:
    """Convert office documents to PDF using LibreOffice headless."""

    # Exposed as a class attribute so tests can override it.
    CONVERSION_TIMEOUT_SEC: int = _CONVERSION_TIMEOUT_SEC

    # ── Public API ────────────────────────────────────────────────────────────

    @staticmethod
    def is_available() -> bool:
        """Return True if the libreoffice binary is on PATH."""
        return shutil.which("libreoffice") is not None

    def convert_to_pdf(self, input_bytes: bytes, suffix: str = ".docx") -> bytes:
        """
        Convert *input_bytes* (a DOCX document) to PDF bytes.

        Writes the input to a private temp directory, invokes LibreOffice
        headless, reads back the produced PDF, and cleans up in all cases.

        Parameters
        ----------
        input_bytes:
            Raw bytes of the input document.
        suffix:
            File extension for the temp input file (e.g. '.docx').
            Must start with '.' and contain only safe characters.

        Raises
        ------
        LibreOfficeNotAvailableError
            If the libreoffice binary is not found.
        LibreOfficeConversionError
            If LibreOffice exits with a non-zero code or the output PDF
            is not produced.
        LibreOfficeTimeoutError
            If the conversion subprocess does not complete within
            CONVERSION_TIMEOUT_SEC.
        """
        binary = shutil.which("libreoffice")
        if binary is None:
            raise LibreOfficeNotAvailableError(
                "LibreOffice is not installed or not on PATH. "
                "Install via: apt-get install libreoffice-writer"
            )

        tmp_dir: Optional[str] = None
        try:
            tmp_dir = tempfile.mkdtemp(prefix="securedoc_lo_")
            input_path = os.path.join(tmp_dir, f"input{suffix}")
            output_path = os.path.join(tmp_dir, "input.pdf")

            with open(input_path, "wb") as fh:
                fh.write(input_bytes)

            # Each conversion gets its own LO profile dir so concurrent Celery
            # workers don't share lock files.
            lo_profile = os.path.join(tmp_dir, "lo_profile")
            os.makedirs(lo_profile, exist_ok=True)

            # Write macro security profile before LibreOffice starts so embedded
            # macros cannot execute during conversion (MacroSecurityLevel=3).
            _xcu_dir = os.path.join(lo_profile, "user", "config")
            os.makedirs(_xcu_dir, exist_ok=True)
            with open(os.path.join(_xcu_dir, "registrymodifications.xcu"), "w", encoding="utf-8") as _xcu_fh:
                _xcu_fh.write(_MACRO_SECURITY_XCU)

            cmd = [
                binary,
                "--headless",
                "--norestore",
                "--nolockcheck",
                f"-env:UserInstallation=file://{lo_profile}",
                "--convert-to", "pdf",
                "--outdir", tmp_dir,
                input_path,
            ]

            # Build a minimal environment for the LibreOffice subprocess.
            # SEC: do NOT inherit the full process environment — it contains DATABASE_URL,
            # STORAGE_SECRET_ACCESS_KEY, SUPABASE_ANON_KEY, IP_HASH_SALT, and other
            # application secrets that LibreOffice has no need of.  If an attacker
            # achieves RCE via a malicious DOCX, a filtered env limits the blast radius
            # to the whitelist below rather than exposing all credentials.
            _LO_ENV_WHITELIST = frozenset({
                "PATH", "HOME", "USER", "LOGNAME",
                "TMPDIR", "TEMP", "TMP",
                "LANG", "LC_ALL", "LC_CTYPE", "LC_MESSAGES",
                "FONTCONFIG_PATH", "FONTCONFIG_FILE",
                "XDG_DATA_HOME", "XDG_CONFIG_HOME", "XDG_RUNTIME_DIR",
                "DISPLAY", "XAUTHORITY",
                "JAVA_HOME", "JAVA_OPTS",
                "LD_LIBRARY_PATH",
            })
            env = {k: v for k, v in os.environ.items() if k in _LO_ENV_WHITELIST}
            if "JAVA_HOME" not in env:
                import glob as _glob
                candidates = sorted(_glob.glob("/usr/lib/jvm/java-*-openjdk*"))
                if candidates:
                    env["JAVA_HOME"] = candidates[-1]  # pick newest

            logger.debug(
                "lo_convert start suffix=%s input_size=%d timeout=%ds java_home=%s",
                suffix, len(input_bytes), self.CONVERSION_TIMEOUT_SEC,
                env.get("JAVA_HOME", "unset"),
            )

            try:
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=self.CONVERSION_TIMEOUT_SEC,
                    check=False,
                    env=env,
                )
            except subprocess.TimeoutExpired as exc:
                raise LibreOfficeTimeoutError(
                    f"LibreOffice conversion timed out after {self.CONVERSION_TIMEOUT_SEC}s"
                ) from exc

            if proc.returncode != 0:
                stderr = proc.stderr.decode("utf-8", errors="replace")[:800]
                stdout = proc.stdout.decode("utf-8", errors="replace")[:200]
                raise LibreOfficeConversionError(
                    f"LibreOffice exited {proc.returncode}: {stderr}"
                    + (f" | stdout: {stdout}" if stdout.strip() else "")
                )

            if not os.path.exists(output_path):
                stderr = proc.stderr.decode("utf-8", errors="replace")[:500]
                raise LibreOfficeConversionError(
                    f"LibreOffice completed but produced no PDF output: {stderr}"
                )

            with open(output_path, "rb") as fh:
                pdf_bytes = fh.read()

            if not pdf_bytes:
                raise LibreOfficeConversionError(
                    "LibreOffice produced an empty PDF file."
                )

            logger.debug(
                "lo_convert done suffix=%s pdf_size=%d",
                suffix, len(pdf_bytes),
            )
            return pdf_bytes

        finally:
            if tmp_dir and os.path.exists(tmp_dir):
                try:
                    shutil.rmtree(tmp_dir, ignore_errors=True)
                except Exception as cleanup_exc:
                    logger.warning("lo_convert cleanup failed for %s: %s", tmp_dir, cleanup_exc)
