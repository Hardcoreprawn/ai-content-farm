"""
Content Processor Endpoints Package

Contains all FastAPI router endpoints for the content processor service.
"""

from .servicebus_router import router as servicebus_router

__all__ = [
    "servicebus_router",
]
