"""
Content Processor Endpoints Package

Contains all FastAPI router endpoints for the content processor service.
"""

from .processing import router as processing_router
from .storage_queue_router import router as storage_queue_router

__all__ = [
    "processing_router",
    "storage_queue_router",
]
