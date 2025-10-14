"""
Pure functional wrappers for Azure Queue Storage client operations.

All operations are async and take QueueClient as explicit parameter.
No stored state, all configuration passed explicitly.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from azure.storage.queue.aio import QueueClient
from queue_operations_pkg.queue_message_builder import create_markdown_trigger_message

logger = logging.getLogger(__name__)


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
        response = await queue_client.send_message(message_json)

        logger.info(
            f"Queue message sent: id={response.id}, "
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
        logger.error(f"Failed to send queue message: {e}")
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
        messages = await queue_client.receive_messages(
            max_messages=max_messages,
            visibility_timeout=visibility_timeout,
        )

        result = []
        async for msg in messages:
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

        logger.info(f"Received {len(result)} messages from queue")
        return result

    except Exception as e:
        logger.error(f"Failed to receive queue messages: {e}")
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
        await queue_client.delete_message(message_id, pop_receipt)
        logger.info(f"Deleted message {message_id} from queue")
        return True

    except Exception as e:
        logger.error(f"Failed to delete message {message_id}: {e}")
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
        messages = await queue_client.peek_messages(max_messages=max_messages)

        result = []
        async for msg in messages:
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

        logger.info(f"Peeked at {len(result)} messages in queue")
        return result

    except Exception as e:
        logger.error(f"Failed to peek queue messages: {e}")
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
        properties = await queue_client.get_queue_properties()

        return {
            "name": queue_client.queue_name,
            "approximate_message_count": properties.approximate_message_count,
            "metadata": properties.metadata or {},
        }

    except Exception as e:
        logger.error(f"Failed to get queue properties: {e}")
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
        await queue_client.clear_messages()
        logger.info(f"🧹 Cleared all messages from queue {queue_client.queue_name}")
        return True

    except Exception as e:
        logger.error(f"Failed to clear queue: {e}")
        return False


# ============================================================================
# Convenience Wrappers
# ============================================================================


async def trigger_markdown_for_article(
    queue_client: QueueClient,
    blob_name: str,
    correlation_id: Optional[str] = None,
    force_trigger: bool = True,
) -> Dict[str, Any]:
    """
    Convenience function to trigger markdown generation for a single article.

    Combines message creation and sending into one function call.

    Args:
        queue_client: Azure QueueClient instance
        blob_name: Name of the processed article blob
        correlation_id: Optional correlation ID for tracking
        force_trigger: Whether to force trigger (unused, kept for compatibility)

    Returns:
        Dict with status, message_id, timestamp, or error information

    Examples:
        >>> from azure.storage.queue import QueueClient
        >>> client = QueueClient.from_connection_string("conn_str", "markdown-queue")
        >>> result = await trigger_markdown_for_article(
        ...     queue_client=client,
        ...     blob_name="processed-content/article.json",
        ...     correlation_id="session-123"
        ... )
        >>> result["status"]
        'success'
    """
    try:
        # Create message for single file
        message = create_markdown_trigger_message(
            processed_files=[blob_name],
            correlation_id=correlation_id,
        )

        # Send message to queue
        result = await send_queue_message(queue_client, message)

        return result

    except Exception as e:
        logger.error(f"Failed to trigger markdown for {blob_name}: {e}")
        return {
            "status": "error",
            "error": str(e),
            "blob_name": blob_name,
        }
