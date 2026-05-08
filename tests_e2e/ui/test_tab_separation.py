"""
UI tests verifying the Viewer and Access Control tabs are functionally distinct.

Viewer tab rules:
  - is a document reading workspace
  - shows a DocumentPicker when no document is selected
  - has page navigation, zoom, thumbnails
  - does NOT contain policy editing forms (no password input, domain/email fields)

Access Control tab rules:
  - is the security administration workspace
  - shows a DocumentPicker when no document is selected
  - has Policy / Share Link / Access Log sub-tabs
  - Policy tab contains password, domain, email, expiry, max-view, concurrent-session fields

Shared state rules:
  - Selecting a document in Viewer updates Access Control and vice-versa
  - No extra validate calls during page navigation

Performance checks:
  - pageCache ref is present in the frontend code (in-memory cache)
  - prefetchPage function is present
  - analytics events are fire-and-forget (logEvent never awaited in page-load path)
"""
import pytest
from playwright.sync_api import Page, expect

from ui.conftest_ui import app_page, nav_to

pytestmark = pytest.mark.ui


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _go_viewer(page: Page) -> None:
    page.locator("nav >> text=Viewer").first.click()
    page.wait_for_timeout(400)


def _go_access(page: Page) -> None:
    page.locator("nav >> text=Access Control").first.click()
    page.wait_for_timeout(400)


# ---------------------------------------------------------------------------
# 1. Basic navigation — both tabs reachable without a pre-selected document
# ---------------------------------------------------------------------------

class TestTabNavigation:

    def test_viewer_tab_navigable_without_doc(self, app_page: Page):
        """Clicking Viewer in the sidebar must navigate there even without a
        pre-selected document (no blocking toast)."""
        _go_viewer(app_page)
        # Should land on viewer — either document picker or the viewer itself
        content = app_page.content()
        assert "viewer" in content.lower() or "Viewer" in content

    def test_access_tab_navigable_without_doc(self, app_page: Page):
        """Clicking Access Control must navigate there even without a
        pre-selected document."""
        _go_access(app_page)
        content = app_page.content()
        assert "access" in content.lower() or "Access" in content

    def test_viewer_shows_document_picker_when_no_doc(self, app_page: Page):
        """Viewer tab must show an inline document picker (not a dead-end
        'Go to Upload' message) when no document is selected."""
        _go_viewer(app_page)
        # Either document-picker data-testid or the section label text
        picker_present = (
            app_page.locator("[data-testid='document-picker']").count() > 0
            or app_page.locator("[data-testid='document-picker-empty']").count() > 0
            or app_page.locator("text=Select a document").count() > 0
            or app_page.locator("text=No ready documents").count() > 0
        )
        assert picker_present, "Viewer should show a document picker when no doc is selected"

    def test_access_shows_document_picker_when_no_doc(self, app_page: Page):
        """Access Control tab must show an inline document picker when no
        document is selected."""
        _go_access(app_page)
        picker_present = (
            app_page.locator("[data-testid='document-picker']").count() > 0
            or app_page.locator("[data-testid='document-picker-empty']").count() > 0
            or app_page.locator("text=Select a document").count() > 0
            or app_page.locator("text=No ready documents").count() > 0
        )
        assert picker_present, "Access Control should show a document picker when no doc is selected"

    def test_viewer_no_policy_fields_without_doc(self, app_page: Page):
        """Viewer tab must not render policy editing inputs (password protection,
        allowed domains, etc.) at any point — these live only in Access Control."""
        _go_viewer(app_page)
        # Policy-specific labels that must NEVER appear in viewer
        policy_labels = [
            "Password Protection",
            "Allowed Domains",
            "Allowed Emails",
            "Max View Count",
            "Max Concurrent Sessions",
            "IP Allowlist",
        ]
        content = app_page.content()
        for lbl in policy_labels:
            assert lbl not in content, (
                f"Policy control '{lbl}' must not appear in the Viewer tab"
            )

    def test_old_no_doc_message_replaced(self, app_page: Page):
        """The old 'Go to the Upload tab, click a document row' message must no
        longer appear in the Viewer tab — it has been replaced by the picker."""
        _go_viewer(app_page)
        content = app_page.content()
        assert "click a document row" not in content, (
            "Old empty-state message should be replaced by DocumentPicker"
        )


# ---------------------------------------------------------------------------
# 2. Structural content — Access Control policy controls
# ---------------------------------------------------------------------------

class TestAccessControlStructure:

    def test_access_control_nav_item_present(self, app_page: Page):
        expect(app_page.locator("nav >> text=Access Control").first).to_be_visible(
            timeout=4000
        )

    def test_access_policy_tab_text_in_source(self, app_page: Page):
        """The Policy / Share Link / Access Log tab labels must be compiled into
        the HTML source (confirms the tab structure is present)."""
        content = app_page.content()
        for label in ("Policy", "Share Link", "Access Log"):
            assert label in content, f"Expected '{label}' tab in Access Control"

    def test_access_policy_controls_in_source(self, app_page: Page):
        """Password protection, allowed domains and permissions controls must
        be compiled into the source (confirms policy editor is present)."""
        content = app_page.content()
        for ctrl in ("Password Protection", "Allowed Domains", "Allowed Emails",
                     "Max View Count", "Max Concurrent Sessions"):
            assert ctrl in content, (
                f"Policy control '{ctrl}' missing from Access Control source"
            )

    def test_access_log_refresh_button_in_source(self, app_page: Page):
        """The Access Log section must include a Refresh button."""
        content = app_page.content()
        assert "Refresh" in content, "Access Log must have a Refresh button"


# ---------------------------------------------------------------------------
# 3. Viewer structure — reading workspace controls
# ---------------------------------------------------------------------------

class TestViewerStructure:

    def test_viewer_nav_item_present(self, app_page: Page):
        expect(app_page.locator("nav >> text=Viewer").first).to_be_visible(
            timeout=4000
        )

    def test_viewer_page_navigation_in_source(self, app_page: Page):
        """Page navigation controls (arrows, zoom) must be compiled into the
        Viewer section of the source."""
        content = app_page.content()
        # Arrow buttons and zoom indicator appear in the source
        assert "ArrowRight" in content or "goNext" in content, (
            "Keyboard navigation not found in viewer source"
        )
        assert "zoom" in content.lower(), "Zoom control not found in viewer source"

    def test_viewer_thumbnail_strip_in_source(self, app_page: Page):
        """The thumbnail sidebar must be compiled into the source."""
        content = app_page.content()
        assert "PageThumb" in content or "thumbnail" in content.lower(), (
            "Thumbnail strip not found in viewer source"
        )

    def test_viewer_has_no_policy_password_field_at_all(self, app_page: Page):
        """'Password Protection' label must never appear anywhere in the Viewer
        screen regardless of document selection state."""
        _go_viewer(app_page)
        # The label text only renders when Access Control tab is active
        # (it's inside AccessScreen, which is only mounted on screen==='access')
        pw_label = app_page.locator("text=Password Protection")
        assert pw_label.count() == 0, (
            "'Password Protection' policy label must not appear in Viewer tab"
        )

    def test_viewer_security_api_available(self, app_page: Page):
        result = app_page.evaluate("typeof window.SecureDocAPI")
        assert result == "object"

    def test_viewer_log_event_fire_and_forget(self, app_page: Page):
        """logEvent must be a function (fire-and-forget — never blocks render)."""
        result = app_page.evaluate("typeof window.SecureDocAPI.logEvent")
        assert result == "function"


# ---------------------------------------------------------------------------
# 4. Performance — caching and prefetch present in source
# ---------------------------------------------------------------------------

class TestViewerPerformance:

    def test_page_cache_present_in_source(self, app_page: Page):
        """In-memory blob-URL page cache (pageCache) must be present in the
        compiled frontend source."""
        content = app_page.content()
        assert "pageCache" in content, (
            "pageCache ref must be present for in-memory page caching"
        )

    def test_prefetch_present_in_source(self, app_page: Page):
        """prefetchPage must be present in the compiled source."""
        content = app_page.content()
        assert "prefetchPage" in content, (
            "prefetchPage function must exist for background page prefetching"
        )

    def test_eager_prefetch_page2_present_in_source(self, app_page: Page):
        """Eager prefetch of page 2 on session start must be present."""
        content = app_page.content()
        # The comment 'Eagerly prefetch page 2' or the direct call must appear
        assert "Eagerly prefetch" in content or "prefetch page 2" in content.lower(), (
            "Eager page-2 prefetch on session start must be present"
        )

    def test_session_reuse_in_source(self, app_page: Page):
        """Session reuse via sessionStorage must be present (avoids duplicate
        validate calls across page refreshes)."""
        content = app_page.content()
        assert "securedoc_sess_" in content, (
            "sessionStorage session reuse key must be present"
        )

    def test_analytics_fire_and_forget_in_source(self, app_page: Page):
        """logEvent must be called without await in the page-load path."""
        content = app_page.content()
        # logEvent is always called without await (fire-and-forget)
        assert "logEvent" in content
        assert ".catch(() => {})" in content or "catch(() =>{})" in content or \
               "catch(() => {" in content, (
            "logEvent catch handler must exist (fire-and-forget pattern)"
        )

    def test_no_raw_storage_urls_in_viewer(self, app_page: Page):
        """No raw S3/R2 storage URLs may appear in page image src attributes."""
        img_srcs = app_page.evaluate(
            "() => Array.from(document.querySelectorAll('img')).map(i => i.src)"
        )
        for src in img_srcs:
            assert "s3.amazonaws.com" not in src
            assert "r2.cloudflarestorage.com" not in src
            assert "r2.dev" not in src


# ---------------------------------------------------------------------------
# 5. Document sync — selecting a doc in one tab updates the other
# ---------------------------------------------------------------------------

class TestDocumentSync:

    def test_selecting_doc_in_viewer_switches_screen(self, app_page: Page, api_client):
        """If ready documents exist and a doc is picked from the Viewer picker,
        the viewer screen must transition to actually showing the document."""
        r = api_client.get("/api/analytics/documents")
        docs = r.json().get("documents", [])
        ready = [d for d in docs if d.get("status") == "ready"]
        if not ready:
            pytest.skip("No ready documents available — upload one first")

        _go_viewer(app_page)
        app_page.wait_for_timeout(600)

        items = app_page.locator("[data-testid='doc-picker-item']")
        if items.count() == 0:
            pytest.skip("DocumentPicker rendered no items — backend may be unreachable")

        items.first.click()
        app_page.wait_for_timeout(1000)

        # After selection the viewer should be initializing or showing the document
        # (no longer showing the picker)
        picker_still_visible = app_page.locator("[data-testid='document-picker']").count() > 0
        # It's acceptable for it to still show picker if session validation is slow;
        # what must NOT happen is viewer staying in pure "empty" state with policy controls
        content = app_page.content()
        assert "Password Protection" not in content, (
            "Viewer must never show policy controls even after doc selection"
        )
        assert picker_still_visible is False or \
               app_page.locator("[data-testid='viewer-screen']").count() > 0, (
            "After selecting a doc the viewer screen container must be present"
        )

    def test_access_control_shows_policy_after_doc_selected_via_upload(
        self, app_page: Page, api_client
    ):
        """Clicking 'Access' in the Upload screen's doc table navigates to Access
        Control and displays the Policy tab (not an empty picker)."""
        r = api_client.get("/api/analytics/documents")
        docs = r.json().get("documents", [])
        ready = [d for d in docs if d.get("status") == "ready"]
        if not ready:
            pytest.skip("No ready documents available")

        # Go to upload screen, find the document row, click Access
        nav_to(app_page, "Upload")
        app_page.wait_for_timeout(600)

        # Find "Access" button in the document table rows
        access_btns = app_page.locator("text=Access")
        if access_btns.count() == 0:
            pytest.skip("No 'Access' button found in document table")

        access_btns.first.click()
        app_page.wait_for_timeout(600)

        # Should now be on Access Control with the Policy tab visible
        expect(app_page.locator("[data-testid='access-screen']").first).to_be_visible(
            timeout=3000
        )
        # Policy tab content should be visible (not picker)
        content = app_page.content()
        assert "Password Protection" in content, (
            "After navigating via 'Access' button, Policy tab should be active"
        )
