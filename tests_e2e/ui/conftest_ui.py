"""
Playwright UI fixtures.
Requires: playwright install chromium
Frontend served at http://localhost:5500/SecureDoc.html
"""
import pytest
from playwright.sync_api import Page, expect

FRONTEND_URL = "http://localhost:5500/SecureDoc.html"


@pytest.fixture(scope="session")
def browser_context_args():
    return {
        "viewport": {"width": 1280, "height": 900},
        "ignore_https_errors": True,
    }


@pytest.fixture
def app_page(page: Page) -> Page:
    """Navigate to the SecureDoc frontend and wait for it to load."""
    page.goto(FRONTEND_URL, wait_until="networkidle")
    return page


def nav_to(page: Page, screen: str) -> None:
    """Click a nav link by partial text."""
    page.locator(f"nav >> text={screen}").first.click()
    page.wait_for_timeout(300)
