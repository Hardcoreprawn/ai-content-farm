"""
Storage Queue Message Handler for Content Processor

Pure functional implementation for processing queue messages.
No classes - uses functional processor API (October 2025 refactor).
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict

# Import functional processor API from core module
from core.processor import cleanup_processor, initialize_processor
from core.processor_operations import process_collection_file
from fastapi import APIRouter

from libs.queue_client import QueueMessageModel

# Configuration
MARKDOWN_QUEUE_NAME = os.getenv("MARKDOWN_QUEUE_NAME", "markdown-generation-requests")

logger = logging.getLogger(__name__)

# Create FastAPI router
router = APIRouter(prefix="/storage-queue", tags=["Storage Queue"])


# ============================================================================
# Pure Functional Queue Message Handler
# ============================================================================

# Module-level processor context (reused across messages in same container lifecycle)
_processor_context = None


async def get_processor_context():
    """Get or create processor context (module-level singleton)."""
    global _processor_context
    if _processor_context is None:
        _processor_context = await initialize_processor()
        logger.info(f"Processor context initialized: {_processor_context.processor_id}")
    return _processor_context


async def process_storage_queue_message(message: QueueMessageModel) -> Dict[str, Any]:
    """
    Process a single Storage Queue message using functional API.

    Core processing flow (the pattern that was working):
    1. Receive queue message with blob_path
    2. Download and validate collection blob
    3. Process each topic (OpenAI generation)
    4. Write processed articles to processed-content blob
    5. Send markdown trigger message to markdown-generation-requests queue
    6. Return success (caller deletes message from queue)
    7. Check for next message
    8. Wait gracefully if queue empty, then shutdown (KEDA scales down)

    Args:
        message: Storage Queue message with operation and payload

    Returns:
        Dict with status, operation, result, message_id
    """
    try:
        logger.debug(
            f"Processing queue message {message.message_id} - "
            f"operation: {message.operation} from {message.service_name}"
        )
        logger.debug(f"Message payload: {message.payload}")

        if message.operation == "process":
            # Main processing path: collection blob → processed articles → markdown trigger
            payload = message.payload

            # Validate required field
            blob_path = payload.get("blob_path")
            if not blob_path:
                logger.error("No blob_path in queue message payload")
                return {
                    "status": "error",
                    "error": "Missing required field: blob_path",
                    "message": "Queue messages must include blob_path",
                }

            # Get processor context (creates once, reuses for subsequent messages)
            context = await get_processor_context()

            # Process the collection file using functional API
            logger.debug(f"Processing collection from queue: {blob_path}")

            # Call functional processor - no class needed!
            result = await process_collection_file(
                context=context,
                blob_path=blob_path,
            )

            logger.info(
                f"Processed {blob_path}: {result.topics_processed} topics, "
                f"{result.articles_generated} articles, ${result.total_cost:.2f}"
            )

            return {
                "status": "success",
                "operation": "processing_completed",
                "result": {
                    "topics_processed": result.topics_processed,
                    "articles_generated": result.articles_generated,
                    "total_cost": result.total_cost,
                    "processing_time": result.processing_time,
                },
                "message_id": message.message_id,
            }

        else:
            logger.warning(f"Unknown operation: {message.operation}")
            return {
                "status": "ignored",
                "operation": message.operation,
                "reason": "Unknown operation type",
                "message_id": message.message_id,
            }

    except Exception as e:
        logger.error(f"Error processing Storage Queue message: {e}", exc_info=True)
        return {
            "status": "error",
            "operation": message.operation,
            "error": str(e),
            "message_id": message.message_id,
        }


# FastAPI endpoints (optional - for HTTP debugging)
@router.get("/health")
async def storage_queue_health() -> Dict[str, Any]:
    """Health check for Storage Queue integration."""
    return {
        "status": "healthy",
        "message": "Storage queue handler ready",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "content-processor",
    }
