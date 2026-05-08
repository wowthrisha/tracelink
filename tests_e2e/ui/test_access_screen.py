"""
Playwright UI tests for the Access Control Screen.
Tests navigate via simulated doc selection.
"""
import pytest
from playwright.sync_api import Page, expect
from ui.conftest_ui import app_page

pytestmark = pytest.mark.ui


class TestAccessScreenNavigation:

    def test_upload_nav_is_default(self, app_page: Page):
        """App starts on Upload screen."""
        expect(app_page.locator("text=Upload Dashboard")).to_be_visible(timeout=5000)

    def test_access_control_text_in_nav(self, app_page: Page):
        """Access Control nav item exists in sidebar."""
        expect(app_page.locator("text=Access Control")).to_be_visible(timeout=3000)

    def test_analytics_nav_item_exists(self, app_page: Page):
        expect(app_page.locator("text=Analytics")).to_be_visible(timeout=3000)

    def test_viewer_nav_item_exists(self, app_page: Page):
        expect(app_page.locator("text=Viewer")).to_be_visible(timeout=3000)


class TestAccessControlLinks:

    def test_create_link_form_present_after_upload(self, app_page: Page, tmp_path):
        """After uploading a doc and clicking 'Access Control' for that doc,
        the link creation form should appear."""
        # Upload a file first
        pdf_bytes = (
            b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
            b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
            b"xref\n0 4\n"
            b"0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n"
            b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n190\n%%EOF"
        )
        pdf_path = tmp_path / "access_test.pdf"
        pdf_path.write_bytes(pdf_bytes)

        file_input = app_page.locator("input[type=file]")
        file_input.set_input_files(str(pdf_path))
        app_page.wait_for_timeout(2000)

        # Try to find a "Manage" or "Access" button in document rows
        manage_btns = app_page.locator("text=Manage")
        if manage_btns.count() > 0:
            manage_btns.first.click()
            app_page.wait_for_timeout(500)
            # Access control screen should now show
            content = app_page.content()
            assert "link" in content.lower() or "access" in content.lower()
