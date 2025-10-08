"""
Pure functional wrappers for Azure Queue Storage operations.

Stateless functions that wrap Azure Queue SDK calls for message operations.
All configuration passed explicitly, no stored state.

Contract Version: 1.0.0
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from azure.storage.queue.aio import QueueClient

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
# Queue Operations (Async Functions)
# ============================================================================


async def send_queue_message(
    queue_client: QueueClient,
    message: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Send message to Azure Queue Storage.

    Pure async function that sends message and returns result.

    Args:
        queue_client: Configured Azure QueueClient
        message: Message dict to send

    Returns:
        Dict with status, message_id, timestamp
        Returns error status on failure

    Examples:
        >>> from azure.storage.queue import QueueClient
        >>> client = QueueClient.from_connection_string("conn_str", "queue")
        >>> result = await send_queue_message(
        ...     client,
        ...     {"service_name": "test", "operation": "wake_up"}
        ... )
        >>> result["status"]
        'success'
    """
    try:
        # Convert message dict to JSON string
        message_json = json.dumps(message)

        # Send to queue
        response = queue_client.send_message(message_json)

        logger.info(
            f"✅ Queue message sent: id={response.id}, "
            f"service={message.get('service_name')}, "
            f"operation={message.get('operation')}"
        )

        return {
            "status": "success",
            "message_id": response.id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "queue_name": queue_client.queue_name,
        }

    except Exception as e:
        logger.error(f"❌ Failed to send queue message: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


async def receive_queue_messages(
    queue_client: QueueClient,
    max_messages: int = 1,
    visibility_timeout: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Receive messages from Azure Queue Storage.

    Pure async function that retrieves messages.

    Args:
        queue_client: Configured Azure QueueClient
        max_messages: Maximum messages to retrieve (1-32)
        visibility_timeout: How long message is invisible after retrieval (seconds)

    Returns:
        List of message dicts with id, content, pop_receipt

    Examples:
        >>> client = QueueClient.from_connection_string("conn_str", "queue")
        >>> messages = await receive_queue_messages(client, max_messages=5)
        >>> len(messages) <= 5
        True
    """
    try:
        messages = queue_client.receive_messages(
            max_messages=max_messages,
            visibility_timeout=visibility_timeout,
        )

        result = []
        for msg in messages:
            try:
                content = json.loads(msg.content)
            except json.JSONDecodeError:
                content = {"raw_content": msg.content}

            result.append(
                {
                    "id": msg.id,
                    "content": content,
                    "pop_receipt": msg.pop_receipt,
                    "dequeue_count": msg.dequeue_count,
                    "insertion_time": msg.insertion_time,
                }
            )

        logger.info(f"📥 Received {len(result)} messages from queue")
        return result

    except Exception as e:
        logger.error(f"❌ Failed to receive queue messages: {e}")
        return []


async def delete_queue_message(
    queue_client: QueueClient,
    message_id: str,
    pop_receipt: str,
) -> bool:
    """
    Delete message from Azure Queue Storage.

    Pure async function that deletes message after processing.

    Args:
        queue_client: Configured Azure QueueClient
        message_id: Message ID to delete
        pop_receipt: Pop receipt from message retrieval

    Returns:
        bool: True if deleted successfully, False otherwise

    Examples:
        >>> client = QueueClient.from_connection_string("conn_str", "queue")
        >>> success = await delete_queue_message(client, "msg_id", "receipt")
        >>> isinstance(success, bool)
        True
    """
    try:
        queue_client.delete_message(message_id, pop_receipt)
        logger.info(f"🗑️  Deleted message {message_id} from queue")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to delete message {message_id}: {e}")
        return False


async def peek_queue_messages(
    queue_client: QueueClient,
    max_messages: int = 1,
) -> List[Dict[str, Any]]:
    """
    Peek at messages without removing them from queue.

    Pure async function that views messages without dequeuing.

    Args:
        queue_client: Configured Azure QueueClient
        max_messages: Maximum messages to peek (1-32)

    Returns:
        List of message dicts with id and content

    Examples:
        >>> client = QueueClient.from_connection_string("conn_str", "queue")
        >>> messages = await peek_queue_messages(client, max_messages=3)
        >>> isinstance(messages, list)
        True
    """
    try:
        messages = queue_client.peek_messages(max_messages=max_messages)

        result = []
        for msg in messages:
            try:
                content = json.loads(msg.content)
            except json.JSONDecodeError:
                content = {"raw_content": msg.content}

            result.append(
                {
                    "id": msg.id,
                    "content": content,
                    "dequeue_count": msg.dequeue_count,
                }
            )

        logger.info(f"👀 Peeked at {len(result)} messages in queue")
        return result

    except Exception as e:
        logger.error(f"❌ Failed to peek queue messages: {e}")
        return []


async def get_queue_properties(
    queue_client: QueueClient,
) -> Dict[str, Any]:
    """
    Get queue properties and metadata.

    Pure async function that retrieves queue information.

    Args:
        queue_client: Configured Azure QueueClient

    Returns:
        Dict with queue properties (approximate_message_count, metadata)

    Examples:
        >>> client = QueueClient.from_connection_string("conn_str", "queue")
        >>> props = await get_queue_properties(client)
        >>> "approximate_message_count" in props
        True
    """
    try:
        properties = queue_client.get_queue_properties()

        return {
            "name": queue_client.queue_name,
            "approximate_message_count": properties.approximate_message_count,
            "metadata": properties.metadata or {},
        }

    except Exception as e:
        logger.error(f"❌ Failed to get queue properties: {e}")
        return {
            "name": queue_client.queue_name,
            "error": str(e),
        }


async def clear_queue(
    queue_client: QueueClient,
) -> bool:
    """
    Clear all messages from queue.

    Pure async function that removes all messages.

    Args:
        queue_client: Configured Azure QueueClient

    Returns:
        bool: True if cleared successfully, False otherwise

    Examples:
        >>> client = QueueClient.from_connection_string("conn_str", "queue")
        >>> success = await clear_queue(client)
        >>> isinstance(success, bool)
        True
    """
    try:
        queue_client.clear_messages()
        logger.info(f"🧹 Cleared all messages from queue {queue_client.queue_name}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to clear queue: {e}")
        return False


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
