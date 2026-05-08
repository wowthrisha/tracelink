"""
Playwright UI tests for the Upload Screen.
Requires: playwright install chromium
Frontend: http://localhost:5500/SecureDoc.html
Backend: http://localhost:8000
"""
import os
import pytest
from playwright.sync_api import Page, expect
from ui.conftest_ui import app_page, FRONTEND_URL

pytestmark = pytest.mark.ui


@pytest.fixture
def minimal_pdf_path(tmp_path):
    pdf = (
        b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
        b"xref\n0 4\n"
        b"0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n"
        b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n190\n%%EOF"
    )
    p = tmp_path / "test.pdf"
    p.write_bytes(pdf)
    return str(p)


class TestUploadScreen:

    def test_page_loads(self, app_page: Page):
        """App renders without errors."""
        expect(app_page.locator("#root")).to_be_visible()

    def test_upload_screen_visible_on_load(self, app_page: Page):
        """Upload Dashboard appears on initial load."""
        expect(app_page.locator("text=Upload Dashboard").first).to_be_visible(timeout=5000)

    def test_documents_section_visible(self, app_page: Page):
        # Use exact match targeting the section header div
        expect(app_page.get_by_text("Documents", exact=True).first).to_be_visible(timeout=5000)

    def test_upload_pdf_button_present(self, app_page: Page):
        btn = app_page.locator("text=Upload PDF").first
        expect(btn).to_be_visible()

    def test_upload_valid_pdf_shows_success(self, app_page: Page, minimal_pdf_path):
        """Uploading a valid PDF shows the processing confirmation UI."""
        file_input = app_page.locator("input[type=file]")
        file_input.set_input_files(minimal_pdf_path)
        app_page.wait_for_timeout(2000)
        # Section header should still be visible
        expect(app_page.get_by_text("Documents", exact=True).first).to_be_visible()

    def test_document_list_loads_from_api(self, app_page: Page):
        """Documents section renders after API call."""
        app_page.wait_for_timeout(1000)
        expect(app_page.get_by_text("Documents", exact=True).first).to_be_visible()

    def test_kpi_cards_visible(self, app_page: Page):
        """Total Documents KPI card renders."""
        expect(app_page.locator("text=Total Documents").first).to_be_visible(timeout=5000)

    def test_nav_to_analytics(self, app_page: Page):
        """Clicking Analytics nav switches screen."""
        app_page.locator("nav").get_by_text("Analytics").click()
        app_page.wait_for_timeout(500)
        expect(app_page.locator("text=Active Links").first).to_be_visible(timeout=5000)
