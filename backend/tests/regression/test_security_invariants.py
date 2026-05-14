"""
Core security invariants. Must NEVER be removed or bypassed.
"""
import pytest


class TestSecurityInvariants:

    @pytest.mark.asyncio
    async def test_INVARIANT_original_pdf_never_exposed_in_any_endpoint(
        self, client, sample_pdf_bytes
    ):
        files = {"file": ("test.pdf", sample_pdf_bytes, "application/pdf")}
        upload_r = await client.post("/api/documents/upload", files=files)
        assert upload_r.status_code == 202
        doc_id = upload_r.json()["id"]

        for r in [
            await client.get("/api/documents"),
            await client.get(f"/api/documents/{doc_id}"),
            await client.get(f"/api/documents/{doc_id}/status"),
        ]:
            body_str = str(r.json())
            assert "originals/" not in body_str, \
                f"RAW PDF PATH EXPOSED in response: {body_str[:200]}"
            assert "storage_key" not in body_str, \
                "storage_key field exposed in response"

    @pytest.mark.asyncio
    async def test_INVARIANT_page_endpoint_never_redirects_to_storage(
        self, client, ready_document, active_link
    ):
        validate_r = await client.post(
            "/api/viewer/validate", json={"token": active_link.token}
        )
        session_id = validate_r.json()["session_id"]
        r = await client.get(
            f"/api/viewer/page/{active_link.token}/1?session_id={session_id}",
            follow_redirects=False,
        )
        assert r.status_code not in (301, 302, 307, 308), \
            f"SECURITY VIOLATION: page endpoint redirected to {r.headers.get('location')}"

    @pytest.mark.asyncio
    async def test_INVARIANT_revoked_link_always_fails_validation(
        self, client, active_link
    ):
        await client.delete(f"/api/links/{active_link.id}")
        for _ in range(10):
            r = await client.post(
                "/api/viewer/validate", json={"token": active_link.token}
            )
            assert r.status_code == 410, "REVOKED LINK ACCEPTED — CRITICAL SECURITY BUG"

    @pytest.mark.asyncio
    async def test_INVARIANT_expired_link_always_fails(self, client, expired_link):
        r = await client.post(
            "/api/viewer/validate", json={"token": expired_link.token}
        )
        assert r.status_code == 410

    @pytest.mark.asyncio
    async def test_INVARIANT_max_views_never_exceeded(
        self, client, sample_document_in_db
    ):
        link_r = await client.post("/api/links", json={
            "document_id": str(sample_document_in_db.id),
            "max_views": 2,
        })
        token = link_r.json()["token"]
        r1 = await client.post("/api/viewer/validate", json={"token": token})
        r2 = await client.post("/api/viewer/validate", json={"token": token})
        assert r1.status_code == 200
        assert r2.status_code == 200
        r3 = await client.post("/api/viewer/validate", json={"token": token})
        assert r3.status_code == 410, "MAX VIEWS NOT ENFORCED — CRITICAL BUG"

    @pytest.mark.asyncio
    async def test_INVARIANT_password_hash_never_in_any_response(
        self, client, sample_document_in_db
    ):
        await client.post("/api/links", json={
            "document_id": str(sample_document_in_db.id),
            "password": "secret123",
        })
        for r in [
            await client.get(f"/api/links?document_id={sample_document_in_db.id}"),
            await client.get("/api/documents"),
        ]:
            assert "$2b$" not in str(r.json()), "BCRYPT HASH EXPOSED IN RESPONSE"
            assert "password_hash" not in str(r.json()), "PASSWORD HASH FIELD EXPOSED"

    @pytest.mark.asyncio
    async def test_INVARIANT_email_validation_is_case_insensitive(
        self, client, sample_document_in_db
    ):
        link_r = await client.post("/api/links", json={
            "document_id": str(sample_document_in_db.id),
            "allowed_emails": ["rahul@iit.ac.in"],
        })
        token = link_r.json()["token"]
        r = await client.post("/api/viewer/validate", json={
            "token": token,
            "email": "RAHUL@IIT.AC.IN",
        })
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_INVARIANT_viewer_email_never_stored_raw(
        self, client, sample_document_in_db
    ):
        """Viewer email in access_events must be masked, never the raw address."""
        link_r = await client.post("/api/links", json={
            "document_id": str(sample_document_in_db.id),
            "allowed_emails": ["viewer@example.com"],
        })
        token = link_r.json()["token"]

        r = await client.post("/api/viewer/validate", json={
            "token": token,
            "email": "viewer@example.com",
        })
        assert r.status_code == 200

        events_r = await client.get(
            "/api/analytics/events",
            params={"document_id": str(sample_document_in_db.id)},
        )
        assert events_r.status_code == 200
        events = events_r.json()["events"]
        email_events = [e for e in events if e.get("viewer_email")]
        assert email_events, "Expected at least one event with viewer_email"

        for e in email_events:
            stored = e["viewer_email"]
            # Full email must not appear
            assert stored != "viewer@example.com", "RAW VIEWER EMAIL STORED IN DB"
            # Must be in masked form: one char + *** @ domain
            local, domain = stored.split("@", 1)
            assert local.endswith("***"), f"Email not masked: {stored!r}"
            assert domain == "example.com", f"Domain corrupted: {stored!r}"

    @pytest.mark.asyncio
    async def test_INVARIANT_ip_never_stored_raw(self, client, active_link):
        await client.post("/api/viewer/validate", json={"token": active_link.token})
        r = await client.get(
            "/api/analytics/events",
            params={"document_id": str(active_link.document_id)},
        )
        for event in r.json()["events"]:
            ip = event.get("ip_hash", "")
            if ip:
                assert "." not in ip, f"RAW IP STORED: {ip}"
                assert ":" not in ip, f"RAW IPv6 STORED: {ip}"


class TestLinkLifecycle:

    @pytest.mark.asyncio
    async def test_full_link_lifecycle_create_use_revoke(
        self, client, sample_document_in_db
    ):
        # 1. Create
        link_r = await client.post("/api/links", json={
            "document_id": str(sample_document_in_db.id),
            "label": "Test lifecycle",
            "max_views": 5,
        })
        assert link_r.status_code == 201
        token = link_r.json()["token"]

        # 2. Validate (should succeed)
        val_r = await client.post("/api/viewer/validate", json={"token": token})
        assert val_r.status_code == 200
        session_id = val_r.json()["session_id"]

        # 3. Log viewer event (client-side events only; page_viewed is server-side)
        log_r = await client.post("/api/analytics/events", json={
            "token": token,
            "session_id": session_id,
            "event_type": "print_attempt",
            "page_number": 1,
        })
        assert log_r.status_code == 200
        assert log_r.json()["logged"] is True

        # 4. Revoke
        link_id = link_r.json()["id"]
        rev_r = await client.delete(f"/api/links/{link_id}")
        assert rev_r.status_code == 200
        assert rev_r.json()["revoked_at"] is not None

        # 5. Validate after revoke (must fail)
        val_r2 = await client.post("/api/viewer/validate", json={"token": token})
        assert val_r2.status_code == 410

    @pytest.mark.asyncio
    async def test_link_stats_appear_in_analytics(self, client, sample_document_in_db):
        link_r = await client.post("/api/links", json={
            "document_id": str(sample_document_in_db.id),
        })
        token = link_r.json()["token"]

        before = await client.get("/api/analytics/overview")
        views_before = before.json()["total_views_today"]

        await client.post("/api/viewer/validate", json={"token": token})

        after = await client.get("/api/analytics/overview")
        views_after = after.json()["total_views_today"]

        assert views_after == views_before + 1
