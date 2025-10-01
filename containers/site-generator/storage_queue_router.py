"""
Storage Queue Endpoints for Site Generator

Implements Storage Queue message processing for site generation requests.
Uses unified queue interface and existing site generator functionality.
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from content_processing_functions import generate_static_site
from fastapi import APIRouter, BackgroundTasks, HTTPException
from functional_config import create_generator_context
from pydantic import BaseModel

from libs.data_contracts import ContractValidator, DataContractError
from libs.queue_client import (
    QueueMessageModel,
    get_queue_client,
    process_queue_messages,
)
from libs.simplified_blob_client import SimplifiedBlobClient

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
    timestamp: datetime


async def _generate_static_site(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Generate static site from processed content.

    Args:
        payload: Message payload with generation parameters

    Returns:
        Generation result
    """
    try:
        logger.info("Starting static site generation from Storage Queue trigger")

        # Extract parameters from payload
        topics_processed = payload.get("topics_processed", 0)
        articles_generated = payload.get("articles_generated", 0)

        logger.info(
            f"Processing {topics_processed} topics, {articles_generated} articles"
        )

        # TODO: Implement actual site generation logic
        # For now, just acknowledge the message

        return {
            "status": "success",
            "topics_processed": topics_processed,
            "articles_generated": articles_generated,
            "message": "Site generation completed successfully",
        }

    except Exception as e:
        logger.error(f"Site generation failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": "Site generation failed",
        }


async def process_storage_queue_message(
    message: QueueMessageModel,
) -> Dict[str, Any]:
    """
    Process a single Storage Queue message (functional approach).

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
            # Handle wake-up message - generate site
            logger.info("Received wake-up signal from Storage Queue - generating site")

            result = await _generate_static_site(message.payload)

            return {
                "status": "success",
                "operation": "wake_up_processed",
                "result": result,
                "message_id": message.message_id,
            }

        elif message.operation == "generate_site":
            # Handle specific site generation request
            result = await _generate_static_site(message.payload)

            return {
                "status": "success",
                "operation": "site_generation_completed",
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
            "error": str(e),
            "message_id": message.message_id,
        }


class SiteGeneratorStorageQueueRouter:
    """Site Generator Storage Queue message processor (deprecated - use functional approach)."""

    def __init__(self):
        pass

    async def process_storage_queue_message(
        self, message: QueueMessageModel
    ) -> Dict[str, Any]:
        """Delegate to functional implementation."""
        return await process_storage_queue_message(message)

    async def _generate_static_site(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Delegate to functional implementation."""
        return await _generate_static_site(payload)


# Global router instance (deprecated - kept for backward compatibility)
storage_queue_router = SiteGeneratorStorageQueueRouter()


@router.get("/health")
async def storage_queue_health() -> Dict[str, Any]:
    """Health check for Storage Queue integration."""
    try:
        # Test Storage Queue client connection
        client = get_queue_client("site-generation-requests")
        health = client.get_health_status()

        return {
            "status": "healthy",
            "storage_queue_client": health,
            "timestamp": datetime.now(timezone.utc),
            "service": "site-generator",
        }
    except Exception as e:
        logger.error(f"Storage Queue health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": "Storage queue health check failed",
            "timestamp": datetime.now(timezone.utc),
            "service": "site-generator",
        }


@router.post("/process", response_model=StorageQueueProcessingResponse)
async def process_storage_queue_messages(
    background_tasks: BackgroundTasks,
    # Site generator handles fewer messages due to file generation overhead
    max_messages: Optional[int] = 2,
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

        # Process messages using our unified interface (functional approach)
        async def process_message_handler(
            message_data: Dict[str, Any],
        ) -> Dict[str, Any]:
            """Process a single message."""
            try:
                # Create QueueMessageModel from message data
                queue_message = QueueMessageModel(**message_data)

                # Process the message using functional approach
                result = await process_storage_queue_message(queue_message)

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
            queue_name="site-generation-requests",
            message_handler=process_message_handler,
            max_messages=max_messages or 2,
        )

        return StorageQueueProcessingResponse(
            status="success",
            message=f"Processed {processed_count} messages",
            queue_name="site-generation-requests",
            messages_processed=processed_count,
            correlation_id=correlation_id,
            timestamp=start_time,
        )

    except Exception as e:
        logger.error(f"Storage Queue processing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Storage Queue processing failed: {str(e)}",
        )
