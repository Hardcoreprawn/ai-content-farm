"""
Pure functions for building queue messages.

All message creation functions are pure - no side effects, deterministic output.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


# ============================================================================
# Message Creation (Pure Functions)
# ============================================================================


def create_queue_message(
    service_name: str,
    operation: str = "wake_up",
    payload: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create standardized queue message structure.

    Pure function that creates message dict following our contract.

    Args:
        service_name: Name of service sending message
        operation: Operation type (e.g., "wake_up", "process", "generate")
        payload: Optional payload data
        correlation_id: Optional correlation ID for tracking

    Returns:
        Dict: Standardized message structure

    Examples:
        >>> msg = create_queue_message(
        ...     service_name="content-processor",
        ...     operation="wake_up",
        ...     payload={"files": ["data.json"]}
        ... )
        >>> msg["service_name"]
        'content-processor'
        >>> msg["operation"]
        'wake_up'
    """
    message = {
        "service_name": service_name,
        "operation": operation,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "correlation_id": correlation_id or generate_correlation_id(service_name),
        "payload": payload or {},
    }

    return message


def generate_correlation_id(service_name: str) -> str:
    """
    Generate correlation ID for message tracking.

    Pure function that creates unique correlation ID.

    Args:
        service_name: Service name to include in ID

    Returns:
        str: Correlation ID in format "service-name_uuid"

    Examples:
        >>> corr_id = generate_correlation_id("content-processor")
        >>> "content-processor_" in corr_id
        True
        >>> len(corr_id) > 20
        True
    """
    return f"{service_name}_{uuid4()}"


def create_markdown_trigger_message(
    processed_files: List[str],
    correlation_id: Optional[str] = None,
    additional_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create message to trigger markdown generation.

    Pure function that creates standardized markdown generation request.

    Args:
        processed_files: List of processed article blob names
        correlation_id: Optional correlation ID
        additional_data: Optional additional metadata

    Returns:
        Dict: Message structure for markdown generation

    Examples:
        >>> msg = create_markdown_trigger_message(
        ...     processed_files=["article1.json", "article2.json"]
        ... )
        >>> msg["operation"]
        'wake_up'
        >>> msg["payload"]["files_count"]
        2
    """
    payload = {
        "content_type": "json",
        "files": processed_files,
        "files_count": len(processed_files),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if additional_data:
        payload.update(additional_data)

    return create_queue_message(
        service_name="content-processor",
        operation="wake_up",
        payload=payload,
        correlation_id=correlation_id,
    )


# ============================================================================
# Decision Functions (Pure)
# ============================================================================


def should_trigger_next_stage(
    files: Optional[List[str]] = None,
    force_trigger: bool = False,
    minimum_files: int = 1,
) -> bool:
    """
    Determine if next pipeline stage should be triggered.

    Pure function with deterministic decision logic.

    Args:
        files: List of files that were created
        force_trigger: If True, always trigger regardless of files
        minimum_files: Minimum number of files required to trigger

    Returns:
        bool: True if next stage should be triggered

    Examples:
        >>> should_trigger_next_stage(["file1.json", "file2.json"], minimum_files=2)
        True
        >>> should_trigger_next_stage(["file1.json"], minimum_files=5)
        False
        >>> should_trigger_next_stage([], force_trigger=True)
        True
    """
    if force_trigger:
        return True

    if not files:
        return False

    return len(files) >= minimum_files
