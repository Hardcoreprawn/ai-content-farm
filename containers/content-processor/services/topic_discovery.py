"""
Topic Discovery Service

Handles finding and filtering available topics for processing.
Extracted from ContentProcessor to improve maintainability.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from models import TopicMetadata, TopicState

from libs.blob_storage import BlobStorageClient

logger = logging.getLogger(__name__)


class TopicDiscoveryService:
    """Service for discovering and filtering available topics from blob storage."""

    def __init__(self, blob_client: Optional[BlobStorageClient] = None):
        self.blob_client = blob_client or BlobStorageClient()

    async def find_available_topics(
        self, batch_size: int, priority_threshold: float
    ) -> List[TopicMetadata]:
        """Find topics available for processing (pure function)."""
        try:
            logger.info(
                f"Searching for topics (batch_size={batch_size}, threshold={priority_threshold})"
            )

            # List all collections from blob storage
            blobs = await self.blob_client.list_blobs("collected-content")
            logger.info(f"Found {len(blobs)} total collections")

            valid_collections = []
            empty_collections = 0

            # Process each collection
            for blob_info in blobs:
                blob_name = blob_info["name"]

                try:
                    # Download and parse collection
                    collection_data = await self.blob_client.download_json(
                        "collected-content", blob_name
                    )

                    # Filter out empty collections
                    if self._is_valid_collection(collection_data):
                        valid_collections.append((blob_name, collection_data))
                        logger.debug(
                            f"Valid collection: {blob_name} ({len(collection_data.get('items', []))} items)"
                        )
                    else:
                        empty_collections += 1
                        logger.debug(f"Skipping empty collection: {blob_name}")

                except Exception as e:
                    logger.warning(f"Error processing collection {blob_name}: {e}")
                    continue

            logger.info(
                f"Found {len(valid_collections)} valid collections, skipped {empty_collections} empty collections"
            )

            # Convert collections to TopicMetadata objects
            topics = []
            for blob_name, collection_data in valid_collections:
                for item in collection_data.get("items", []):
                    topic = self._collection_item_to_topic_metadata(
                        item, blob_name, collection_data
                    )
                    if topic:
                        topics.append(topic)

            # Sort by priority and limit batch size
            topics.sort(key=lambda t: t.priority_score, reverse=True)
            result = topics[:batch_size]

            logger.info(f"Returning {len(result)} topics for processing")
            return result

        except Exception as e:
            logger.error(f"Error finding available topics: {e}")
            return []

    def _is_valid_collection(self, collection_data: Dict[str, Any]) -> bool:
        """
        Check if collection has valid structure and non-empty items.

        Args:
            collection_data: The collection data to validate

        Returns:
            bool: True if collection is valid for processing
        """
        if not isinstance(collection_data, dict):
            return False

        items = collection_data.get("items", [])
        if not isinstance(items, list) or len(items) == 0:
            return False

        # Check if collection has required metadata
        collection_metadata = collection_data.get("metadata", {})
        if not isinstance(collection_metadata, dict):
            return False

        # Validate that items have required fields
        for item in items:
            if not isinstance(item, dict):
                continue
            if not item.get("title") or not item.get("url"):
                continue
            # At least one item is valid
            return True

        return False

    def _collection_item_to_topic_metadata(
        self, item: Dict[str, Any], blob_name: str, collection_data: Dict[str, Any]
    ) -> Optional[TopicMetadata]:
        """
        Convert a collection item to TopicMetadata.

        Args:
            item: Individual item from collection
            blob_name: Name of the collection blob
            collection_data: Full collection data for context

        Returns:
            TopicMetadata object or None if conversion fails
        """
        try:
            # Extract required fields
            title = item.get("title", "").strip()
            url = item.get("url", "").strip()

            if not title or not url:
                return None

            # Calculate priority score
            priority_score = self._calculate_priority_score(item)

            # Create unique topic ID
            topic_id = f"{blob_name}_{hash(url) % 1000000}"

            # Extract metadata
            collection_metadata = collection_data.get("metadata", {})
            source = collection_metadata.get("source", "unknown")
            collected_at_str = collection_metadata.get("collected_at")

            collected_at = None
            if collected_at_str:
                try:
                    collected_at = datetime.fromisoformat(
                        collected_at_str.replace("Z", "+00:00")
                    )
                except (ValueError, AttributeError):
                    collected_at = datetime.now(timezone.utc)
            else:
                collected_at = datetime.now(timezone.utc)

            return TopicMetadata(
                topic_id=topic_id,
                title=title,
                url=url,
                source=source,
                priority_score=priority_score,
                upvotes=item.get("upvotes", 0),
                comments=item.get("comments", 0),
                collected_at=collected_at,
                state=TopicState.AVAILABLE,
            )

        except Exception as e:
            logger.warning(f"Error converting item to TopicMetadata: {e}")
            return None

    def _calculate_priority_score(self, item: Dict[str, Any]) -> float:
        """
        Calculate priority score for a topic based on engagement metrics.

        Pure function that considers:
        - Upvotes/likes (weighted heavily)
        - Comments (engagement indicator)
        - Recency (if available)
        - Content quality indicators

        Args:
            item: The topic item to score

        Returns:
            float: Priority score between 0.0 and 1.0
        """
        try:
            # Base score components
            upvotes = float(item.get("upvotes", 0))
            comments = float(item.get("comments", 0))

            # Normalize upvotes (log scale for viral content)
            upvote_score = min(1.0, (upvotes / 100.0)) if upvotes > 0 else 0.0
            if upvotes > 10:
                upvote_score = min(1.0, 0.5 + (upvotes - 10) / 200.0)

            # Comment engagement score
            comment_score = min(0.3, comments / 50.0) if comments > 0 else 0.0

            # Title quality indicators (length, keywords)
            title = item.get("title", "")
            title_score = 0.0
            if title:
                # Optimal title length bonus
                if 20 <= len(title) <= 100:
                    title_score += 0.1

                # Keyword relevance (simple check)
                engaging_words = [
                    "how",
                    "why",
                    "what",
                    "best",
                    "new",
                    "2024",
                    "2025",
                    "guide",
                    "tips",
                ]
                if any(word in title.lower() for word in engaging_words):
                    title_score += 0.05

            # URL quality check
            url = item.get("url", "")
            url_score = 0.05 if url and len(url) > 10 else 0.0

            # Combine scores with weights
            final_score = (
                upvote_score * 0.6  # Upvotes are primary indicator
                + comment_score * 0.25  # Comments show engagement
                + title_score * 0.1  # Title quality
                + url_score * 0.05  # Basic URL validation
            )

            # Ensure score is between 0.0 and 1.0
            return max(0.0, min(1.0, final_score))

        except (ValueError, TypeError) as e:
            logger.warning(f"Error calculating priority score: {e}")
            return 0.0
