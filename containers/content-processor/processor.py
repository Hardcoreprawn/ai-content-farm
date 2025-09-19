"""
Content Processor Core Logic

Functional processor implementing wake-up work queue pattern with:
- Lease-based coordination for parallel processing
- Azure OpenAI integration for article generation
- Cost tracking and quality assessment
- Immutable data patterns for thread safety
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from models import (
    ProcessingAttempt,
    ProcessingResult,
    ProcessorStatus,
    TopicMetadata,
    TopicState,
)
from openai_client import OpenAIClient

from libs.blob_storage import BlobStorageClient

logger = logging.getLogger(__name__)


class ContentProcessor:
    """
    Functional content processor with lease-based coordination.

    Implements pure functional patterns for thread safety and scalability.
    """

    def __init__(self):
        self.processor_id = str(uuid4())[:8]
        self.session_id = str(uuid4())
        self.blob_client = BlobStorageClient()
        self.openai_client = OpenAIClient()

        # Session tracking (immutable append-only)
        self.session_start = datetime.now(timezone.utc)
        self.session_topics_processed = 0
        self.session_cost = 0.0
        self.session_processing_time = 0.0

        logger.info(f"Content processor initialized: {self.processor_id}")

    async def check_health(self) -> ProcessorStatus:
        """Health check with dependency validation."""
        try:
            # Test blob storage
            blob_available = await self._test_blob_storage()

            # Test OpenAI
            openai_available = await self._test_openai()

            # Determine overall status
            if blob_available and openai_available:
                status = "idle"
            else:
                status = "error"

            return ProcessorStatus(
                processor_id=self.processor_id,
                status=status,
                azure_openai_available=openai_available,
                blob_storage_available=blob_available,
                last_health_check=datetime.now(timezone.utc),
            )

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return ProcessorStatus(
                processor_id=self.processor_id,
                status="error",
                azure_openai_available=False,
                blob_storage_available=False,
                last_health_check=datetime.now(timezone.utc),
            )

    async def get_status(self) -> ProcessorStatus:
        """Get current processor status."""
        return ProcessorStatus(
            processor_id=self.processor_id,
            status="idle",  # Simplified for now
            session_topics_processed=self.session_topics_processed,
            session_cost=self.session_cost,
            session_processing_time=self.session_processing_time,
            azure_openai_available=True,  # Will be checked by health endpoint
            blob_storage_available=True,
            last_health_check=datetime.now(timezone.utc),
        )

    async def process_available_work(
        self,
        batch_size: int = 10,
        priority_threshold: float = 0.5,
        options: Optional[Dict[str, Any]] = None,
    ) -> ProcessingResult:
        """
        Process available work using wake-up work queue pattern.

        Pure functional approach:
        1. Find available topics (no mutation)
        2. Lease topics atomically
        3. Process topics functionally
        4. Update results immutably
        """
        start_time = datetime.now(timezone.utc)
        processed_topics = []
        failed_topics = []
        total_cost = 0.0

        try:
            # Phase 1: Find available topics
            available_topics = await self._find_available_topics(
                batch_size, priority_threshold
            )

            if not available_topics:
                logger.info("No topics available for processing")
                return ProcessingResult(
                    success=True,
                    topics_processed=0,
                    articles_generated=0,
                    total_cost=0.0,
                    processing_time=0.0,
                )

            logger.info(f"Found {len(available_topics)} topics for processing")

            # Phase 2: Process each topic with lease coordination
            for topic_metadata in available_topics:
                try:
                    # Attempt to lease topic
                    if await self._acquire_topic_lease(topic_metadata.topic_id):
                        result = await self._process_single_topic(topic_metadata)

                        if result:
                            processed_topics.append(topic_metadata.topic_id)
                            total_cost += result.get("cost", 0.0)
                        else:
                            failed_topics.append(topic_metadata.topic_id)

                        # Release lease
                        await self._release_topic_lease(topic_metadata.topic_id)

                except Exception as e:
                    logger.error(
                        f"Error processing topic {topic_metadata.topic_id}: {e}"
                    )
                    failed_topics.append(topic_metadata.topic_id)
                    await self._release_topic_lease(topic_metadata.topic_id)

            # Update session metrics (immutable append pattern)
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            self.session_topics_processed += len(processed_topics)
            self.session_cost += total_cost
            self.session_processing_time += processing_time

            return ProcessingResult(
                success=True,
                topics_processed=len(processed_topics),
                articles_generated=len(processed_topics),  # 1:1 for now
                total_cost=total_cost,
                processing_time=processing_time,
                completed_topics=processed_topics,
                failed_topics=failed_topics,
            )

        except Exception as e:
            logger.error(f"Work processing failed: {e}", exc_info=True)
            return ProcessingResult(
                success=False,
                topics_processed=0,
                articles_generated=0,
                total_cost=total_cost,
                processing_time=0.0,
                failed_topics=failed_topics,
                error_messages=[str(e)],
            )

    async def process_specific_topics(
        self,
        topic_ids: List[str],
        force_reprocess: bool = False,
        options: Optional[Dict[str, Any]] = None,
    ) -> ProcessingResult:
        """Process specific topics by ID (manual batch processing)."""
        # Simplified implementation for now
        logger.info(f"Manual processing requested for {len(topic_ids)} topics")

        return ProcessingResult(
            success=True,
            topics_processed=0,
            articles_generated=0,
            total_cost=0.0,
            processing_time=0.0,
            completed_topics=[],
            failed_topics=topic_ids,  # Mark as failed until implemented
            error_messages=["Manual processing not yet implemented"],
        )

    # Private helper methods (functional)

    async def _find_available_topics(
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
        """Check if collection contains actual content worth processing."""
        if not collection_data:
            return False

        metadata = collection_data.get("metadata", {})
        items = collection_data.get("items", [])

        # Skip empty collections
        if metadata.get("total_collected", 0) == 0:
            return False

        if len(items) == 0:
            return False

        # Skip collections with only errors (all keys end with "_error")
        source_breakdown = metadata.get("source_breakdown", {})
        if source_breakdown and all(
            key.endswith("_error") for key in source_breakdown.keys()
        ):
            return False

        return True

    def _collection_item_to_topic_metadata(
        self, item: Dict[str, Any], blob_name: str, collection_data: Dict[str, Any]
    ) -> Optional[TopicMetadata]:
        """Convert a collection item to TopicMetadata."""
        try:
            # Extract basic information
            topic_id = item.get("id", f"unknown_{blob_name}")
            title = item.get("title", "Untitled Topic")
            source = item.get("source", "unknown")

            # Parse collected_at timestamp
            collected_at_str = item.get("collected_at") or collection_data.get(
                "metadata", {}
            ).get("timestamp")
            if collected_at_str:
                collected_at = datetime.fromisoformat(
                    collected_at_str.replace("Z", "+00:00")
                )
            else:
                collected_at = datetime.now(timezone.utc)

            # Calculate priority score based on content characteristics
            priority_score = self._calculate_priority_score(item)

            return TopicMetadata(
                topic_id=topic_id,
                title=title,
                source=source,
                collected_at=collected_at,
                priority_score=priority_score,
                subreddit=item.get("subreddit"),  # Optional field
                url=item.get("url"),
                upvotes=item.get("ups") or item.get("upvotes"),
                comments=item.get("num_comments") or item.get("comments"),
            )

        except Exception as e:
            logger.warning(f"Error converting item to TopicMetadata: {e}")
            return None

    def _calculate_priority_score(self, item: Dict[str, Any]) -> float:
        """Calculate priority score for a topic based on engagement and freshness."""
        try:
            score = 0.0

            # Base score from upvotes/score
            item_score = item.get("score", 0)
            if item_score > 0:
                score += min(
                    item_score / 100.0, 1.0
                )  # Normalize to 0-1, cap at 100 upvotes

            # Bonus for comments (engagement)
            num_comments = item.get("num_comments", 0)
            if num_comments > 0:
                score += min(
                    num_comments / 50.0, 0.5
                )  # Up to 0.5 bonus, cap at 50 comments

            # Freshness bonus (items collected more recently get higher priority)
            collected_at_str = item.get("collected_at")
            if collected_at_str:
                try:
                    collected_at = datetime.fromisoformat(
                        collected_at_str.replace("Z", "+00:00")
                    )
                    hours_ago = (
                        datetime.now(timezone.utc) - collected_at
                    ).total_seconds() / 3600
                    # Freshness bonus decreases over 24 hours
                    if hours_ago < 24:
                        freshness_bonus = (24 - hours_ago) / 24 * 0.3  # Up to 0.3 bonus
                        score += freshness_bonus
                except Exception:
                    pass  # Skip freshness bonus if timestamp parsing fails

            # Ensure score is between 0 and 1
            return max(0.0, min(score, 1.0))

        except Exception as e:
            logger.warning(f"Error calculating priority score: {e}")
            return 0.5  # Default score

    async def _acquire_topic_lease(self, topic_id: str) -> bool:
        """Atomically acquire lease on topic (pure function)."""
        try:
            # Mock implementation - always succeeds for now
            logger.debug(f"Acquired lease for topic: {topic_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to acquire lease for {topic_id}: {e}")
            return False

    async def _release_topic_lease(self, topic_id: str) -> bool:
        """Release topic lease (pure function)."""
        try:
            # Mock implementation
            logger.debug(f"Released lease for topic: {topic_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to release lease for {topic_id}: {e}")
            return False

    async def _process_single_topic(
        self, topic_metadata: TopicMetadata
    ) -> Optional[Dict[str, Any]]:
        """Process a single topic into an article using Azure OpenAI."""
        try:
            logger.info(f"Processing topic: {topic_metadata.title}")
            start_time = datetime.now(timezone.utc)

            # Prepare research content from the topic
            research_content = self._prepare_research_content(topic_metadata)

            # Generate article using OpenAI
            article_content, cost_usd, tokens_used = (
                await self.openai_client.generate_article(
                    topic_title=topic_metadata.title,
                    research_content=research_content,
                    target_word_count=3000,
                    quality_requirements={
                        "source": topic_metadata.source,
                        "priority_score": topic_metadata.priority_score,
                        "engagement": f"{topic_metadata.upvotes or 0} upvotes, {topic_metadata.comments or 0} comments",
                    },
                )
            )

            if not article_content:
                logger.error(
                    f"Failed to generate article for topic: {topic_metadata.title}"
                )
                return None

            # Calculate article metadata
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            word_count = len(article_content.split())
            quality_score = self._calculate_quality_score(article_content, word_count)

            # Prepare article result
            article_result = {
                "topic_id": topic_metadata.topic_id,
                "title": topic_metadata.title,
                "article_content": article_content,
                "word_count": word_count,
                "quality_score": quality_score,
                "cost": cost_usd,
                "tokens_used": tokens_used,
                "processing_time": processing_time,
                "source_priority": topic_metadata.priority_score,
                "source": topic_metadata.source,
                "original_url": topic_metadata.url,
                "generated_at": start_time.isoformat(),
                "metadata": {
                    "processor_id": self.processor_id,
                    "session_id": self.session_id,
                    "openai_model": getattr(
                        self.openai_client, "model_name", "unknown"
                    ),
                    "original_upvotes": topic_metadata.upvotes or 0,
                    "original_comments": topic_metadata.comments or 0,
                    "content_type": "generated_article",
                },
            }

            # Save to processed-content container
            await self._save_processed_article(article_result)

            logger.info(
                f"Article generated successfully: {word_count} words, "
                f"${cost_usd:.4f} cost, {processing_time:.2f}s processing time"
            )

            return {
                "article_content": article_content,
                "word_count": word_count,
                "quality_score": quality_score,
                "cost": cost_usd,
            }

        except Exception as e:
            logger.error(f"Error processing topic {topic_metadata.topic_id}: {e}")
            return None

    def _prepare_research_content(self, topic_metadata: TopicMetadata) -> str:
        """Prepare research content from topic metadata for article generation."""
        try:
            research_parts = []

            # Add basic topic information
            research_parts.append(f"Title: {topic_metadata.title}")
            research_parts.append(f"Source: {topic_metadata.source}")

            if topic_metadata.url:
                research_parts.append(f"Original URL: {topic_metadata.url}")

            if topic_metadata.subreddit:
                research_parts.append(f"Subreddit: r/{topic_metadata.subreddit}")

            # Add engagement metrics
            engagement_info = []
            if topic_metadata.upvotes is not None:
                engagement_info.append(f"{topic_metadata.upvotes} upvotes")
            if topic_metadata.comments is not None:
                engagement_info.append(f"{topic_metadata.comments} comments")

            if engagement_info:
                research_parts.append(f"Engagement: {', '.join(engagement_info)}")

            research_parts.append(
                f"Priority Score: {topic_metadata.priority_score:.2f}"
            )
            research_parts.append(
                f"Collected At: {topic_metadata.collected_at.isoformat()}"
            )

            return "\n".join(research_parts)

        except Exception as e:
            logger.error(f"Error preparing research content: {e}")
            return f"Title: {topic_metadata.title}\nSource: {topic_metadata.source}"

    def _calculate_quality_score(self, article_content: str, word_count: int) -> float:
        """Calculate quality score for generated article."""
        try:
            score = 0.0

            # Base score for having content
            if article_content and word_count > 0:
                score += 0.3

            # Word count score (target ~3000 words)
            if word_count >= 2000:
                score += 0.3
            elif word_count >= 1000:
                score += 0.2
            elif word_count >= 500:
                score += 0.1

            # Structure score (check for headings and sections)
            if article_content:
                # Count headers
                header_count = article_content.count("#")
                if header_count >= 3:
                    score += 0.2
                elif header_count >= 1:
                    score += 0.1

                # Check for paragraphs
                paragraph_count = len(
                    [p for p in article_content.split("\n\n") if p.strip()]
                )
                if paragraph_count >= 5:
                    score += 0.2
                elif paragraph_count >= 3:
                    score += 0.1

            # Ensure score is between 0 and 1
            return max(0.0, min(score, 1.0))

        except Exception as e:
            logger.error(f"Error calculating quality score: {e}")
            return 0.5  # Default score

    async def _save_processed_article(self, article_result: Dict[str, Any]) -> bool:
        """Save processed article to the processed-content container."""
        try:
            # Generate blob name with timestamp and topic ID
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            topic_id = article_result.get("topic_id", "unknown")
            blob_name = f"{timestamp}_{topic_id}.json"

            # Save to processed-content container
            success = await self.blob_client.upload_json(
                container_name="processed-content",
                blob_name=blob_name,
                data=article_result,
            )

            if success:
                logger.info(f"Saved processed article to blob: {blob_name}")
                return True
            else:
                logger.error(f"Failed to save processed article: {blob_name}")
                return False

        except Exception as e:
            logger.error(f"Error saving processed article: {e}")
            return False

    async def _test_blob_storage(self) -> bool:
        """Test blob storage connectivity."""
        try:
            # test_connection returns Dict[str, Any], not awaitable
            result = self.blob_client.test_connection()
            return result.get("status") == "healthy"
        except Exception as e:
            logger.error(f"Blob storage test failed: {e}")
            return False

    async def _test_openai(self) -> bool:
        """Test OpenAI connectivity."""
        try:
            return await self.openai_client.test_connection()
        except Exception as e:
            logger.error(f"OpenAI test failed: {e}")
            return False
