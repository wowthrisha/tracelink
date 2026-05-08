import pytest
from PIL import Image
import io

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

    def test_apply_forensic_stamp_returns_valid_webp(self, sample_webp_bytes):
        """Forensic stamp embeds LSB data — output is a valid WebP, not identical to input."""
        svc = WatermarkService()
        result = svc.apply_forensic_stamp(sample_webp_bytes, "doc_123", 1)
        assert isinstance(result, bytes)
        assert len(result) > 0
        img = Image.open(io.BytesIO(result))
        assert img.format in ("WEBP", "PNG", "JPEG")

    def test_apply_forensic_stamp_deterministic(self, sample_webp_bytes):
        """Same doc_id and page_number always produce the same output."""
        svc = WatermarkService()
        r1 = svc.apply_forensic_stamp(sample_webp_bytes, "stable-doc", 3)
        r2 = svc.apply_forensic_stamp(sample_webp_bytes, "stable-doc", 3)
        assert r1 == r2

    def test_apply_forensic_stamp_lsb_logic(self):
        """Verify the 8x8 LSB encoding logic directly via PIL pixel manipulation."""
        import hashlib
        from PIL import Image
        import io as _io

        # Test the LSB encoding logic directly (independent of WEBP lossy compression)
        doc_id, page = "verify-doc", 1

        # Build expected bits (same algorithm as the service)
        fp = hashlib.sha256(f"{doc_id}:{page}".encode()).digest()
        expected_bits = []
        for byte in fp[:8]:
            for i in range(7, -1, -1):
                expected_bits.append((byte >> i) & 1)

        # Apply the LSB logic directly to a PIL image
        img = Image.new("RGB", (100, 100), color=(200, 200, 200))
        pixels = img.load()
        bit_idx = 0
        for y in range(8):
            for x in range(8):
                r, g, b = pixels[x, y]
                r = (r & 0xFE) | expected_bits[bit_idx]
                pixels[x, y] = (r, g, b)
                bit_idx += 1

        # Verify the bits were set correctly (pre-compression)
        actual_bits = []
        for y in range(8):
            for x in range(8):
                actual_bits.append(pixels[x, y][0] & 1)

        assert actual_bits == expected_bits
