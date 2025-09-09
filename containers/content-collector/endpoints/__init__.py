"""
Content Womble Endpoints Package

Modular endpoint organization following REST best practices.
"""

from .collections import router as collections_router
from .diagnostics import router as diagnostics_router
from .discoveries import router as discoveries_router
from .servicebus_router import router as servicebus_router
from .sources import router as sources_router

__all__ = [
    "collections_router",
    "discoveries_router",
    "sources_router",
    "diagnostics_router",
    "servicebus_router",
]
