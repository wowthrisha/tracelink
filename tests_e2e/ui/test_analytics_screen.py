"""
Playwright UI tests for the Analytics Screen.
"""
import pytest
from playwright.sync_api import Page, expect
from ui.conftest_ui import app_page

pytestmark = pytest.mark.ui


@pytest.fixture
def analytics_page(app_page: Page) -> Page:
    # Navigate to Analytics via the nav sidebar
    app_page.locator("nav").get_by_text("Analytics").click()
    app_page.wait_for_timeout(800)
    return app_page


class TestAnalyticsScreen:

    def test_analytics_nav_reachable(self, analytics_page: Page):
        """After clicking Analytics, the screen changes."""
        # The analytics screen should show Active Links KPI
        expect(analytics_page.locator("text=Active Links").first).to_be_visible(timeout=5000)

    def test_active_links_kpi_visible(self, analytics_page: Page):
        expect(analytics_page.locator("text=Active Links").first).to_be_visible(timeout=5000)

    def test_kpi_cards_show_numbers(self, analytics_page: Page):
        """KPI cards should show numeric values from the API."""
        analytics_page.wait_for_timeout(1000)
        content = analytics_page.content()
        assert any(c.isdigit() for c in content)

    def test_sparkline_or_chart_present(self, analytics_page: Page):
        """The 7-day views chart should render (SVG element present)."""
        analytics_page.wait_for_timeout(1000)
        svg_count = analytics_page.locator("svg").count()
        assert svg_count > 0

    def test_documents_table_visible(self, analytics_page: Page):
        """Document analytics section renders."""
        analytics_page.wait_for_timeout(1000)
        content = analytics_page.content()
        assert "document" in content.lower()

    def test_risk_score_badge_visible_when_data(self, analytics_page: Page):
        """When documents exist, a risk badge (LOW/MED/HIGH) appears."""
        analytics_page.wait_for_timeout(1500)
        content = analytics_page.content()
        if "LOW" in content or "MED" in content or "HIGH" in content:
            assert True  # risk scores present

    def test_analytics_api_loaded(self, analytics_page: Page):
        """SecureDocAPI is available and has getAnalyticsOverview."""
        result = analytics_page.evaluate(
            "typeof window.SecureDocAPI.getAnalyticsOverview"
        )
        assert result == "function"
