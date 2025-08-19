"""
Content Processor Service Logic

Handles blob storage integration and pipeline workflow for content processing.
"""

import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from libs.blob_storage import BlobStorageClient, BlobContainers, get_timestamped_blob_name
from processor import process_reddit_batch


class ContentProcessorService:
    """Service for processing content and managing blob storage."""

    def __init__(self):
        """Initialize the content processor service."""
        self.storage = BlobStorageClient()
        self.stats = {
            "total_processed": 0,
            "successful_processing": 0,
            "failed_processing": 0,
            "last_processed": None
        }

    async def process_collected_content(
        self,
        collection_data: Dict[str, Any],
        save_to_storage: bool = True
    ) -> Dict[str, Any]:
        """
        Process collected content and optionally save to blob storage.

        Args:
            collection_data: Collection data from content-collector
            save_to_storage: Whether to save processed results to blob storage

        Returns:
            Processing result with metadata
        """
        start_time = time.time()
        process_id = f"process_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        try:
            # Extract items from collection data
            items = collection_data.get("items", [])
            collection_metadata = collection_data.get("metadata", {})

            if not items:
                # Handle empty collections
                processed_items = []
                processing_metadata = {
                    "total_items": 0,
                    "processed_items": 0,
                    "source_collection": collection_data.get("collection_id", "unknown"),
                    "processing_errors": 0
                }
            else:
                # Process the content using existing business logic
                # Determine source type from items or metadata
                source = collection_metadata.get(
                    "source", "reddit")  # Default to reddit

                if source == "reddit" or any("subreddit" in item for item in items):
                    # Use Reddit batch processing
                    processed_items = process_reddit_batch(items)
                else:
                    # Generic processing for other sources
                    processed_items = []
                    for item in items:
                        # Basic processing for non-Reddit content
                        processed_item = {
                            "original_id": item.get("id", "unknown"),
                            "title": item.get("title", ""),
                            "content": item.get("content", item.get("selftext", "")),
                            "url": item.get("url", ""),
                            "source": source,
                            "processed_at": datetime.now(timezone.utc).isoformat(),
                            "quality_score": 0.5,  # Default quality score
                            "content_type": item.get("content_type", "unknown"),
                            "metadata": {
                                "original_score": item.get("score", 0),
                                "engagement_metrics": {}
                            }
                        }
                        processed_items.append(processed_item)

                processing_metadata = {
                    "total_items": len(items),
                    "processed_items": len(processed_items),
                    "source_collection": collection_data.get("collection_id", "unknown"),
                    "processing_errors": 0,
                    "source_type": source
                }

            # Add processing timing
            processing_time = time.time() - start_time
            processing_metadata.update({
                "processing_time_seconds": round(processing_time, 3),
                "process_id": process_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "processor_version": "1.0.0"
            })

            # Prepare result
            result = {
                "process_id": process_id,
                "processed_items": processed_items,
                "metadata": processing_metadata,
                "timestamp": processing_metadata["timestamp"],
                "storage_location": None
            }

            # Save to blob storage if requested
            if save_to_storage:
                storage_location = await self._save_processed_content(
                    process_id, processed_items, processing_metadata, collection_data
                )
                result["storage_location"] = storage_location

            # Update statistics
            self.stats["total_processed"] += 1
            self.stats["successful_processing"] += 1
            self.stats["last_processed"] = processing_metadata["timestamp"]

            return result

        except Exception as e:
            self.stats["total_processed"] += 1
            self.stats["failed_processing"] += 1
            raise e

    async def _save_processed_content(
        self,
        process_id: str,
        processed_items: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        original_collection: Dict[str, Any]
    ) -> str:
        """
        Save processed content to blob storage.

        Args:
            process_id: Unique processing identifier
            processed_items: Processed content items
            metadata: Processing metadata
            original_collection: Original collection data for reference

        Returns:
            Storage location path
        """
        # Prepare the complete data structure
        processed_data = {
            "process_id": process_id,
            "metadata": metadata,
            "processed_items": processed_items,
            "source_collection": {
                "collection_id": original_collection.get("collection_id"),
                "collected_at": original_collection.get("metadata", {}).get("collected_at"),
                "total_source_items": len(original_collection.get("items", []))
            },
            "format_version": "1.0"
        }

        # Generate storage path
        timestamp = datetime.now(timezone.utc)
        container_name = BlobContainers.PROCESSED_CONTENT
        blob_name = f"processed/{timestamp.strftime('%Y/%m/%d')}/{process_id}.json"

        # Save to blob storage
        content_json = json.dumps(processed_data, indent=2, ensure_ascii=False)
        self.storage.upload_text(
            container_name=container_name,
            blob_name=blob_name,
            content=content_json,
            content_type="application/json"
        )

        return f"{container_name}/{blob_name}"

    async def find_unprocessed_collections(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Find collected content that hasn't been processed yet.

        Args:
            limit: Maximum number of collections to return

        Returns:
            List of unprocessed collection metadata
        """
        try:
            # List collected content
            collected_blobs = self.storage.list_blobs(
                container_name=BlobContainers.COLLECTED_CONTENT,
                prefix="collections/"
            )

            # List processed content
            processed_blobs = self.storage.list_blobs(
                container_name=BlobContainers.PROCESSED_CONTENT,
                prefix="processed/"
            )

            # Extract processed collection IDs
            processed_collection_ids = set()
            for blob in processed_blobs:
                try:
                    # Download and check source collection ID
                    content = self.storage.download_text(
                        BlobContainers.PROCESSED_CONTENT, blob["name"]
                    )
                    processed_data = json.loads(content)
                    source_id = processed_data.get(
                        "source_collection", {}).get("collection_id")
                    if source_id:
                        processed_collection_ids.add(source_id)
                except Exception:
                    continue

            # Find unprocessed collections
            unprocessed = []
            for blob in collected_blobs[:limit]:
                try:
                    # Download collection data
                    content = self.storage.download_text(
                        BlobContainers.COLLECTED_CONTENT, blob["name"]
                    )
                    collection_data = json.loads(content)
                    collection_id = collection_data.get("collection_id")

                    if collection_id and collection_id not in processed_collection_ids:
                        unprocessed.append({
                            "collection_id": collection_id,
                            "blob_name": blob["name"],
                            "collection_data": collection_data,
                            "collected_at": collection_data.get("metadata", {}).get("collected_at"),
                            "total_items": len(collection_data.get("items", []))
                        })

                        if len(unprocessed) >= limit:
                            break
                except Exception:
                    continue

            return unprocessed

        except Exception as e:
            # Return empty list if there are issues
            return []

    def get_service_stats(self) -> Dict[str, Any]:
        """Get current service statistics."""
        return self.stats.copy()
