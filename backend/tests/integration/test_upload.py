import uuid
import pytest

from app.models.document import Document
from tests.conftest import TEST_USER_B_ID


class TestUploadEndpoint:

    @pytest.mark.asyncio
    async def test_upload_valid_pdf_returns_202(self, client, sample_pdf_bytes):
        files = {"file": ("test.pdf", sample_pdf_bytes, "application/pdf")}
        r = await client.post("/api/documents/upload", files=files)
        assert r.status_code == 202
        body = r.json()
        assert "id" in body
        assert body["status"] == "uploaded"

    @pytest.mark.asyncio
    async def test_upload_invalid_file_type_returns_400(self, client):
        # JPEG is not supported — must be rejected
        files = {"file": ("photo.jpg", b"\xff\xd8\xff\xe0fake-jpeg", "image/jpeg")}
        r = await client.post("/api/documents/upload", files=files)
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_upload_docx_now_supported(self, client):
        # DOCX is now supported — must be accepted with valid ZIP magic bytes
        files = {"file": ("report.docx", b"PK\x03\x04" + b"\x00" * 30,
                          "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        r = await client.post("/api/documents/upload", files=files)
        assert r.status_code == 202

    @pytest.mark.asyncio
    async def test_upload_txt_returns_202(self, client):
        files = {"file": ("notes.txt", b"Hello\nWorld\n", "text/plain")}
        r = await client.post("/api/documents/upload", files=files)
        assert r.status_code == 202
        body = r.json()
        assert body["status"] == "uploaded"

    @pytest.mark.asyncio
    async def test_upload_non_pdf_bytes_returns_400(self, client, invalid_bytes):
        files = {"file": ("fake.pdf", invalid_bytes, "application/pdf")}
        r = await client.post("/api/documents/upload", files=files)
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_upload_response_never_contains_storage_key(self, client, sample_pdf_bytes):
        files = {"file": ("test.pdf", sample_pdf_bytes, "application/pdf")}
        r = await client.post("/api/documents/upload", files=files)
        body = r.json()
        assert "storage_key" not in body
        assert "originals/" not in str(body)

    @pytest.mark.asyncio
    async def test_get_documents_returns_list(self, client, sample_pdf_bytes):
        files = {"file": ("test.pdf", sample_pdf_bytes, "application/pdf")}
        await client.post("/api/documents/upload", files=files)
        r = await client.get("/api/documents")
        assert r.status_code == 200
        assert "documents" in r.json()
        assert len(r.json()["documents"]) == 1

    @pytest.mark.asyncio
    async def test_get_documents_never_returns_storage_keys(self, client, sample_pdf_bytes):
        files = {"file": ("test.pdf", sample_pdf_bytes, "application/pdf")}
        await client.post("/api/documents/upload", files=files)
        r = await client.get("/api/documents")
        body_str = str(r.json())
        assert "originals/" not in body_str
        assert "storage_key" not in body_str

    @pytest.mark.asyncio
    async def test_delete_document_returns_204(self, client, sample_document_in_db):
        r = await client.delete(f"/api/documents/{sample_document_in_db.id}")
        assert r.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_document_removes_from_list(self, client, db_session, sample_pdf_bytes):
        files = {"file": ("test.pdf", sample_pdf_bytes, "application/pdf")}
        upload_r = await client.post("/api/documents/upload", files=files)
        doc_id = upload_r.json()["id"]
        await client.delete(f"/api/documents/{doc_id}")
        r = await client.get("/api/documents")
        assert len(r.json()["documents"]) == 0

    @pytest.mark.asyncio
    async def test_status_polling_endpoint(self, client, sample_document_in_db):
        r = await client.get(f"/api/documents/{sample_document_in_db.id}/status")
        assert r.status_code == 200
        assert r.json()["status"] in ("uploaded", "processing", "ready", "error")


class TestDocumentOwnership:

    async def _create_user_b_doc(self, db_session) -> Document:
        doc = Document(
            id=uuid.uuid4(),
            filename="user_b.pdf",
            storage_key=f"originals/{uuid.uuid4()}.pdf",
            status="ready",
            page_count=1,
            file_size_bytes=512,
            user_id=uuid.UUID(TEST_USER_B_ID),
        )
        db_session.add(doc)
        await db_session.commit()
        await db_session.refresh(doc)
        return doc

    @pytest.mark.asyncio
    async def test_user_a_cannot_see_user_b_document_in_list(self, client, db_session):
        doc_b = await self._create_user_b_doc(db_session)
        r = await client.get("/api/documents")
        assert r.status_code == 200
        listed_ids = [d["id"] for d in r.json()["documents"]]
        assert str(doc_b.id) not in listed_ids

    @pytest.mark.asyncio
    async def test_user_a_cannot_get_user_b_document_by_id(self, client, db_session):
        doc_b = await self._create_user_b_doc(db_session)
        r = await client.get(f"/api/documents/{doc_b.id}")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_user_a_cannot_poll_status_of_user_b_document(self, client, db_session):
        doc_b = await self._create_user_b_doc(db_session)
        r = await client.get(f"/api/documents/{doc_b.id}/status")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_user_a_cannot_delete_user_b_document(self, client, db_session):
        doc_b = await self._create_user_b_doc(db_session)
        r = await client.delete(f"/api/documents/{doc_b.id}")
        assert r.status_code == 404  # must not leak document existence

    @pytest.mark.asyncio
    async def test_upload_sets_user_id_on_document(self, client, db_session, sample_pdf_bytes):
        files = {"file": ("test.pdf", sample_pdf_bytes, "application/pdf")}
        r = await client.post("/api/documents/upload", files=files)
        assert r.status_code == 202
        doc_id = uuid.UUID(r.json()["id"])
        from sqlalchemy import select
        result = await db_session.execute(
            select(Document).where(Document.id == doc_id)
        )
        doc = result.scalar_one()
        from tests.conftest import TEST_USER_ID
        assert doc.user_id == uuid.UUID(TEST_USER_ID)

    @pytest.mark.asyncio
    async def test_user_b_document_is_preserved_in_db_after_user_a_list(
        self, client, db_session
    ):
        # Verify user A's filtered list does NOT delete user B's doc from the DB
        doc_b = await self._create_user_b_doc(db_session)
        await client.get("/api/documents")
        await db_session.refresh(doc_b)
        assert doc_b.id is not None  # still exists
