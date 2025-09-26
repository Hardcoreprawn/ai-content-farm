"""
Topic Discovery Service

Handles finding and filtering available topics for processing.
Extracted from ContentProcessor to improve maintainability.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from models import TopicMetadata, TopicState

from libs.data_contracts import ContractValidator, DataContractError
from libs.simplified_blob_client import SimplifiedBlobClient

logger = logging.getLogger(__name__)


class TopicDiscoveryService:
    """Service for discovering and filtering available topics from blob storage."""

    def __init__(self, blob_client: Optional[SimplifiedBlobClient] = None):
        self.blob_client = blob_client or SimplifiedBlobClient()

    async def find_available_topics(
        self, batch_size: int, priority_threshold: float
    ) -> List[TopicMetadata]:
        """Find topics available for processing (pure function)."""
        try:
            logger.info(
                f"🔍 TOPIC-DISCOVERY: Searching for topics (batch_size={batch_size}, threshold={priority_threshold})"
            )

            # List all collections from blob storage
            logger.info(
                "📂 BLOB-STORAGE: Connecting to blob storage to list collections..."
            )
            blobs = await self.blob_client.list_blobs("collected-content")
            logger.info(f"📂 BLOB-STORAGE: Found {len(blobs)} total collection blobs")

            if blobs:
                logger.info(
                    f"📋 BLOB-LIST: Recent collections found: {[b['name'] for b in blobs[-3:]]}"
                )
            else:
                logger.warning(
                    "⚠️ BLOB-STORAGE: No collections found in collected-content container!"
                )

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

            # Convert collections to TopicMetadata objects using data contracts
            topics = []
            for blob_name, collection_data in valid_collections:
                logger.info(
                    f"📄 PROCESSING: Collection {blob_name} - validating with data contracts"
                )

                try:
                    # Use contract validator to ensure consistent data structure
                    validated_collection = ContractValidator.validate_collection_data(
                        collection_data
                    )
                    logger.info(
                        f"✅ CONTRACT: Successfully validated collection with {len(validated_collection.items)} items"
                    )

                    # Process validated items
                    for idx, item in enumerate(validated_collection.items):
                        logger.info(
                            f"📄 ITEM-{idx}: Processing validated item: {item.title[:50]}..."
                        )
                        topic = self._validated_item_to_topic_metadata(item, blob_name)
                        if topic:
                            topics.append(topic)

                except DataContractError as e:
                    logger.error(
                        f"❌ CONTRACT: Collection {blob_name} failed validation: {e}"
                    )
                    continue
                except Exception as e:
                    logger.error(
                        f"❌ PROCESSING: Unexpected error processing {blob_name}: {e}"
                    )
                    continue

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

    def _validated_item_to_topic_metadata(
        self, item, blob_name: str
    ) -> Optional[TopicMetadata]:
        """Convert validated CollectionItem to TopicMetadata."""
        try:
            # Calculate priority score
            priority_score = self._calculate_priority_score_from_validated_item(item)

            return TopicMetadata(
                topic_id=item.id,
                title=item.title,
                source=item.source,
                collected_at=item.collected_at,
                priority_score=priority_score,
                subreddit=item.subreddit,
                url=item.url,
                upvotes=item.upvotes,
                comments=item.comments,
            )

        except Exception as e:
            logger.error(f"Error converting validated item to topic metadata: {e}")
            return None

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
            logger.debug(f"🔄 CONVERTING: Item type: {type(item)}, value: {item}")

            # Check if item is actually a dictionary
            if not isinstance(item, dict):
                logger.warning(
                    f"⚠️ CONVERT-ERROR: Item is not a dict, it's {type(item)}: {item}"
                )
                return None

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
        TEMPORARY: Accept everything mode for pipeline testing.

        Args:
            item: The topic item to score

        Returns:
            float: Priority score between 0.5 and 1.0 (high acceptance)
        """
        try:
            # TEMPORARY: Accept everything mode - give high base score
            base_score = 0.6

            # Base score components (bonuses on top of base)
            upvotes = float(item.get("upvotes", 0))
            comments = float(item.get("comments", 0))

            # Reddit engagement bonuses
            upvote_bonus = min(0.2, upvotes / 100.0) if upvotes > 0 else 0.0
            comment_bonus = min(0.1, comments / 50.0) if comments > 0 else 0.0

            # Title quality indicators (generous)
            title = item.get("title", "")
            title_bonus = 0.0
            if title:
                # Any reasonable title length gets bonus
                if 10 <= len(title) <= 200:
                    title_bonus += 0.1

                # Expanded engaging keywords
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
                    "breakthrough",
                    "revolutionary",
                    "discovered",
                    "reveals",
                    "major",
                    "ai",
                    "tech",
                    "technology",
                    "science",
                    "future",
                    "innovation",
                ]
                if any(word in title.lower() for word in engaging_words):
                    title_bonus += 0.1

            # URL quality check (generous)
            url = item.get("url", "")
            url_bonus = 0.05 if url and len(url) > 10 else 0.0

            # Combine with generous scoring
            final_score = (
                base_score + upvote_bonus + comment_bonus + title_bonus + url_bonus
            )

            # Ensure score is between 0.5 and 1.0 (minimum 0.5 for all content)
            return max(0.5, min(1.0, final_score))

        except (ValueError, TypeError) as e:
            logger.warning(f"Error calculating priority score: {e}")
            return 0.0

    def _calculate_priority_score_from_validated_item(self, item) -> float:
        """Calculate priority score from validated CollectionItem."""
        try:
            # TEMPORARY: Accept everything mode for pipeline testing
            # Start with a high base score for all content
            base_score = 0.6  # Give everything a decent base score

            # Extract metrics with proper defaults
            upvotes = float(item.upvotes or 0)
            comments = float(item.comments or 0)

            # Reddit content bonuses (on top of base score)
            upvote_bonus = min(0.2, upvotes / 100.0) if upvotes > 0 else 0.0
            comment_bonus = min(0.1, comments / 50.0) if comments > 0 else 0.0

            # Title quality indicators (generous scoring)
            title_bonus = 0.0
            if item.title:
                # Any reasonable title length gets a bonus
                if 10 <= len(item.title) <= 200:
                    title_bonus += 0.1

                # Many engaging keywords (expanded list)
                engaging_words = [
                    "breakthrough",
                    "new",
                    "revolutionary",
                    "discovered",
                    "reveals",
                    "major",
                    "first",
                    "unprecedented",
                    "study",
                    "research",
                    "how",
                    "why",
                    "what",
                    "best",
                    "guide",
                    "tips",
                    "amazing",
                    "incredible",
                    "shocking",
                    "must",
                    "should",
                    "could",
                    "will",
                    "ai",
                    "tech",
                    "technology",
                    "science",
                    "future",
                    "innovation",
                ]
                if any(word in item.title.lower() for word in engaging_words):
                    title_bonus += 0.1

            # URL quality check (generous)
            url_bonus = 0.05 if item.url and len(item.url) > 10 else 0.0

            # Freshness bonus - all recent content is good
            freshness_bonus = 0.0
            if item.collected_at:
                hours_ago = (
                    datetime.now(timezone.utc) - item.collected_at
                ).total_seconds() / 3600
                if hours_ago < 48:  # Extended to 48 hours
                    freshness_bonus = 0.15  # Fixed bonus for recent content

            # Combine with generous scoring
            final_score = (
                base_score  # High base score for all content
                + upvote_bonus  # Reddit engagement bonus
                + comment_bonus  # Comment engagement bonus
                + title_bonus  # Title quality bonus
                + url_bonus  # URL validation bonus
                + freshness_bonus  # Freshness bonus
            )

            # Ensure score is between 0.0 and 1.0
            # Minimum 0.5 for all content
            final_score = max(0.5, min(1.0, final_score))

            logger.debug(
                f"Priority score for '{item.title[:30]}...': {final_score:.2f}"
            )
            return final_score

        except Exception as e:
            logger.warning(f"Error calculating priority score from validated item: {e}")
            return 0.5  # Default to 0.5 instead of 0.0
