import io
import pytest
from unittest.mock import patch
from PIL import Image

from app.services.rasterizer import RasterizerService, RasterizerError


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
        fake_pages = []
        for _ in range(3):
            img = Image.new("RGB", (595, 842), color=(255, 255, 255))
            fake_pages.append(img)
        mock_convert.return_value = fake_pages
        svc = RasterizerService()
        result = await svc.rasterize_document(sample_pdf_bytes, "doc_123")
        assert len(result) == 3
        assert result[0].page_number == 1
        assert result[2].page_number == 3

    @pytest.mark.asyncio
    @patch("pdf2image.convert_from_bytes")
    async def test_each_page_has_image_bytes(self, mock_convert, sample_pdf_bytes):
        img = Image.new("RGB", (595, 842))
        mock_convert.return_value = [img]
        svc = RasterizerService()
        result = await svc.rasterize_document(sample_pdf_bytes, "doc_123")
        assert isinstance(result[0].image_bytes, bytes)
        assert len(result[0].image_bytes) > 0
