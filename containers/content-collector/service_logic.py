"""
Content Collector Service Logic

Core business logic for content collection with blob storage integration.
"""

import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from content_processing import collect_content_batch, deduplicate_content

from libs.blob_storage import BlobContainers, BlobStorageClient
from libs.service_bus_client import (
    ServiceBusClient,
    ServiceBusConfig,
    ServiceBusMessageModel,
)


class MockBlobStorageClient:
    """Mock blob storage client for testing."""

    async def upload_text(
        self,
        container_name: str,
        blob_name: str,
        content: str,
        content_type: str = "text/plain",
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        return f"mock://blob/{blob_name}"

    async def upload_json(
        self,
        container_name: str,
        blob_name: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        return f"mock://blob/{blob_name}"

    def download_text(self, container_name: str, blob_name: str) -> str:
        return '{"mock": "data"}'

    def list_blobs(self, container_name: str, prefix: str = "") -> List[Dict[str, Any]]:
        return []


class ContentCollectorService:
    """Service for collecting and storing content."""

    def __init__(self, storage_client: Optional[BlobStorageClient] = None):
        """Initialize the content collector service.

        Args:
            storage_client: Optional storage client for dependency injection.
                           If None, creates appropriate storage client based on environment.
        """
        if storage_client:
            self.storage = storage_client
        elif os.getenv("PYTEST_CURRENT_TEST"):  # Running in pytest
            self.storage = MockBlobStorageClient()
        else:
            self.storage = BlobStorageClient()

        # Initialize Service Bus client for sending processing requests
        self.service_bus_client = None

        self.stats = {
            "total_collections": 0,
            "successful_collections": 0,
            "failed_collections": 0,
            "last_collection": None,
        }

    async def _get_service_bus_client(self) -> Optional[ServiceBusClient]:
        """Get or create Service Bus client for sending messages."""
        if self.service_bus_client is None:
            try:
                # Create config for content processing requests queue
                config = ServiceBusConfig(
                    namespace=os.getenv("SERVICE_BUS_NAMESPACE", ""),
                    queue_name="content-processing-requests",  # Send to processing queue
                    max_wait_time=30,
                    max_messages=10,
                    retry_attempts=3,
                )
                self.service_bus_client = ServiceBusClient(config)
                await self.service_bus_client.connect()
            except Exception as e:
                # Log error but don't fail the whole operation
                import logging

                logger = logging.getLogger(__name__)
                logger.error(f"Failed to initialize Service Bus client: {e}")
                return None

        return self.service_bus_client

    async def _send_processing_request(self, collection_result: Dict[str, Any]) -> bool:
        """Send content processing request to Service Bus."""
        try:
            service_bus = await self._get_service_bus_client()
            if not service_bus:
                return False

            # Create processing request message
            message = ServiceBusMessageModel(
                service_name="content-collector",
                operation="process_content",
                payload={
                    "collection_id": collection_result["collection_id"],
                    "storage_location": collection_result["storage_location"],
                    "items_count": len(collection_result["collected_items"]),
                    "metadata": collection_result["metadata"],
                },
                metadata={
                    "source_service": "content-collector",
                    "target_service": "content-processor",
                    "content_type": "collected_content",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

            success = await service_bus.send_message(message)
            if success:
                import logging

                logger = logging.getLogger(__name__)
                logger.info(
                    f"Sent processing request for collection {collection_result['collection_id']}"
                )

            return success

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send processing request: {e}")
            return False

    async def collect_and_store_content(
        self,
        sources_data: List[Dict[str, Any]],
        deduplicate: bool = True,
        similarity_threshold: float = 0.8,
        save_to_storage: bool = True,
    ) -> Dict[str, Any]:
        """
        Collect content from sources and optionally save to blob storage.

        Args:
            sources_data: List of source configurations
            deduplicate: Whether to deduplicate content
            similarity_threshold: Threshold for deduplication
            save_to_storage: Whether to save to blob storage

        Returns:
            Collection result with metadata
        """
        start_time = time.time()
        collection_id = (
            f"collection_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        )

        try:
            # Apply default criteria to Reddit sources (if needed)
            for source_dict in sources_data:
                if source_dict["type"] == "reddit" and not source_dict.get("criteria"):
                    source_dict["criteria"] = {}  # Default empty criteria

            # Collect content
            result = await collect_content_batch(sources_data)
            collected_items = result["collected_items"]
            metadata = result["metadata"]

            # Apply deduplication if requested
            if deduplicate and collected_items:
                original_count = len(collected_items)
                collected_items = deduplicate_content(
                    collected_items, similarity_threshold
                )
                metadata["deduplication"] = {
                    "enabled": True,
                    "original_count": original_count,
                    "deduplicated_count": len(collected_items),
                    "removed_count": original_count - len(collected_items),
                    "similarity_threshold": similarity_threshold,
                }
            else:
                metadata["deduplication"] = {"enabled": False}

            # Add processing time and collection info
            processing_time = time.time() - start_time
            metadata.update(
                {
                    "processing_time_seconds": round(processing_time, 3),
                    "collection_id": collection_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "total_items": len(collected_items),
                }
            )

            # Save to blob storage if requested
            storage_location = None
            if save_to_storage:  # Always save if requested, even with empty collections
                storage_location = await self._save_to_storage(
                    collection_id, collected_items, metadata
                )

            # Update statistics
            self.stats["total_collections"] += 1
            self.stats["successful_collections"] += 1
            self.stats["last_collection"] = metadata["timestamp"]

            result = {
                "collection_id": collection_id,
                "collected_items": collected_items,
                "metadata": metadata,
                "timestamp": metadata["timestamp"],
                "storage_location": storage_location,
            }

            # Send processing request to Service Bus if we have content
            if collected_items and storage_location:
                await self._send_processing_request(result)

            return result

        except Exception as e:
            self.stats["total_collections"] += 1
            self.stats["failed_collections"] += 1
            raise e

    async def _save_to_storage(
        self,
        collection_id: str,
        collected_items: List[Dict[str, Any]],
        metadata: Dict[str, Any],
    ) -> str:
        """
        Save collected content to blob storage.

        Args:
            collection_id: Unique collection identifier
            collected_items: Collected content items
            metadata: Collection metadata

        Returns:
            Storage location path
        """
        # Prepare the complete data structure
        content_data = {
            "collection_id": collection_id,
            "metadata": metadata,
            "items": collected_items,
            "format_version": "1.0",
        }

        # Generate storage path
        timestamp = datetime.now(timezone.utc)
        container_name = BlobContainers.COLLECTED_CONTENT
        blob_name = f"collections/{timestamp.strftime('%Y/%m/%d')}/{collection_id}.json"

        # Save to blob storage
        content_json = json.dumps(content_data, indent=2, ensure_ascii=False)
        await self.storage.upload_text(
            container_name=container_name,
            blob_name=blob_name,
            content=content_json,
            content_type="application/json",
        )

        return f"{container_name}/{blob_name}"

    def get_service_stats(self) -> Dict[str, Any]:
        """Get current service statistics."""
        return self.stats.copy()

    def get_recent_collections(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get list of recent collections from blob storage.

        Args:
            limit: Maximum number of collections to return

        Returns:
            List of recent collection metadata
        """
        try:
            # List recent collection files
            container_name = BlobContainers.COLLECTED_CONTENT
            blobs = self.storage.list_blobs(
                container_name=container_name, prefix="collections/"
            )

            # Sort by name (which includes timestamp) and take most recent
            sorted_blobs = sorted([blob["name"] for blob in blobs], reverse=True)[
                :limit
            ]

            collections = []
            for blob_name in sorted_blobs:
                try:
                    # Extract collection info from blob name
                    collection_id = blob_name.split("/")[-1].replace(".json", "")
                    path_parts = blob_name.split("/")
                    if (
                        len(path_parts) >= 4
                    ):  # collections/YYYY/MM/DD/collection_id.json
                        date_str = f"{path_parts[1]}-{path_parts[2]}-{path_parts[3]}"
                        collections.append(
                            {
                                "collection_id": collection_id,
                                "date": date_str,
                                "storage_path": f"{container_name}/{blob_name}",
                            }
                        )
                except Exception:
                    continue  # Skip malformed blob names

            return collections

        except Exception as e:
            # If we can't access storage, return empty list
            return []

    def get_collection_by_id(self, collection_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific collection from blob storage.

        Args:
            collection_id: Collection identifier

        Returns:
            Collection data or None if not found
        """
        try:
            # Search for the collection file
            container_name = "raw-content"
            blobs = self.storage.list_blobs(
                container_name=container_name, prefix="collections/"
            )

            # Find the blob with matching collection ID
            target_blob = None
            for blob in blobs:
                blob_name = blob["name"]
                if collection_id in blob_name and blob_name.endswith(".json"):
                    target_blob = blob_name
                    break

            if not target_blob:
                return None

            # Load the collection data
            content = self.storage.download_text(
                container_name=container_name, blob_name=target_blob
            )

            return json.loads(content)

        except Exception:
            return None
