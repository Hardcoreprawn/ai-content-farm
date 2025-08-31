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
            # Mock implementation for now - returns empty list
            # In Phase 2, this will read from blob storage
            logger.info(
                f"Searching for topics (batch_size={batch_size}, threshold={priority_threshold})"
            )
            return []

        except Exception as e:
            logger.error(f"Error finding available topics: {e}")
            return []

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
        """Process a single topic into an article (pure function)."""
        try:
            # Mock processing for now
            logger.info(f"Processing topic: {topic_metadata.title}")

            # Simulate processing time
            await asyncio.sleep(0.1)

            return {
                "article_content": f"Mock article for: {topic_metadata.title}",
                "word_count": 3000,
                "quality_score": 0.85,
                "cost": 0.15,
            }

        except Exception as e:
            logger.error(f"Error processing topic {topic_metadata.topic_id}: {e}")
            return None

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
