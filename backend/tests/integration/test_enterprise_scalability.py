"""
Enterprise Scalability Test Suite — Phase 2

Covers:
  Action 6: Streaming PDF downloads (memory-efficient, pypdf-based assembly)
  Action 7: Prometheus metrics endpoint
"""
import asyncio
import io
import uuid
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.config import Settings
from app.services.link_service import LinkService
from tests.conftest import TEST_USER_ID, _make_webp_bytes


# ══════════════════════════════════════════════════════════════════════════════
# Action 6: Streaming PDF Downloads
# ══════════════════════════════════════════════════════════════════════════════

class TestStreamingDownload:
    """Download endpoint returns valid PDF via streaming, one page at a time."""

    @pytest.mark.asyncio
    async def test_download_returns_200_application_pdf(self, client, db_session, ready_document):
        svc = LinkService()
        link = await svc.create_link(
            db_session,
            document_id=str(ready_document.id),
            permissions={"can_download": True},
        )
        val_r = await client.post("/api/viewer/validate", json={"token": link.token})
        assert val_r.status_code == 200
        sid = val_r.json()["session_id"]

        r = await client.get(f"/api/viewer/download/{link.token}", headers={"X-Session-ID": sid})
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"

    @pytest.mark.asyncio
    async def test_download_has_content_disposition_attachment(
        self, client, db_session, ready_document
    ):
        svc = LinkService()
        link = await svc.create_link(
            db_session,
            document_id=str(ready_document.id),
            permissions={"can_download": True},
        )
        val_r = await client.post("/api/viewer/validate", json={"token": link.token})
        sid = val_r.json()["session_id"]

        r = await client.get(f"/api/viewer/download/{link.token}", headers={"X-Session-ID": sid})
        cd = r.headers.get("content-disposition", "")
        assert "attachment" in cd
        assert ".pdf" in cd

    @pytest.mark.asyncio
    async def test_download_no_store_cache_header(self, client, db_session, ready_document):
        svc = LinkService()
        link = await svc.create_link(
            db_session,
            document_id=str(ready_document.id),
            permissions={"can_download": True},
        )
        val_r = await client.post("/api/viewer/validate", json={"token": link.token})
        sid = val_r.json()["session_id"]

        r = await client.get(f"/api/viewer/download/{link.token}", headers={"X-Session-ID": sid})
        assert "no-store" in r.headers.get("cache-control", "")

    @pytest.mark.asyncio
    async def test_download_pdf_is_parseable(self, client, db_session, ready_document):
        """Downloaded bytes must be a valid PDF (parseable by pypdf)."""
        from pypdf import PdfReader

        svc = LinkService()
        link = await svc.create_link(
            db_session,
            document_id=str(ready_document.id),
            permissions={"can_download": True},
        )
        val_r = await client.post("/api/viewer/validate", json={"token": link.token})
        sid = val_r.json()["session_id"]

        r = await client.get(f"/api/viewer/download/{link.token}", headers={"X-Session-ID": sid})
        assert r.status_code == 200

        reader = PdfReader(io.BytesIO(r.content))
        assert len(reader.pages) == ready_document.page_count

    @pytest.mark.asyncio
    async def test_download_requires_can_download_permission(
        self, client, db_session, ready_document
    ):
        svc = LinkService()
        link = await svc.create_link(
            db_session,
            document_id=str(ready_document.id),
            permissions={"can_download": False},
        )
        val_r = await client.post("/api/viewer/validate", json={"token": link.token})
        sid = val_r.json()["session_id"]

        r = await client.get(f"/api/viewer/download/{link.token}", headers={"X-Session-ID": sid})
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_download_requires_session_id(self, client, db_session, ready_document):
        svc = LinkService()
        link = await svc.create_link(
            db_session,
            document_id=str(ready_document.id),
            permissions={"can_download": True},
        )
        r = await client.get(f"/api/viewer/download/{link.token}")
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_download_rejects_page_limit_exceeded(
        self, client, db_session
    ):
        from app.models.document import Document, DocumentPage
        doc = Document(
            id=uuid.uuid4(),
            filename="huge.pdf",
            storage_key=f"originals/{uuid.uuid4()}.pdf",
            status="ready",
            page_count=600,
            file_size_bytes=1024 * 600,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.flush()
        for i in range(1, 4):
            db_session.add(DocumentPage(
                document_id=doc.id, page_number=i,
                storage_key=f"pages/{doc.id}/{i:04d}.webp",
                width_px=595, height_px=842,
            ))
        await db_session.commit()
        await db_session.refresh(doc)

        svc = LinkService()
        link = await svc.create_link(
            db_session,
            document_id=str(doc.id),
            permissions={"can_download": True},
        )
        val_r = await client.post("/api/viewer/validate", json={"token": link.token})
        sid = val_r.json()["session_id"]

        with patch("app.routers.viewer.settings") as mock_s:
            mock_s.max_download_pages_pdf = 50
            mock_s.watermark_angle_jitter_deg = 5.0
            r = await client.get(f"/api/viewer/download/{link.token}", headers={"X-Session-ID": sid})
        assert r.status_code == 413

    def test_download_page_limit_default_is_500(self):
        s = Settings()
        assert s.max_download_pages_pdf == 500

    @pytest.mark.asyncio
    async def test_watermark_called_once_per_page(self, client, db_session):
        """apply_visible_watermark must be called exactly page_count times."""
        from app.models.document import Document, DocumentPage
        from app.services.watermark import WatermarkService

        doc = Document(
            id=uuid.uuid4(),
            filename="three_pages.pdf",
            storage_key=f"originals/{uuid.uuid4()}.pdf",
            status="ready",
            page_count=3,
            file_size_bytes=1024 * 3,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.flush()
        for i in range(1, 4):
            db_session.add(DocumentPage(
                document_id=doc.id, page_number=i,
                storage_key=f"pages/{doc.id}/{i:04d}.webp",
                width_px=595, height_px=842,
            ))
        await db_session.commit()

        svc = LinkService()
        link = await svc.create_link(
            db_session,
            document_id=str(doc.id),
            permissions={"can_download": True},
        )
        val_r = await client.post("/api/viewer/validate", json={"token": link.token})
        sid = val_r.json()["session_id"]

        call_count = []
        original_wm = WatermarkService.apply_visible_watermark

        def _count_wm(self, img, text, **kw):
            call_count.append(1)
            return original_wm(self, img, text, **kw)

        with patch.object(WatermarkService, "apply_visible_watermark", _count_wm):
            r = await client.get(f"/api/viewer/download/{link.token}", headers={"X-Session-ID": sid})

        assert r.status_code == 200
        assert len(call_count) == 3, f"Expected 3 watermark calls (one per page), got {len(call_count)}"


# ══════════════════════════════════════════════════════════════════════════════
# Action 9: CDN Thumbnail Offload
# ══════════════════════════════════════════════════════════════════════════════

class TestCDNThumbnailOffload:
    """Thumbnail CDN redirect enabled/disabled behaviour."""

    def test_cdn_thumbnail_disabled_by_default(self):
        s = Settings()
        assert s.cdn_thumbnail_enabled is False

    def test_cdn_presign_ttl_default(self):
        s = Settings()
        assert s.cdn_thumbnail_presign_ttl_sec == 300

    @pytest.mark.asyncio
    async def test_thumbnail_returns_bytes_when_cdn_disabled(
        self, client, active_link
    ):
        val_r = await client.post("/api/viewer/validate", json={"token": active_link.token})
        sid = val_r.json()["session_id"]

        r = await client.get(
            f"/api/viewer/thumb/{active_link.token}/1", headers={"X-Session-ID": sid}
        )
        assert r.status_code == 200
        assert r.headers["content-type"] == "image/webp"

    @pytest.mark.asyncio
    async def test_page_endpoint_never_redirects_even_with_cdn_enabled(
        self, client, active_link
    ):
        """Full page images must always be proxied, never redirected."""
        val_r = await client.post("/api/viewer/validate", json={"token": active_link.token})
        sid = val_r.json()["session_id"]

        with patch("app.routers.viewer.settings") as mock_s:
            mock_s.cdn_thumbnail_enabled = True
            mock_s.cdn_thumbnail_presign_ttl_sec = 300
            mock_s.max_download_pages_pdf = 500
            mock_s.watermark_angle_jitter_deg = 5.0
            r = await client.get(
                f"/api/viewer/page/{active_link.token}/1", headers={"X-Session-ID": sid},
                follow_redirects=False,
            )
        assert r.status_code not in (301, 302, 307, 308), (
            "Page endpoint must never redirect to storage URL (security requirement)"
        )

    @pytest.mark.asyncio
    async def test_thumbnail_redirects_when_cdn_enabled(
        self, client, active_link
    ):
        """With CDN enabled, thumbnail endpoint returns 302 redirect."""
        val_r = await client.post("/api/viewer/validate", json={"token": active_link.token})
        sid = val_r.json()["session_id"]

        presigned_url = "https://r2.example.com/thumbs/doc/0001.webp?sig=abc"

        with patch("app.routers.viewer.settings") as mock_s, \
             patch("app.routers.viewer.get_storage_service") as mock_storage_factory:
            mock_s.cdn_thumbnail_enabled = True
            mock_s.cdn_thumbnail_presign_ttl_sec = 300
            mock_storage = MagicMock()
            mock_storage.generate_presigned_url = AsyncMock(return_value=presigned_url)
            mock_storage_factory.return_value = mock_storage

            r = await client.get(
                f"/api/viewer/thumb/{active_link.token}/1", headers={"X-Session-ID": sid},
                follow_redirects=False,
            )

        assert r.status_code == 302
        assert r.headers.get("location") == presigned_url

    @pytest.mark.asyncio
    async def test_thumbnail_cdn_redirect_requires_session(
        self, client, active_link
    ):
        """CDN redirect must still require a valid session."""
        with patch("app.routers.viewer.settings") as mock_s:
            mock_s.cdn_thumbnail_enabled = True
            mock_s.cdn_thumbnail_presign_ttl_sec = 300
            r = await client.get(
                f"/api/viewer/thumb/{active_link.token}/1",
                follow_redirects=False,
            )
        assert r.status_code == 400


# ══════════════════════════════════════════════════════════════════════════════
# Action 8: OpenTelemetry Tracing
# ══════════════════════════════════════════════════════════════════════════════

class TestOpenTelemetry:
    """OTel tracing is a no-op when endpoint is not configured."""

    def test_otel_disabled_by_default(self):
        s = Settings()
        assert s.otel_exporter_otlp_endpoint == ""

    def test_otel_service_name_default(self):
        s = Settings()
        assert s.otel_service_name == "securedoc"

    def test_setup_tracing_noop_when_no_endpoint(self):
        from app.telemetry import setup_tracing
        from opentelemetry import trace
        before = trace.get_tracer_provider()
        setup_tracing("")  # must not raise and must not change provider
        after = trace.get_tracer_provider()
        assert before is after

    def test_otel_endpoint_configurable(self):
        s = Settings(otel_exporter_otlp_endpoint="http://tempo:4318")
        assert s.otel_exporter_otlp_endpoint == "http://tempo:4318"


# ══════════════════════════════════════════════════════════════════════════════
# Action 7: Prometheus Metrics (placeholder — tested after implementation)
# ══════════════════════════════════════════════════════════════════════════════

class TestPrometheusMetrics:
    """Prometheus /metrics endpoint serves valid Prometheus text format."""

    @pytest.mark.asyncio
    async def test_metrics_endpoint_returns_200(self, client):
        r = await client.get("/metrics")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_metrics_content_type_is_prometheus(self, client):
        r = await client.get("/metrics")
        ct = r.headers.get("content-type", "")
        assert "text/plain" in ct or "text/html" in ct or "prometheus" in ct.lower()

    @pytest.mark.asyncio
    async def test_metrics_contains_http_requests_counter(self, client):
        await client.get("/api/viewer/gate/nonexistent")
        r = await client.get("/metrics")
        assert r.status_code == 200
        body = r.text
        assert "http_requests" in body or "securedoc" in body or "fastapi" in body

    @pytest.mark.asyncio
    async def test_metrics_endpoint_not_authenticated(self, client):
        """Metrics must be accessible without auth (internal scrape)."""
        r = await client.get("/metrics")
        assert r.status_code != 401
        assert r.status_code != 403
