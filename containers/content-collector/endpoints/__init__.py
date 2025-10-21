"""
Content Womble Endpoints Package - Streaming Architecture

Pure functional streaming endpoints for content collection:
- trigger: Manual collection trigger for testing
- storage_queue: KEDA integration via Azure Storage Queue messages
"""

from .storage_queue_router import router as storage_queue_router
from .trigger import router as trigger_router

__all__ = [
    "trigger_router",  # Manual collection trigger (testing/debugging)
    "storage_queue_router",  # KEDA queue integration (production)
]
