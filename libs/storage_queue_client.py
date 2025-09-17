"""
Azure Storage Queue Client - Replacement for Service Bus Client

Provides standardized Storage Queue messaging functionality for all container services.
Implements secure, resilient Storage Queue operations with managed identity authentication
to resolve Service Bus authentication conflicts with Container Apps KEDA scaling.

Key Features:
- Managed identity authentication (no connection strings needed)
- Compatible with Container Apps KEDA azure-queue scaler
- Standardized message polling with exponential backoff
- Error handling and retry logic
- Correlation ID tracking for message tracing
- Health check integration
- Resolves authentication conflicts between managed identity and connection strings

Usage:
    from libs.storage_queue_client import StorageQueueClient

    client = StorageQueueClient(queue_name="content-collection-requests")
    await client.send_message({
        "service_name": "content-collector",
        "operation": "wake_up",
        "payload": {"collection_id": "tech-news"}
    })

    messages = await client.receive_messages(max_messages=10)
    for message in messages:
        # Process message
        await client.delete_message(message)
"""

import asyncio
import base64
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from azure.identity.aio import DefaultAzureCredential
from azure.storage.queue.aio import QueueClient, QueueServiceClient
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class StorageQueueMessageModel(BaseModel):
    """Standardized Storage Queue message format for container services."""

    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    service_name: str = Field(..., description="Name of the requesting service")
    operation: str = Field(..., description="Operation to perform")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Message payload")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    def to_queue_message(self) -> str:
        """Convert to Azure Storage Queue message format (JSON string)."""
        return self.model_dump_json()

    @classmethod
    def from_queue_message(cls, message_content: str) -> "StorageQueueMessageModel":
        """Create from Azure Storage Queue message content."""
        try:
            data = json.loads(message_content)
            return cls(**data)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse queue message: {e}")
            # Return a default message with the raw content
            return cls(
                service_name="unknown",
                operation="parse_error",
                payload={"raw_content": message_content, "error": str(e)},
            )


class StorageQueueConfig(BaseModel):
    """Storage Queue configuration model.

    Storage Queues support managed identity authentication with Container Apps KEDA scaling,
    resolving the authentication conflicts that exist with Service Bus connection strings.
    """

    storage_account_name: str = Field(..., description="Storage account name")
    queue_name: str = Field(..., description="Queue name")
    max_wait_time: int = Field(
        default=1, description="Max wait time for receiving messages (seconds)"
    )
    max_messages: int = Field(
        default=10, description="Max messages to receive per poll"
    )
    retry_attempts: int = Field(default=3, description="Number of retry attempts")
    visibility_timeout: int = Field(
        default=30, description="Message visibility timeout in seconds"
    )

    @classmethod
    def from_environment(cls, queue_name: Optional[str] = None) -> "StorageQueueConfig":
        """Create config from environment variables."""
        storage_account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME", "").strip()
        env_queue_name = os.getenv("STORAGE_QUEUE_NAME", "").strip()

        # Use provided queue_name or fallback to environment or default
        final_queue_name = queue_name or env_queue_name or "content-processing-requests"

        if not storage_account_name:
            raise ValueError(
                "AZURE_STORAGE_ACCOUNT_NAME environment variable is required"
            )

        return cls(
            storage_account_name=storage_account_name,
            queue_name=final_queue_name,
        )


class StorageQueueClient:
    """
    Azure Storage Queue client with managed identity authentication.

    Provides high-level interface for sending and receiving messages
    with built-in error handling and retry logic. Replaces ServiceBusClient
    to resolve Container Apps KEDA authentication conflicts.
    """

    def __init__(
        self,
        config: Optional[StorageQueueConfig] = None,
        queue_name: Optional[str] = None,
    ):
        """
        Initialize Storage Queue client.

        Args:
            config: Storage Queue configuration. If None, loads from environment.
            queue_name: Override queue name from config
        """
        if config is None:
            config = StorageQueueConfig.from_environment(queue_name)
        elif queue_name:
            config.queue_name = queue_name

        self.config = config
        self.credential = DefaultAzureCredential()
        self._queue_client: Optional[QueueClient] = None

        logger.info(
            f"StorageQueueClient initialized for queue: {self.config.queue_name}"
        )

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def connect(self) -> None:
        """Establish connection to Storage Queue using managed identity or Azurite."""
        try:
            # Check for local development with Azurite
            connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
            
            if (connection_string and 
                "devstoreaccount1" in connection_string and 
                "azurite" in connection_string):
                # Local development with Azurite
                # Build Azurite queue connection string
                azurite_queue_connection = connection_string
                if "QueueEndpoint=" not in azurite_queue_connection:
                    # Add queue endpoint if missing
                    if "azurite:10000" in azurite_queue_connection:
                        azurite_queue_connection = azurite_queue_connection.replace(
                            "BlobEndpoint=http://azurite:10000/devstoreaccount1;",
                            "BlobEndpoint=http://azurite:10000/devstoreaccount1;QueueEndpoint=http://azurite:10001/devstoreaccount1;"
                        )
                
                logger.info(f"Using Azurite connection for queue: {self.config.queue_name}")
                self._queue_client = QueueClient.from_connection_string(
                    conn_str=azurite_queue_connection,
                    queue_name=self.config.queue_name
                )
            else:
                # Production Azure with managed identity
                self._queue_client = QueueClient(
                    account_url=f"https://{self.config.storage_account_name}.queue.core.windows.net",
                    queue_name=self.config.queue_name,
                    credential=self.credential,
                )
                logger.info(f"Using managed identity for queue: {self.config.queue_name}")

            # Ensure queue exists
            try:
                await self._queue_client.create_queue()
                logger.info(
                    f"Queue '{self.config.queue_name}' created or already exists"
                )
            except Exception as e:
                if "QueueAlreadyExists" in str(e):
                    logger.info(f"Queue '{self.config.queue_name}' already exists")
                else:
                    logger.warning(f"Queue creation check failed: {e}")

            logger.info(
                f"Connected to Storage Queue: {self.config.queue_name}"
            )

        except Exception as e:
            logger.error(f"Failed to connect to Storage Queue: {e}")
            raise

    async def close(self) -> None:
        """Close Storage Queue connection."""
        try:
            if self._queue_client:
                await self._queue_client.close()
                logger.info(
                    f"Storage Queue connection closed for queue: {self.config.queue_name}"
                )
        except Exception as e:
            logger.error(f"Error closing Storage Queue connection: {e}")

    async def send_message(
        self, message: Union[StorageQueueMessageModel, Dict[str, Any], str], **kwargs
    ) -> Dict[str, Any]:
        """
        Send a message to the Storage Queue.

        Args:
            message: Message to send (StorageQueueMessageModel, dict, or JSON string)
            **kwargs: Additional arguments for queue client

        Returns:
            Message metadata including message_id and pop_receipt
        """
        if not self._queue_client:
            await self.connect()

        try:
            # Convert message to appropriate format
            if isinstance(message, StorageQueueMessageModel):
                message_content = message.to_queue_message()
                message_id = message.message_id
            elif isinstance(message, dict):
                # Convert dict to StorageQueueMessageModel for consistency
                queue_message = StorageQueueMessageModel(**message)
                message_content = queue_message.to_queue_message()
                message_id = queue_message.message_id
            else:
                message_content = str(message)
                message_id = str(uuid.uuid4())

            # Send message to queue
            response = await self._queue_client.send_message(
                content=message_content, **kwargs
            )

            logger.info(
                f"Message sent to queue '{self.config.queue_name}': {message_id}"
            )

            return {
                "message_id": response.id,
                "pop_receipt": response.pop_receipt,
                "time_next_visible": response.time_next_visible,
                "insertion_time": response.insertion_time,
                "expiration_time": response.expiration_time,
            }

        except Exception as e:
            logger.error(
                f"Failed to send message to queue '{self.config.queue_name}': {e}"
            )
            raise

    async def receive_messages(self, max_messages: Optional[int] = None) -> List[Any]:
        """
        Receive messages from the Storage Queue.

        Args:
            max_messages: Maximum number of messages to receive

        Returns:
            List of received messages
        """
        if not self._queue_client:
            await self.connect()

        max_msgs = max_messages or self.config.max_messages

        try:
            messages = []
            async for message in self._queue_client.receive_messages(
                messages_per_page=max_msgs,
                visibility_timeout=self.config.visibility_timeout,
            ):
                messages.append(message)
                if len(messages) >= max_msgs:
                    break

            logger.info(
                f"Received {len(messages)} messages from queue '{self.config.queue_name}'"
            )
            return messages

        except Exception as e:
            logger.error(
                f"Failed to receive messages from queue '{self.config.queue_name}': {e}"
            )
            raise

    async def delete_message(self, message) -> None:
        """
        Delete a message from the Storage Queue.

        Args:
            message: Message object to delete
        """
        if not self._queue_client:
            await self.connect()

        try:
            await self._queue_client.delete_message(message)
            logger.debug(f"Message deleted from queue '{self.config.queue_name}'")

        except Exception as e:
            logger.error(
                f"Failed to delete message from queue '{self.config.queue_name}': {e}"
            )
            raise

    async def get_queue_properties(self) -> Dict[str, Any]:
        """
        Get queue properties and metadata.

        Returns:
            Dictionary containing queue properties
        """
        if not self._queue_client:
            await self.connect()

        try:
            properties = await self._queue_client.get_queue_properties()

            return {
                "approximate_message_count": properties.approximate_message_count,
                "metadata": properties.metadata or {},
                "queue_name": self.config.queue_name,
                "storage_account": self.config.storage_account_name,
                "last_modified": properties.last_modified,
                "etag": properties.etag,
            }

        except Exception as e:
            logger.error(
                f"Failed to get queue properties for '{self.config.queue_name}': {e}"
            )
            raise

    async def peek_messages(self, max_messages: Optional[int] = None) -> List[Any]:
        """
        Peek at messages in the queue without removing them.

        Args:
            max_messages: Maximum number of messages to peek

        Returns:
            List of peeked messages
        """
        if not self._queue_client:
            await self.connect()

        max_msgs = max_messages or self.config.max_messages

        try:
            messages = []
            async for message in self._queue_client.peek_messages(
                max_messages=max_msgs
            ):
                messages.append(message)

            logger.info(
                f"Peeked at {len(messages)} messages in queue '{self.config.queue_name}'"
            )
            return messages

        except Exception as e:
            logger.error(
                f"Failed to peek messages in queue '{self.config.queue_name}': {e}"
            )
            raise

    async def clear_queue(self) -> None:
        """
        Clear all messages from the queue.

        Warning: This is a destructive operation!
        """
        if not self._queue_client:
            await self.connect()

        try:
            await self._queue_client.clear_messages()
            logger.info(f"Queue '{self.config.queue_name}' cleared")

        except Exception as e:
            logger.error(f"Failed to clear queue '{self.config.queue_name}': {e}")
            raise

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get client health status.

        Returns:
            Dictionary containing health information
        """
        return {
            "status": "healthy" if self._queue_client else "not_connected",
            "queue_name": self.config.queue_name,
            "storage_account": self.config.storage_account_name,
            "authentication": "managed_identity",
            "client_type": "storage_queue",
        }


# Compatibility function for easy migration from ServiceBusClient
async def create_storage_queue_client(queue_name: str) -> StorageQueueClient:
    """
    Create and connect a StorageQueueClient instance.

    Args:
        queue_name: Name of the Storage Queue

    Returns:
        Connected StorageQueueClient instance
    """
    client = StorageQueueClient(queue_name=queue_name)
    await client.connect()
    return client
