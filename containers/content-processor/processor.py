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
from services import (
    ArticleGenerationService,
    LeaseCoordinator,
    ProcessorStorageService,
    TopicDiscoveryService,
)

from config import ContentProcessorSettings
from libs.processing_config import ProcessingConfigManager
from libs.simplified_blob_client import SimplifiedBlobClient

logger = logging.getLogger(__name__)


class ContentProcessor:
    """
    Functional content processor with lease-based coordination.

    Implements pure functional patterns for thread safety and scalability.
    """

    def __init__(self):
        self.processor_id = str(uuid4())[:8]
        self.session_id = str(uuid4())
        self.blob_client = SimplifiedBlobClient()
        self.openai_client = OpenAIClient()
        self.config = ContentProcessorSettings()
        self.processing_config = ProcessingConfigManager(self.blob_client)

        # Initialize service dependencies - will load container config from blob storage
        self.topic_discovery = TopicDiscoveryService(self.blob_client)
        self.article_generation = ArticleGenerationService(self.openai_client)
        self.lease_coordinator = LeaseCoordinator(self.processor_id)
        self.storage = ProcessorStorageService(self.blob_client)

        # Session tracking (immutable append-only)
        self.session_start = datetime.now(timezone.utc)
        self.session_topics_processed = 0
        self.session_cost = 0.0
        self.session_processing_time = 0.0

        logger.info(f"Content processor initialized: {self.processor_id}")

    async def initialize_config(self):
        """Initialize configuration from blob storage."""
        try:
            # Load container configuration
            container_config = await self.processing_config.get_container_config(
                "content-processor"
            )

            # Update topic discovery with the correct container
            input_container = container_config.get("input_container")
            if input_container:
                self.topic_discovery = TopicDiscoveryService(
                    self.blob_client, input_container=input_container
                )
                logger.info(
                    f"✅ CONFIG: Topic discovery configured for container: {input_container}"
                )

            # Load processing configuration
            processing_config = await self.processing_config.get_processing_config(
                "content-processor"
            )
            self.default_batch_size = processing_config.get("default_batch_size", 10)
            self.max_batch_size = processing_config.get("max_batch_size", 100)
            self.default_priority_threshold = processing_config.get(
                "default_priority_threshold", 0.5
            )

            logger.info(
                f"✅ CONFIG: Processing config loaded - batch_size={self.default_batch_size}, threshold={self.default_priority_threshold}"
            )

        except Exception as e:
            logger.warning(
                f"⚠️ CONFIG: Failed to load configuration from blob storage, using defaults: {e}"
            )

    async def cleanup(self):
        """Clean up resources to prevent asyncio errors."""
        try:
            # Close async OpenAI client
            await self.openai_client.close()
            logger.info("OpenAI client closed")

            # Close blob client if it has async resources
            if hasattr(self.blob_client, "close"):
                await self.blob_client.close()
                logger.info("Blob client closed")

            # Close any other service clients
            services_to_close = [
                self.topic_discovery,
                self.article_generation,
                self.lease_coordinator,
                self.storage,
            ]

            for service in services_to_close:
                if hasattr(service, "close"):
                    await service.close()
                    logger.info(f"{service.__class__.__name__} closed")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    async def check_health(self) -> ProcessorStatus:
        """Health check with dependency validation."""
        try:
            # Test blob storage
            blob_available = await self.storage.test_storage_connectivity()

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
        batch_size: Optional[int] = None,
        priority_threshold: Optional[float] = None,
        options: Optional[Dict[str, Any]] = None,
        debug_bypass: bool = False,
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
            # Initialize configuration from blob storage if not done yet
            if not hasattr(self, "default_batch_size"):
                await self.initialize_config()

            # Use configured defaults if parameters not provided
            if batch_size is None:
                batch_size = getattr(self, "default_batch_size", 10)
            if priority_threshold is None:
                priority_threshold = getattr(self, "default_priority_threshold", 0.5)
            # Phase 1: Find available topics
            if debug_bypass:
                logger.info(
                    f"🔧 DEBUG-BYPASS: Opening the taps! Searching for ALL topics (batch_size={batch_size}, bypassing threshold={priority_threshold})"
                )
            else:
                logger.info(
                    f"🔍 DISCOVERY: Searching for available topics with batch_size={batch_size}, priority_threshold={priority_threshold}"
                )
            available_topics = await self.topic_discovery.find_available_topics(
                batch_size, priority_threshold, debug_bypass=debug_bypass
            )

            if not available_topics:
                logger.info(
                    "ℹ️ DISCOVERY: No topics available for processing - returning empty result"
                )
                return ProcessingResult(
                    success=True,
                    topics_processed=0,
                    articles_generated=0,
                    total_cost=0.0,
                    processing_time=0.0,
                )

            logger.info(
                f"✅ DISCOVERY: Found {len(available_topics)} topics for processing"
            )

            # Phase 2: Process each topic with lease coordination
            for topic_metadata in available_topics:
                try:
                    # Attempt to lease topic
                    if await self.lease_coordinator.acquire_topic_lease(
                        topic_metadata.topic_id
                    ):
                        result = await self._process_single_topic(topic_metadata)

                        if result:
                            processed_topics.append(topic_metadata.topic_id)
                            total_cost += result.get("cost", 0.0)
                        else:
                            failed_topics.append(topic_metadata.topic_id)

                        # Release lease
                        await self.lease_coordinator.release_topic_lease(
                            topic_metadata.topic_id
                        )

                except Exception as e:
                    logger.error(
                        f"Error processing topic {topic_metadata.topic_id}: {e}"
                    )
                    failed_topics.append(topic_metadata.topic_id)
                    await self.lease_coordinator.release_topic_lease(
                        topic_metadata.topic_id
                    )

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

    def _collection_item_to_topic_metadata(
        self, item: Dict[str, Any], blob_name: str, collection_data: Dict[str, Any]
    ) -> Optional[TopicMetadata]:
        """Convert a collection item to TopicMetadata."""
        try:
            # Debug: log the actual item type and content
            logger.info(f"🔍 ITEM-DEBUG: Processing item type: {type(item)}")
            logger.info(f"🔍 ITEM-DEBUG: Item content: {item}")

            # Validate that item is a dictionary
            if not isinstance(item, dict):
                logger.error(f"❌ ITEM-ERROR: Expected dict, got {type(item)}: {item}")
                return None

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

    async def _process_single_topic(
        self, topic_metadata: TopicMetadata
    ) -> Optional[Dict[str, Any]]:
        """Process a single topic into an article using ArticleGenerationService."""
        try:
            logger.info(
                f"📝 TOPIC-PROCESSING: Starting processing for topic: '{topic_metadata.title}' (ID: {topic_metadata.topic_id})"
            )
            logger.info(
                f"📝 TOPIC-PROCESSING: Topic priority: {topic_metadata.priority}, source: {topic_metadata.source}"
            )

            # Generate article using service
            logger.info("🎯 ARTICLE-GENERATION: Calling ArticleGenerationService...")
            result = await self.article_generation.generate_article_from_topic(
                topic_metadata, self.processor_id, self.session_id
            )

            if not result:
                logger.error(
                    f"❌ ARTICLE-GENERATION: Failed to generate article for topic: {topic_metadata.title}"
                )
                return None

            logger.info(
                f"✅ ARTICLE-GENERATION: Successfully generated article for '{topic_metadata.title}' - cost: ${result.get('cost', 0):.6f}"
            )

            # Save to processed-content container
            article_result = result.get("article_result")
            if article_result:
                logger.info(f"💾 STORAGE: Saving processed article to blob storage...")
                await self.storage.save_processed_article(article_result)
                logger.info(f"✅ STORAGE: Article saved successfully")
            else:
                logger.warning(
                    "⚠️ STORAGE: No article_result to save - skipping storage"
                )

            # Return minimal result for session tracking
            processing_result = {
                "article_content": result.get("article_content"),
                "word_count": result.get("word_count"),
                "quality_score": result.get("quality_score"),
                "cost": result.get("cost"),
            }
            logger.info(
                f"📊 TOPIC-PROCESSING: Topic processing completed - word_count: {processing_result.get('word_count')}, quality: {processing_result.get('quality_score')}"
            )
            return processing_result

        except Exception as e:
            logger.error(f"Error processing topic {topic_metadata.topic_id}: {e}")
            return None

    async def _test_openai(self) -> bool:
        """Test OpenAI connectivity."""
        try:
            return await self.openai_client.test_connection()
        except Exception as e:
            logger.error(f"OpenAI test failed: {e}")
            return False
