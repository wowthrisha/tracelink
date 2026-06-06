import io
import os
import pytest
from unittest.mock import patch
from PIL import Image

from app.services.rasterizer import RasterizerService, RasterizerError


def _fake_convert_factory(page_count: int, width: int = 595, height: int = 842):
    """
    Return a side_effect for pdf2image.convert_from_bytes that writes real PPM
    files to output_folder and returns their paths (matching the streaming
    implementation's paths_only=True call contract).
    """
    def _fake(pdf_bytes, dpi=200, output_folder=None, paths_only=False, **kwargs):
        paths = []
        for i in range(1, page_count + 1):
            img = Image.new("RGB", (width, height), color=(i * 40 % 256, 100, 200))
            path = os.path.join(output_folder, f"output-{i:04d}.ppm")
            img.save(path, format="PPM")
            paths.append(path)
        return paths
    return _fake


class TestRasterizerService:

    def test_is_valid_pdf_returns_true_for_valid_bytes(self, sample_pdf_bytes):
        svc = RasterizerService()
        assert svc._is_valid_pdf(sample_pdf_bytes) is True

    def test_is_valid_pdf_returns_false_for_invalid_bytes(self, invalid_bytes):
        svc = RasterizerService()
        assert svc._is_valid_pdf(invalid_bytes) is False

    def test_is_valid_pdf_returns_false_for_empty_bytes(self):
        svc = RasterizerService()
        assert svc._is_valid_pdf(b"") is False

    def test_is_valid_pdf_returns_false_for_truncated_header(self):
        svc = RasterizerService()
        assert svc._is_valid_pdf(b"%PDF") is False

    @pytest.mark.asyncio
    async def test_rasterize_raises_on_invalid_pdf(self, invalid_bytes):
        svc = RasterizerService()
        with pytest.raises(RasterizerError):
            await svc.rasterize_document(invalid_bytes, "doc_123")

    @pytest.mark.asyncio
    @patch("pdf2image.convert_from_bytes")
    async def test_rasterize_returns_correct_page_count(self, mock_convert, sample_pdf_bytes):
        mock_convert.side_effect = _fake_convert_factory(page_count=3)
        svc = RasterizerService()
        result = await svc.rasterize_document(sample_pdf_bytes, "doc_123")
        assert len(result) == 3
        assert result[0].page_number == 1
        assert result[2].page_number == 3

    @pytest.mark.asyncio
    @patch("pdf2image.convert_from_bytes")
    async def test_each_page_has_image_bytes(self, mock_convert, sample_pdf_bytes):
        mock_convert.side_effect = _fake_convert_factory(page_count=1)
        svc = RasterizerService()
        result = await svc.rasterize_document(sample_pdf_bytes, "doc_123")
        assert isinstance(result[0].image_bytes, bytes)
        assert len(result[0].image_bytes) > 0

    @pytest.mark.asyncio
    @patch("pdf2image.convert_from_bytes")
    async def test_page_dimensions_captured(self, mock_convert, sample_pdf_bytes):
        mock_convert.side_effect = _fake_convert_factory(page_count=1, width=800, height=1100)
        svc = RasterizerService()
        result = await svc.rasterize_document(sample_pdf_bytes, "doc_123")
        assert result[0].width_px == 800
        assert result[0].height_px == 1100

    @pytest.mark.asyncio
    @patch("pdf2image.convert_from_bytes")
    async def test_temp_files_cleaned_up_after_processing(self, mock_convert, sample_pdf_bytes):
        """Verify temp directory is removed after successful rasterization."""
        captured_tmp = []

        def _fake_and_capture(pdf_bytes, dpi=200, output_folder=None, paths_only=False, **kwargs):
            captured_tmp.append(output_folder)
            img = Image.new("RGB", (100, 100))
            path = os.path.join(output_folder, "output-0001.ppm")
            img.save(path, format="PPM")
            return [path]

        mock_convert.side_effect = _fake_and_capture
        svc = RasterizerService()
        await svc.rasterize_document(sample_pdf_bytes, "doc_123")
        assert captured_tmp, "expected output_folder to be set"
        assert not os.path.exists(captured_tmp[0]), "temp dir should be cleaned up"

    @pytest.mark.asyncio
    @patch("pdf2image.convert_from_bytes")
    async def test_temp_files_cleaned_up_on_error(self, mock_convert, sample_pdf_bytes):
        """Verify temp directory is removed even when conversion raises."""
        captured_tmp = []

        def _failing_convert(pdf_bytes, dpi=200, output_folder=None, **kwargs):
            captured_tmp.append(output_folder)
            raise RuntimeError("simulated conversion error")

        mock_convert.side_effect = _failing_convert
        svc = RasterizerService()
        with pytest.raises(RasterizerError):
            await svc.rasterize_document(sample_pdf_bytes, "doc_123")
        assert captured_tmp
        assert not os.path.exists(captured_tmp[0]), "temp dir should be cleaned up on error"
