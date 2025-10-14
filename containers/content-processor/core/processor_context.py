"""
Pure functional processor context management.

Context dataclass for passing dependencies through processing pipeline.
Immutable context with explicit dependency injection.
"""

import logging
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


# ============================================================================
# Processor Context Dataclass (Immutable)
# ============================================================================


@dataclass(frozen=True)
class ProcessorContext:
    """
    Immutable context for content processing operations.

    Provides explicit dependency injection instead of hidden state.
    All dependencies passed as constructor parameters.
    """

    processor_id: str
    session_id: str
    blob_client: Any  # SimplifiedBlobClient
    queue_client: Any  # QueueClient
    rate_limiter: Any  # RateLimiter
    openai_client: Any  # AsyncOpenAI client

    # Container names
    input_container: str = "collected-content"
    output_container: str = "processed-content"
    markdown_queue: str = "markdown-generation"

    # Processing configuration
    max_articles_per_run: int = 10
    min_articles_for_trigger: int = 5
    lease_timeout_seconds: int = 300


# ============================================================================
# Context Creation - Pure Functions
# ============================================================================


def create_processor_context(
    blob_client: Any,
    queue_client: Any,
    rate_limiter: Any,
    openai_client: Any,
    processor_id: str | None = None,
    input_container: str = "collected-content",
    output_container: str = "processed-content",
    markdown_queue: str = "markdown-generation",
    max_articles: int = 10,
    min_trigger: int = 5,
    lease_timeout: int = 300,
) -> ProcessorContext:
    """
    Create processor context with all dependencies.

    Pure function.

    Args:
        blob_client: SimplifiedBlobClient for blob storage
        queue_client: QueueClient for queue operations
        rate_limiter: RateLimiter for OpenAI rate limiting
        openai_client: AsyncOpenAI client
        processor_id: Unique processor ID (generated if None)
        input_container: Input blob container name
        output_container: Output blob container name
        markdown_queue: Markdown generation queue name
        max_articles: Maximum articles to process per run
        min_trigger: Minimum articles before triggering next stage
        lease_timeout: Lease timeout in seconds

    Returns:
        New ProcessorContext instance
    """
    if processor_id is None:
        processor_id = str(uuid4())[:8]

    session_id = str(uuid4())[:8]

    logger.info(f"🔧 CONTEXT: Created processor {processor_id}, session {session_id}")
    logger.debug(
        f"  Input: {input_container}, Output: {output_container}, "
        f"Queue: {markdown_queue}"
    )

    return ProcessorContext(
        processor_id=processor_id,
        session_id=session_id,
        blob_client=blob_client,
        queue_client=queue_client,
        rate_limiter=rate_limiter,
        openai_client=openai_client,
        input_container=input_container,
        output_container=output_container,
        markdown_queue=markdown_queue,
        max_articles_per_run=max_articles,
        min_articles_for_trigger=min_trigger,
        lease_timeout_seconds=lease_timeout,
    )


def log_context_info(context: ProcessorContext) -> None:
    """
    Log context configuration details.

    Pure function (logging is acceptable side effect).

    Args:
        context: Processor context to log
    """
    logger.info(
        f"🔧 CONTEXT INFO: Processor {context.processor_id}, "
        f"Session {context.session_id}"
    )
    logger.info(f"  Containers: {context.input_container} → {context.output_container}")
    logger.info(f"  Queue: {context.markdown_queue}")
    logger.info(
        f"  Limits: {context.max_articles_per_run} max articles, "
        f"{context.min_articles_for_trigger} min trigger"
    )
    logger.info(f"  Lease timeout: {context.lease_timeout_seconds}s")
