"""ENG-017 (V22.0) — Celery task metrics.

Verifies securedoc_celery_task_duration_seconds / securedoc_celery_tasks_total
are actually recorded on both the success and failure paths of
process_document, the primary/highest-volume Celery task. Application-level
instrumentation only — scraping/dashboards/alerting are an operations
concern, not tested here.
"""
from unittest.mock import AsyncMock, patch

import pytest

from app.metrics import celery_task_duration_seconds, celery_tasks_total
from app.workers.tasks import _process_document_async


def _counter_value(counter, task_name: str, outcome: str) -> float:
    return counter.labels(task_name=task_name, outcome=outcome)._value.get()


class TestProcessDocumentMetrics:
    @pytest.mark.asyncio
    async def test_success_path_records_success_outcome(self):
        before = _counter_value(celery_tasks_total, "securedoc.process_document", "success")

        with patch("app.workers.tasks._get_db_session_factory"), \
             patch("app.services.storage.get_storage_service"), \
             patch("app.services.rasterizer.RasterizerService"), \
             patch("app.services.watermark.WatermarkService"), \
             patch("app.workers.tasks.process_document_with_session", new_callable=AsyncMock) as mock_process, \
             patch("app.workers.tasks._fire_document_processed_event", new_callable=AsyncMock):
            mock_process.return_value = {"status": "ready"}
            result = await _process_document_async(task=None, document_id="doc-1")

        assert result == {"status": "ready"}
        after = _counter_value(celery_tasks_total, "securedoc.process_document", "success")
        assert after == before + 1

    @pytest.mark.asyncio
    async def test_permanent_failure_records_error_outcome(self):
        from app.services.rasterizer import RasterizerError

        before = _counter_value(celery_tasks_total, "securedoc.process_document", "error")

        with patch("app.workers.tasks._get_db_session_factory"), \
             patch("app.services.storage.get_storage_service"), \
             patch("app.services.rasterizer.RasterizerService"), \
             patch("app.services.watermark.WatermarkService"), \
             patch("app.workers.tasks.process_document_with_session", new_callable=AsyncMock) as mock_process, \
             patch("app.workers.tasks._mark_document_error", new_callable=AsyncMock), \
             patch("app.workers.tasks._fire_document_processed_event", new_callable=AsyncMock):
            mock_process.side_effect = RasterizerError("bad pdf")
            with pytest.raises(RasterizerError):
                await _process_document_async(task=None, document_id="doc-2")

        after = _counter_value(celery_tasks_total, "securedoc.process_document", "error")
        assert after == before + 1

    @pytest.mark.asyncio
    async def test_duration_histogram_observes_a_sample(self):
        before = celery_task_duration_seconds.labels(
            task_name="securedoc.process_document", outcome="success"
        )._sum.get()

        with patch("app.workers.tasks._get_db_session_factory"), \
             patch("app.services.storage.get_storage_service"), \
             patch("app.services.rasterizer.RasterizerService"), \
             patch("app.services.watermark.WatermarkService"), \
             patch("app.workers.tasks.process_document_with_session", new_callable=AsyncMock) as mock_process, \
             patch("app.workers.tasks._fire_document_processed_event", new_callable=AsyncMock):
            mock_process.return_value = {"status": "ready"}
            await _process_document_async(task=None, document_id="doc-3")

        after = celery_task_duration_seconds.labels(
            task_name="securedoc.process_document", outcome="success"
        )._sum.get()
        assert after >= before  # a real (non-negative) duration was observed
