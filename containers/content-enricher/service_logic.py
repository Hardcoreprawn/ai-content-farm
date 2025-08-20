"""
Content Enricher Service Logic

Business logic layer for the content enricher service that handles:
- Reading processed content from blob storage
- Enriching content with sentiment analysis, topic classification, and summarization
- Saving enriched content back to blob storage
- Managing enrichment pipeline workflow
"""

import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from enricher import enrich_content_batch

from libs.blob_storage import BlobContainers, BlobStorageClient


class ContentEnricherService:
    """Service layer for content enrichment with blob storage integration."""

    def __init__(self):
        """Initialize the enricher service with blob storage client."""
        self.storage = BlobStorageClient()
        self.stats = {
            "total_enriched": 0,
            "successful_enrichment": 0,
            "failed_enrichment": 0,
            "last_enriched": None,
        }

    async def enrich_processed_content(
        self, processed_data: Dict[str, Any], save_to_storage: bool = True
    ) -> Dict[str, Any]:
        """
        Enrich processed content with sentiment, topics, and summaries.

        Args:
            processed_data: Processed content from content-processor
            save_to_storage: Whether to save enriched results to blob storage

        Returns:
            Enrichment result with metadata
        """
        start_time = time.time()
        enrichment_id = (
            f"enrichment_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        )

        try:
            # Extract processed items from the data
            processed_items = processed_data.get("processed_items", [])
            source_metadata = processed_data.get("metadata", {})

            if not processed_items:
                # Handle empty processed data
                enriched_items = []
                enrichment_metadata = {
                    "total_items": 0,
                    "enriched_items": 0,
                    "source_process": processed_data.get("process_id", "unknown"),
                    "enrichment_errors": 0,
                }
            else:
                # Enrich the content using existing business logic
                enriched_items = enrich_content_batch(processed_items)

                enrichment_metadata = {
                    "total_items": len(processed_items),
                    "enriched_items": len(enriched_items),
                    "source_process": processed_data.get("process_id", "unknown"),
                    "enrichment_errors": len(processed_items) - len(enriched_items),
                    "enrichment_types": ["sentiment", "topic", "summary", "trend"],
                }

            # Add enrichment timing and metadata
            enrichment_time = time.time() - start_time
            enrichment_metadata.update(
                {
                    "enrichment_time_seconds": round(enrichment_time, 3),
                    "enrichment_id": enrichment_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "enricher_version": "1.0.0",
                }
            )

            # Prepare result
            result = {
                "enrichment_id": enrichment_id,
                "enriched_items": enriched_items,
                "metadata": enrichment_metadata,
                "timestamp": enrichment_metadata["timestamp"],
                "storage_location": None,
                "source_data": {
                    "process_id": processed_data.get("process_id"),
                    "source_collection": source_metadata.get("source_collection"),
                    "processed_at": processed_data.get("timestamp"),
                },
            }

            # Save to blob storage if requested
            if save_to_storage:
                storage_location = await self._save_enriched_content(
                    enrichment_id, enriched_items, enrichment_metadata, processed_data
                )
                result["storage_location"] = storage_location

            # Update statistics
            self.stats["total_enriched"] += 1
            self.stats["successful_enrichment"] += 1
            self.stats["last_enriched"] = enrichment_metadata["timestamp"]

            return result

        except Exception as e:
            self.stats["total_enriched"] += 1
            self.stats["failed_enrichment"] += 1
            raise e

    async def _save_enriched_content(
        self,
        enrichment_id: str,
        enriched_items: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        original_processed: Dict[str, Any],
    ) -> str:
        """
        Save enriched content to blob storage.

        Args:
            enrichment_id: Unique enrichment identifier
            enriched_items: List of enriched content items
            metadata: Enrichment metadata
            original_processed: Original processed data for reference

        Returns:
            Storage location path
        """
        # Determine target container
        container_name = BlobContainers.ENRICHED_CONTENT

        # Create enriched data structure
        enriched_data = {
            "enrichment_id": enrichment_id,
            "metadata": metadata,
            "enriched_items": enriched_items,
            "source_data": {
                "process_id": original_processed.get("process_id"),
                "source_collection": original_processed.get("metadata", {}).get(
                    "source_collection"
                ),
                "processed_items": len(original_processed.get("processed_items", [])),
                "processed_at": original_processed.get("timestamp"),
            },
            "format_version": "1.0",
        }

        # Create blob path with date structure
        timestamp = datetime.now(timezone.utc)
        blob_name = f"enriched/{timestamp.strftime('%Y/%m/%d')}/{enrichment_id}.json"

        # Save to blob storage
        content_json = json.dumps(enriched_data, indent=2, ensure_ascii=False)
        self.storage.upload_text(
            container_name=container_name,
            blob_name=blob_name,
            content=content_json,
            content_type="application/json",
        )

        return f"{container_name}/{blob_name}"

    async def find_unenriched_processed_content(
        self, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find processed content that hasn't been enriched yet.

        Args:
            limit: Maximum number of processed items to return

        Returns:
            List of unenriched processed content metadata
        """
        try:
            # List processed content
            processed_blobs = self.storage.list_blobs(
                container_name=BlobContainers.PROCESSED_CONTENT, prefix="processed/"
            )

            # List enriched content
            enriched_blobs = self.storage.list_blobs(
                container_name=BlobContainers.ENRICHED_CONTENT, prefix="enriched/"
            )

            # Extract enriched process IDs
            enriched_process_ids = set()
            for blob in enriched_blobs:
                try:
                    # Download and check source process ID
                    content = self.storage.download_text(
                        BlobContainers.ENRICHED_CONTENT, blob["name"]
                    )
                    enriched_data = json.loads(content)
                    source_id = enriched_data.get("source_data", {}).get("process_id")
                    if source_id:
                        enriched_process_ids.add(source_id)
                except Exception:
                    continue

            # Find unenriched processed content
            unenriched = []
            for blob in processed_blobs[:limit]:
                try:
                    # Download processed data
                    content = self.storage.download_text(
                        BlobContainers.PROCESSED_CONTENT, blob["name"]
                    )
                    processed_data = json.loads(content)
                    process_id = processed_data.get("process_id")

                    if process_id and process_id not in enriched_process_ids:
                        unenriched.append(
                            {
                                "process_id": process_id,
                                "blob_name": blob["name"],
                                "processed_data": processed_data,
                                "processed_at": processed_data.get("timestamp"),
                                "total_items": len(
                                    processed_data.get("processed_items", [])
                                ),
                            }
                        )

                        if len(unenriched) >= limit:
                            break
                except Exception:
                    continue

            return unenriched

        except Exception as e:
            # Return empty list if there are issues
            return []

    def get_service_stats(self) -> Dict[str, Any]:
        """Get current service statistics."""
        return self.stats.copy()
