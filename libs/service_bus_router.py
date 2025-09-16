"""
Shared Service Bus Router - Base Implementation for Container Services

Provides standardized Service Bus handling patterns while allowing for
service-specific message processing logic. Eliminates code duplication
across container services.

Usage:
    from libs.service_bus_router import ServiceBusRouterBase

    class MyServiceBusRouter(ServiceBusRouterBase):
        async def process_message_payload(self, payload: Dict[str, Any], operation: str) -> Dict[str, Any]:
            # Service-specific logic here
            return {"status": "success", "result": "..."}
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field

from libs.service_bus_client import ServiceBusClient, ServiceBusConfig
from libs.shared_models import StandardResponse, create_service_dependency

logger = logging.getLogger(__name__)


class ServiceBusStatusResponse(BaseModel):
    """Standard Service Bus status response model."""

    connection_status: str = Field(..., description="Service Bus connection status")
    queue_name: str = Field(..., description="Configured queue name")
    namespace: str = Field(..., description="Service Bus namespace")
    last_poll_time: str = Field(..., description="Last polling time")
    messages_processed: int = Field(..., description="Total messages processed")


class ServiceBusProcessResponse(BaseModel):
    """Standard Service Bus process response model."""

    messages_received: int = Field(..., description="Number of messages received")
    messages_processed: int = Field(
        ..., description="Number of messages processed successfully"
    )
    messages_failed: int = Field(
        ..., description="Number of messages that failed processing"
    )


class ServiceBusRouterBase(ABC):
    """
    Base class for Service Bus routers with standardized patterns.

    Each container service should inherit from this and implement
    process_message_payload() with their specific business logic.
    """

    def __init__(self, service_name: str, queue_name: str, prefix: str = "/internal"):
        """
        Initialize the Service Bus router.

        Args:
            service_name: Name of the service (for metadata)
            queue_name: Service Bus queue name to listen to
            prefix: API route prefix
        """
        self.service_name = service_name
        self.queue_name = queue_name
        self.router = APIRouter(prefix=prefix, tags=["Service Bus"])
        self._service_bus_client: Optional[ServiceBusClient] = None

        # Create service metadata dependency
        self.service_metadata = create_service_dependency(service_name)

        # Register routes
        self._register_routes()

    def _register_routes(self):
        """Register standard Service Bus routes."""

        @self.router.post(
            "/process-servicebus-message",
            response_model=StandardResponse[ServiceBusProcessResponse],
        )
        async def process_servicebus_message(
            background_tasks: BackgroundTasks, metadata=Depends(self.service_metadata)
        ) -> StandardResponse[ServiceBusProcessResponse]:
            """Poll Service Bus queue and process messages."""
            return await self._process_servicebus_message_impl(metadata)

        @self.router.get(
            "/servicebus-status",
            response_model=StandardResponse[ServiceBusStatusResponse],
        )
        async def get_servicebus_status(
            metadata=Depends(self.service_metadata),
        ) -> StandardResponse[ServiceBusStatusResponse]:
            """Get Service Bus connection and queue status."""
            return await self._get_servicebus_status_impl(metadata)

        @self.router.get(
            "/scaling-metrics",
            response_model=StandardResponse,
        )
        async def get_scaling_metrics(
            metadata=Depends(self.service_metadata),
        ) -> StandardResponse:
            """Get scaling performance metrics for this service."""
            try:
                from libs.scaling_metrics import get_metrics_collector

                metrics = get_metrics_collector(self.service_name)
                summary = metrics.get_performance_summary()

                return StandardResponse(
                    status="success",
                    message="Scaling metrics retrieved",
                    data=summary,
                    errors=[],
                    metadata=metadata,
                )
            except Exception as e:
                return StandardResponse(
                    status="error",
                    message="Failed to retrieve scaling metrics",
                    data={},
                    errors=[str(e)],
                    metadata=metadata,
                )

    async def _get_service_bus_client(self) -> ServiceBusClient:
        """Get or create Service Bus client."""
        if self._service_bus_client is None:
            try:
                config = ServiceBusConfig.from_environment()
                # Override queue name with service-specific queue
                config.queue_name = self.queue_name

                self._service_bus_client = ServiceBusClient(config)
                await self._service_bus_client.connect()
                logger.info(f"Service Bus client initialized for {self.service_name}")
            except Exception as e:
                logger.error(
                    f"Failed to initialize Service Bus client for {self.service_name}"
                )
                logger.debug(f"Service Bus initialization error: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Service Bus client initialization failed",
                )

        return self._service_bus_client

    async def _process_servicebus_message_impl(
        self, metadata: Dict[str, Any]
    ) -> StandardResponse[ServiceBusProcessResponse]:
        """Standard Service Bus message processing implementation with metrics collection."""
        import time
        import uuid

        batch_start_time = time.time() * 1000  # Start timing the batch
        batch_id = str(uuid.uuid4())[:8]

        try:
            # Import metrics collector
            from libs.scaling_metrics import get_metrics_collector

            metrics = get_metrics_collector(self.service_name)

            client = await self._get_service_bus_client()

            # Get queue depth before processing
            queue_depth_before = None
            try:
                queue_props = await client.get_queue_properties()
                if queue_props.get("status") == "healthy":
                    queue_depth_before = queue_props.get("active_message_count")
            except Exception as e:
                logger.debug(f"Could not get queue depth before processing: {e}")

            # Receive messages from Service Bus
            messages = await client.receive_messages(
                max_messages=self.get_max_messages()
            )

            messages_processed = 0
            messages_failed = 0

            for batch_position, message in enumerate(messages):
                message_start_time = (
                    time.time() * 1000
                )  # Start timing individual message
                message_success = False
                error_type = None

                try:
                    # Parse message body
                    message_body = str(message)
                    message_data = json.loads(message_body)

                    logger.info(f"Processing Service Bus message: {message.message_id}")

                    # Extract operation and payload
                    operation = message_data.get("operation", "default")
                    payload = message_data.get("payload", {})

                    # Call service-specific processing logic
                    result = await self.process_message_payload(payload, operation)

                    if self.is_processing_successful(result):
                        # Acknowledge successful processing
                        await client.complete_message(message)
                        messages_processed += 1
                        message_success = True
                        logger.info(
                            f"Successfully processed message: {message.message_id}"
                        )
                    else:
                        # Processing failed, abandon message for retry
                        await client.abandon_message(message)
                        messages_failed += 1
                        error_type = "processing_failed"
                        logger.error(
                            f"Processing failed for message: {message.message_id}"
                        )

                except json.JSONDecodeError as e:
                    # Invalid JSON, dead letter the message
                    await client.dead_letter_message(message, "Invalid JSON format")
                    messages_failed += 1
                    error_type = "invalid_json"
                    logger.error(f"Invalid JSON in message {message.message_id}: {e}")

                except Exception as e:
                    # Processing error, abandon for retry
                    await client.abandon_message(message)
                    messages_failed += 1
                    error_type = "processing_error"
                    logger.error(f"Error processing message {message.message_id}: {e}")

                finally:
                    # Record individual message processing metrics
                    message_end_time = time.time() * 1000
                    processing_time_ms = int(message_end_time - message_start_time)

                    metrics.record_message_processing(
                        message_id=message.message_id,
                        queue_name=self.queue_name,
                        processing_time_ms=processing_time_ms,
                        batch_size=len(messages),
                        batch_position=batch_position,
                        success=message_success,
                        error_type=error_type,
                    )

            # Get queue depth after processing
            queue_depth_after = None
            try:
                queue_props = await client.get_queue_properties()
                if queue_props.get("status") == "healthy":
                    queue_depth_after = queue_props.get("active_message_count")
            except Exception as e:
                logger.debug(f"Could not get queue depth after processing: {e}")

            # Record batch processing metrics
            batch_end_time = time.time() * 1000
            total_processing_time_ms = int(batch_end_time - batch_start_time)

            metrics.record_batch_processing(
                batch_id=batch_id,
                queue_name=self.queue_name,
                batch_size=len(messages),
                total_processing_time_ms=total_processing_time_ms,
                messages_processed=messages_processed,
                messages_failed=messages_failed,
                queue_depth_before=queue_depth_before,
                queue_depth_after=queue_depth_after,
            )

            response_data = ServiceBusProcessResponse(
                messages_received=len(messages),
                messages_processed=messages_processed,
                messages_failed=messages_failed,
            )

            return StandardResponse(
                status="success",
                message=f"Processed {messages_processed} messages successfully",
                data=response_data,
                errors=[],
                metadata=metadata,
            )

        except Exception as e:
            logger.error(
                f"Service Bus message processing failed for {self.service_name}: {e}"
            )
            return StandardResponse(
                status="error",
                message="Service Bus message processing failed",
                data=ServiceBusProcessResponse(
                    messages_received=0, messages_processed=0, messages_failed=0
                ),
                errors=[str(e)],
                metadata=metadata,
            )

    async def _get_servicebus_status_impl(
        self, metadata: Dict[str, Any]
    ) -> StandardResponse[ServiceBusStatusResponse]:
        """Standard Service Bus status implementation."""
        try:
            client = await self._get_service_bus_client()

            status_data = ServiceBusStatusResponse(
                connection_status="connected",
                queue_name=self.queue_name,
                namespace=client.config.namespace,
                last_poll_time="N/A",  # Could be enhanced with actual tracking
                messages_processed=0,  # Could be enhanced with actual tracking
            )

            return StandardResponse(
                status="success",
                message="Service Bus status retrieved successfully",
                data=status_data,
                errors=[],
                metadata=metadata,
            )

        except Exception as e:
            logger.error(
                f"Failed to get Service Bus status for {self.service_name}: {e}"
            )

            status_data = ServiceBusStatusResponse(
                connection_status="error",
                queue_name=self.queue_name,
                namespace="unknown",
                last_poll_time="N/A",
                messages_processed=0,
            )

            return StandardResponse(
                status="error",
                message="Failed to retrieve Service Bus status",
                data=status_data,
                errors=[str(e)],
                metadata=metadata,
            )

    # Abstract methods that services must implement
    @abstractmethod
    async def process_message_payload(
        self, payload: Dict[str, Any], operation: str
    ) -> Dict[str, Any]:
        """
        Process a Service Bus message payload.

        This method must be implemented by each service to handle their
        specific message processing logic.

        Args:
            payload: Message payload data
            operation: Operation type from the message

        Returns:
            Dict with processing result (must include status indicator)
        """
        pass

    def is_processing_successful(self, result: Dict[str, Any]) -> bool:
        """
        Determine if message processing was successful.

        Default implementation checks for status="success" or non-empty results.
        Services can override this for custom success criteria.

        Args:
            result: Processing result from process_message_payload

        Returns:
            True if processing was successful
        """
        return (
            result.get("status") == "success"
            or len(result.get("collected_items", [])) >= 0
            or len(result.get("processed_items", [])) >= 0
            or len(result.get("generated_items", [])) >= 0
            or result.get("success", False)
        )

    def get_max_messages(self) -> int:
        """
        Get maximum messages to process per batch.

        Services can override this to customize batch sizes.
        """
        return 10
