"""
Content Processor Endpoints Package

Contains all FastAPI router endpoints for the content processor service.
"""

from .diagnostics import router as diagnostics_router
from .servicebus_router import router as servicebus_router

__all__ = [
    "diagnostics_router",
    "servicebus_router",
]
