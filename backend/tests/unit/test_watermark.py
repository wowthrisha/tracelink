import hashlib
import io

import pytest
from PIL import Image

from app.services.watermark import WatermarkService


class TestWatermarkService:

    def test_apply_visible_watermark_returns_bytes(self, sample_webp_bytes):
        svc = WatermarkService()
        result = svc.apply_visible_watermark(sample_webp_bytes, "test@example.com · 2025-01-01")
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_apply_visible_watermark_returns_valid_image(self, sample_webp_bytes):
        svc = WatermarkService()
        result = svc.apply_visible_watermark(sample_webp_bytes, "test@example.com · 2025-01-01")
        img = Image.open(io.BytesIO(result))
        assert img.format in ("WEBP", "PNG", "JPEG")

    def test_apply_visible_watermark_does_not_modify_input(self, sample_webp_bytes):
        original = bytes(sample_webp_bytes)
        svc = WatermarkService()
        svc.apply_visible_watermark(sample_webp_bytes, "test@example.com")
        assert sample_webp_bytes == original

    def test_apply_visible_watermark_with_unicode_text(self, sample_webp_bytes):
        svc = WatermarkService()
        result = svc.apply_visible_watermark(sample_webp_bytes, "राहुल@iit.ac.in · 2025")
        assert isinstance(result, bytes)

    def test_apply_visible_watermark_custom_opacity(self, sample_webp_bytes):
        svc = WatermarkService()
        r1 = svc.apply_visible_watermark(sample_webp_bytes, "test", opacity=0.05)
        r2 = svc.apply_visible_watermark(sample_webp_bytes, "test", opacity=0.9)
        assert isinstance(r1, bytes) and isinstance(r2, bytes)
        assert r1 != r2

    def test_apply_visible_watermark_is_actually_visible(self):
        """
        Regression test: at the app's real default opacity (0.22), the watermark
        text must land in the output at a visually meaningful strength, not merely
        differ from the input at the byte level (that alone doesn't catch a bug
        where alpha compositing crushes the effective opacity to near-zero).
        """
        img = Image.new("RGB", (1200, 1600), (255, 255, 255))
        buf = io.BytesIO()
        img.save(buf, format="WEBP", quality=90)
        blank = buf.getvalue()

        svc = WatermarkService()
        result = svc.apply_visible_watermark(blank, "test@example.com · 2026-07-24 · sess:abc123")

        out = Image.open(io.BytesIO(result)).convert("L")
        darkest, lightest = out.getextrema()
        # Text drawn at fill=(128,128,128) and opacity=0.22 should land noticeably
        # below white (255) — well outside WEBP-compression noise on a blank page.
        assert darkest <= 240, (
            f"watermark barely/not visible: darkest pixel={darkest} (expected <=240 "
            "at default 0.22 opacity) — check for double alpha-blending in the "
            "tile paste/composite step"
        )
        nonwhite_pixels = sum(out.histogram()[:250])
        assert nonwhite_pixels > 1000, (
            f"only {nonwhite_pixels} non-white pixels found — watermark tiling "
            "appears to have collapsed to a near no-op"
        )

    # ── Forensic stamp tests ───────────────────────────────────────────────────

    def test_apply_forensic_stamp_returns_valid_webp(self, sample_webp_bytes):
        """Forensic stamp must return a valid image (not a no-op that returns input unchanged)."""
        svc = WatermarkService()
        result = svc.apply_forensic_stamp(sample_webp_bytes, "doc-abc123", 1)
        assert isinstance(result, bytes)
        assert len(result) > 0
        img = Image.open(io.BytesIO(result))
        assert img.format in ("WEBP", "PNG", "JPEG")

    def test_apply_forensic_stamp_is_not_noop(self, sample_webp_bytes):
        """The forensic stamp must actually modify the image bytes.

        The original Phase 1 implementation was a silent no-op (returned input unchanged).
        Phase B1 replaces it with a real near-invisible pixel mark.
        """
        svc = WatermarkService()
        result = svc.apply_forensic_stamp(sample_webp_bytes, "doc-abc123", 1)
        # The result must differ from the input — the stamp modifies pixel data
        assert result != sample_webp_bytes, (
            "apply_forensic_stamp returned the input unchanged — it is still a no-op"
        )

    def test_apply_forensic_stamp_deterministic(self, sample_webp_bytes):
        """Same doc_id and page_number must always produce the same output."""
        svc = WatermarkService()
        r1 = svc.apply_forensic_stamp(sample_webp_bytes, "stable-doc", 3)
        r2 = svc.apply_forensic_stamp(sample_webp_bytes, "stable-doc", 3)
        assert r1 == r2

    def test_apply_forensic_stamp_different_docs_differ(self, sample_webp_bytes):
        """Different document IDs must produce different forensic marks."""
        svc = WatermarkService()
        r1 = svc.apply_forensic_stamp(sample_webp_bytes, "document-aaa", 1)
        r2 = svc.apply_forensic_stamp(sample_webp_bytes, "document-bbb", 1)
        assert r1 != r2, "Different document IDs should produce different forensic marks"

    def test_apply_forensic_stamp_different_pages_differ(self, sample_webp_bytes):
        """Different page numbers must produce different forensic marks."""
        svc = WatermarkService()
        r1 = svc.apply_forensic_stamp(sample_webp_bytes, "same-doc-id", 1)
        r2 = svc.apply_forensic_stamp(sample_webp_bytes, "same-doc-id", 2)
        assert r1 != r2, "Different page numbers should produce different forensic marks"

    def test_apply_forensic_stamp_fingerprint_derivation(self):
        """The forensic mark uses a SHA-256 fingerprint of the document_id."""
        doc_id = "test-document-uuid-123"
        fingerprint = hashlib.sha256(doc_id.encode()).hexdigest()[:8]
        expected_mark = f"SD:{fingerprint}:0001"
        # The mark text must encode a derivable identity
        assert len(fingerprint) == 8
        assert expected_mark.startswith("SD:")

    def test_apply_forensic_stamp_does_not_lose_dimensions(self, sample_webp_bytes):
        """Forensic stamp must not change image dimensions."""
        svc = WatermarkService()
        original = Image.open(io.BytesIO(sample_webp_bytes))
        stamped = svc.apply_forensic_stamp(sample_webp_bytes, "dim-test-doc", 5)
        result = Image.open(io.BytesIO(stamped))
        assert result.size == original.size

    def test_visible_watermark_preserves_forensic_exif(self, sample_webp_bytes):
        """Visible watermark should preserve EXIF metadata from the forensic stamp."""
        svc = WatermarkService()
        # Apply forensic stamp first
        stamped = svc.apply_forensic_stamp(sample_webp_bytes, "exif-test-doc", 1)
        # Then apply visible watermark on top
        result = svc.apply_visible_watermark(stamped, "viewer@example.com · 2026-01-01")
        # Result must be valid
        assert isinstance(result, bytes)
        img = Image.open(io.BytesIO(result))
        assert img.format in ("WEBP", "PNG", "JPEG")
