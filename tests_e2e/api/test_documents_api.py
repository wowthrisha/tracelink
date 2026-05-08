"""
API contract tests for /api/documents/*
Runs against the live stack — no mocks.

API shapes:
  POST /api/documents/upload → 202 {id, filename, status, message}
  GET  /api/documents        → 200 {"documents": [{id, filename, status, page_count,
                                     file_size_bytes, created_at, share_link_count, total_views}]}
  GET  /api/documents/{id}/status → 200 {status, page_count, error_message}
  DELETE /api/documents/{id} → 204
"""
import pytest
import httpx
from conftest import upload_pdf, make_minimal_pdf

pytestmark = pytest.mark.api


class TestDocumentsUpload:

    def test_upload_valid_pdf_returns_202(self, api_client, minimal_pdf_bytes):
        r = api_client.post(
            "/api/documents/upload",
            files={"file": ("valid.pdf", minimal_pdf_bytes, "application/pdf")},
            data={"filename": "valid.pdf"},
        )
        assert r.status_code == 202

    def test_upload_response_has_required_fields(self, api_client, minimal_pdf_bytes):
        r = api_client.post(
            "/api/documents/upload",
            files={"file": ("check.pdf", minimal_pdf_bytes, "application/pdf")},
            data={"filename": "check.pdf"},
        )
        body = r.json()
        assert "id" in body
        assert "status" in body
        assert "filename" in body
        assert body["status"] in ("uploaded", "processing", "ready")

    def test_upload_non_pdf_returns_400(self, api_client):
        r = api_client.post(
            "/api/documents/upload",
            files={"file": ("bad.txt", b"hello world", "text/plain")},
            data={"filename": "bad.txt"},
        )
        assert r.status_code in (400, 422)

    def test_upload_fake_pdf_extension_returns_400(self, api_client):
        """File with .pdf extension but wrong magic bytes."""
        r = api_client.post(
            "/api/documents/upload",
            files={"file": ("fake.pdf", b"not a pdf at all", "application/pdf")},
            data={"filename": "fake.pdf"},
        )
        assert r.status_code == 400

    def test_upload_response_never_exposes_storage_key(self, api_client, minimal_pdf_bytes):
        r = api_client.post(
            "/api/documents/upload",
            files={"file": ("nokey.pdf", minimal_pdf_bytes, "application/pdf")},
            data={"filename": "nokey.pdf"},
        )
        body = r.json()
        assert "storage_key" not in body

    def test_upload_assigns_unique_id(self, api_client, minimal_pdf_bytes):
        ids = set()
        for _ in range(3):
            r = api_client.post(
                "/api/documents/upload",
                files={"file": ("u.pdf", minimal_pdf_bytes, "application/pdf")},
                data={"filename": "u.pdf"},
            )
            ids.add(r.json()["id"])
        assert len(ids) == 3


class TestDocumentsList:

    def test_list_returns_200(self, api_client):
        r = api_client.get("/api/documents")
        assert r.status_code == 200

    def test_list_response_has_documents_key(self, api_client):
        r = api_client.get("/api/documents")
        body = r.json()
        assert "documents" in body
        assert isinstance(body["documents"], list)

    def test_list_never_exposes_storage_key(self, api_client, minimal_pdf_bytes):
        upload_pdf(api_client, minimal_pdf_bytes)
        r = api_client.get("/api/documents")
        for doc in r.json()["documents"]:
            assert "storage_key" not in doc

    def test_list_items_have_required_fields(self, api_client, minimal_pdf_bytes):
        upload_pdf(api_client, minimal_pdf_bytes)
        r = api_client.get("/api/documents")
        for doc in r.json()["documents"]:
            assert "id" in doc
            assert "filename" in doc
            assert "status" in doc
            assert "share_link_count" in doc
            assert "total_views" in doc


class TestDocumentStatus:

    def test_status_returns_200(self, api_client, ready_doc):
        r = api_client.get(f"/api/documents/{ready_doc['id']}/status")
        assert r.status_code == 200

    def test_status_has_required_fields(self, api_client, ready_doc):
        r = api_client.get(f"/api/documents/{ready_doc['id']}/status")
        body = r.json()
        assert "status" in body
        assert "page_count" in body

    def test_status_invalid_id_returns_404(self, api_client):
        fake_id = "00000000-0000-0000-0000-000000000000"
        r = api_client.get(f"/api/documents/{fake_id}/status")
        assert r.status_code == 404

    def test_status_never_exposes_storage_key(self, api_client, ready_doc):
        r = api_client.get(f"/api/documents/{ready_doc['id']}/status")
        body = r.json()
        assert "storage_key" not in body


class TestDocumentDelete:

    def test_delete_returns_204(self, api_client, minimal_pdf_bytes):
        body = upload_pdf(api_client, minimal_pdf_bytes)
        doc_id = body["id"]
        r = api_client.delete(f"/api/documents/{doc_id}")
        assert r.status_code == 204

    def test_deleted_document_not_in_list(self, api_client, minimal_pdf_bytes):
        body = upload_pdf(api_client, minimal_pdf_bytes)
        doc_id = body["id"]
        api_client.delete(f"/api/documents/{doc_id}")
        r = api_client.get("/api/documents")
        ids = [d["id"] for d in r.json()["documents"]]
        assert doc_id not in ids

    def test_delete_nonexistent_returns_404(self, api_client):
        fake_id = "00000000-0000-0000-0000-000000000099"
        r = api_client.delete(f"/api/documents/{fake_id}")
        assert r.status_code == 404
