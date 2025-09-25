"""
Storage Queue Endpoints for Site Generator

Implements Storage Queue message processing for site generation requests.
Uses unified queue interface and existing site generator functionality.
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
    timestamp: datetime


class SiteGeneratorStorageQueueRouter:
    """Site Generator Storage Queue message processor."""

    def __init__(self):
        pass

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
                # Handle wake-up message - generate site
                logger.info(
                    "Received wake-up signal from Storage Queue - generating site"
                )

                result = await self._generate_static_site(message.payload)

                return {
                    "status": "success",
                    "operation": "wake_up_processed",
                    "result": result,
                    "message_id": message.message_id,
                }

            elif message.operation == "generate_site":
                # Handle specific site generation request
                result = await self._generate_static_site(message.payload)

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

    async def _generate_static_site(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Generate static site from processed content."""
        try:
            processed_content_location = payload.get("processed_content_location")
            items_count = payload.get("items_count", 0)

            if not processed_content_location:
                # If no specific content location provided, generate from available content
                logger.info(
                    "No specific content location provided, generating from available content"
                )
                from site_generator import SiteGenerator

                generator = SiteGenerator()
                result = await generator.generate_static_site(
                    theme="minimal", force_rebuild=True
                )

                logger.info("Generated site from available content")
                return {
                    "status": "success",
                    "generated_files": result.files_generated,
                    "site_location": result.output_location,
                    "success": True,
                    "pages_generated": result.pages_generated,
                    "processing_time": result.processing_time,
                    "generator_id": result.generator_id,
                }

            # Load processed content from storage
            import os

            from azure.identity import DefaultAzureCredential
            from azure.storage.blob import BlobServiceClient

            from libs.simplified_blob_client import SimplifiedBlobClient

            storage_account_url = os.getenv("AZURE_STORAGE_ACCOUNT_URL")
            if not storage_account_url:
                raise ValueError(
                    "AZURE_STORAGE_ACCOUNT_URL environment variable is required"
                )

            credential = DefaultAzureCredential()
            blob_service_client = BlobServiceClient(
                account_url=storage_account_url, credential=credential
            )
            storage = SimplifiedBlobClient(blob_service_client)

            # Parse storage location
            parts = processed_content_location.split("/", 1)
            if len(parts) != 2:
                return {
                    "status": "error",
                    "error": f"Invalid storage location format: {processed_content_location}",
                }

            container_name, blob_name = parts
            content_json = await storage.download_text(container_name, blob_name)

            import json

            processed_data = json.loads(content_json)
            processed_items = processed_data.get("items", [])

            # Generate site from processed content
            from site_generator import SiteGenerator

            generator = SiteGenerator()

            # Generate markdown files from processed content
            result = await generator.generate_static_site(
                theme="minimal", force_rebuild=True
            )

            logger.info(f"Generated site from {len(processed_items)} processed items")
            return {
                "status": "success",
                "generated_files": result.files_generated,
                "site_location": result.output_location,
                "processed_items_count": len(processed_items),
                "success": True,
                "pages_generated": result.pages_generated,
                "processing_time": result.processing_time,
                "generator_id": result.generator_id,
            }

        except Exception as e:
            logger.error(f"Failed to generate static site: {e}")
            return {"status": "error", "error": str(e)}


# Global router instance
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

        # Process messages using our unified interface
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
                return {"status": "error", "error": str(e)}

        # Use the process_queue_messages utility from our unified interface
        processed_count = await process_queue_messages(
            queue_name="site-generation-requests",
            message_handler=process_message,
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
