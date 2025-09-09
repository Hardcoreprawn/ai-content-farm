"""
Service Bus Endpoints for Content Collector

Implements Phase 1 Security Implementation endpoints for Service Bus message processing.
These endpoints handle Service Bus messages sent by Logic Apps, replacing direct HTTP calls.

Features:
- Service Bus message polling and processing
- KEDA scaling integration
- Standard error handling and logging
- Message acknowledgment and retry logic
"""

import json
import logging
from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field

from libs.service_bus_client import (
    ServiceBusClient,
    ServiceBusConfig,
    ServiceBusPollingService,
    create_service_bus_client,
)
from libs.shared_models import StandardResponse, create_service_dependency

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/internal", tags=["Service Bus"])

# Service metadata dependency
service_metadata = create_service_dependency("content-collector")


class ServiceBusStatusResponse(BaseModel):
    """Service Bus status response model."""

    connection_status: str = Field(..., description="Service Bus connection status")
    queue_name: str = Field(..., description="Configured queue name")
    namespace: str = Field(..., description="Service Bus namespace")
    last_poll_time: str = Field(..., description="Last polling time")
    messages_processed: int = Field(..., description="Total messages processed")


class ServiceBusProcessResponse(BaseModel):
    """Service Bus process response model."""

    messages_received: int = Field(..., description="Number of messages received")
    messages_processed: int = Field(
        ..., description="Number of messages processed successfully"
    )
    messages_failed: int = Field(
        ..., description="Number of messages that failed processing"
    )


# Global Service Bus client (initialized on first use)
_service_bus_client: ServiceBusClient = None


async def get_service_bus_client() -> ServiceBusClient:
    """Get or create Service Bus client."""
    global _service_bus_client

    if _service_bus_client is None:
        try:
            config = ServiceBusConfig.from_environment()
            _service_bus_client = ServiceBusClient(config)
            await _service_bus_client.connect()
            logger.info("Service Bus client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Service Bus client: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Service Bus client initialization failed: {str(e)}",
            )

    return _service_bus_client


@router.post(
    "/process-servicebus-message",
    response_model=StandardResponse[ServiceBusProcessResponse],
)
async def process_servicebus_message(
    background_tasks: BackgroundTasks, metadata=Depends(service_metadata)
) -> StandardResponse[ServiceBusProcessResponse]:
    """
    Poll Service Bus queue and process messages.

    This endpoint is called by KEDA when messages are available in the queue.
    It processes collection requests sent by Logic Apps via Service Bus.

    Returns:
        StandardResponse with processing statistics
    """
    try:
        client = await get_service_bus_client()

        # Receive messages from Service Bus
        messages = await client.receive_messages(max_messages=10)

        messages_processed = 0
        messages_failed = 0

        for message in messages:
            try:
                # Parse message body
                message_body = str(message)
                message_data = json.loads(message_body)

                logger.info(f"Processing Service Bus message: {message.message_id}")

                # Extract collection request from message payload
                if "payload" in message_data and "sources" in message_data["payload"]:
                    collection_request = message_data["payload"]

                    # Process the collection request using existing logic
                    # Import here to avoid circular imports
                    from endpoints.collections_router import process_collection_request

                    result = await process_collection_request(collection_request)

                    if result.get("status") == "success":
                        # Acknowledge successful processing
                        await client.complete_message(message)
                        messages_processed += 1
                        logger.info(
                            f"Successfully processed message: {message.message_id}"
                        )
                    else:
                        # Processing failed, abandon message for retry
                        await client.abandon_message(message)
                        messages_failed += 1
                        logger.error(
                            f"Processing failed for message: {message.message_id}"
                        )
                else:
                    # Invalid message format
                    await client.dead_letter_message(message, "Invalid message format")
                    messages_failed += 1
                    logger.error(f"Invalid message format: {message.message_id}")

            except json.JSONDecodeError as e:
                # Invalid JSON, dead letter the message
                await client.dead_letter_message(message, "Invalid JSON format")
                messages_failed += 1
                logger.error(f"Invalid JSON in message {message.message_id}: {e}")

            except Exception as e:
                # Processing error, abandon for retry
                await client.abandon_message(message)
                messages_failed += 1
                logger.error(f"Error processing message {message.message_id}: {e}")

        response_data = ServiceBusProcessResponse(
            messages_received=len(messages),
            messages_processed=messages_processed,
            messages_failed=messages_failed,
        )

        return StandardResponse(
            status="success",
            message=f"Processed {messages_processed} messages successfully",
            data=response_data,
            metadata=metadata,
        )

    except Exception as e:
        logger.error(f"Service Bus message processing failed: {e}")
        return StandardResponse(
            status="error",
            message="Service Bus message processing failed",
            data=ServiceBusProcessResponse(
                messages_received=0, messages_processed=0, messages_failed=0
            ),
            errors=[str(e)],
            metadata=metadata,
        )


@router.get(
    "/servicebus-status", response_model=StandardResponse[ServiceBusStatusResponse]
)
async def get_servicebus_status(
    metadata=Depends(service_metadata),
) -> StandardResponse[ServiceBusStatusResponse]:
    """
    Get Service Bus connection and queue status.

    Returns:
        StandardResponse with Service Bus status information
    """
    try:
        client = await get_service_bus_client()
        health_info = await client.health_check()

        status_data = ServiceBusStatusResponse(
            connection_status=health_info.get("status", "unknown"),
            queue_name=client.config.queue_name,
            namespace=client.config.namespace,
            last_poll_time=health_info.get("timestamp", ""),
            messages_processed=0,  # TODO: Add tracking of processed message count
        )

        return StandardResponse(
            status="success",
            message="Service Bus status retrieved successfully",
            data=status_data,
            metadata=metadata,
        )

    except Exception as e:
        logger.error(f"Failed to get Service Bus status: {e}")
        return StandardResponse(
            status="error",
            message="Failed to get Service Bus status",
            data=ServiceBusStatusResponse(
                connection_status="error",
                queue_name="unknown",
                namespace="unknown",
                last_poll_time="",
                messages_processed=0,
            ),
            errors=[str(e)],
            metadata=metadata,
        )


@router.post("/start-servicebus-polling")
async def start_servicebus_polling(
    background_tasks: BackgroundTasks, metadata=Depends(service_metadata)
) -> StandardResponse[Dict[str, Any]]:
    """
    Start background Service Bus message polling.

    This endpoint starts a background task that continuously polls
    the Service Bus queue for messages. Used in conjunction with KEDA scaling.

    Returns:
        StandardResponse with polling status
    """
    try:
        client = await get_service_bus_client()

        # Define message handler function
        async def message_handler(message_data: Dict[str, Any]) -> bool:
            """Handle received Service Bus messages."""
            try:
                if "payload" in message_data and "sources" in message_data["payload"]:
                    collection_request = message_data["payload"]

                    # Import here to avoid circular imports
                    from endpoints.collections_router import process_collection_request

                    result = await process_collection_request(collection_request)
                    return result.get("status") == "success"
                else:
                    logger.error("Invalid message format received")
                    return False

            except Exception as e:
                logger.error(f"Message handler error: {e}")
                return False

        # Create and start polling service
        polling_service = ServiceBusPollingService(
            client, message_handler, poll_interval=10
        )

        # Start polling in background
        background_tasks.add_task(polling_service.start_polling)

        return StandardResponse(
            status="success",
            message="Service Bus polling started successfully",
            data={"polling_status": "started", "poll_interval": 10},
            metadata=metadata,
        )

    except Exception as e:
        logger.error(f"Failed to start Service Bus polling: {e}")
        return StandardResponse(
            status="error",
            message="Failed to start Service Bus polling",
            data={"polling_status": "failed"},
            errors=[str(e)],
            metadata=metadata,
        )
