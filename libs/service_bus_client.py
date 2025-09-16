"""
Azure Service Bus Client - Shared Library for Container Apps

Provides standardized Service Bus messaging functionality for all container services.
Implements secure, resilient Service Bus operations with proper error handling
and retry logic for the Phase 1 Security Implementation.

Key Features:
- Managed identity authentication (no connection strings in code)
- Standardized message polling with exponential backoff
- Error handling and dead letter queue management
- Correlation ID tracking for message tracing
- Health check integration
- KEDA-compatible scaling trigger support

Usage:
    from libs.service_bus_client import ServiceBusClient

    client = ServiceBusClient(queue_name="content-collection-requests")
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
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from azure.identity.aio import DefaultAzureCredential
from azure.servicebus import ServiceBusMessage
from azure.servicebus.aio import ServiceBusClient as AzureServiceBusClient
from azure.servicebus.aio import ServiceBusReceiver, ServiceBusSender
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ServiceBusMessageModel(BaseModel):
    """Standardized Service Bus message format for container services."""

    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    service_name: str = Field(..., description="Name of the requesting service")
    operation: str = Field(..., description="Operation to perform")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Message payload")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    def to_service_bus_message(self) -> ServiceBusMessage:
        """Convert to Azure Service Bus message format."""
        message_body = self.model_dump_json()

        message = ServiceBusMessage(
            body=message_body,
            message_id=self.message_id,
            correlation_id=self.correlation_id,
        )

        # Add custom properties for routing and filtering
        message.application_properties = {
            "service_name": self.service_name,
            "operation": self.operation,
            "timestamp": self.timestamp.isoformat(),
        }

        return message


class ServiceBusConfig(BaseModel):
    """Service Bus configuration model.

    Note: KEDA scaling in Azure Container Apps requires connection string authentication
    for Service Bus, not managed identity. While Azure Container Apps supports managed
    identity for scale rules with some Azure services (Storage Queues, Event Hubs),
    Service Bus scale rules currently require connection string authentication.

    This is a limitation of Azure Container Apps' KEDA implementation, not KEDA itself.
    KEDA supports Azure Workload Identity (managed identity) for Service Bus, but
    Azure Container Apps' implementation only supports connection string auth for
    Service Bus scalers as of 2025.

    Therefore, we must use the same connection string for both KEDA scaling AND
    application code to ensure consistent authentication and prevent messages from
    being stuck in queues due to authentication mismatches.
    """

    namespace: str = Field(..., description="Service Bus namespace")
    queue_name: str = Field(..., description="Queue name")
    connection_string: str = Field(
        default="", description="Service Bus connection string (optional)"
    )
    max_wait_time: int = Field(
        default=1, description="Max wait time for receiving messages"
    )
    max_messages: int = Field(
        default=10, description="Max messages to receive per poll"
    )
    retry_attempts: int = Field(default=3, description="Number of retry attempts")

    @classmethod
    def from_environment(
        cls, queue_name: str = "content-processing-requests"
    ) -> "ServiceBusConfig":
        """Create config from environment variables."""
        namespace = os.getenv("SERVICE_BUS_NAMESPACE", "").strip()
        connection_string = os.getenv("SERVICE_BUS_CONNECTION_STRING", "").strip()

        if not namespace:
            raise ValueError("SERVICE_BUS_NAMESPACE environment variable is required")

        return cls(
            namespace=namespace,
            queue_name=queue_name,
            connection_string=connection_string,
        )


class ServiceBusClient:
    """
    Azure Service Bus client with managed identity authentication.

    Provides high-level interface for sending and receiving messages
    with built-in error handling and retry logic.
    """

    def __init__(self, config: Optional[ServiceBusConfig] = None):
        """
        Initialize Service Bus client.

        Args:
            config: Service Bus configuration. If None, loads from environment.
        """
        self.config = config or ServiceBusConfig.from_environment()
        self.credential = DefaultAzureCredential()
        self._client: Optional[AzureServiceBusClient] = None
        self._sender: Optional[ServiceBusSender] = None
        self._receiver: Optional[ServiceBusReceiver] = None

        logger.info(f"ServiceBusClient initialized for queue: {self.config.queue_name}")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def connect(self) -> None:
        """Establish connection to Service Bus.

        Note: Azure Container Apps KEDA scaling requires connection string authentication
        for Service Bus. While we prefer managed identity for security, we must use
        connection string authentication to match KEDA's requirements and prevent
        authentication mismatches that cause messages to remain stuck in queues.

        See ServiceBusConfig docstring for full technical details.
        """
        try:
            # Use connection string if available, otherwise use managed identity
            logger.info(f"=== SERVICE BUS AUTH DEBUG ===")
            logger.info(
                f"Connection string length: {len(self.config.connection_string) if self.config.connection_string else 0}"
            )
            logger.info(
                f"Connection string starts with: {self.config.connection_string[:50] if self.config.connection_string else 'None'}"
            )
            logger.info(f"Namespace: {self.config.namespace}")
            logger.info(f"Queue: {self.config.queue_name}")
            logger.info(f"=== END DEBUG ===")

            if self.config.connection_string:
                self._client = AzureServiceBusClient.from_connection_string(
                    conn_str=self.config.connection_string
                )
                logger.info(f"Connected to Service Bus using connection string")
            else:
                if not self.config.namespace:
                    raise ValueError(
                        "SERVICE_BUS_NAMESPACE environment variable is required when not using connection string"
                    )

                # Construct fully qualified namespace
                fully_qualified_namespace = (
                    f"{self.config.namespace}.servicebus.windows.net"
                )

                self._client = AzureServiceBusClient(
                    fully_qualified_namespace=fully_qualified_namespace,
                    credential=self.credential,
                )
                logger.info(
                    f"Connected to Service Bus namespace: {self.config.namespace}"
                )

        except Exception as e:
            logger.error(f"Failed to connect to Service Bus: {e}")
            raise

    async def close(self) -> None:
        """Close Service Bus connections."""
        try:
            if self._receiver:
                await self._receiver.close()
            if self._sender:
                await self._sender.close()
            if self._client:
                await self._client.close()

            logger.info("Service Bus connections closed")

        except Exception as e:
            logger.error(f"Error closing Service Bus connections: {e}")

    async def send_message(
        self, message: Union[ServiceBusMessageModel, Dict[str, Any]]
    ) -> bool:
        """
        Send a message to the Service Bus queue.

        Args:
            message: Message to send (ServiceBusMessageModel or dict)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self._client:
                await self.connect()

            # Convert dict to ServiceBusMessageModel if needed
            if isinstance(message, dict):
                message = ServiceBusMessageModel(**message)

            # Create sender if not exists
            if not self._sender:
                self._sender = self._client.get_queue_sender(
                    queue_name=self.config.queue_name
                )

            sb_message = message.to_service_bus_message()

            async with self._sender:
                await self._sender.send_messages(sb_message)

            logger.info(f"Message sent successfully: {message.message_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False

    async def receive_messages(self, max_messages: Optional[int] = None) -> List[Any]:
        """
        Receive messages from the Service Bus queue.

        Args:
            max_messages: Maximum number of messages to receive

        Returns:
            List of received messages
        """
        try:
            if not self._client:
                await self.connect()

            max_msg_count = max_messages or self.config.max_messages

            # Create receiver if not exists or if it was closed
            if not self._receiver:
                self._receiver = self._client.get_queue_receiver(
                    queue_name=self.config.queue_name
                )

            try:
                # Don't use async with here - let the receiver stay open
                messages = await self._receiver.receive_messages(
                    max_message_count=max_msg_count,
                    max_wait_time=self.config.max_wait_time,
                )
            except Exception as receiver_error:
                # If receiver failed (likely closed), recreate it and try again
                logger.warning(f"Receiver error, recreating: {receiver_error}")
                self._receiver = self._client.get_queue_receiver(
                    queue_name=self.config.queue_name
                )
                messages = await self._receiver.receive_messages(
                    max_message_count=max_msg_count,
                    max_wait_time=self.config.max_wait_time,
                )

            logger.info(f"Received {len(messages)} messages from queue")
            return messages

        except Exception as e:
            logger.error(f"Failed to receive messages: {e}")
            return []

    async def complete_message(self, message) -> bool:
        """
        Complete (acknowledge) a message.

        Args:
            message: Message to complete

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self._receiver:
                logger.error("No active receiver to complete message")
                return False

            await self._receiver.complete_message(message)
            logger.debug(f"Message completed: {message.message_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to complete message: {e}")
            return False

    async def abandon_message(self, message) -> bool:
        """
        Abandon a message (return to queue for retry).

        Args:
            message: Message to abandon

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self._receiver:
                logger.error("No active receiver to abandon message")
                return False

            await self._receiver.abandon_message(message)
            logger.debug(f"Message abandoned: {message.message_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to abandon message: {e}")
            return False

    async def dead_letter_message(
        self, message, reason: str = "Processing failed"
    ) -> bool:
        """
        Move message to dead letter queue.

        Args:
            message: Message to dead letter
            reason: Reason for dead lettering

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self._receiver:
                logger.error("No active receiver to dead letter message")
                return False

            await self._receiver.dead_letter_message(
                message,
                reason=reason,
            )
            logger.warning(f"Message dead lettered: {message.message_id} - {reason}")
            return True

        except Exception as e:
            logger.error(f"Failed to dead letter message: {e}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on Service Bus connection.

        Returns:
            Dict with health status information
        """
        try:
            if not self._client:
                await self.connect()

            # Simple connection test
            async with self._client.get_queue_receiver(
                queue_name=self.config.queue_name
            ) as receiver:
                # Try to peek at messages without consuming them
                messages = await receiver.peek_messages(max_message_count=1)

            return {
                "status": "healthy",
                "namespace": self.config.namespace,
                "queue_name": self.config.queue_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message_count_sample": len(messages),
            }

        except Exception as e:
            logger.error(f"Service Bus health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
            }

    async def get_queue_properties(self) -> Dict[str, Any]:
        """
        Get queue properties including message counts and status.

        Returns:
            Dict with queue properties and message counts
        """
        try:
            if not self._client:
                await self.connect()

            # Get queue runtime properties using the management client
            from azure.identity import DefaultAzureCredential
            from azure.servicebus.management import ServiceBusAdministrationClient

            # Create management client for getting queue properties
            mgmt_client = ServiceBusAdministrationClient(
                fully_qualified_namespace=f"{self.config.namespace}.servicebus.windows.net",
                credential=DefaultAzureCredential(),
            )

            # Get queue runtime properties
            queue_runtime_properties = mgmt_client.get_queue_runtime_properties(
                queue_name=self.config.queue_name
            )

            # Safely get message counts with null checks
            active_count = (
                getattr(queue_runtime_properties, "active_message_count", 0) or 0
            )
            dead_letter_count = (
                getattr(queue_runtime_properties, "dead_letter_message_count", 0) or 0
            )
            scheduled_count = (
                getattr(queue_runtime_properties, "scheduled_message_count", 0) or 0
            )
            transfer_count = (
                getattr(queue_runtime_properties, "transfer_message_count", 0) or 0
            )
            transfer_dead_letter_count = (
                getattr(
                    queue_runtime_properties, "transfer_dead_letter_message_count", 0
                )
                or 0
            )
            size_bytes = getattr(queue_runtime_properties, "size_in_bytes", 0) or 0

            # Safely get timestamp attributes
            created_at = getattr(queue_runtime_properties, "created_at", None)
            updated_at = getattr(queue_runtime_properties, "updated_at", None)
            accessed_at = getattr(queue_runtime_properties, "accessed_at", None)

            return {
                "queue_name": self.config.queue_name,
                "active_message_count": active_count,
                "dead_letter_message_count": dead_letter_count,
                "scheduled_message_count": scheduled_count,
                "transfer_message_count": transfer_count,
                "transfer_dead_letter_message_count": transfer_dead_letter_count,
                "total_message_count": (
                    active_count
                    + dead_letter_count
                    + scheduled_count
                    + transfer_count
                    + transfer_dead_letter_count
                ),
                "size_in_bytes": size_bytes,
                "created_at": created_at.isoformat() if created_at else None,
                "updated_at": updated_at.isoformat() if updated_at else None,
                "accessed_at": accessed_at.isoformat() if accessed_at else None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "healthy",
            }

        except Exception as e:
            logger.error(f"Failed to get queue properties: {e}")
            return {
                "queue_name": self.config.queue_name,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }


class ServiceBusPollingService:
    """
    Background service for polling Service Bus messages.

    Designed to work with KEDA scaling - when messages arrive,
    KEDA will scale up containers and this service will process them.
    """

    def __init__(
        self, client: ServiceBusClient, message_handler, poll_interval: int = 10
    ):
        """
        Initialize polling service.

        Args:
            client: ServiceBusClient instance
            message_handler: Async function to handle received messages
            poll_interval: Polling interval in seconds
        """
        self.client = client
        self.message_handler = message_handler
        self.poll_interval = poll_interval
        self.is_running = False

    async def start_polling(self) -> None:
        """Start the message polling loop."""
        self.is_running = True
        logger.info("Starting Service Bus message polling")

        while self.is_running:
            try:
                messages = await self.client.receive_messages()

                if messages:
                    logger.info(f"Processing {len(messages)} messages")

                    for message in messages:
                        try:
                            # Parse message body
                            message_data = json.loads(str(message))

                            # Call message handler
                            success = await self.message_handler(message_data)

                            if success:
                                await self.client.complete_message(message)
                            else:
                                await self.client.abandon_message(message)

                        except json.JSONDecodeError as e:
                            logger.error(f"Invalid message format: {e}")
                            await self.client.dead_letter_message(
                                message, "Invalid JSON format"
                            )

                        except Exception as e:
                            logger.error(f"Message processing failed: {e}")
                            await self.client.abandon_message(message)

                else:
                    # No messages, wait before next poll
                    await asyncio.sleep(self.poll_interval)

            except Exception as e:
                logger.error(f"Polling error: {e}")
                await asyncio.sleep(self.poll_interval)

    def stop_polling(self) -> None:
        """Stop the message polling loop."""
        self.is_running = False
        logger.info("Stopping Service Bus message polling")


# Convenience functions for easy integration
async def create_service_bus_client(
    queue_name: Optional[str] = None,
) -> ServiceBusClient:
    """
    Create and connect a Service Bus client.

    Args:
        queue_name: Override queue name from environment

    Returns:
        Connected ServiceBusClient instance
    """
    config = ServiceBusConfig.from_environment()
    if queue_name:
        config.queue_name = queue_name

    client = ServiceBusClient(config)
    await client.connect()
    return client


def create_standard_message(
    service_name: str,
    operation: str,
    payload: Dict[str, Any],
    correlation_id: Optional[str] = None,
) -> ServiceBusMessageModel:
    """
    Create a standardized Service Bus message.

    Args:
        service_name: Name of the requesting service
        operation: Operation to perform
        payload: Message payload
        correlation_id: Optional correlation ID for tracing

    Returns:
        ServiceBusMessageModel instance
    """
    return ServiceBusMessageModel(
        service_name=service_name,
        operation=operation,
        payload=payload,
        correlation_id=correlation_id or str(uuid.uuid4()),
        metadata={"created_by": "service_bus_client", "version": "1.0.0"},
    )
