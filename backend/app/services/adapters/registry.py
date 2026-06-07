"""Adapter registry — maps file_type strings to DocumentAdapter instances."""
from __future__ import annotations

from app.services.adapters.base import DocumentAdapter

_REGISTRY: dict[str, DocumentAdapter] = {}


def register(adapter: DocumentAdapter) -> None:
    """Register an adapter by its file_type."""
    _REGISTRY[adapter.file_type] = adapter


def get_adapter(file_type: str) -> DocumentAdapter:
    """
    Return the adapter for *file_type*.

    Falls back to the PDF adapter for unknown types, preserving the
    pre-refactor 'else → PDF pipeline' default behaviour.
    """
    return _REGISTRY.get(file_type) or _REGISTRY["pdf"]


def all_adapters() -> list[DocumentAdapter]:
    """Return all registered adapters in registration order."""
    return list(_REGISTRY.values())


def allowed_content_types() -> frozenset:
    """
    Return the union of upload_mime_types() across all registered adapters.

    Does not include 'application/octet-stream' — callers add that separately
    as a browser pass-through for content types that cannot be determined.
    """
    return frozenset(
        ct for adapter in _REGISTRY.values() for ct in adapter.upload_mime_types()
    )


# ── Built-in registrations ─────────────────────────────────────────────────
# Called once at import time; idempotent if re-imported.

def _bootstrap() -> None:
    from app.services.adapters.pdf import PDFAdapter
    from app.services.adapters.text import TXTAdapter, MDAdapter, LOGAdapter
    from app.services.adapters.word import DOCXAdapter, DOCAdapter
    from app.services.adapters.presentation import PPTXAdapter
    from app.services.adapters.spreadsheet import XLSXAdapter

    for adapter in (
        PDFAdapter(),
        TXTAdapter(),
        MDAdapter(),
        LOGAdapter(),
        DOCXAdapter(),
        DOCAdapter(),
        PPTXAdapter(),
        XLSXAdapter(),
    ):
        register(adapter)


_bootstrap()
