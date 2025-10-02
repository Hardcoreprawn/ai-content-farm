"""
Queue Trigger Functions - Shared Library

Generic queue trigger functions for event-driven pipeline orchestration.
Pure functions for sending queue messages to trigger downstream processing.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from libs.queue_client import QueueMessageModel, get_queue_client

logger = logging.getLogger(__name__)


async def trigger_next_stage(
    queue_name: str,
    service_name: str,
    operation: str = "wake_up",
    content_type: Optional[str] = None,
    files: Optional[List[str]] = None,
    correlation_id: Optional[str] = None,
    additional_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generic function to trigger the next stage in the content pipeline.

    Sends a queue message to wake up the next container in the processing chain.
    This is the shared implementation used across all containers.

    Args:
        queue_name: Name of the target queue
        service_name: Name of the service sending the message
        operation: Operation type (default: "wake_up")
        content_type: Type of content that was produced (e.g., "json", "markdown")
        files: Optional list of files that were created
        correlation_id: Optional correlation ID for tracking
        additional_metadata: Optional additional data to include in payload

    Returns:
        Dict with status and message details:
        {
            "status": "success" | "error" | "skipped",
            "message_id": "...",
            "queue_name": "...",
            "timestamp": "...",
            "error": "..." (if status is error)
        }

    Raises:
        No exceptions raised - errors are returned in the result dict
    """
    try:
        # Build base payload
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "correlation_id": correlation_id
            or f"{service_name}_{datetime.now(timezone.utc).timestamp()}",
        }

        # Add optional fields
        if content_type:
            payload["content_type"] = content_type
        if files:
            payload["files"] = files
            payload["files_count"] = len(files)
        if additional_metadata:
            payload.update(additional_metadata)

        # Create queue message
        message = QueueMessageModel(
            service_name=service_name,
            operation=operation,
            payload=payload,
        )

        # Send message to queue
        logger.info(
            f"Triggering next stage: queue={queue_name}, service={service_name}, "
            f"operation={operation}, content_type={content_type}"
        )

        async with get_queue_client(queue_name) as queue_client:
            result = await queue_client.send_message(message)

        logger.info(
            f"✅ Queue trigger sent successfully: "
            f"message_id={result.get('message_id')}, queue={queue_name}"
        )

        return {
            "status": "success",
            "message_id": result.get("message_id"),
            "queue_name": queue_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ Failed to send queue trigger: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "queue_name": queue_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


async def should_trigger_next_stage(
    files: Optional[List[str]] = None,
    force_trigger: bool = False,
    minimum_files: int = 1,
) -> bool:
    """
    Pure decision function to determine if the next stage should be triggered.

    Args:
        files: List of files that were created
        force_trigger: If True, always trigger regardless of files
        minimum_files: Minimum number of files required to trigger

    Returns:
        True if the next stage should be triggered, False otherwise
    """
    if force_trigger:
        return True

    if not files:
        return False

    return len(files) >= minimum_files


# Convenience functions for specific pipeline stages


async def trigger_processing(
    collected_files: List[str],
    queue_name: str = "content-processing-requests",
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Trigger content processing stage after collection.

    Args:
        collected_files: List of collected content files
        queue_name: Processing queue name
        correlation_id: Optional correlation ID

    Returns:
        Result dict with status and details
    """
    return await trigger_next_stage(
        queue_name=queue_name,
        service_name="content-collector",
        operation="wake_up",
        content_type="json",
        files=collected_files,
        correlation_id=correlation_id,
    )


async def trigger_markdown_generation(
    processed_files: List[str],
    queue_name: str = "site-generation-requests",
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Trigger markdown generation after content processing.

    Args:
        processed_files: List of processed article files
        queue_name: Site generation queue name
        correlation_id: Optional correlation ID

    Returns:
        Result dict with status and details
    """
    return await trigger_next_stage(
        queue_name=queue_name,
        service_name="content-processor",
        operation="wake_up",
        content_type="processed",
        files=processed_files,
        correlation_id=correlation_id,
    )


async def trigger_html_generation(
    markdown_files: List[str],
    queue_name: str = "site-generation-requests",
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Trigger HTML site generation after markdown creation.

    Args:
        markdown_files: List of markdown files created
        queue_name: Site generation queue name
        correlation_id: Optional correlation ID

    Returns:
        Result dict with status and details
    """
    return await trigger_next_stage(
        queue_name=queue_name,
        service_name="site-generator",
        operation="wake_up",
        content_type="markdown",
        files=markdown_files,
        correlation_id=correlation_id,
    )
