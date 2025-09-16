"""
Background Service Bus Polling - Shared Library

Provides standardized background polling for KEDA-scaled containers.
When a container starts up, it automatically polls its Service Bus queue
and processes messages until the queue is empty, then sleeps.

Usage:
    from libs.service_bus_router import ServiceBusRouterBase

    # In your FastAPI lifespan
    poller = BackgroundPoller(service_bus_router, poll_interval=5.0)
    await poller.start()
    # ... app runs ...
    await poller.stop()
"""

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class BackgroundPoller:
    """
    Background Service Bus queue polling service.

    Automatically polls a Service Bus queue for messages and processes them
    using the provided service bus router. Designed for KEDA-scaled containers
    that need to process messages until the queue is empty.
    """

    def __init__(
        self,
        service_bus_router,
        poll_interval: float = 5.0,
        max_poll_attempts: int = 3,
        empty_queue_sleep: float = 30.0,
    ):
        """
        Initialize background poller.

        Args:
            service_bus_router: Service bus router instance with process_servicebus_message_impl method
            poll_interval: Seconds between polls when queue has messages
            max_poll_attempts: Maximum consecutive empty polls before longer sleep
            empty_queue_sleep: Seconds to sleep when queue is consistently empty
        """
        self.service_bus_router = service_bus_router
        self.poll_interval = poll_interval
        self.max_poll_attempts = max_poll_attempts
        self.empty_queue_sleep = empty_queue_sleep

        self._polling_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._is_running = False

    async def start(self):
        """Start background polling."""
        if self._is_running:
            logger.warning("Background poller already running")
            return

        self._is_running = True
        self._stop_event.clear()

        # Create metadata for service bus calls
        metadata = {
            "timestamp": self._get_current_iso_timestamp(),
            "function": self.service_bus_router.service_name,
            "version": "1.0.0",
            "poller": "background_poller",
        }

        self._polling_task = asyncio.create_task(self._polling_loop(metadata))

        logger.info(
            f"Started background polling for {self.service_bus_router.service_name} "
            f"(queue: {self.service_bus_router.queue_name})"
        )

    async def stop(self):
        """Stop background polling."""
        if not self._is_running:
            return

        logger.info(
            f"Stopping background polling for {self.service_bus_router.service_name}"
        )

        self._stop_event.set()

        if self._polling_task and not self._polling_task.done():
            try:
                await asyncio.wait_for(self._polling_task, timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning("Polling task did not stop gracefully, cancelling")
                self._polling_task.cancel()
                try:
                    await self._polling_task
                except asyncio.CancelledError:
                    pass

        self._is_running = False
        logger.info(
            f"Background polling stopped for {self.service_bus_router.service_name}"
        )

    async def _polling_loop(self, metadata: dict):
        """Main polling loop - runs until stop event is set."""
        empty_poll_count = 0

        while not self._stop_event.is_set():
            try:
                # Update metadata timestamp
                metadata["timestamp"] = self._get_current_iso_timestamp()

                # Process messages from Service Bus
                result = await self.service_bus_router._process_servicebus_message_impl(
                    metadata
                )

                # Check if we processed any messages
                if result.status == "success" and hasattr(
                    result.data, "messages_processed"
                ):
                    messages_processed = result.data.messages_processed

                    if messages_processed > 0:
                        # Reset empty poll counter if we processed messages
                        empty_poll_count = 0
                        logger.info(
                            f"Processed {messages_processed} messages from "
                            f"{self.service_bus_router.queue_name}"
                        )

                        # Short pause before next poll when actively processing
                        await asyncio.sleep(self.poll_interval)
                    else:
                        # No messages processed
                        empty_poll_count += 1

                        if empty_poll_count >= self.max_poll_attempts:
                            # Queue seems empty, longer sleep
                            logger.debug(
                                f"Queue {self.service_bus_router.queue_name} empty "
                                f"after {empty_poll_count} attempts, sleeping {self.empty_queue_sleep}s"
                            )
                            await asyncio.sleep(self.empty_queue_sleep)
                            empty_poll_count = 0  # Reset counter after long sleep
                        else:
                            # Short pause before retry
                            await asyncio.sleep(self.poll_interval)
                else:
                    # Error occurred, longer pause
                    logger.warning(
                        f"Service Bus polling error for {self.service_bus_router.queue_name}: "
                        f"{result.message}"
                    )
                    await asyncio.sleep(self.empty_queue_sleep)
                    empty_poll_count = 0

            except asyncio.CancelledError:
                logger.info("Polling loop cancelled")
                break
            except Exception as e:
                logger.error(f"Unexpected error in polling loop: {e}")
                # Don't crash the loop, just wait and retry
                await asyncio.sleep(self.empty_queue_sleep)

    def _get_current_iso_timestamp(self) -> str:
        """Get current ISO timestamp."""
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat()

    @property
    def is_running(self) -> bool:
        """Check if poller is currently running."""
        return self._is_running
