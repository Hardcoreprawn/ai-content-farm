"""
Service Bus Endpoints for Content Processor

Implements Service Bus message processing for content processing requests.
Uses shared Service Bus router base and existing processor functionality.
"""

import logging
from typing import Any, Dict

from libs.service_bus_router import ServiceBusRouterBase

logger = logging.getLogger(__name__)


class ContentProcessorServiceBusRouter(ServiceBusRouterBase):
    """Service Bus router for content processing service."""

    def __init__(self):
        super().__init__(
            service_name="content-processor",
            queue_name="content-processing-requests",
            prefix="/internal",
        )

    async def process_message_payload(
        self, payload: Dict[str, Any], operation: str
    ) -> Dict[str, Any]:
        """
        Process wake-up messages from Service Bus.

        The Service Bus message is just a wake-up signal. The actual work
        is to scan blob storage and process all available collections.

        Args:
            payload: Wake-up message payload (content doesn't matter)
            operation: Operation type (ignored - we always do full scan)

        Returns:
            Dict with processing results
        """
        try:
            logger.info(
                "Received wake-up signal from Service Bus - scanning for available work"
            )

            # Import processor here to avoid circular imports
            from processor import ContentProcessor

            processor = ContentProcessor()

            # Process all available work (this scans blob storage)
            result = await processor.process_available_work(
                batch_size=50,  # Process up to 50 items per wake-up
                priority_threshold=0.0,  # Process all available content
            )

            logger.info(
                f"Wake-up processing completed: {result.topics_processed} topics processed, "
                f"{result.articles_generated} articles generated, "
                f"${result.total_cost:.4f} cost, "
                f"{result.processing_time:.2f}s duration"
            )

            return {
                "status": "success",
                "message": "Wake-up processing completed",
                "topics_processed": result.topics_processed,
                "articles_generated": result.articles_generated,
                "total_cost": result.total_cost,
                "processing_time": result.processing_time,
                "wake_up_trigger": True,
            }

        except Exception as e:
            logger.error(f"Wake-up processing failed: {e}")
            return {"status": "error", "error": str(e), "wake_up_trigger": True}

    async def _process_individual_item(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single content item from the collector.

        This handles individual items sent by the new collector architecture
        for immediate processing and responsive scaling.
        """
        try:
            collection_id = payload.get("collection_id")
            item_index = payload.get("item_index")
            item_data = payload.get("item_data")

            if not collection_id or item_index is None or not item_data:
                return {
                    "status": "error",
                    "error": "Missing collection_id, item_index, or item_data",
                }

            logger.info(
                f"Processing individual item {item_index} for collection {collection_id}"
            )

            # Import processor here to avoid circular imports
            from libs.content_processor import ContentProcessor, ProcessingStatus
            from libs.shared_models import ContentProcessingRequest

            processor = ContentProcessor()

            # Create processing request from the item data
            processing_request = ContentProcessingRequest(
                content=item_data.get("content", ""),
                title=item_data.get("title", ""),
                source_url=item_data.get("url", item_data.get("source_url", "")),
                content_type=item_data.get("content_type", "text"),
                metadata=item_data.get("metadata", {}),
            )

            # Process the item
            result = await processor.process_content(processing_request)

            if result.status == ProcessingStatus.COMPLETED:
                # Enhance the original item with processing results
                enhanced_item = item_data.copy()
                enhanced_item.update(
                    {
                        "processed_content": result.processed_content,
                        "quality_score": result.quality_score,
                        "processing_time": result.processing_time,
                        "model_used": result.model_used,
                        "enhanced_at": _get_current_iso_timestamp(),
                        "processing_status": "completed",
                    }
                )

                # Save individual processed item to storage
                storage_result = await self._save_individual_processed_item(
                    collection_id, item_index, enhanced_item
                )

                logger.info(
                    f"Successfully processed item {item_index} for collection {collection_id}"
                )

                return {
                    "status": "success",
                    "processed_item": enhanced_item,
                    "collection_id": collection_id,
                    "item_index": item_index,
                    "storage_location": storage_result.get("storage_location"),
                    "success": True,
                }
            else:
                # Processing failed, but don't lose the item
                item_data["processing_error"] = (
                    result.error_message or "Processing failed"
                )
                item_data["processing_status"] = "failed"

                # Save failed item to storage for tracking
                storage_result = await self._save_individual_processed_item(
                    collection_id, item_index, item_data
                )

                logger.warning(
                    f"Processing failed for item {item_index} in collection {collection_id}: {result.error_message}"
                )

                return {
                    "status": "partial_success",
                    "processed_item": item_data,
                    "collection_id": collection_id,
                    "item_index": item_index,
                    "storage_location": storage_result.get("storage_location"),
                    "error": result.error_message,
                    "success": False,
                }

        except Exception as e:
            logger.error(f"Failed to process individual item: {e}")
            return {"status": "error", "error": str(e)}

    async def _process_collected_content(
        self, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process collected content items using existing processor."""
        try:
            collection_id = payload.get("collection_id")
            storage_location = payload.get("storage_location")

            if not collection_id or not storage_location:
                return {
                    "status": "error",
                    "error": "Missing collection_id or storage_location",
                }

            # Load collected content from storage
            from libs.blob_storage import BlobStorageClient

            storage = BlobStorageClient()

            # Parse storage location (format: container/path/to/file.json)
            parts = storage_location.split("/", 1)
            if len(parts) != 2:
                return {
                    "status": "error",
                    "error": f"Invalid storage location format: {storage_location}",
                }

            container_name, blob_name = parts
            content_json = storage.download_text(container_name, blob_name)

            import json

            content_data = json.loads(content_json)
            collected_items = content_data.get("items", [])

            # Use existing processing service to enhance content
            from processing_service import (
                ContentProcessingService,
                ProcessingRequest,
                ProcessingStatus,
            )

            from config import settings

            processor = ContentProcessingService(settings)

            # Process content using existing logic
            enhanced_items = []
            for i, item in enumerate(collected_items):
                # Convert to format expected by processor
                processing_request = ProcessingRequest(
                    topic_id=f"{collection_id}_{i}",
                    content=item.get("content", "") or item.get("summary", ""),
                    metadata={
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "source": item.get("source", ""),
                    },
                )

                # Process the item
                result = await processor.process_content(processing_request)

                if result.status == ProcessingStatus.COMPLETED:
                    enhanced_item = item.copy()
                    enhanced_item.update(
                        {
                            "processed_content": result.processed_content,
                            "quality_score": result.quality_score,
                            "processing_time": result.processing_time,
                            "model_used": result.model_used,
                            "enhanced_at": _get_current_iso_timestamp(),
                        }
                    )
                    enhanced_items.append(enhanced_item)
                else:
                    # Keep original item if processing failed
                    item["processing_error"] = (
                        result.error_message or "Processing failed"
                    )
                    enhanced_items.append(item)

            # Save processed content and trigger site generation
            result = await self._save_processed_content(collection_id, enhanced_items)

            # Send message to site generator
            await self._send_site_generation_request(result)

            logger.info(
                f"Processed {len(enhanced_items)} items for collection {collection_id}"
            )
            return {
                "status": "success",
                "processed_items": enhanced_items,
                "collection_id": collection_id,
                "storage_location": result.get("storage_location"),
                "success": True,
            }

        except Exception as e:
            logger.error(f"Failed to process collected content: {e}")
            return {"status": "error", "error": str(e)}

    async def _generate_content(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Generate new content using existing content generator."""
        try:
            from content_generation import GenerationRequest, get_content_generator

            generator = get_content_generator()

            # Extract generation parameters
            topic = payload.get("topic", "")
            content_type = payload.get("content_type", "blog")
            sources = payload.get("sources", [])

            if not topic:
                return {
                    "status": "error",
                    "error": "Missing topic for content generation",
                }

            # Create generation request
            request = GenerationRequest(
                topic=topic, content_type=content_type, sources=sources
            )

            # Generate content
            generated_content = await generator.generate_content(request)

            return {
                "status": "success",
                "generated_content": generated_content.model_dump(),
                "success": True,
            }

        except Exception as e:
            logger.error(f"Failed to generate content: {e}")
            return {"status": "error", "error": str(e)}

    async def _save_processed_content(
        self, collection_id: str, processed_items: list
    ) -> Dict[str, Any]:
        """Save processed content to storage."""
        try:
            import json
            from datetime import datetime, timezone

            from libs.blob_storage import BlobContainers, BlobStorageClient

            storage = BlobStorageClient()

            # Prepare the processed data
            processed_data = {
                "collection_id": collection_id,
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "items_count": len(processed_items),
                "items": processed_items,
                "format_version": "1.0",
            }

            # Generate storage path
            timestamp = datetime.now(timezone.utc)
            blob_name = f"processed/{timestamp.strftime('%Y/%m/%d')}/{collection_id}_processed.json"

            # Save processed content
            content_json = json.dumps(processed_data, indent=2, ensure_ascii=False)
            storage.upload_text(
                container_name=BlobContainers.COLLECTED_CONTENT,
                blob_name=blob_name,
                content=content_json,
                content_type="application/json",
            )

            return {
                "storage_location": f"{BlobContainers.COLLECTED_CONTENT}/{blob_name}",
                "items_count": len(processed_items),
            }

        except Exception as e:
            logger.error(f"Failed to save processed content: {e}")
            raise

    async def _save_individual_processed_item(
        self, collection_id: str, item_index: int, processed_item: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Save individual processed item to storage."""
        try:
            import json
            from datetime import datetime, timezone

            from libs.blob_storage import BlobContainers, BlobStorageClient

            storage = BlobStorageClient()

            # Prepare the processed item data
            item_data = {
                "collection_id": collection_id,
                "item_index": item_index,
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "item": processed_item,
                "format_version": "1.0",
            }

            # Generate storage path for individual item
            timestamp = datetime.now(timezone.utc)
            blob_name = f"processed/{timestamp.strftime('%Y/%m/%d')}/{collection_id}_item_{item_index:03d}.json"

            # Save processed item
            content_json = json.dumps(item_data, indent=2, ensure_ascii=False)
            await storage.upload_text(
                container_name=BlobContainers.COLLECTED_CONTENT,
                blob_name=blob_name,
                content=content_json,
                content_type="application/json",
            )

            return {
                "storage_location": f"{BlobContainers.COLLECTED_CONTENT}/{blob_name}",
                "item_index": item_index,
            }

        except Exception as e:
            logger.error(f"Failed to save individual processed item: {e}")
            raise

    async def _send_site_generation_request(
        self, processing_result: Dict[str, Any]
    ) -> bool:
        """Send site generation request to Service Bus."""
        try:
            import os
            from datetime import datetime, timezone

            from libs.service_bus_client import (
                ServiceBusClient,
                ServiceBusConfig,
                ServiceBusMessageModel,
            )

            # Create config for site generation requests queue
            config = ServiceBusConfig(
                namespace=os.getenv("SERVICE_BUS_NAMESPACE", ""),
                queue_name="site-generation-requests",
                max_wait_time=30,
                max_messages=10,
                retry_attempts=3,
            )

            client = ServiceBusClient(config)
            await client.connect()

            # Create site generation request message
            message = ServiceBusMessageModel(
                service_name="content-processor",
                operation="generate_site",
                payload={
                    "processed_content_location": processing_result["storage_location"],
                    "items_count": processing_result["items_count"],
                },
                metadata={
                    "source_service": "content-processor",
                    "target_service": "site-generator",
                    "content_type": "processed_content",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

            success = await client.send_message(message)
            if success:
                logger.info(
                    f"Sent site generation request for {processing_result['storage_location']}"
                )

            return success

        except Exception as e:
            logger.error(f"Failed to send site generation request: {e}")
            return False

    def get_max_messages(self) -> int:
        """Content processor handles fewer messages due to AI processing overhead."""
        return 3


def _get_current_iso_timestamp():
    """Helper to get current ISO timestamp."""
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


# Create router instance
service_bus_router = ContentProcessorServiceBusRouter()
router = service_bus_router.router
