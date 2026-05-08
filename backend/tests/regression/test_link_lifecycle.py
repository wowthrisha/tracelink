"""Additional link lifecycle regression tests."""
import pytest


class TestLinkLifecycleAdditional:

    @pytest.mark.asyncio
    async def test_max_views_exactly_at_limit_still_succeeds(
        self, client, sample_document_in_db
    ):
        link_r = await client.post("/api/links", json={
            "document_id": str(sample_document_in_db.id),
            "max_views": 1,
        })
        token = link_r.json()["token"]
        r = await client.post("/api/viewer/validate", json={"token": token})
        assert r.status_code == 200
        r2 = await client.post("/api/viewer/validate", json={"token": token})
        assert r2.status_code == 410

    @pytest.mark.asyncio
    async def test_max_views_exhausted_link_is_inactive_in_list(
        self, client, sample_document_in_db
    ):
        """GET /api/links must show is_active=False when max_views is exhausted."""
        link_r = await client.post("/api/links", json={
            "document_id": str(sample_document_in_db.id),
            "max_views": 1,
        })
        link_id = link_r.json()["id"]
        token = link_r.json()["token"]
        # Use the one allowed view
        await client.post("/api/viewer/validate", json={"token": token})
        # List should now show is_active=False
        list_r = await client.get(f"/api/links?document_id={sample_document_in_db.id}")
        link_summary = next(l for l in list_r.json()["links"] if l["id"] == link_id)
        assert link_summary["is_active"] is False

    @pytest.mark.asyncio
    async def test_revoked_link_cannot_be_unrevoked_via_patch(
        self, client, sample_document_in_db
    ):
        link_r = await client.post("/api/links", json={
            "document_id": str(sample_document_in_db.id),
        })
        link_id = link_r.json()["id"]
        token = link_r.json()["token"]

        await client.delete(f"/api/links/{link_id}")

        # Try to patch revoked_at to None — should not re-enable link
        r = await client.patch(f"/api/links/{link_id}", json={"label": "patched"})
        # Link should still be revoked after patch
        v = await client.post("/api/viewer/validate", json={"token": token})
        assert v.status_code == 410
