"""
WatermarkService unit tests — import directly from the backend.
Add securedoc/backend to sys.path before running:
  PYTHONPATH=../backend pytest services/test_watermark_service.py
"""
import io
import sys
import os
import pytest
from PIL import Image

# Make backend importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

from app.services.watermark import WatermarkService

pytestmark = pytest.mark.service


def _make_webp(width=400, height=600, color=(220, 220, 220)) -> bytes:
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="WEBP")
    return buf.getvalue()


@pytest.fixture(scope="module")
def svc():
    return WatermarkService()


@pytest.fixture(scope="module")
def blank_webp():
    return _make_webp()


class TestApplyVisibleWatermark:

    def test_returns_bytes(self, svc, blank_webp):
        result = svc.apply_visible_watermark(blank_webp, "CONFIDENTIAL")
        assert isinstance(result, bytes)

    def test_output_is_valid_image(self, svc, blank_webp):
        result = svc.apply_visible_watermark(blank_webp, "CONFIDENTIAL")
        img = Image.open(io.BytesIO(result))
        assert img.width > 0
        assert img.height > 0

    def test_output_dimensions_preserved(self, svc, blank_webp):
        result = svc.apply_visible_watermark(blank_webp, "CONFIDENTIAL")
        orig = Image.open(io.BytesIO(blank_webp))
        out = Image.open(io.BytesIO(result))
        assert out.width == orig.width
        assert out.height == orig.height

    def test_watermark_alters_pixels(self, svc, blank_webp):
        """Watermarked image should differ from the original.
        Use high opacity so the text survives WEBP lossy compression."""
        result = svc.apply_visible_watermark(blank_webp, "CONFIDENTIAL", opacity=0.9)
        orig = Image.open(io.BytesIO(blank_webp)).convert("RGB")
        out = Image.open(io.BytesIO(result)).convert("RGB")
        orig_data = list(orig.getdata())
        out_data = list(out.getdata())
        diffs = sum(1 for a, b in zip(orig_data, out_data) if a != b)
        assert diffs > 0

    def test_output_format_is_webp(self, svc, blank_webp):
        result = svc.apply_visible_watermark(blank_webp, "CONFIDENTIAL")
        img = Image.open(io.BytesIO(result))
        assert img.format == "WEBP"

    def test_different_texts_produce_different_outputs(self, svc, blank_webp):
        """Use high opacity to ensure text shape differences survive WEBP compression."""
        r1 = svc.apply_visible_watermark(blank_webp, "alice@example.com", opacity=0.9)
        r2 = svc.apply_visible_watermark(blank_webp, "bob@example.com", opacity=0.9)
        assert r1 != r2

    def test_custom_opacity(self, svc, blank_webp):
        r_low = svc.apply_visible_watermark(blank_webp, "TEXT", opacity=0.1)
        r_high = svc.apply_visible_watermark(blank_webp, "TEXT", opacity=0.9)
        assert r_low != r_high

    def test_custom_angle(self, svc, blank_webp):
        """Use high opacity to ensure the rotated text differences survive compression."""
        r_flat = svc.apply_visible_watermark(blank_webp, "WATERMARK", angle=0.0, opacity=0.9)
        r_angled = svc.apply_visible_watermark(blank_webp, "WATERMARK", angle=-45.0, opacity=0.9)
        assert r_flat != r_angled

    def test_handles_small_image(self, svc):
        tiny = _make_webp(width=50, height=50)
        result = svc.apply_visible_watermark(tiny, "X")
        assert isinstance(result, bytes)
        img = Image.open(io.BytesIO(result))
        assert img.width == 50

    def test_handles_large_image(self, svc):
        big = _make_webp(width=2480, height=3508)  # A4 @ 300dpi
        result = svc.apply_visible_watermark(big, "CONFIDENTIAL")
        assert isinstance(result, bytes)
        img = Image.open(io.BytesIO(result))
        assert img.width == 2480

    def test_empty_text_does_not_crash(self, svc, blank_webp):
        result = svc.apply_visible_watermark(blank_webp, "")
        assert isinstance(result, bytes)


class TestApplyForensicStamp:

    def test_returns_original_bytes_unchanged(self, svc, blank_webp):
        result = svc.apply_forensic_stamp(blank_webp, "doc-id", 1)
        assert result == blank_webp

    def test_phase1_noop(self, svc, blank_webp):
        """Phase 1 forensic stamp must be a no-op pass-through."""
        r1 = svc.apply_forensic_stamp(blank_webp, "any-id", 1)
        r2 = svc.apply_forensic_stamp(blank_webp, "any-id", 1)
        assert r1 == r2 == blank_webp
