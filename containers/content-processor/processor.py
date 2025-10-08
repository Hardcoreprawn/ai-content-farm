"""
Content Processor Core Logic

Functional processor implementing wake-up work queue pattern with:
- Lease-based coordination for parallel processing
- Azure OpenAI integration for article generation
- Cost tracking and quality assessment
- Immutable data patterns for thread safety
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from models import (
    ProcessingResult,
    ProcessorStatus,
    TopicMetadata,
)
from openai_client import OpenAIClient
from services import (
    ArticleGenerationService,
    LeaseCoordinator,
    ProcessorStorageService,
    QueueCoordinator,
    SessionTracker,
    TopicConversionService,
)

from libs.processing_config import ProcessingConfigManager
from libs.simplified_blob_client import SimplifiedBlobClient

logger = logging.getLogger(__name__)


class ContentProcessor:
    """Functional content processor with lease-based coordination."""

    def __init__(self):
        self.processor_id = str(uuid4())[:8]
        self.session_id = str(uuid4())
        self.blob_client = SimplifiedBlobClient()
        self.openai_client = OpenAIClient()
        self.processing_config = ProcessingConfigManager(self.blob_client)

        # Initialize services
        # NOTE: TopicDiscoveryService removed - topics now sent individually via queue
        self.topic_conversion = TopicConversionService()
        self.article_generation = ArticleGenerationService(self.openai_client)
        self.lease_coordinator = LeaseCoordinator(self.processor_id)
        self.storage = ProcessorStorageService(self.blob_client)
        self.queue_coordinator = QueueCoordinator(self.session_id)
        self.session_tracker = SessionTracker(self.processor_id)

        logger.info(f"Content processor initialized: {self.processor_id}")

    async def initialize_config(self):
        """Initialize configuration from blob storage."""
        try:
            container_config = await self.processing_config.get_container_config(
                "content-processor"
            )
            input_container = container_config.get("input_container")
            if input_container:
                logger.info(f"✅ CONFIG: Configured for container: {input_container}")

            processing_config = await self.processing_config.get_processing_config(
                "content-processor"
            )
            self.default_batch_size = processing_config.get("default_batch_size", 10)
            self.max_batch_size = processing_config.get("max_batch_size", 100)
            self.default_priority_threshold = processing_config.get(
                "default_priority_threshold", 0.5
            )

            logger.info(
                f"✅ CONFIG: batch_size={self.default_batch_size}, threshold={self.default_priority_threshold}"
            )
        except Exception as e:
            logger.warning(f"⚠️ CONFIG: Using defaults: {e}")

    async def cleanup(self):
        """Clean up resources to prevent asyncio errors."""
        try:
            await self.openai_client.close()
            logger.info("OpenAI client closed")

            # Close services that have close methods
            for service in [
                self.article_generation,
                self.lease_coordinator,
                self.storage,
            ]:
                if hasattr(service, "close"):
                    await service.close()

            # Log session summary
            self.session_tracker.log_summary()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    async def check_health(self) -> ProcessorStatus:
        """Health check with dependency validation."""
        try:
            blob_available = await self.storage.test_storage_connectivity()
            openai_available = await self._test_openai()
            status = "idle" if (blob_available and openai_available) else "error"

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
        stats = self.session_tracker.get_stats()
        return ProcessorStatus(
            processor_id=self.processor_id,
            status="idle",  # Simplified for now
            session_topics_processed=stats["topics_processed"],
            session_cost=stats["total_cost"],
            session_processing_time=stats["total_processing_time"],
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
        collection_files: Optional[List[str]] = None,
    ) -> ProcessingResult:
        """
        DEPRECATED: Legacy "wake up and discover" pattern.

        This method is being phased out in favor of queue-driven single-topic processing.
        New architecture: content-collector sends individual topic messages to queue.

        Returns empty result with deprecation message.
        """
        logger.warning(
            "⚠️ DEPRECATED: process_available_work() called. "
            "Use queue-driven single-topic processing instead."
        )
        return self._empty_result(
            success=False,
            error_msg="This endpoint is deprecated. Use queue-driven processing.",
        )

    async def process_collection_file(
        self,
        blob_path: str,
        collection_id: Optional[str] = None,
    ) -> ProcessingResult:
        """Process a specific collection file from queue message."""
        start_time = datetime.now(timezone.utc)
        processed_topics = []
        failed_topics = []
        total_cost = 0.0

        try:
            logger.info(f"Processing collection: {blob_path}")

            # Load collection
            collection_data = await self.blob_client.download_json(
                container="collected-content",
                blob_name=blob_path,
            )

            if not collection_data:
                return self._empty_result(
                    success=False, error_msg=f"Collection file not found: {blob_path}"
                )

            items = collection_data.get("items", [])
            if not items:
                logger.info(f"No items in collection: {blob_path}")
                return self._empty_result(
                    processing_time=(
                        datetime.now(timezone.utc) - start_time
                    ).total_seconds()
                )

            logger.info(f"Found {len(items)} items in {blob_path}")

            # Process each item
            for item in items:
                try:
                    topic_metadata = (
                        self.topic_conversion.collection_item_to_topic_metadata(
                            item, blob_path, collection_data
                        )
                    )
                    if not topic_metadata:
                        continue

                    success, cost = await self._process_topic_with_lease(topic_metadata)
                    if success:
                        processed_topics.append(topic_metadata.topic_id)
                        total_cost += cost
                    else:
                        failed_topics.append(topic_metadata.topic_id)
                except Exception as e:
                    logger.error(f"Error processing item: {e}")

            # Calculate processing time
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()

            logger.info(
                f"Completed {blob_path}: {len(processed_topics)} processed, "
                f"{len(failed_topics)} failed, ${total_cost:.4f}, {processing_time:.2f}s"
            )

            return ProcessingResult(
                success=True,
                topics_processed=len(processed_topics),
                articles_generated=len(processed_topics),
                total_cost=total_cost,
                processing_time=processing_time,
                completed_topics=processed_topics,
                failed_topics=failed_topics,
            )

        except Exception as e:
            logger.error(
                f"Failed to process collection {blob_path}: {e}", exc_info=True
            )
            return self._empty_result(
                success=False,
                error_msg=str(e),
                processing_time=(
                    datetime.now(timezone.utc) - start_time
                ).total_seconds(),
            )

    async def process_specific_topics(
        self,
        topic_ids: List[str],
        force_reprocess: bool = False,
        options: Optional[Dict[str, Any]] = None,
    ) -> ProcessingResult:
        """Process specific topics by ID - not yet implemented."""
        logger.info(f"Manual processing for {len(topic_ids)} topics - not implemented")
        result = self._empty_result()
        result.failed_topics = topic_ids
        result.error_messages = ["Manual processing not yet implemented"]
        return result

    async def _process_single_topic(
        self, topic_metadata: TopicMetadata
    ) -> Optional[Dict[str, Any]]:
        """Process a single topic into an article using ArticleGenerationService."""
        start_time = datetime.now(timezone.utc)
        try:
            logger.info(
                f"📝 TOPIC-PROCESSING: '{topic_metadata.title}' (ID: {topic_metadata.topic_id}, priority: {topic_metadata.priority_score}, source: {topic_metadata.source})"
            )

            # Generate article using service
            result = await self.article_generation.generate_article_from_topic(
                topic_metadata, self.processor_id, self.session_id
            )

            if not result:
                logger.error(
                    f"❌ ARTICLE-GENERATION: Failed for '{topic_metadata.title}'"
                )
                return None

            logger.info(
                f"✅ ARTICLE-GENERATION: '{topic_metadata.title}' - cost: ${result.get('cost', 0):.6f}"
            )

            # Save to processed-content container
            article_result = result.get("article_result")
            if not article_result:
                logger.warning("⚠️ STORAGE: No article_result to save")
                return None

            save_success, blob_name = await self.storage.save_processed_article(
                article_result
            )
            if not save_success or not blob_name:
                logger.error("❌ STORAGE: Failed to save article")
                return None

            logger.info(f"✅ STORAGE: Saved to {blob_name}")

            # Trigger markdown generation
            trigger_result = await self.queue_coordinator.trigger_markdown_for_article(
                blob_name=blob_name, force_trigger=True
            )
            status_log = (
                "✅ TRIGGER: Sent request"
                if trigger_result["status"] == "success"
                else f"⚠️ TRIGGER: Failed - {trigger_result.get('error')}"
            )
            logger.info(status_log)

            return {
                "article_content": result.get("article_content"),
                "word_count": result.get("word_count"),
                "quality_score": result.get("quality_score"),
                "cost": result.get("cost"),
                "processing_time": (
                    datetime.now(timezone.utc) - start_time
                ).total_seconds(),
            }
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

    def _empty_result(
        self,
        success: bool = True,
        error_msg: Optional[str] = None,
        processing_time: float = 0.0,
    ) -> ProcessingResult:
        """Create an empty ProcessingResult."""
        return ProcessingResult(
            success=success,
            topics_processed=0,
            articles_generated=0,
            total_cost=0.0,
            processing_time=processing_time,
            error_messages=[error_msg] if error_msg else [],
        )

    async def _process_topic_with_lease(
        self, topic_metadata: TopicMetadata
    ) -> Tuple[bool, float]:
        """Process topic with lease coordination. Returns (success, cost)."""
        if not await self.lease_coordinator.acquire_topic_lease(
            topic_metadata.topic_id
        ):
            return False, 0.0

        try:
            result = await self._process_single_topic(topic_metadata)
            if not result:
                self.session_tracker.record_topic_failure()
                return False, 0.0

            cost = result.get("cost", 0.0)
            self.session_tracker.record_topic_success(
                cost=cost,
                processing_time=result.get("processing_time", 0.0),
                word_count=result.get("word_count", 0),
                quality_score=result.get("quality_score"),
            )
            return True, cost
        except Exception as e:
            logger.error(f"Error processing {topic_metadata.topic_id}: {e}")
            self.session_tracker.record_topic_failure(str(e))
            return False, 0.0
        finally:
            await self.lease_coordinator.release_topic_lease(topic_metadata.topic_id)
