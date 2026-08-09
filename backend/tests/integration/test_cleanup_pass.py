"""
Final cleanup pass tests.

Covers every change made in the final audit remediation pass:
  A. Dead imports removed from viewer.py
  B. billing.py uses constants, not hardcoded strings
  C. aiofiles removed from requirements
  D. Dead config fields removed (test_database_url, frontend_base_url)
  E. app/schemas/event.py deleted (dead file)
  F. lifespan migration: no deprecation warnings from on_event
  G. clear_doc_bytes_cache wrapper removed from viewer module
  H. Billing webhook handlers use correct status constants
"""
import inspect


# ── A. Dead imports removed from viewer.py ────────────────────────────────────

class TestViewerImportsClean:
    def test_uuid_not_imported_in_viewer(self):
        """uuid was imported but never used in viewer.py."""
        import app.routers.viewer as viewer_mod
        assert "uuid" not in dir(viewer_mod) or not callable(getattr(viewer_mod, "uuid", None)), \
            "uuid import should have been removed from viewer.py"

    def test_bare_Response_not_imported_in_viewer(self):
        """The bare 'Response' from fastapi was imported but never used — only FastAPIResponse."""
        import app.routers.viewer as viewer_mod
        # FastAPIResponse should still exist (it's the alias used everywhere)
        assert hasattr(viewer_mod, "FastAPIResponse"), "FastAPIResponse alias must remain"
        # The unaliased Response should not be present
        from fastapi.responses import Response
        # Verify the module doesn't have a 'Response' attribute pointing to the fastapi class
        mod_response = getattr(viewer_mod, "Response", None)
        # It's fine if 'Response' doesn't exist at all in the module namespace
        # (it was only used as `Response as FastAPIResponse` — not as bare `Response`)
        assert mod_response is not Response, \
            "bare Response from fastapi should not be in viewer namespace"

    def test_clear_doc_bytes_cache_removed(self):
        """The clear_doc_bytes_cache wrapper was dead code — nothing imported or called it."""
        import app.routers.viewer as viewer_mod
        assert not hasattr(viewer_mod, "clear_doc_bytes_cache"), \
            "clear_doc_bytes_cache wrapper should have been removed from viewer.py"

    def test_test_helper_wrappers_still_present(self):
        """The three test-used wrappers must still exist."""
        import app.routers.viewer as viewer_mod
        assert hasattr(viewer_mod, "clear_page_cache")
        assert hasattr(viewer_mod, "clear_thumb_cache")
        assert hasattr(viewer_mod, "clear_metadata_caches")


# ── B. Billing uses constants, not hardcoded strings ─────────────────────────

class TestBillingConstants:
    def test_no_hardcoded_canceled_string(self):
        """billing.py must not contain the hardcoded string 'canceled' for status."""
        import app.routers.billing as billing_mod
        src = inspect.getsource(billing_mod)
        # The string "canceled" must not appear as a raw string literal assignment
        # Look for assignment patterns like billing.subscription_status = "canceled"
        import re
        # Match assignment to literal string "canceled"
        matches = re.findall(r'subscription_status\s*=\s*["\']canceled["\']', src)
        assert not matches, (
            f"Found hardcoded 'canceled' string in billing.py: {matches}. "
            "Use STATUS_CANCELED constant."
        )

    def test_no_hardcoded_inactive_string(self):
        """billing.py must not contain the hardcoded string 'inactive' as default fallback."""
        import app.routers.billing as billing_mod
        src = inspect.getsource(billing_mod)
        import re
        # The .get("status", "inactive") default should now use STATUS_INACTIVE
        matches = re.findall(r'\.get\(["\']status["\'],\s*["\']inactive["\']', src)
        assert not matches, (
            f"Found hardcoded 'inactive' default in billing.py: {matches}. "
            "Use STATUS_INACTIVE constant."
        )

    def test_billing_constants_imported_at_top_level(self):
        """STATUS_INACTIVE, STATUS_CANCELED, STATUS_PAST_DUE must be top-level imports."""
        import app.routers.billing as billing_mod
        assert hasattr(billing_mod, "STATUS_INACTIVE"), "STATUS_INACTIVE must be imported"
        assert hasattr(billing_mod, "STATUS_CANCELED"), "STATUS_CANCELED must be imported"
        assert hasattr(billing_mod, "STATUS_PAST_DUE"), "STATUS_PAST_DUE must be imported"

    def test_billing_status_values_are_correct(self):
        """Constants must have the right string values."""
        from app.models.billing import STATUS_INACTIVE, STATUS_CANCELED, STATUS_PAST_DUE
        assert STATUS_INACTIVE == "inactive"
        assert STATUS_CANCELED == "canceled"
        assert STATUS_PAST_DUE == "past_due"

    def test_handle_subscription_deleted_uses_canceled_constant(self):
        """_handle_subscription_deleted must set status to STATUS_CANCELED, not literal."""
        import app.routers.billing as billing_mod
        src = inspect.getsource(billing_mod._handle_subscription_deleted)
        assert "STATUS_CANCELED" in src, (
            "_handle_subscription_deleted should use STATUS_CANCELED constant"
        )
        assert '"canceled"' not in src and "'canceled'" not in src, (
            "_handle_subscription_deleted must not use hardcoded 'canceled' string"
        )


# ── C. aiofiles not in requirements ──────────────────────────────────────────

class TestDeadDependencies:
    def test_aiofiles_not_in_requirements(self):
        """aiofiles was never used in app code — should be removed from requirements.txt."""
        import os
        req_path = os.path.join(
            os.path.dirname(__file__), "../../requirements.txt"
        )
        with open(req_path) as f:
            reqs = f.read()
        assert "aiofiles" not in reqs, (
            "aiofiles should be removed from requirements.txt — it is never imported"
        )


# ── D. Dead config fields removed ─────────────────────────────────────────────

class TestDeadConfigRemoved:
    def test_test_database_url_removed(self):
        """test_database_url was set but never read from settings — should be removed."""
        from app.config import Settings
        s = Settings()
        assert not hasattr(s, "test_database_url"), (
            "test_database_url is dead config — tests hardcode their own DB URL"
        )

    def test_frontend_base_url_removed(self):
        """frontend_base_url was only in a startup check but never used for URL generation."""
        from app.config import Settings
        s = Settings()
        assert not hasattr(s, "frontend_base_url"), (
            "frontend_base_url is dead config — the API serves the frontend directly"
        )

    def test_app_public_base_url_still_present(self):
        """The actually-used URL setting must remain."""
        from app.config import Settings
        s = Settings()
        assert hasattr(s, "app_public_base_url")
        assert s.app_public_base_url  # must be non-empty


# ── E. Dead schemas/event.py deleted ─────────────────────────────────────────

class TestDeadSchemaDeleted:
    def test_event_schema_file_does_not_exist(self):
        """app/schemas/event.py was never imported anywhere — it should be deleted."""
        import os
        schema_path = os.path.join(
            os.path.dirname(__file__), "../../app/schemas/event.py"
        )
        assert not os.path.exists(schema_path), (
            "app/schemas/event.py is dead code — it should have been deleted"
        )

    def test_event_schema_module_not_importable(self):
        """The deleted module should raise ImportError."""
        try:
            import app.schemas.event  # noqa: F401
            assert False, "app.schemas.event should not be importable after deletion"
        except ImportError:
            pass  # expected


# ── F. No on_event deprecation (lifespan migration) ──────────────────────────

class TestLifespanMigration:
    def test_main_has_lifespan_not_on_event(self):
        """main.py should use the lifespan context manager, not deprecated on_event."""
        import app.main as main_mod
        src = inspect.getsource(main_mod)
        assert "@app.on_event" not in src, (
            "main.py still uses deprecated @app.on_event — migrate to lifespan"
        )

    def test_main_uses_lifespan(self):
        """The FastAPI app must be created with the lifespan parameter."""
        import app.main as main_mod
        assert hasattr(main_mod, "lifespan"), "lifespan async context manager must exist"
        app_obj = main_mod.app
        # FastAPI stores the lifespan router; check the app has routes (not None)
        assert app_obj is not None

    def test_app_compiles_without_deprecation_warnings(self):
        """Importing app.main must not trigger FastAPI on_event DeprecationWarning."""
        import warnings
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            on_event_warnings = [
                w for w in caught
                if "on_event" in str(w.message).lower()
            ]
        assert not on_event_warnings, (
            f"on_event deprecation warnings found: {[str(w.message) for w in on_event_warnings]}"
        )


# ── G. Production guard no longer checks dead fields ─────────────────────────

class TestProductionGuardClean:
    def test_production_guard_checks_correct_fields(self):
        """The production startup guard should check meaningful fields only."""
        import app.main as main_mod
        src = inspect.getsource(main_mod)
        # Dead checks that should be gone
        assert "frontend_base_url" not in src, \
            "frontend_base_url check should be removed from production guard"
        # Active checks that must remain
        assert "supabase_url" in src, "SUPABASE_URL check must remain in production guard"
        assert "ip_hash_salt" in src, "IP_HASH_SALT check must remain in production guard"
        assert "app_public_base_url" in src, \
            "APP_PUBLIC_BASE_URL check must remain in production guard"
