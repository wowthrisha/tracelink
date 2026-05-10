"""Multi-user group ownership isolation tests.

Guarantees:
  1. User A cannot see user B's groups.
  2. User A cannot modify or delete user B's groups.
  3. User A cannot assign documents to user B's groups.
  4. Groups created by a user belong to that user only.
"""
import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch

from app.auth import get_current_user
from app.database import get_db
from app.main import app
from app.models.group import DocumentGroup
from app.models.document import Document
from tests.conftest import TEST_USER_ID, TEST_USER_B_ID


# ── fixtures ───────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client_b(db_session):
    """Client authenticated as user B."""
    async def override_db():
        yield db_session

    def override_user_b():
        return {"user_id": TEST_USER_B_ID, "email": "userb@example.com", "role": "authenticated"}

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user_b

    with patch("app.services.storage.StorageService.upload_file", new_callable=AsyncMock), \
         patch("app.services.storage.StorageService.generate_presigned_url", new_callable=AsyncMock), \
         patch("app.services.storage.StorageService.download_bytes", new_callable=AsyncMock), \
         patch("app.services.storage.StorageService.delete_file", new_callable=AsyncMock), \
         patch("app.services.storage.StorageService.list_keys_with_prefix", new_callable=AsyncMock), \
         patch("app.workers.tasks.process_document.delay") as mock_celery:
        mock_celery.return_value = MagicMock(id="fake-task-id")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c

    app.dependency_overrides.clear()


async def _make_group(db_session, user_id: str, name: str = "My Group") -> DocumentGroup:
    g = DocumentGroup(
        id=uuid.uuid4(),
        user_id=uuid.UUID(user_id),
        name=name,
        color="#6366f1",
    )
    db_session.add(g)
    await db_session.commit()
    await db_session.refresh(g)
    return g


async def _make_doc(db_session, user_id: str) -> Document:
    doc = Document(
        id=uuid.uuid4(),
        filename="test.pdf",
        storage_key=f"originals/{uuid.uuid4()}.pdf",
        status="ready",
        page_count=1,
        file_size_bytes=512,
        user_id=uuid.UUID(user_id),
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)
    return doc


# ══════════════════════════════════════════════════════════════════════════
# 1. VISIBILITY ISOLATION
# ══════════════════════════════════════════════════════════════════════════

class TestGroupVisibilityIsolation:
    """User A must never see user B's groups."""

    @pytest.mark.asyncio
    async def test_user_a_cannot_see_user_b_groups(self, client, db_session):
        group_b = await _make_group(db_session, TEST_USER_B_ID, "B's Group")

        r = await client.get("/api/groups")
        assert r.status_code == 200
        group_ids = [g["id"] for g in r.json()["groups"]]
        assert str(group_b.id) not in group_ids

    @pytest.mark.asyncio
    async def test_user_a_cannot_get_user_b_group_by_id(self, client, db_session):
        group_b = await _make_group(db_session, TEST_USER_B_ID)

        r = await client.get(f"/api/groups/{group_b.id}")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_user_b_cannot_see_user_a_groups(self, client_b, db_session):
        group_a = await _make_group(db_session, TEST_USER_ID, "A's Group")

        r = await client_b.get("/api/groups")
        assert r.status_code == 200
        group_ids = [g["id"] for g in r.json()["groups"]]
        assert str(group_a.id) not in group_ids

    @pytest.mark.asyncio
    async def test_user_a_sees_own_groups_not_b(self, client, db_session):
        group_a = await _make_group(db_session, TEST_USER_ID, "Group A Unique")
        group_b = await _make_group(db_session, TEST_USER_B_ID, "Group B Unique")

        r_a = await client.get("/api/groups")
        ids_a = [g["id"] for g in r_a.json()["groups"]]
        assert str(group_a.id) in ids_a
        assert str(group_b.id) not in ids_a

    @pytest.mark.asyncio
    async def test_user_b_sees_own_groups_not_a(self, client_b, db_session):
        group_a = await _make_group(db_session, TEST_USER_ID, "Group A Only")
        group_b = await _make_group(db_session, TEST_USER_B_ID, "Group B Only")

        r_b = await client_b.get("/api/groups")
        ids_b = [g["id"] for g in r_b.json()["groups"]]
        assert str(group_b.id) in ids_b
        assert str(group_a.id) not in ids_b


# ══════════════════════════════════════════════════════════════════════════
# 2. MUTATION ISOLATION
# ══════════════════════════════════════════════════════════════════════════

class TestGroupMutationIsolation:
    """User A must not mutate user B's groups."""

    @pytest.mark.asyncio
    async def test_user_a_cannot_rename_user_b_group(self, client, db_session):
        group_b = await _make_group(db_session, TEST_USER_B_ID)

        r = await client.patch(
            f"/api/groups/{group_b.id}", json={"name": "Hijacked"}
        )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_user_a_cannot_delete_user_b_group(self, client, db_session):
        group_b = await _make_group(db_session, TEST_USER_B_ID)

        r = await client.delete(f"/api/groups/{group_b.id}")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_user_a_cannot_assign_docs_to_user_b_group(self, client, db_session):
        group_b = await _make_group(db_session, TEST_USER_B_ID)
        doc_a = await _make_doc(db_session, TEST_USER_ID)

        r = await client.put(
            f"/api/groups/{group_b.id}/documents",
            json={"document_ids": [str(doc_a.id)]},
        )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_user_a_cannot_remove_doc_from_user_b_group(self, client, db_session):
        group_b = await _make_group(db_session, TEST_USER_B_ID)
        doc_b = await _make_doc(db_session, TEST_USER_B_ID)
        # Assign doc_b to group_b directly
        doc_b.group_id = group_b.id
        await db_session.commit()

        r = await client.delete(f"/api/groups/{group_b.id}/documents/{doc_b.id}")
        # group belongs to B — A should get 404 on group lookup
        assert r.status_code == 404


# ══════════════════════════════════════════════════════════════════════════
# 3. GROUP CREATION IS USER-SCOPED
# ══════════════════════════════════════════════════════════════════════════

class TestGroupCreationOwnership:
    """Created groups must belong to the authenticated user."""

    @pytest.mark.asyncio
    async def test_group_is_owned_by_creator(self, client, db_session):
        r = await client.post("/api/groups", json={"name": "My Group"})
        assert r.status_code == 201

        group_id = uuid.UUID(r.json()["id"])
        from sqlalchemy import select
        result = await db_session.execute(
            select(DocumentGroup).where(DocumentGroup.id == group_id)
        )
        group = result.scalar_one_or_none()
        assert group is not None
        assert group.user_id == uuid.UUID(TEST_USER_ID)

    @pytest.mark.asyncio
    async def test_two_users_can_have_same_group_name(self, client, db_session):
        """Name uniqueness is per-user, not global.
        Create user B's group directly in DB; user A should still be able to create same name.
        """
        # User B has "Shared Name" in DB
        await _make_group(db_session, TEST_USER_B_ID, "Shared Name")

        # User A (client) should also be able to create "Shared Name" — different user_id
        r_a = await client.post("/api/groups", json={"name": "Shared Name"})
        assert r_a.status_code == 201

    @pytest.mark.asyncio
    async def test_same_user_cannot_duplicate_group_name(self, client, db_session):
        await client.post("/api/groups", json={"name": "Unique"})
        r = await client.post("/api/groups", json={"name": "Unique"})
        assert r.status_code == 409


# ══════════════════════════════════════════════════════════════════════════
# 4. CROSS-USER DOCUMENT ASSIGNMENT TO OWN GROUP
# ══════════════════════════════════════════════════════════════════════════

class TestGroupDocumentAssignment:
    """Cannot assign another user's doc to your own group."""

    @pytest.mark.asyncio
    async def test_cannot_assign_user_b_doc_to_user_a_group(self, client, db_session):
        group_a = await _make_group(db_session, TEST_USER_ID, "A Group")
        doc_b = await _make_doc(db_session, TEST_USER_B_ID)

        r = await client.put(
            f"/api/groups/{group_a.id}/documents",
            json={"document_ids": [str(doc_b.id)]},
        )
        assert r.status_code == 200
        # assigned count must be 0 — B's doc is invisible to A's group assignment
        assert r.json()["assigned"] == 0
