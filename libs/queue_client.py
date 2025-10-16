"""
Unified Queue Client Interface for Container Services

Provides a standardized interface for queue operations that can be implemented
by different queue backends (Service Bus, Storage Queue, etc.). This allows
containers to use the same interface regardless of the underlying queue technology.

Usage:
    from libs.queue_client import get_queue_client

    # Get a queue client (automatically uses Storage Queue with managed identity)
    async with get_queue_client("content-processing-requests") as client:
        # Send a wake-up message
        await client.send_message({
            "service_name": "content-collector",
            "operation": "wake_up",
            "payload": {"collection_id": "tech-news"}
        })

        # Receive and process messages
        messages = await client.receive_messages(max_messages=10)
        for message in messages:
            # Process message
            await client.complete_message(message)
"""

import asyncio
import json
import logging
import os
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from azure.identity.aio import DefaultAzureCredential
from azure.storage.queue.aio import QueueClient
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class QueueMessageModel(BaseModel):
    """Standardized queue message format for all container services."""

    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    service_name: str = Field(..., description="Name of the requesting service")
    operation: str = Field(..., description="Operation to perform")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Message payload")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class QueueClientInterface(ABC):
    """Abstract interface for queue clients."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the queue."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the queue connection."""
        pass

    @abstractmethod
    async def send_message(
        self, message: Union[QueueMessageModel, Dict[str, Any], str], **kwargs
    ) -> Dict[str, Any]:
        """Send a message to the queue."""
        pass

    @abstractmethod
    async def receive_messages(self, max_messages: Optional[int] = None) -> List[Any]:
        """Receive messages from the queue."""
        pass

    @abstractmethod
    async def complete_message(self, message) -> None:
        """Complete/delete a message from the queue."""
        pass

    @abstractmethod
    async def get_queue_properties(self) -> Dict[str, Any]:
        """Get queue properties and metadata."""
        pass

    @abstractmethod
    def get_health_status(self) -> Dict[str, Any]:
        """Get client health status."""
        pass

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


class StorageQueueClient(QueueClientInterface):
    """Storage Queue implementation of the queue client interface."""

    def __init__(self, queue_name: str, storage_account_name: Optional[str] = None):
        """
        Initialize Storage Queue client.

        Args:
            queue_name: Name of the Storage Queue
            storage_account_name: Storage account name (optional, can be from env)
        """
        self.queue_name = queue_name
        self.storage_account_name = storage_account_name or os.getenv(
            "AZURE_STORAGE_ACCOUNT_NAME"
        )

        if not self.storage_account_name:
            raise ValueError("AZURE_STORAGE_ACCOUNT_NAME must be provided")

        self._queue_client = None
        self._credential = None
        logger.info(f"StorageQueueClient initialized for queue: {queue_name}")

    async def connect(self) -> None:
        """Establish connection to Storage Queue using managed identity."""
        try:
            self._credential = DefaultAzureCredential()

            self._queue_client = QueueClient(
                account_url=f"https://{self.storage_account_name}.queue.core.windows.net",
                queue_name=self.queue_name,
                credential=self._credential,
            )

            # Ensure queue exists
            try:
                await self._queue_client.create_queue()
                logger.info(f"Queue '{self.queue_name}' created or already exists")
            except Exception as e:
                if "QueueAlreadyExists" in str(e):
                    logger.info(f"Queue '{self.queue_name}' already exists")
                else:
                    logger.warning(f"Queue creation check failed: {e}")

            logger.info(f"Connected to Storage Queue: {self.queue_name}")

        except Exception as e:
            logger.error(f"Failed to connect to Storage Queue: {e}")
            raise

    async def close(self) -> None:
        """Close Storage Queue connection and credential."""
        try:
            if self._queue_client:
                await self._queue_client.close()
                logger.info(f"Storage Queue connection closed: {self.queue_name}")

            if self._credential:
                await self._credential.close()
                logger.debug(f"Credential closed for queue: {self.queue_name}")
        except Exception as e:
            logger.error(f"Error closing Storage Queue connection: {e}")

    async def send_message(
        self, message: Union[QueueMessageModel, Dict[str, Any], str], **kwargs
    ) -> Dict[str, Any]:
        """Send a message to the Storage Queue."""
        if not self._queue_client:
            await self.connect()

        if not self._queue_client:
            raise RuntimeError("Queue client not connected")

        try:
            # Convert message to appropriate format
            if isinstance(message, QueueMessageModel):
                message_content = message.model_dump_json()
                message_id = message.message_id
            elif isinstance(message, dict):
                # Convert dict to QueueMessageModel for consistency
                queue_message = QueueMessageModel(**message)
                message_content = queue_message.model_dump_json()
                message_id = queue_message.message_id
            else:
                message_content = str(message)
                message_id = str(uuid.uuid4())

            # Send message to queue
            response = await self._queue_client.send_message(
                content=message_content, **kwargs
            )

            logger.info(f"Message sent to queue '{self.queue_name}': {message_id}")

            return {
                "message_id": response.id,
            }

        except Exception as e:
            logger.error(f"Failed to send message to queue '{self.queue_name}': {e}")
            raise

    async def receive_messages(self, max_messages: Optional[int] = None) -> List[Any]:
        """Receive messages from the Storage Queue.

        Functional approach with proper async iterator cleanup to prevent
        unclosed client session warnings and ensure messages are received.
        """
        if not self._queue_client:
            await self.connect()

        if not self._queue_client:
            raise RuntimeError("Queue client not connected")

        max_msgs = max_messages or 10

        try:
            messages = []

            # Get the async iterator - this is the Azure SDK AsyncItemPaged object
            message_pager = self._queue_client.receive_messages(
                messages_per_page=max_msgs,
                visibility_timeout=300,  # 5 minutes - enough time for AI processing
            )

            # Properly manage the async iterator lifecycle
            try:
                # Use async for but ensure we don't break without cleanup
                count = 0
                async for message in message_pager:
                    messages.append(message)
                    count += 1
                    # Stop after max_msgs, but iterator will auto-close at loop end
                    if count >= max_msgs:
                        break
            finally:
                # Explicitly close the iterator if it has cleanup
                # Azure AsyncItemPaged should have aclose() or close()
                if hasattr(message_pager, "aclose"):
                    await message_pager.aclose()
                elif hasattr(message_pager, "close"):
                    await message_pager.close()

            logger.info(
                f"Received {len(messages)} messages from queue '{self.queue_name}'"
            )
            return messages

        except Exception as e:
            logger.error(
                f"Failed to receive messages from queue '{self.queue_name}': {e}"
            )
            raise

    async def complete_message(self, message) -> None:
        """Complete/delete a message from the Storage Queue."""
        if not self._queue_client:
            await self.connect()

        if not self._queue_client:
            raise RuntimeError("Queue client not connected")

        try:
            await self._queue_client.delete_message(message)
            logger.debug(f"Message completed in queue '{self.queue_name}'")

        except Exception as e:
            logger.error(
                f"Failed to complete message in queue '{self.queue_name}': {e}"
            )
            raise

    async def get_queue_properties(self) -> Dict[str, Any]:
        """Get queue properties and metadata."""
        if not self._queue_client:
            await self.connect()

        if not self._queue_client:
            raise RuntimeError("Queue client not connected")

        try:
            properties = await self._queue_client.get_queue_properties()

            return {
                "approximate_message_count": properties.approximate_message_count,
                "metadata": properties.metadata or {},
                "queue_name": self.queue_name,
                "storage_account": self.storage_account_name,
                "last_modified": properties.last_modified,
                "etag": properties.etag,
            }

        except Exception as e:
            logger.error(f"Failed to get queue properties for '{self.queue_name}': {e}")
            raise

    def get_health_status(self) -> Dict[str, Any]:
        """Get client health status."""
        return {
            "status": "healthy" if self._queue_client else "not_connected",
            "queue_name": self.queue_name,
            "storage_account": self.storage_account_name,
            "authentication": "managed_identity",
            "client_type": "storage_queue",
        }


def get_queue_client(
    queue_name: str, storage_account_name: Optional[str] = None
) -> QueueClientInterface:
    """
    Get a queue client instance.

    Currently returns StorageQueueClient, but this can be extended to support
    different queue backends based on configuration.

    Args:
        queue_name: Name of the queue
        storage_account_name: Storage account name (optional)

    Returns:
        QueueClientInterface implementation
    """
    return StorageQueueClient(
        queue_name=queue_name, storage_account_name=storage_account_name
    )


async def create_queue_client(
    queue_name: str, storage_account_name: Optional[str] = None
) -> QueueClientInterface:
    """
    Create and connect a queue client instance.

    Async version of get_queue_client that also connects the client.

    Args:
        queue_name: Name of the queue
        storage_account_name: Storage account name (optional)

    Returns:
        Connected QueueClientInterface implementation
    """
    client = StorageQueueClient(
        queue_name=queue_name, storage_account_name=storage_account_name
    )
    await client.connect()
    return client


# Convenience functions for common operations
async def send_wake_up_message(
    queue_name: str, service_name: str, payload: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Send a wake-up message to a queue.

    Args:
        queue_name: Name of the queue
        service_name: Name of the service sending the message
        payload: Optional payload data

    Returns:
        Message metadata
    """
    message = QueueMessageModel(
        service_name=service_name, operation="wake_up", payload=payload or {}
    )

    async with get_queue_client(queue_name) as client:
        return await client.send_message(message)


async def process_queue_messages(
    queue_name: str, message_handler, max_messages: int = 10
) -> int:
    """
    Process messages from a queue using a handler function.

    Args:
        queue_name: Name of the queue
        message_handler: Async function to process each message
        max_messages: Maximum messages to process

    Returns:
        Number of messages processed
    """
    processed_count = 0

    async with get_queue_client(queue_name) as client:
        messages = await client.receive_messages(max_messages=max_messages)

        for message in messages:
            try:
                # Parse message content
                try:
                    message_data = json.loads(message.content)
                    queue_message = QueueMessageModel(**message_data)
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Failed to parse message: {e}")
                    queue_message = QueueMessageModel(
                        service_name="unknown",
                        operation="parse_error",
                        payload={"raw_content": message.content, "error": str(e)},
                    )

                # Process message
                await message_handler(queue_message, message)

                # Complete message
                await client.complete_message(message)
                processed_count += 1

            except Exception as e:
                logger.error(f"Failed to process message: {e}")
                # Message will become visible again for retry

    return processed_count
