"""
Storage Queue Endpoints for Content Collector

Implements Storage Queue message processing for content collection requests.
Uses shared Storage Queue client for consistency across services.
Replaces Service Bus to resolve Container Apps authentication conflicts.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel
from service_logic import ContentCollectorService

from libs.queue_client import (
    QueueMessageModel,
    get_queue_client,
    send_wake_up_message,
)

logger = logging.getLogger(__name__)

# Create API router
router = APIRouter(prefix="/storage-queue", tags=["storage-queue"])


class StorageQueueProcessingResponse(BaseModel):
    """Response model for Storage Queue processing operations."""

    status: str
    message: str
    queue_name: str
    messages_processed: int
    correlation_id: str
    timestamp: datetime


class ContentCollectorStorageQueueRouter:
    """Content Collector Storage Queue message processor."""

    def __init__(self):
        self.service = ContentCollectorService()

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
                f"Processing Storage Queue message: {message.operation} from {message.service_name}"
            )

            if message.operation == "wake_up":
                # Handle wake-up message - return stats for now
                # The collector doesn't need to do work on wake-up, it collects when triggered
                stats = self.service.get_service_stats()
                return {
                    "status": "success",
                    "operation": "wake_up_acknowledged",
                    "result": stats,
                    "message_id": message.message_id,
                }

            elif message.operation == "collect":
                # Handle specific collection request
                sources_data = message.payload.get("sources_data", [])
                deduplicate = message.payload.get("deduplicate", True)
                similarity_threshold = message.payload.get("similarity_threshold", 0.8)
                save_to_storage = message.payload.get("save_to_storage", True)

                result = await self.service.collect_and_store_content(
                    sources_data=sources_data,
                    deduplicate=deduplicate,
                    similarity_threshold=similarity_threshold,
                    save_to_storage=save_to_storage,
                )
                return {
                    "status": "success",
                    "operation": "collection_completed",
                    "result": result,
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
                "error": "Internal processing error occurred",
                "message_id": message.message_id,
            }


# Global router instance
storage_queue_router = ContentCollectorStorageQueueRouter()


@router.get("/health")
async def storage_queue_health() -> Dict[str, Any]:
    """Health check for Storage Queue integration."""
    try:
        # Test Storage Queue client connection
        client = get_queue_client("content-collection-requests")
        health = client.get_health_status()

        return {
            "status": "healthy",
            "storage_queue_client": health,
            "timestamp": datetime.now(timezone.utc),
            "service": "content-collector",
        }
    except Exception as e:
        logger.error(f"Storage Queue health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": "Health check failed",
            "timestamp": datetime.now(timezone.utc),
            "service": "content-collector",
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

        client = get_queue_client("content-collection-requests")

        # Receive and process messages using our unified interface
        async def process_message(message_data: Dict[str, Any]) -> Dict[str, Any]:
            """Process a single message."""
            try:
                # Create QueueMessageModel from message data
                queue_message = QueueMessageModel(**message_data)

                # Process the message
                result = await storage_queue_router.process_storage_queue_message(
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
                return {"status": "error", "error": "Message processing failed"}

        # Use the process_queue_messages utility from our unified interface
        from libs.queue_client import process_queue_messages

        processed_count = await process_queue_messages(
            queue_name="content-collection-requests",
            message_handler=process_message,
            max_messages=max_messages or 10,
        )

        return StorageQueueProcessingResponse(
            status="success",
            message=f"Processed {processed_count} messages",
            queue_name="content-collection-requests",
            messages_processed=processed_count,
            correlation_id=correlation_id,
            timestamp=start_time,
        )

    except Exception as e:
        logger.error(f"Storage Queue processing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Storage Queue processing failed",
        )


@router.post("/send-wake-up")
async def send_wake_up_endpoint(collection_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Send wake-up message to trigger processing.

    Args:
        collection_id: Optional collection identifier

    Returns:
        Send result
    """
    try:
        # Use our unified send_wake_up_message function
        result = await send_wake_up_message(
            queue_name="content-processing-requests",
            service_name="content-collector",
            payload={
                "collection_id": collection_id
                or f"collection_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "trigger": "manual",
            },
        )

        return {
            "status": "success",
            "message": "Wake-up message sent",
            "queue_name": "content-processing-requests",
            "message_id": result["message_id"],
            "timestamp": datetime.now(timezone.utc),
        }

    except Exception as e:
        logger.error(f"Failed to send wake-up message: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to send wake-up message",
        )


# Create service bus router for backward compatibility during migration
service_bus_router = router
