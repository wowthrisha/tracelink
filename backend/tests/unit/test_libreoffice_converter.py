"""
Unit tests for LibreOfficeConverter.

All tests mock the subprocess and filesystem so they run without LibreOffice
being installed in the test environment.
"""
import os
import subprocess
import tempfile
from unittest.mock import MagicMock, patch, mock_open

import pytest

from app.services.libreoffice_converter import (
    LibreOfficeConverter,
    LibreOfficeError,
    LibreOfficeConversionError,
    LibreOfficeNotAvailableError,
    LibreOfficeTimeoutError,
)


# ── A. is_available ───────────────────────────────────────────────────────────

class TestIsAvailable:
    def test_returns_true_when_binary_on_path(self):
        with patch("shutil.which", return_value="/usr/bin/libreoffice"):
            assert LibreOfficeConverter.is_available() is True

    def test_returns_false_when_binary_not_found(self):
        with patch("shutil.which", return_value=None):
            assert LibreOfficeConverter.is_available() is False


# ── B. convert_to_pdf — success path ─────────────────────────────────────────

class TestConvertToPdfSuccess:
    def _make_converter(self) -> LibreOfficeConverter:
        c = LibreOfficeConverter()
        c.CONVERSION_TIMEOUT_SEC = 5
        return c

    def test_returns_pdf_bytes_on_success(self, tmp_path):
        fake_pdf = b"%PDF-1.4 fake content"
        converter = self._make_converter()

        with patch("shutil.which", return_value="/usr/bin/libreoffice"), \
             patch("subprocess.run") as mock_run, \
             patch("tempfile.mkdtemp", return_value=str(tmp_path)), \
             patch("shutil.rmtree"):

            mock_run.return_value = MagicMock(returncode=0, stderr=b"")

            # Pre-create the expected output file
            (tmp_path / "input.pdf").write_bytes(fake_pdf)

            result = converter.convert_to_pdf(b"PK\x03\x04 fake docx", ".docx")

        assert result == fake_pdf

    def test_subprocess_called_with_list_not_shell(self, tmp_path):
        converter = self._make_converter()
        fake_pdf = b"%PDF-1.4 fake"

        with patch("shutil.which", return_value="/usr/bin/libreoffice"), \
             patch("subprocess.run") as mock_run, \
             patch("tempfile.mkdtemp", return_value=str(tmp_path)), \
             patch("shutil.rmtree"):

            mock_run.return_value = MagicMock(returncode=0, stderr=b"")
            (tmp_path / "input.pdf").write_bytes(fake_pdf)

            converter.convert_to_pdf(b"PK\x03\x04 fake docx", ".docx")

        call_args = mock_run.call_args
        cmd = call_args.args[0]
        assert isinstance(cmd, list), "subprocess.run must receive a list, not a shell string"
        # shell=True must not be passed (defaults to False)
        assert not call_args.kwargs.get("shell", False)

    def test_subprocess_receives_correct_flags(self, tmp_path):
        converter = self._make_converter()
        fake_pdf = b"%PDF-1.4 fake"

        with patch("shutil.which", return_value="/usr/bin/libreoffice"), \
             patch("subprocess.run") as mock_run, \
             patch("tempfile.mkdtemp", return_value=str(tmp_path)), \
             patch("shutil.rmtree"):

            mock_run.return_value = MagicMock(returncode=0, stderr=b"")
            (tmp_path / "input.pdf").write_bytes(fake_pdf)

            converter.convert_to_pdf(b"PK\x03\x04 fake docx", ".docx")

        cmd = mock_run.call_args.args[0]
        assert "--headless" in cmd
        assert "--convert-to" in cmd
        assert "pdf" in cmd
        # --nomacroexecution was removed in LibreOffice 25.2; macro security is
        # now enforced via registrymodifications.xcu (MacroSecurityLevel=3).
        assert "--nomacroexecution" not in cmd

    def test_macro_security_xcu_written_before_subprocess(self, tmp_path):
        """Macro security profile must be written to lo_profile/user/config/ before LO runs."""
        converter = self._make_converter()
        fake_pdf = b"%PDF-1.4 fake"

        with patch("shutil.which", return_value="/usr/bin/libreoffice"), \
             patch("subprocess.run") as mock_run, \
             patch("tempfile.mkdtemp", return_value=str(tmp_path)), \
             patch("shutil.rmtree"):

            mock_run.return_value = MagicMock(returncode=0, stderr=b"")
            (tmp_path / "input.pdf").write_bytes(fake_pdf)

            converter.convert_to_pdf(b"PK\x03\x04 fake docx", ".docx")

        xcu_path = tmp_path / "lo_profile" / "user" / "config" / "registrymodifications.xcu"
        assert xcu_path.exists(), "XCU macro security profile must be created"
        content = xcu_path.read_text()
        assert "MacroSecurityLevel" in content
        assert "<value>3</value>" in content

    def test_input_filename_is_fixed_not_user_supplied(self, tmp_path):
        """The input filename must be 'input.docx', never derived from user data."""
        converter = self._make_converter()
        fake_pdf = b"%PDF-1.4 fake"

        with patch("shutil.which", return_value="/usr/bin/libreoffice"), \
             patch("subprocess.run") as mock_run, \
             patch("tempfile.mkdtemp", return_value=str(tmp_path)), \
             patch("shutil.rmtree"):

            mock_run.return_value = MagicMock(returncode=0, stderr=b"")
            (tmp_path / "input.pdf").write_bytes(fake_pdf)

            converter.convert_to_pdf(b"PK\x03\x04 fake", ".docx")

        cmd = mock_run.call_args.args[0]
        input_path = cmd[-1]
        assert os.path.basename(input_path) == "input.docx"


# ── C. convert_to_pdf — error paths ──────────────────────────────────────────

class TestConvertToPdfErrors:
    def _converter(self) -> LibreOfficeConverter:
        c = LibreOfficeConverter()
        c.CONVERSION_TIMEOUT_SEC = 5
        return c

    def test_raises_not_available_when_binary_missing(self):
        with patch("shutil.which", return_value=None):
            with pytest.raises(LibreOfficeNotAvailableError):
                self._converter().convert_to_pdf(b"data", ".docx")

    def test_raises_conversion_error_on_nonzero_returncode(self, tmp_path):
        with patch("shutil.which", return_value="/usr/bin/libreoffice"), \
             patch("subprocess.run") as mock_run, \
             patch("tempfile.mkdtemp", return_value=str(tmp_path)), \
             patch("shutil.rmtree"):

            mock_run.return_value = MagicMock(
                returncode=1,
                stderr=b"Error: input file not found",
            )

            with pytest.raises(LibreOfficeConversionError):
                self._converter().convert_to_pdf(b"PK\x03\x04 fake", ".docx")

    def test_raises_conversion_error_when_pdf_not_produced(self, tmp_path):
        """LibreOffice exits 0 but does not produce the expected PDF file."""
        with patch("shutil.which", return_value="/usr/bin/libreoffice"), \
             patch("subprocess.run") as mock_run, \
             patch("tempfile.mkdtemp", return_value=str(tmp_path)), \
             patch("shutil.rmtree"):

            mock_run.return_value = MagicMock(returncode=0, stderr=b"")
            # Do NOT create the output PDF — simulates LO bug / unsupported format

            with pytest.raises(LibreOfficeConversionError):
                self._converter().convert_to_pdf(b"PK\x03\x04 fake", ".docx")

    def test_raises_conversion_error_on_empty_pdf(self, tmp_path):
        """LibreOffice exits 0, file exists, but file is empty."""
        with patch("shutil.which", return_value="/usr/bin/libreoffice"), \
             patch("subprocess.run") as mock_run, \
             patch("tempfile.mkdtemp", return_value=str(tmp_path)), \
             patch("shutil.rmtree"):

            mock_run.return_value = MagicMock(returncode=0, stderr=b"")
            (tmp_path / "input.pdf").write_bytes(b"")  # empty file

            with pytest.raises(LibreOfficeConversionError):
                self._converter().convert_to_pdf(b"PK\x03\x04 fake", ".docx")

    def test_raises_timeout_error_on_subprocess_timeout(self, tmp_path):
        with patch("shutil.which", return_value="/usr/bin/libreoffice"), \
             patch("subprocess.run", side_effect=subprocess.TimeoutExpired(
                 cmd=["libreoffice"], timeout=5
             )), \
             patch("tempfile.mkdtemp", return_value=str(tmp_path)), \
             patch("shutil.rmtree"):

            with pytest.raises(LibreOfficeTimeoutError):
                self._converter().convert_to_pdf(b"PK\x03\x04 fake", ".docx")


# ── D. Temp file cleanup ──────────────────────────────────────────────────────

class TestTempFileCleanup:
    def test_temp_dir_cleaned_up_on_success(self, tmp_path):
        fake_pdf = b"%PDF-1.4 fake"
        converter = LibreOfficeConverter()

        # Use a real temp dir so we can verify it gets deleted
        real_tmp = tempfile.mkdtemp(dir=str(tmp_path), prefix="securedoc_lo_")

        def fake_mkdtemp(**kwargs):
            return real_tmp

        def fake_subprocess_run(cmd, **kwargs):
            # Write the expected output PDF inside the temp dir
            open(os.path.join(real_tmp, "input.pdf"), "wb").write(fake_pdf)
            return MagicMock(returncode=0, stderr=b"")

        with patch("shutil.which", return_value="/usr/bin/libreoffice"), \
             patch("subprocess.run", side_effect=fake_subprocess_run), \
             patch("tempfile.mkdtemp", side_effect=fake_mkdtemp):
            converter.convert_to_pdf(b"PK\x03\x04 fake", ".docx")

        assert not os.path.exists(real_tmp), f"Temp dir {real_tmp!r} was not cleaned up"

    def test_temp_dir_cleaned_up_on_failure(self, tmp_path):
        converter = LibreOfficeConverter()

        real_tmp = tempfile.mkdtemp(dir=str(tmp_path), prefix="securedoc_lo_")

        def fake_mkdtemp(**kwargs):
            return real_tmp

        with patch("shutil.which", return_value="/usr/bin/libreoffice"), \
             patch("subprocess.run", return_value=MagicMock(returncode=1, stderr=b"error")), \
             patch("tempfile.mkdtemp", side_effect=fake_mkdtemp):

            with pytest.raises(LibreOfficeConversionError):
                converter.convert_to_pdf(b"PK\x03\x04 fake", ".docx")

        assert not os.path.exists(real_tmp), f"Temp dir {real_tmp!r} was not cleaned up on failure"


# ── E. Exception hierarchy ────────────────────────────────────────────────────

class TestExceptionHierarchy:
    def test_not_available_is_libreoffice_error(self):
        assert issubclass(LibreOfficeNotAvailableError, LibreOfficeError)

    def test_conversion_error_is_libreoffice_error(self):
        assert issubclass(LibreOfficeConversionError, LibreOfficeError)

    def test_timeout_error_is_libreoffice_error(self):
        assert issubclass(LibreOfficeTimeoutError, LibreOfficeError)
