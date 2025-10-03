"""
Storage Queue Endpoints for Content Processor

Implements Storage Queue message processing for content processing requests.
Uses unified queue interface and existing processor functionality.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from libs.queue_client import (
    QueueMessageModel,
    get_queue_client,
    process_queue_messages,
    send_wake_up_message,
)

logger = logging.getLogger(__name__)

# Create FastAPI router
router = APIRouter(prefix="/storage-queue", tags=["Storage Queue"])


class StorageQueueProcessingResponse(BaseModel):
    """Response for Storage Queue processing operations."""

    status: str
    message: str
    queue_name: str
    messages_processed: int
    correlation_id: str
    timestamp: str  # ISO format timestamp


class ContentProcessorStorageQueueRouter:
    """Content Processor Storage Queue message processor."""

    def __init__(self):
        self.processor = None

    def get_processor(self):
        """Get or create processor instance."""
        if self.processor is None:
            from processor import ContentProcessor

            self.processor = ContentProcessor()
        return self.processor

    async def process_storage_queue_message(
        self, message: QueueMessageModel
    ) -> Dict[str, Any]:
        """
        Process a single Storage Queue message.

        Args:
            message: Storage Queue message to process

        Returns:
            Processing result
        """
        try:
            logger.info(
                f"🔄 PROCESSING: Storage Queue message {message.message_id} - operation: {message.operation} from {message.service_name}"
            )
            logger.info(f"📝 MESSAGE PAYLOAD: {message.payload}")

            if message.operation == "wake_up":
                # Handle wake-up message - scan for available work
                logger.info(
                    "🚀 WAKE-UP: Received wake-up signal from Storage Queue - scanning for available work"
                )

                # Process available work using the wake-up pattern
                logger.info("🏭 PROCESSOR: Creating ContentProcessor instance...")
                processor = self.get_processor()
                logger.info(
                    "✅ PROCESSOR: ContentProcessor instance created successfully"
                )

                # Extract parameters from message payload with safe defaults
                batch_size = message.payload.get("batch_size", 10)
                priority_threshold = message.payload.get("priority_threshold", 0.5)
                debug_bypass = message.payload.get("debug_bypass", False)

                logger.info(
                    f"⚙️ PROCESSING: Starting work processing with batch_size={batch_size}, priority_threshold={priority_threshold}, debug_bypass={debug_bypass}"
                )
                result = await processor.process_available_work(
                    batch_size=batch_size,
                    priority_threshold=priority_threshold,
                    debug_bypass=debug_bypass,
                )
                logger.info(
                    f"✅ PROCESSING: Work processing completed - {result.topics_processed} topics processed, cost: ${result.total_cost:.4f}"
                )

                response = {
                    "status": "success",
                    "operation": "wake_up_processed",
                    "result": {
                        "topics_processed": result.topics_processed,
                        "articles_generated": result.articles_generated,
                        "total_cost": result.total_cost,
                        "processing_time": result.processing_time,
                        "batch_size": batch_size,
                        "priority_threshold": priority_threshold,
                        "debug_bypass": debug_bypass,
                    },
                    "message_id": message.message_id,
                }
                logger.info(f"📤 RESPONSE: Returning processing result: {response}")
                return response

            elif message.operation == "process":
                # Handle specific processing request - use the available work processor
                processor = self.get_processor()
                payload = message.payload
                batch_size = payload.get("batch_size", 10)
                priority_threshold = payload.get("priority_threshold", 0.5)

                result = await processor.process_available_work(
                    batch_size=batch_size,
                    priority_threshold=priority_threshold,
                    options=payload.get("processing_options", {}),
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
            logger.error(f"Error processing Storage Queue message: {e}")
            return {
                "status": "error",
                "operation": message.operation,
                "error": str(e),
                "message_id": message.message_id,
            }


# Global router instance - lazy loading for tests
_storage_queue_router = None


def get_storage_queue_router() -> ContentProcessorStorageQueueRouter:
    """Get or create storage queue router instance."""
    global _storage_queue_router
    if _storage_queue_router is None:
        _storage_queue_router = ContentProcessorStorageQueueRouter()
    return _storage_queue_router


@router.get("/health")
async def storage_queue_health() -> Dict[str, Any]:
    """Health check for Storage Queue integration."""
    try:
        # Test Storage Queue client connection
        client = get_queue_client("content-processing-requests")
        health = client.get_health_status()

        return {
            "status": "healthy",
            "storage_queue_client": health,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "content-processor",
        }
    except Exception as e:
        logger.error(f"Storage Queue health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": "Storage queue health check failed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "content-processor",
        }


@router.post("/process", response_model=StorageQueueProcessingResponse)
async def process_storage_queue_messages(
    background_tasks: BackgroundTasks,
    max_messages: Optional[int] = 10,
) -> StorageQueueProcessingResponse:
    """
    Process Storage Queue messages.

    Args:
        background_tasks: FastAPI background tasks
        max_messages: Maximum number of messages to process

    Returns:
        Processing response
    """
    correlation_id = str(uuid.uuid4())
    start_time = datetime.now(timezone.utc)

    try:
        logger.info(
            f"Starting Storage Queue processing (correlation_id: {correlation_id})"
        )

        # Process a single message for now
        async def process_message(
            queue_message: QueueMessageModel, message: Any
        ) -> Dict[str, Any]:
            """Process a single message."""
            try:
                # Process the message using the queue_message data
                router_instance = get_storage_queue_router()
                result = await router_instance.process_storage_queue_message(
                    queue_message
                )

                if result["status"] == "success":
                    logger.info(
                        f"Successfully processed message {queue_message.message_id}"
                    )
                else:
                    logger.warning(
                        f"Message processing failed: {result.get('error', 'Unknown error')}"
                    )

                return result
            except Exception as e:
                logger.error(f"Error processing individual message: {e}")
                return {"status": "error", "error": str(e)}

        # Use the process_queue_messages utility from our unified interface
        processed_count = await process_queue_messages(
            queue_name="content-processing-requests",
            message_handler=process_message,
            max_messages=max_messages or 10,
        )

        return StorageQueueProcessingResponse(
            status="success",
            message=f"Processed {processed_count} messages",
            queue_name="content-processing-requests",
            messages_processed=processed_count,
            correlation_id=correlation_id,
            timestamp=start_time.isoformat(),
        )

    except Exception as e:
        logger.error(f"Storage Queue processing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Storage Queue processing failed: {str(e)}",
        )


@router.post("/send-wake-up")
async def send_wake_up_endpoint() -> Dict[str, Any]:
    """
    Send wake-up message to trigger site generation.

    Returns:
        Send result
    """
    try:
        # Use our unified send_wake_up_message function to trigger site generation
        result = await send_wake_up_message(
            queue_name="site-generation-requests",
            service_name="content-processor",
            payload={
                "trigger": "content_processed",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        return {
            "status": "success",
            "message": "Wake-up message sent to site generator",
            "queue_name": "site-generation-requests",
            "message_id": result["message_id"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to send wake-up message: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send wake-up message: {str(e)}",
        )
