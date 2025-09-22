"""
Content Womble Endpoints Package

Modular endpoint organization following REST best practices.
Storage Queue integration replaces Service Bus for Container Apps compatibility.
"""

from .collections import router as collections_router
from .diagnostics import router as diagnostics_router
from .discoveries import router as discoveries_router
from .sources import router as sources_router
from .storage_queue_router import router as storage_queue_router
from .templates import router as templates_router

__all__ = [
    "collections_router",
    "discoveries_router",
    "sources_router",
    "diagnostics_router",
    "storage_queue_router",
    "templates_router",
]
