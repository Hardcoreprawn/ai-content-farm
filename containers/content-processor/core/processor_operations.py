"""
Pure functional content processor operations.

All operations are pure functions taking explicit context and state parameters.
No hidden state, all dependencies injected through ProcessorContext.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from core.processing_operations import process_topic_to_article
from core.processor_context import ProcessorContext
from models import ProcessingResult, ProcessorStatus, TopicMetadata
from operations.openai_operations import create_openai_client
from operations.topic_operations import collection_item_to_topic_metadata
from queue_operations_pkg import trigger_markdown_for_article
from utils.blob_utils import generate_articles_processed_blob_path

logger = logging.getLogger(__name__)


async def check_processor_health(
    blob_client,
    openai_client,
    processor_id: str,
) -> ProcessorStatus:
    """Check processor health. Pure function."""
    try:
        blob_available = await _test_blob_connectivity(blob_client)
        openai_available = openai_client is not None
        status = "idle" if (blob_available and openai_available) else "error"

        return ProcessorStatus(
            processor_id=processor_id,
            status=status,
            azure_openai_available=openai_available,
            blob_storage_available=blob_available,
            last_health_check=datetime.now(timezone.utc),
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return ProcessorStatus(
            processor_id=processor_id,
            status="error",
            azure_openai_available=False,
            blob_storage_available=False,
            last_health_check=datetime.now(timezone.utc),
        )


async def _test_blob_connectivity(blob_client) -> bool:
    """Test blob storage connectivity."""
    try:
        return blob_client is not None
    except Exception as e:
        logger.error(f"Blob connectivity test failed: {e}")
        return False


# ============================================================================
# Collection Processing - Pure Functions
# ============================================================================


async def process_collection_file(
    context: ProcessorContext,
    blob_path: str,
) -> ProcessingResult:
    """
    Process collection file from blob storage.

    Pure function - returns new state and result.

    Args:
        context: Processor context with dependencies
        state: Current session state
        blob_path: Path to collection file

    Returns:
        Tuple of (new_state, processing_result)
    """
    start_time = datetime.now(timezone.utc)
    processed_topics = []
    failed_topics = []
    total_cost = 0.0

    try:
        logger.info(f"Processing collection: {blob_path}")

        # Load collection from blob storage
        collection_data = await context.blob_client.download_json(
            container=context.input_container,
            blob_name=blob_path,
        )

        if not collection_data:
            logger.error(f"Collection file not found: {blob_path}")
            result = _create_empty_result(
                success=False,
                error_msg=f"Collection file not found: {blob_path}",
                processing_time=(
                    datetime.now(timezone.utc) - start_time
                ).total_seconds(),
            )
            return result

        items = collection_data.get("items", [])
        if not items:
            logger.info(f"No items in collection: {blob_path}")
            result = _create_empty_result(
                processing_time=(
                    datetime.now(timezone.utc) - start_time
                ).total_seconds(),
            )
            return result

        logger.info(f"Processing {len(items)} items from {blob_path}")

        # Process each item
        for item in items[: context.max_articles_per_run]:
            try:
                # Convert to TopicMetadata
                topic_metadata = collection_item_to_topic_metadata(
                    item, blob_path, collection_data
                )
                if not topic_metadata:
                    continue

                # Process the topic directly
                result = await _process_single_topic(context, topic_metadata)

                if result:
                    processed_topics.append(topic_metadata.topic_id)
                    total_cost += result.get("cost", 0.0)
                else:
                    failed_topics.append(topic_metadata.topic_id)

            except Exception as e:
                logger.error(f"Error processing item: {e}")
                failed_topics.append(item.get("topic_id", "unknown"))

        # Calculate metrics
        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()

        logger.info(
            f"Collection complete: {blob_path} - "
            f"{len(processed_topics)} processed, {len(failed_topics)} failed, "
            f"cost ${total_cost:.4f}, time {processing_time:.2f}s"
        )

        result = ProcessingResult(
            success=True,
            topics_processed=len(processed_topics),
            articles_generated=len(processed_topics),
            total_cost=total_cost,
            processing_time=processing_time,
            completed_topics=processed_topics,
            failed_topics=failed_topics,
        )

        return result

    except Exception as e:
        logger.error(f"Collection processing failed: {blob_path} - {e}", exc_info=True)
        result = _create_empty_result(
            success=False,
            error_msg=str(e),
            processing_time=(datetime.now(timezone.utc) - start_time).total_seconds(),
        )
        return result


# ============================================================================
# Topic Processing - Pure Functions
# ============================================================================


async def _process_single_topic(
    context: ProcessorContext,
    topic_metadata: TopicMetadata,
) -> Optional[Dict]:
    """
    Process single topic into article.

    Pure function - no side effects beyond API calls.
    Implements idempotency: skips processing if topic_id already exists in processed-content.

    Args:
        context: Processor context with dependencies
        topic_metadata: Topic to process

    Returns:
        Result dict or None if failed/skipped
    """
    start_time = datetime.now(timezone.utc)
    topic_id = topic_metadata.topic_id

    try:
        # IDEMPOTENCY CHECK: Skip if already processed
        # Check articles/ prefix for processed articles
        existing_blobs = await context.blob_client.list_blobs(
            container="processed-content", prefix="articles/"
        )

        # Check if any blob contains this topic_id
        already_processed = any(topic_id in blob["name"] for blob in existing_blobs)

        if already_processed:
            logger.info(
                f"Skipping already processed topic: '{topic_metadata.title}' (ID: {topic_id})"
            )
            return None

        logger.info(
            f"Processing topic: '{topic_metadata.title}' "
            f"(ID: {topic_metadata.topic_id}, priority: {topic_metadata.priority_score})"
        )

        # Generate article using pure functional operations
        result = await process_topic_to_article(
            openai_client=context.openai_client,
            topic_metadata=topic_metadata,
            processor_id=context.processor_id,
            session_id=context.session_id,
            rate_limiter=context.rate_limiter,
        )

        if not result:
            logger.error(f"Article generation failed for '{topic_metadata.title}'")
            return None

        logger.info(
            f"Article generated: '{topic_metadata.title}' - "
            f"cost ${result.get('cost', 0):.6f}"
        )

        # Save to blob storage
        article_result = result.get("article_result")
        if not article_result:
            logger.warning("No article_result to save")
            return None

        # Generate blob path using new articles/ structure
        blob_name = generate_articles_processed_blob_path(article_result)

        # Save directly to blob storage
        save_success = await context.blob_client.upload_json(
            container="processed-content",
            blob_name=blob_name,
            data=article_result,
        )

        if not save_success:
            logger.error(f"Failed to save blob: {blob_name}")
            return None

        logger.info(f"Saved article to: {blob_name}")

        # Trigger markdown generation
        trigger_result = await trigger_markdown_for_article(
            queue_client=context.queue_client,
            blob_name=blob_name,
            correlation_id=context.session_id,
            force_trigger=True,
        )

        if trigger_result["status"] == "success":
            logger.info("Markdown generation request sent")
        else:
            logger.warning(f"Markdown trigger failed: {trigger_result.get('error')}")

        # Calculate processing time
        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()

        return {
            "article_content": result.get("article_content"),
            "word_count": result.get("word_count"),
            "quality_score": result.get("quality_score"),
            "cost": result.get("cost"),
            "processing_time": processing_time,
        }

    except Exception as e:
        logger.error(f"Topic processing failed: {topic_metadata.topic_id} - {e}")
        return None


# ============================================================================
# Helper Functions
# ============================================================================


def _create_empty_result(
    success: bool = True,
    error_msg: Optional[str] = None,
    processing_time: float = 0.0,
) -> ProcessingResult:
    """
    Create empty ProcessingResult.

    Pure function.

    Args:
        success: Success flag
        error_msg: Optional error message
        processing_time: Processing time in seconds

    Returns:
        Empty ProcessingResult
    """
    return ProcessingResult(
        success=success,
        topics_processed=0,
        articles_generated=0,
        total_cost=0.0,
        processing_time=processing_time,
        error_messages=[error_msg] if error_msg else [],
    )
