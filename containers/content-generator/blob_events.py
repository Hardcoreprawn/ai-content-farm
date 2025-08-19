"""
Real-time event processing for blob storage events using Azure Service Bus
"""

import json
import asyncio
import logging
from typing import Dict, Any, Optional
from azure.servicebus.aio import ServiceBusClient
from azure.servicebus import ServiceBusMessage
from azure.identity import DefaultAzureCredential
import os

logger = logging.getLogger(__name__)


class BlobEventProcessor:
    """Process blob storage events in real-time using Service Bus"""

    def __init__(self, content_generator_service):
        self.content_generator = content_generator_service
        self.namespace = os.getenv("SERVICE_BUS_NAMESPACE")
        self.queue_name = os.getenv("BLOB_EVENTS_QUEUE", "blob-events")
        self.credential = DefaultAzureCredential()
        self.client = None
        self.receiver = None
        self.is_running = False

    async def start(self):
        """Start processing blob events from Service Bus"""
        if not self.namespace:
            logger.warning(
                "No Service Bus namespace configured, falling back to polling")
            return False

        try:
            # Create Service Bus client
            fully_qualified_namespace = f"{self.namespace}.servicebus.windows.net"
            self.client = ServiceBusClient(
                fully_qualified_namespace=fully_qualified_namespace,
                credential=self.credential
            )

            # Create receiver for the queue
            self.receiver = self.client.get_queue_receiver(
                queue_name=self.queue_name,
                max_wait_time=30
            )

            self.is_running = True
            logger.info(
                f"Started Service Bus event processor for queue: {self.queue_name}")

            # Start processing messages
            await self._process_messages()
            return True

        except Exception as e:
            logger.error(f"Failed to start Service Bus event processor: {e}")
            return False

    async def stop(self):
        """Stop processing events"""
        self.is_running = False
        if self.receiver:
            await self.receiver.close()
        if self.client:
            await self.client.close()
        logger.info("Stopped Service Bus event processor")

    async def _process_messages(self):
        """Process incoming messages from Service Bus"""
        while self.is_running:
            try:
                # Receive messages with timeout
                received_msgs = await self.receiver.receive_messages(
                    max_message_count=10,
                    max_wait_time=30
                )

                for message in received_msgs:
                    try:
                        # Process the blob event
                        await self._handle_blob_event(message)

                        # Complete the message (remove from queue)
                        await self.receiver.complete_message(message)

                    except Exception as e:
                        logger.error(f"Failed to process message: {e}")
                        # Dead letter the message if processing fails
                        await self.receiver.dead_letter_message(
                            message,
                            reason="ProcessingError",
                            error_description=str(e)
                        )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in message processing loop: {e}")
                await asyncio.sleep(10)  # Wait before retrying

    async def _handle_blob_event(self, message: ServiceBusMessage):
        """Handle a single blob storage event"""
        try:
            # Parse the Event Grid event from Service Bus message
            event_data = json.loads(str(message))

            # Event Grid sends events as an array
            if isinstance(event_data, list):
                events = event_data
            else:
                events = [event_data]

            for event in events:
                await self._process_blob_event(event)

        except Exception as e:
            logger.error(f"Failed to handle blob event: {e}")
            raise

    async def _process_blob_event(self, event: Dict[str, Any]):
        """Process a single blob creation event"""
        try:
            # Extract event information
            event_type = event.get("eventType")
            subject = event.get("subject", "")
            data = event.get("data", {})

            if event_type != "Microsoft.Storage.BlobCreated":
                logger.debug(f"Ignoring event type: {event_type}")
                return

            # Extract blob information
            blob_url = data.get("url", "")
            blob_name = self._extract_blob_name(subject)
            container_name = self._extract_container_name(subject)

            if not blob_name or container_name != "ranked-content":
                logger.debug(
                    f"Ignoring blob: {blob_name} in container: {container_name}")
                return

            if not blob_name.endswith(".json"):
                logger.debug(f"Ignoring non-JSON blob: {blob_name}")
                return

            logger.info(f"Processing blob event: {blob_name}")

            # Process the ranked content blob
            await self.content_generator._process_ranked_content_blob(blob_name)

        except Exception as e:
            logger.error(f"Failed to process blob event: {e}")
            raise

    def _extract_blob_name(self, subject: str) -> Optional[str]:
        """Extract blob name from Event Grid subject"""
        # Subject format: /blobServices/default/containers/{container}/blobs/{blob}
        parts = subject.split("/")
        if len(parts) >= 6 and parts[4] == "blobs":
            return "/".join(parts[5:])  # Handle blobs with / in name
        return None

    def _extract_container_name(self, subject: str) -> Optional[str]:
        """Extract container name from Event Grid subject"""
        # Subject format: /blobServices/default/containers/{container}/blobs/{blob}
        parts = subject.split("/")
        if len(parts) >= 5 and parts[2] == "containers":
            return parts[3]
        return None
