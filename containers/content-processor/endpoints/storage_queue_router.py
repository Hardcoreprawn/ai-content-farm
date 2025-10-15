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
        logger.info(
            f"Processing queue message {message.message_id} - "
            f"operation: {message.operation} from {message.service_name}"
        )
        logger.info(f"Message payload: {message.payload}")

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

        elif message.operation == "process_topic":
            # Single-topic processing path: individual topic → processed article → markdown trigger
            payload = message.payload

            # Extract topic metadata from payload
            topic_id = payload.get("topic_id")
            title = payload.get("title")

            if not topic_id or not title:
                logger.error(
                    f"Missing required fields in process_topic payload: {payload}"
                )
                return {
                    "status": "error",
                    "error": "Missing required fields: topic_id and title",
                    "message_id": message.message_id,
                }

            # Get processor context
            context = await get_processor_context()

            # Convert payload to TopicMetadata
            from models import TopicMetadata

            # Parse collected_at to datetime if present
            collected_at_raw = payload.get("collected_at")
            if collected_at_raw:
                if isinstance(collected_at_raw, datetime):
                    collected_at = collected_at_raw
                else:
                    try:
                        # Handle ISO format with Z suffix
                        collected_at = datetime.fromisoformat(
                            collected_at_raw.replace("Z", "+00:00")
                        )
                    except Exception:
                        collected_at = datetime.now(timezone.utc)
            else:
                collected_at = datetime.now(timezone.utc)

            topic_metadata = TopicMetadata(
                topic_id=topic_id,
                title=title,
                source=payload.get("source", "unknown"),
                url=payload.get("url"),
                subreddit=payload.get("subreddit"),
                upvotes=payload.get("upvotes"),
                comments=payload.get("comments"),
                collected_at=collected_at,
                priority_score=payload.get("priority_score", 0.5),
            )

            logger.info(
                f"Processing single topic: '{title}' (ID: {topic_id}, source: {topic_metadata.source})"
            )

            # Import the single-topic processor
            from core.processor_operations import _process_single_topic

            # Process the single topic
            result = await _process_single_topic(context, topic_metadata)

            if result:
                logger.info(
                    f"Successfully processed topic '{title}': article_id={result.get('article_id')}, "
                    f"cost=${result.get('cost', 0):.4f}"
                )
                return {
                    "status": "success",
                    "operation": "topic_processed",
                    "result": result,
                    "message_id": message.message_id,
                }
            else:
                logger.info(f"Topic '{title}' was skipped (likely already processed)")
                return {
                    "status": "skipped",
                    "operation": "topic_already_processed",
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
