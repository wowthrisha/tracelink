import pytest


class TestLinksEndpoint:

    @pytest.mark.asyncio
    async def test_create_link_returns_201_with_share_url(self, client, sample_document_in_db):
        r = await client.post("/api/links", json={"document_id": str(sample_document_in_db.id)})
        assert r.status_code == 201
        body = r.json()
        assert "share_url" in body
        assert len(body["token"]) == 64
        assert "/v/" in body["share_url"]

    @pytest.mark.asyncio
    async def test_create_link_response_never_returns_password_hash(self, client, sample_document_in_db):
        r = await client.post("/api/links", json={
            "document_id": str(sample_document_in_db.id),
            "password": "secret123"
        })
        body_str = str(r.json())
        assert "password_hash" not in body_str
        assert "$2b$" not in body_str
        assert "secret123" not in body_str

    @pytest.mark.asyncio
    async def test_get_links_shows_has_password_true(self, client, sample_document_in_db):
        await client.post("/api/links", json={
            "document_id": str(sample_document_in_db.id),
            "password": "secret"
        })
        r = await client.get(f"/api/links?document_id={sample_document_in_db.id}")
        link = r.json()["links"][0]
        assert link["has_password"] is True
        assert "password_hash" not in link

    @pytest.mark.asyncio
    async def test_revoke_link_sets_is_active_false(self, client, sample_link):
        r = await client.delete(f"/api/links/{sample_link.id}")
        assert r.status_code == 200
        assert r.json()["revoked_at"] is not None
        v = await client.post("/api/viewer/validate", json={"token": sample_link.token})
        assert v.status_code == 410

    @pytest.mark.asyncio
    async def test_patch_link_updates_label(self, client, sample_link):
        r = await client.patch(f"/api/links/{sample_link.id}", json={"label": "New Label"})
        assert r.status_code == 200
        assert r.json()["label"] == "New Label"

    @pytest.mark.asyncio
    async def test_patch_link_cannot_change_document_id(self, client, sample_link, other_document):
        r = await client.patch(
            f"/api/links/{sample_link.id}",
            json={"document_id": str(other_document.id)}
        )
        if r.status_code == 200:
            assert str(r.json().get("document_id", "")) != str(other_document.id)
        else:
            assert r.status_code == 400
