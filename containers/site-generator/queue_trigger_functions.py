"""
Queue Trigger Functions for Site Generator

Pure functions for sending queue messages to trigger subsequent processing stages.
Follows functional programming principles with no side effects except queue I/O.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from libs.queue_client import QueueMessageModel, get_queue_client

logger = logging.getLogger(__name__)


async def trigger_html_generation(
    markdown_files: List[str],
    queue_name: str,
    generator_id: str,
    correlation_id: Optional[str] = None,
    additional_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Send queue message to trigger HTML generation from markdown files.

    Pure function that sends a wake-up message to the queue to trigger
    the HTML generation stage after markdown files have been created.

    Args:
        markdown_files: List of markdown file paths that were generated
        queue_name: Name of the queue to send the message to
        generator_id: ID of the generator that created the markdown
        correlation_id: Optional correlation ID for tracking
        additional_metadata: Optional additional data to include in payload

    Returns:
        Dict with status and message details:
        {
            "status": "success" | "error",
            "message_id": "...",
            "queue_name": "...",
            "markdown_files_count": N,
            "timestamp": "...",
            "error": "..." (if status is error)
        }

    Raises:
        No exceptions raised - errors are returned in the result dict
    """
    try:
        if not markdown_files:
            logger.warning("No markdown files provided - skipping HTML trigger")
            return {
                "status": "skipped",
                "reason": "no_markdown_files",
                "queue_name": queue_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        # Build payload for HTML generation
        payload = {
            "content_type": "markdown",
            "markdown_files_count": len(markdown_files),
            "trigger": "markdown_completion",
            "correlation_id": correlation_id or generator_id,
            "generator_id": generator_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Add any additional metadata
        if additional_metadata:
            payload.update(additional_metadata)

        # Create queue message
        message = QueueMessageModel(
            service_name="site-generator",
            operation="wake_up",
            payload=payload,
        )

        # Send message to queue
        logger.info(
            f"Triggering HTML generation: {len(markdown_files)} markdown files ready, "
            f"queue={queue_name}, generator_id={generator_id}"
        )

        async with get_queue_client(queue_name) as queue_client:
            result = await queue_client.send_message(message)

        logger.info(
            f"HTML generation trigger sent successfully: "
            f"message_id={result.get('message_id')}, "
            f"files_count={len(markdown_files)}"
        )

        return {
            "status": "success",
            "message_id": result.get("message_id"),
            "queue_name": queue_name,
            "markdown_files_count": len(markdown_files),
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        error_msg = f"Failed to trigger HTML generation: {e}"
        logger.error(error_msg)

        # Don't raise - return error result so markdown generation can still succeed
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__,
            "queue_name": queue_name,
            "markdown_files_count": len(markdown_files) if markdown_files else 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


async def trigger_batch_operation(
    operation_type: str,
    queue_name: str,
    service_name: str,
    payload: Dict[str, Any],
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Send generic queue message for batch operations.

    Pure function for triggering any type of batch operation via queue.
    More flexible than trigger_html_generation for future use cases.

    Args:
        operation_type: Type of operation to trigger (e.g., "wake_up", "generate_site")
        queue_name: Name of the queue to send the message to
        service_name: Name of the service sending the message
        payload: Operation-specific payload data
        correlation_id: Optional correlation ID for tracking

    Returns:
        Dict with status and message details

    Raises:
        No exceptions raised - errors are returned in the result dict
    """
    try:
        # Add correlation tracking
        enriched_payload = {
            **payload,
            "correlation_id": correlation_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Create queue message
        message = QueueMessageModel(
            service_name=service_name,
            operation=operation_type,
            payload=enriched_payload,
        )

        logger.info(
            f"Triggering batch operation: operation={operation_type}, "
            f"service={service_name}, queue={queue_name}"
        )

        # Send message to queue
        async with get_queue_client(queue_name) as queue_client:
            result = await queue_client.send_message(message)

        logger.info(
            f"Batch operation trigger sent: message_id={result.get('message_id')}"
        )

        return {
            "status": "success",
            "message_id": result.get("message_id"),
            "queue_name": queue_name,
            "operation_type": operation_type,
            "payload": enriched_payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        error_msg = f"Failed to trigger batch operation: {e}"
        logger.error(error_msg)

        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__,
            "queue_name": queue_name,
            "operation_type": operation_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


def should_trigger_html_generation(
    markdown_files: List[str],
    config: Dict[str, Any],
    force_trigger: bool = False,
) -> bool:
    """
    Determine if HTML generation should be triggered.

    Pure function with no side effects - just returns a boolean decision.

    Args:
        markdown_files: List of markdown files generated
        config: Configuration dict with trigger settings
        force_trigger: Force triggering regardless of conditions

    Returns:
        True if HTML generation should be triggered, False otherwise

    Examples:
        >>> should_trigger_html_generation(["file1.md"], {}, False)
        True
        >>> should_trigger_html_generation([], {}, False)
        False
        >>> should_trigger_html_generation([], {}, True)
        True
    """
    if force_trigger:
        return True

    if not markdown_files:
        return False

    # Check minimum threshold if configured
    min_files = config.get("html_trigger_min_files", 1)
    if len(markdown_files) < min_files:
        return False

    return True
