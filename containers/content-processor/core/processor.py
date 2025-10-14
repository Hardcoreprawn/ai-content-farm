"""
Content Processor - Pure Functional Interface

Pure functions for creating processor context and initializing clients.
All processing logic is in *_operations.py modules.

Refactored: January 2025 - Pure functions only, no OOP classes.
"""

import logging
import os
from typing import Optional

from aiolimiter import AsyncLimiter
from openai_operations import create_openai_client
from processor_context import ProcessorContext, create_processor_context

from libs.queue_client import create_queue_client
from libs.simplified_blob_client import SimplifiedBlobClient

logger = logging.getLogger(__name__)


async def initialize_processor(
    rate_limiter: Optional[AsyncLimiter] = None,
    processor_id: Optional[str] = None,
) -> ProcessorContext:
    """
    Initialize processor context.

    Pure function - creates immutable context object.

    Args:
        rate_limiter: Optional rate limiter for OpenAI calls
        processor_id: Optional processor ID (generated if None)

    Returns:
        ProcessorContext with all dependencies
    """
    blob_client = SimplifiedBlobClient()

    markdown_queue_name = os.getenv(
        "MARKDOWN_QUEUE_NAME", "markdown-generation-requests"
    )
    queue_client = await create_queue_client(queue_name=markdown_queue_name)

    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-07-01-preview")

    openai_client = None
    if endpoint:
        openai_client = await create_openai_client(
            endpoint=endpoint, api_version=api_version
        )
        logger.info("OpenAI client initialized")
    else:
        logger.warning("Azure OpenAI endpoint not configured - mock mode")

    context = create_processor_context(
        blob_client=blob_client,
        queue_client=queue_client,
        rate_limiter=rate_limiter,
        openai_client=openai_client,
        processor_id=processor_id,
    )

    logger.info(
        f"Processor initialized: {context.processor_id}, session {context.session_id}"
    )

    return context


async def cleanup_processor(
    context: ProcessorContext,
) -> None:
    """
    Clean up processor resources.

    Pure function - closes clients, no session tracking.
    """
    try:
        if context.openai_client:
            await context.openai_client.close()
            logger.info("OpenAI client closed")

        logger.info("Processor resources cleaned up")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
