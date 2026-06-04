"""
Document adapter registry.

Usage::

    from app.services.adapters import get_adapter, allowed_content_types

    adapter = get_adapter("pdf")
    adapter.viewer_mode           # "image"
    adapter.supports_thumbnails() # True
    await adapter.process(...)
"""
from app.services.adapters.registry import (  # noqa: F401
    get_adapter,
    all_adapters,
    allowed_content_types,
    register,
)
