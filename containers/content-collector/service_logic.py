"""
Content Collector Service Logic

Core business logic for content collection with blob storage integration.
"""

import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from content_processing_simple import collect_content_batch, deduplicate_content

from libs import BlobContainers, BlobStorageClient


class ContentCollectorService:
    """Service for collecting and storing content."""

    def __init__(self, storage_client: Optional[Union[BlobStorageClient, Any]] = None):
        """Initialize the content collector service.

        Args:
            storage_client: Optional storage client for dependency injection.
                           If None, creates appropriate storage client based on environment.
        """
        if storage_client:
            self.storage = storage_client
        elif os.getenv("PYTEST_CURRENT_TEST"):  # Running in pytest
            # Import here to avoid circular imports
            from tests.test_fixtures import MockBlobStorageClient

            self.storage = MockBlobStorageClient()
        else:
            self.storage = BlobStorageClient()

        # Initialize Storage Queue client for sending processing requests
        self.queue_client = None

        self.stats = {
            "total_collections": 0,
            "successful_collections": 0,
            "failed_collections": 0,
            "last_collection": None,
        }

    async def _send_processing_request(self, collection_result: Dict[str, Any]) -> bool:
        """Send wake-up message to Storage Queue to trigger content processing.

        Sends a single wake-up message that causes the processor to scan
        blob storage and process all available collections, including this one.
        """
        import logging

        logger = logging.getLogger(__name__)

        try:
            from libs.queue_client import send_wake_up_message

            collection_id = collection_result.get("collection_id")
            total_items = len(collection_result.get("collected_items", []))

            logger.info(
                f"Sending wake-up message for collection {collection_id} ({total_items} items collected)"
            )

            # Send wake-up message to the processor using our unified interface
            result = await send_wake_up_message(
                queue_name="content-processing-requests",
                service_name="content-collector",
                payload={
                    "trigger_reason": "new_collection",
                    "collection_id": collection_id,
                    "items_count": total_items,
                    "storage_location": collection_result.get("storage_location"),
                    "message": f"Content collected for {collection_id}, processor should scan storage",
                },
            )

            logger.info(
                f"Wake-up message sent successfully for collection {collection_id}, message_id: {result['message_id']}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send wake-up message: {e}")
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

            # Send processing request to queue if collection was saved to storage
            # This enables end-to-end pipeline testing even with empty collections
            if storage_location:
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

    async def get_recent_collections(self, limit: int = 10) -> List[Dict[str, Any]]:
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
            blobs = await self.storage.list_blobs(
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

    async def get_collection_by_id(
        self, collection_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get collection data by ID.

        Args:
            collection_id: The collection identifier

        Returns:
            Collection data or None if not found
        """
        try:
            # Search for the collection file
            container_name = "raw-content"
            blobs = await self.storage.list_blobs(
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
            content = await self.storage.download_text(
                container_name=container_name, blob_name=target_blob
            )

            return json.loads(content)

        except Exception:
            return None

    def _generate_collection_id(self) -> str:
        """Generate a unique collection ID with timestamp."""
        timestamp = datetime.now(timezone.utc)
        return f"content_collection_{timestamp.strftime('%Y%m%d_%H%M%S')}"

    def _get_storage_path(self, collection_id: str) -> str:
        """Generate storage path for a collection."""
        # Extract date from collection ID - look for YYYYMMDD_HHMMSS pattern
        import re

        # Look for 8-digit date followed by underscore and 6-digit time
        date_match = re.search(r"(\d{8})_(\d{6})", collection_id)

        if date_match:
            date_part = date_match.group(1)  # YYYYMMDD
            # Format as YYYY/MM/DD
            year = date_part[:4]
            month = date_part[4:6]
            day = date_part[6:8]
        else:
            # Fallback to current date if pattern not found
            now = datetime.now(timezone.utc)
            year = now.strftime("%Y")
            month = now.strftime("%m")
            day = now.strftime("%d")

        return f"{BlobContainers.COLLECTED_CONTENT}/collections/{year}/{month}/{day}/{collection_id}.json"

    async def _list_collection_files(
        self, prefix: str = "collections/"
    ) -> List[Dict[str, Any]]:
        """List collection files from storage."""
        return await self.storage.list_blobs(
            container_name=BlobContainers.COLLECTED_CONTENT, prefix=prefix
        )
