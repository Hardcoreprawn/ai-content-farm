#!/usr/bin/env python3
"""
Service logic for Content Ranker service.

Handles blob storage integration and content ranking pipeline operations.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from ranker import rank_content_items

from libs.blob_storage import BlobContainers, BlobStorageClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ContentRankerService:
    """Service for ranking enriched content."""

    def __init__(self):
        """Initialize the content ranker service."""
        self.blob_client = BlobStorageClient()
        self.enriched_container = BlobContainers.ENRICHED_CONTENT
        self.ranked_container = BlobContainers.RANKED_CONTENT
        logger.info("ContentRankerService initialized")

    async def ensure_containers(self) -> None:
        """Ensure required blob containers exist."""
        containers = [self.enriched_container, self.ranked_container]

        for container in containers:
            try:
                self.blob_client.ensure_container(container)
                logger.info(f"Container '{container}' ready")
            except Exception as e:
                logger.warning(
                    f"Container '{container}' creation failed (may already exist): {e}"
                )

    async def get_enriched_content(
        self, content_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve enriched content from blob storage.

        Args:
            content_id: Optional specific content ID to retrieve

        Returns:
            List of enriched content items
        """
        try:
            if content_id:
                # Get specific content item
                blob_name = f"enriched_{content_id}.json"
                content_data = self.blob_client.download_json(
                    self.enriched_container, blob_name
                )

                if content_data:
                    return [content_data]
                else:
                    logger.warning(f"Content ID {content_id} not found")
                    return []
            else:
                # Get all enriched content
                blob_list = self.blob_client.list_blobs(self.enriched_container)

                content_items = []
                for blob_info in blob_list:
                    blob_name = blob_info["name"]
                    if blob_name.startswith("enriched_") and blob_name.endswith(
                        ".json"
                    ):
                        try:
                            content_item = self.blob_client.download_json(
                                self.enriched_container, blob_name
                            )

                            if content_item:
                                content_items.append(content_item)
                        except Exception as e:
                            logger.error(f"Failed to download {blob_name}: {e}")
                            continue

                logger.info(f"Retrieved {len(content_items)} enriched content items")
                return content_items

        except Exception as e:
            logger.error(f"Failed to retrieve enriched content: {e}")
            raise

    async def rank_content_batch(
        self,
        weights: Optional[Dict[str, float]] = None,
        target_topics: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Rank a batch of enriched content.

        Args:
            weights: Custom weights for ranking factors
            target_topics: Target topics for relevance scoring
            limit: Maximum number of items to return

        Returns:
            Dictionary with ranking results and metadata
        """
        try:
            # Get all enriched content
            enriched_items = await self.get_enriched_content()

            if not enriched_items:
                logger.warning("No enriched content found for ranking")
                return {
                    "ranked_items": [],
                    "total_processed": 0,
                    "ranking_metadata": {
                        "timestamp": datetime.utcnow().isoformat(),
                        "weights": weights,
                        "target_topics": target_topics,
                        "limit": limit,
                    },
                }

            # Perform ranking
            ranked_items = rank_content_items(
                content_items=enriched_items,
                weights=weights,
                target_topics=target_topics,
                limit=limit,
            )

            # Store ranked content in blob storage
            await self._store_ranked_content(ranked_items)

            logger.info(f"Successfully ranked {len(ranked_items)} content items")

            return {
                "ranked_items": ranked_items,
                "total_processed": len(enriched_items),
                "ranking_metadata": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "weights": weights,
                    "target_topics": target_topics,
                    "limit": limit,
                    "items_returned": len(ranked_items),
                },
            }

        except Exception as e:
            logger.error(f"Failed to rank content batch: {e}")
            raise

    async def rank_specific_content(
        self,
        content_items: List[Dict[str, Any]],
        weights: Optional[Dict[str, float]] = None,
        target_topics: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Rank specific content items.

        Args:
            content_items: List of content items to rank
            weights: Custom weights for ranking factors
            target_topics: Target topics for relevance scoring
            limit: Maximum number of items to return

        Returns:
            List of ranked content items
        """
        try:
            if not content_items:
                logger.warning("No content items provided for ranking")
                return []

            # Perform ranking
            ranked_items = rank_content_items(
                content_items=content_items,
                weights=weights,
                target_topics=target_topics,
                limit=limit,
            )

            logger.info(
                f"Successfully ranked {len(ranked_items)} specific content items"
            )
            return ranked_items

        except Exception as e:
            logger.error(f"Failed to rank specific content: {e}")
            raise

    async def _store_ranked_content(self, ranked_items: List[Dict[str, Any]]) -> None:
        """
        Store ranked content in blob storage.

        Args:
            ranked_items: List of ranked content items
        """
        try:
            # Store individual ranked items
            for item in ranked_items:
                content_id = item.get("id", "unknown")
                blob_name = f"ranked_{content_id}.json"

                self.blob_client.upload_json(
                    container_name=self.ranked_container, blob_name=blob_name, data=item
                )

            # Store batch results
            batch_blob_name = (
                f"ranked_batch_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            )
            batch_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "total_items": len(ranked_items),
                "ranked_items": ranked_items,
            }

            self.blob_client.upload_json(
                container_name=self.ranked_container,
                blob_name=batch_blob_name,
                data=batch_data,
            )

            logger.info(f"Stored {len(ranked_items)} ranked items in blob storage")

        except Exception as e:
            logger.error(f"Failed to store ranked content: {e}")
            raise

    async def get_ranking_status(self) -> Dict[str, Any]:
        """
        Get status information for the ranking service.

        Returns:
            Dictionary with status information
        """
        try:
            # Count enriched content
            enriched_blobs = self.blob_client.list_blobs(self.enriched_container)
            enriched_count = len(
                [b for b in enriched_blobs if b["name"].startswith("enriched_")]
            )

            # Count ranked content
            ranked_blobs = self.blob_client.list_blobs(self.ranked_container)
            ranked_count = len(
                [b for b in ranked_blobs if b["name"].startswith("ranked_")]
            )

            return {
                "service": "content-ranker",
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "content_stats": {
                    "enriched_items_available": enriched_count,
                    "ranked_items_stored": ranked_count,
                },
                "containers": {
                    "enriched_content": self.enriched_container,
                    "ranked_content": self.ranked_container,
                },
            }

        except Exception as e:
            logger.error(f"Failed to get ranking status: {e}")
            return {
                "service": "content-ranker",
                "status": "error",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
            }
