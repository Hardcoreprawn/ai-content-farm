"""
Service Bus Endpoints for Content Collector

Implements Service Bus message processing for content collection requests.
Uses shared Service Bus router base for consistency across services.
"""

import logging
from typing import Any, Dict

from libs.service_bus_router import ServiceBusRouterBase

logger = logging.getLogger(__name__)


class ContentCollectorServiceBusRouter(ServiceBusRouterBase):
    """Service Bus router for content collection service."""

    def __init__(self):
        super().__init__(
            service_name="content-collector",
            queue_name="content-collection-requests",
            prefix="/internal",
        )

    async def process_message_payload(
        self, payload: Dict[str, Any], operation: str
    ) -> Dict[str, Any]:
        """
        Process content collection requests from Service Bus.

        Args:
            payload: Collection request payload with sources, options
            operation: Operation type (collect_content, etc.)

        Returns:
            Dict with collection results
        """
        try:
            if operation == "collect_content" and "sources" in payload:
                # Process the collection request using existing logic
                from service_logic import ContentCollectorService

                collector_service = ContentCollectorService()
                result = await collector_service.collect_and_store_content(
                    sources_data=payload.get("sources", []),
                    deduplicate=payload.get("deduplicate", True),
                    similarity_threshold=payload.get("similarity_threshold", 0.8),
                    save_to_storage=payload.get("save_to_storage", True),
                )

                logger.info(f"Collected {len(result.get('collected_items', []))} items")
                return {
                    "status": "success",
                    "collected_items": result.get("collected_items", []),
                    "collection_id": result.get("collection_id"),
                    "storage_location": result.get("storage_location"),
                }
            else:
                logger.error(f"Invalid operation or payload: {operation}")
                return {
                    "status": "error",
                    "error": f"Invalid operation '{operation}' or missing sources",
                }

        except Exception as e:
            logger.error(f"Content collection failed: {e}")
            return {"status": "error", "error": str(e)}

    def get_max_messages(self) -> int:
        """Content collector can handle more messages concurrently."""
        return 15


# Create router instance
service_bus_router = ContentCollectorServiceBusRouter()
router = service_bus_router.router

import asyncio
import json
import logging
from typing import Any, Dict, Optional

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
_service_bus_client: Optional[ServiceBusClient] = None


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
            logger.error("Failed to initialize Service Bus client")
            logger.debug(f"Service Bus client initialization error details: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Service Bus client initialization failed",
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
                    from service_logic import ContentCollectorService

                    collector_service = ContentCollectorService()
                    result = await collector_service.collect_and_store_content(
                        sources_data=collection_request.get("sources", []),
                        deduplicate=collection_request.get("deduplicate", True),
                        similarity_threshold=collection_request.get(
                            "similarity_threshold", 0.8
                        ),
                        save_to_storage=collection_request.get("save_to_storage", True),
                    )

                    if (
                        result.get("status") == "success"
                        or len(result.get("collected_items", [])) >= 0
                    ):
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
                logger.error(f"Invalid JSON in message {message.message_id}")
                logger.debug(
                    f"JSON decode error details for message {message.message_id}: {e}"
                )

            except Exception as e:
                # Processing error, abandon for retry
                await client.abandon_message(message)
                messages_failed += 1
                logger.error(f"Error processing message {message.message_id}")
                logger.debug(
                    f"Message processing error details for {message.message_id}: {e}"
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
        logger.error("Service Bus message processing failed")
        logger.debug(f"Service Bus message processing error details: {e}")
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
            errors=[],
            metadata=metadata,
        )

    except Exception as e:
        logger.error("Failed to get Service Bus status")
        logger.debug(f"Service Bus status retrieval error details: {e}")
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

                    # Process the collection request using existing logic
                    from service_logic import ContentCollectorService

                    collector_service = ContentCollectorService()
                    result = await collector_service.collect_and_store_content(
                        sources_data=collection_request.get("sources", []),
                        deduplicate=collection_request.get("deduplicate", True),
                        similarity_threshold=collection_request.get(
                            "similarity_threshold", 0.8
                        ),
                        save_to_storage=collection_request.get("save_to_storage", True),
                    )
                    return (
                        len(result.get("collected_items", [])) >= 0
                    )  # Success if we got results
                else:
                    logger.error("Invalid message format received")
                    return False

            except Exception as e:
                logger.error("Message handler error")
                logger.debug(f"Message handler error details: {e}")
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
            errors=[],
            metadata=metadata,
        )

    except Exception as e:
        logger.error("Failed to start Service Bus polling")
        logger.debug(f"Service Bus polling start error details: {e}")
        return StandardResponse(
            status="error",
            message="Failed to start Service Bus polling",
            data={"polling_status": "failed"},
            errors=["Service Bus polling initialization failed"],
            metadata=metadata,
        )
