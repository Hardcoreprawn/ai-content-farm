"""
Topic Discovery Service

Handles finding and filtering available topics for pro                    processed_col                    processed_collections += 1ions += 1

                    # Process items in the collection
                    items = collection_data.get("items", [])
                    logger.info(f"📋 ITEMS: Found {len(items)} items in {blob_name}")

                    if debug_bypass:
                        # In debug mode, process raw items without validation
                        for idx, item_data in enumerate(items):
                            topic = self._raw_item_to_topic_metadata(item_data, blob_name, debug_bypass=True)
                            if topic:
                                topics.append(topic)
                                logger.info(f"🔧 DEBUG-RAW: Added topic {idx+1}/{len(items)}: {topic.title[:50]}...")
                    else:
                        # Normal mode: validate with data contracts
                        try:
                            validated_collection = ContractValidator.validate_collection_data(collection_data)
                            logger.info(f"✅ CONTRACT: Successfully validated collection with {len(validated_collection.items)} items")

                            # Process validated items
                            for idx, item in enumerate(validated_collection.items):
                                topic = self._validated_item_to_topic_metadata(item, blob_name)
                                if topic:
                                    topics.append(topic)
                                    logger.info(f"📄 ITEM-{idx}: Added validated topic: {topic.title[:50]}...")
                        except DataContractError as e:
                            logger.error(f"❌ CONTRACT: Collection {blob_name} failed validation: {e}")
                            continue

                except Exception as e:
                    logger.error(f"❌ PROCESSING: Unexpected error processing {blob_name}: {e}")
                    continue

            logger.info(f"📊 SUMMARY: Processed {processed_collections} collections, skipped {skipped_collections}, found {len(topics)} total topics")ing.
Extracted from ContentProcessor to improve maintainability.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from models import TopicMetadata, TopicState

from libs.app_config import BlobContainers
from libs.data_contracts import ContractValidator, DataContractError
from libs.extended_data_contracts import DataContractError as ExtendedDataContractError
from libs.extended_data_contracts import (
    ExtendedContractValidator,
)
from libs.simplified_blob_client import SimplifiedBlobClient

logger = logging.getLogger(__name__)


class TopicDiscoveryService:
    """Service for discovering and filtering available topics from blob storage."""

    def __init__(
        self,
        blob_client: Optional[SimplifiedBlobClient] = None,
        input_container: str = BlobContainers.COLLECTED_CONTENT,
    ):
        self.blob_client = blob_client or SimplifiedBlobClient()
        self.input_container = input_container

    async def find_available_topics(
        self, batch_size: int, priority_threshold: float, debug_bypass: bool = False
    ) -> List[TopicMetadata]:
        """Find topics available for processing (pure function).

        Args:
            batch_size: Maximum number of topics to return
            priority_threshold: Minimum priority score required
            debug_bypass: If True, bypass all filtering for diagnosis
        """
        try:
            logger.info(
                f"🔍 TOPIC-DISCOVERY: Searching for topics (batch_size={batch_size}, threshold={priority_threshold}, debug_bypass={debug_bypass})"
            )

            # List all collections from blob storage using standardized paths
            logger.info(
                "📂 BLOB-STORAGE: Connecting to blob storage to list collections..."
            )
            # Use the collections/ prefix to find all collections in the standardized path structure
            blobs = await self.blob_client.list_blobs(
                self.input_container, prefix="collections/"
            )
            logger.info(
                f"📂 BLOB-STORAGE: Found {len(blobs)} total collection blobs in collections/ path"
            )

            if blobs:
                logger.info(
                    f"📋 BLOB-LIST: Recent collections found: {[b['name'] for b in blobs[-3:]]}"
                )
            else:
                logger.warning(
                    f"⚠️ BLOB-STORAGE: No collections found in {self.input_container}/collections/ path!"
                )

            # Process each collection file
            topics = []
            processed_collections = 0
            skipped_collections = 0

            for blob in blobs:
                try:
                    blob_name = blob["name"]
                    logger.info(f"📄 PROCESSING: {blob_name}")

                    # Download and parse collection
                    collection_data = await self.blob_client.download_json(
                        self.input_container, blob_name
                    )

                    # Validate collection structure (bypass in debug mode)
                    if not debug_bypass and not self._is_valid_collection(
                        collection_data
                    ):
                        logger.warning(
                            f"⚠️ VALIDATION: Skipping invalid collection: {blob_name}"
                        )
                        skipped_collections += 1
                        continue
                    elif debug_bypass:
                        logger.info(
                            f"🔧 DEBUG-BYPASS: Skipping validation for {blob_name}"
                        )

                    processed_collections += 1

                    # Process items in the collection
                    items = collection_data.get("items", [])
                    logger.info(f"� ITEMS: Found {len(items)} items in {blob_name}")

                    if debug_bypass:
                        # In debug mode, process raw items without validation
                        for idx, item_data in enumerate(items):
                            topic = self._raw_item_to_topic_metadata(
                                item_data, blob_name, debug_bypass=True
                            )
                            if topic:
                                topics.append(topic)
                                logger.info(
                                    f"🔧 DEBUG-RAW: Added topic {idx+1}/{len(items)}: {topic.title[:50]}..."
                                )
                    else:
                        # Normal mode: validate with enhanced data contracts
                        try:
                            # Try enhanced contracts first, fallback to legacy
                            validated_collection = None
                            provenance_entries = []

                            try:
                                # Try enhanced contracts first
                                enhanced_result = (
                                    ExtendedContractValidator.validate_collection_data(
                                        collection_data
                                    )
                                )
                                # ExtendedCollectionResult has items attribute
                                validated_collection = enhanced_result
                                # Extract provenance from collection metadata and items
                                provenance_entries = (
                                    enhanced_result.metadata.collection_provenance.copy()
                                    if enhanced_result.metadata.collection_provenance
                                    else []
                                )
                                # Add item-level provenance
                                for item in enhanced_result.items:
                                    if item.provenance:
                                        provenance_entries.extend(item.provenance)
                                logger.info(
                                    f"✅ ENHANCED-CONTRACT: Successfully validated collection with {len(enhanced_result.items)} items and {len(provenance_entries)} provenance entries"
                                )
                            except (
                                ExtendedDataContractError,
                                AttributeError,
                            ) as enhanced_error:
                                logger.info(
                                    f"📄 FALLBACK: Enhanced validation failed ({enhanced_error}), trying legacy contracts..."
                                )
                                # Fallback to legacy contracts
                                validated_collection = (
                                    ContractValidator.validate_collection_data(
                                        collection_data
                                    )
                                )
                                logger.info(
                                    f"✅ LEGACY-CONTRACT: Successfully validated collection with {len(validated_collection.items)} items"
                                )

                            # Process validated items - works for both enhanced and legacy
                            for idx, item in enumerate(validated_collection.items):
                                topic = self._validated_item_to_topic_metadata(
                                    item, blob_name, provenance_entries
                                )
                                if topic:
                                    topics.append(topic)
                                    logger.info(
                                        f"📄 ITEM-{idx}: Added validated topic: {topic.title[:50]}..."
                                    )

                        except (DataContractError, ExtendedDataContractError) as e:
                            logger.error(
                                f"❌ CONTRACT: Collection {blob_name} failed all validation attempts: {e}"
                            )
                            continue

                except Exception as e:
                    logger.error(
                        f"❌ PROCESSING: Unexpected error processing {blob_name}: {e}"
                    )
                    continue

            logger.info(
                f"📊 SUMMARY: Processed {processed_collections} collections, skipped {skipped_collections}, found {len(topics)} total topics"
            )

            # Sort by priority and limit batch size (bypass filtering in debug mode)
            if debug_bypass:
                logger.info(
                    f"🔧 DEBUG-BYPASS: Found {len(topics)} raw topics, returning first {min(batch_size, len(topics))}"
                )
                result = topics[:batch_size]
            else:
                # Apply priority filtering
                filtered_topics = [
                    t for t in topics if t.priority_score >= priority_threshold
                ]
                logger.info(
                    f"📊 FILTERING: {len(topics)} total topics, {len(filtered_topics)} above threshold {priority_threshold}"
                )
                filtered_topics.sort(key=lambda t: t.priority_score, reverse=True)
                result = filtered_topics[:batch_size]

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
        self, item, blob_name: str, provenance_entries: List = None
    ) -> Optional[TopicMetadata]:
        """Convert validated CollectionItem or ContentItem to TopicMetadata with enhanced metadata support."""
        try:
            # Handle both legacy CollectionItem and enhanced ContentItem
            is_enhanced = hasattr(item, "source") and hasattr(
                item.source, "source_type"
            )

            if is_enhanced:
                # Enhanced ContentItem - extract data from SourceMetadata
                source_str = item.source.source_type
                collected_at = item.source.collected_at
                upvotes = item.source.upvotes or 0
                comments = item.source.comments or 0
                subreddit = None
                if item.source.reddit_data:
                    subreddit = item.source.reddit_data.get("subreddit")
                logger.info(
                    f"📋 ENHANCED-ITEM: Processing enhanced ContentItem {item.id}"
                )
            else:
                # Legacy CollectionItem - direct attribute access
                source_str = item.source
                collected_at = item.collected_at
                upvotes = item.upvotes or 0
                comments = item.comments or 0
                subreddit = getattr(item, "subreddit", None)
                logger.info(
                    f"📋 LEGACY-ITEM: Processing legacy CollectionItem {item.id}"
                )

            # Calculate priority score
            priority_score = self._calculate_priority_score_from_validated_item(item)

            # Create base TopicMetadata
            topic_metadata = TopicMetadata(
                topic_id=item.id,
                title=item.title,
                source=source_str,
                collected_at=collected_at,
                priority_score=priority_score,
                subreddit=subreddit,
                url=item.url,
                upvotes=upvotes,
                comments=comments,
            )

            # If enhanced contracts are available, extract additional metadata
            if is_enhanced:
                enhanced_metadata = {
                    "is_enhanced": True,
                    "source_metadata": item.source,
                    "provenance_entries": provenance_entries or [],
                    "quality_score": getattr(item, "quality_score", None),
                    "relevance_score": getattr(item, "relevance_score", None),
                    "engagement_score": getattr(item, "engagement_score", None),
                    "topics": getattr(item, "topics", []),
                    "keywords": getattr(item, "keywords", []),
                    "entities": getattr(item, "entities", []),
                    "sentiment": getattr(item, "sentiment", None),
                }

                if hasattr(item, "custom_fields") and item.custom_fields:
                    enhanced_metadata["custom_fields"] = item.custom_fields
                    logger.info(
                        f"📋 ENHANCED: Found custom fields for topic {item.id}: {list(item.custom_fields.keys())}"
                    )

                # Store enhanced metadata for later use in article generation
                topic_metadata.__dict__["enhanced_metadata"] = enhanced_metadata
                logger.info(
                    f"📋 SOURCE-META: Enhanced metadata stored for topic {item.id}"
                )

            return topic_metadata

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
        """Calculate priority score from validated CollectionItem or ContentItem."""
        try:
            # TEMPORARY: Accept everything mode for pipeline testing
            # Start with a high base score for all content
            base_score = 0.6  # Give everything a decent base score

            # Handle both legacy and enhanced formats
            is_enhanced = hasattr(item, "source") and hasattr(
                item.source, "source_type"
            )

            if is_enhanced:
                # Enhanced ContentItem - extract from SourceMetadata
                upvotes = float(item.source.upvotes or 0)
                comments = float(item.source.comments or 0)
                collected_at = item.source.collected_at
            else:
                # Legacy CollectionItem - direct access
                upvotes = float(item.upvotes or 0)
                comments = float(item.comments or 0)
                collected_at = item.collected_at

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
            if collected_at:
                hours_ago = (
                    datetime.now(timezone.utc) - collected_at
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

    def _raw_item_to_topic_metadata(
        self, item_data: Dict[str, Any], blob_name: str, debug_bypass: bool = False
    ) -> Optional[TopicMetadata]:
        """
        Create TopicMetadata from raw item data for debug bypass mode.
        Minimal validation, just ensure basic fields exist.
        """
        try:
            title = item_data.get("title", "NO_TITLE")
            url = item_data.get("url", "")
            content = item_data.get("content", "")

            # In debug mode, use high priority score to ensure processing
            priority_score = 0.9 if debug_bypass else 0.5

            logger.info(
                f"🔧 DEBUG-RAW: Creating topic for '{title[:50]}...' with score {priority_score}"
            )

            return TopicMetadata(
                id=item_data.get("id", f"raw_{blob_name}_{title[:20]}"),
                title=title,
                url=url,
                content=content,
                source=item_data.get("source", "unknown"),
                priority_score=priority_score,
                # Use current time if missing
                collected_at=datetime.now(timezone.utc),
                upvotes=item_data.get("upvotes", 0),
                comments=item_data.get("comments", 0),
                state=TopicState.PENDING,
            )

        except Exception as e:
            logger.warning(f"Error creating raw TopicMetadata: {e}")
            return None
