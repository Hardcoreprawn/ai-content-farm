"""
Storage Queue Background Polling - Shared Library

Provides standardized background polling for KEDA-scaled containers using Azure Storage Queues.
When DISABLE_AUTO_SHUTDOWN=true, the container will continuously poll the queue and process messages.

Usage:
    from libs.storage_queue_poller import StorageQueuePoller

    # In your FastAPI lifespan or startup
    async def process_message(message_data: Dict[str, Any]) -> Dict[str, Any]:
        # Your message processing logic
        return {"status": "success", "data": {...}}

    poller = StorageQueuePoller(
        queue_name="content-processing-requests",
        message_handler=process_message,
        poll_interval=5.0
    )
    await poller.start()
    # ... app runs ...
    await poller.stop()
"""

import asyncio
import logging
import os
from typing import Any, Callable, Coroutine, Dict, Optional

logger = logging.getLogger(__name__)


class StorageQueuePoller:
    """
    Background Storage Queue polling service.

    Automatically polls an Azure Storage Queue for messages and processes them
    using the provided message handler. Designed for KEDA-scaled containers
    that need to process messages continuously when DISABLE_AUTO_SHUTDOWN=true.
    """

    def __init__(
        self,
        queue_name: str,
        message_handler: Callable[
            [Dict[str, Any]], Coroutine[Any, Any, Dict[str, Any]]
        ],
        poll_interval: float = 5.0,
        max_messages_per_batch: int = 10,
        max_empty_polls: int = 3,
        empty_queue_sleep: float = 30.0,
        process_queue_messages_func: Optional[Callable] = None,
    ):
        """
        Initialize storage queue poller.

        Args:
            queue_name: Name of the Azure Storage Queue to poll
            message_handler: Async function to process each message
            poll_interval: Seconds between polls when queue has messages
            max_messages_per_batch: Maximum messages to process in each batch
            max_empty_polls: Maximum consecutive empty polls before longer sleep
            empty_queue_sleep: Seconds to sleep when queue is consistently empty
            process_queue_messages_func: Optional function to process queue messages
                                        (defaults to importing from libs.queue_triggers)
        """
        self.queue_name = queue_name
        self.message_handler = message_handler
        self.poll_interval = poll_interval
        self.max_messages_per_batch = max_messages_per_batch
        self.max_empty_polls = max_empty_polls
        self.empty_queue_sleep = empty_queue_sleep
        self.process_queue_messages_func = process_queue_messages_func

        self._polling_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._is_running = False
        self._total_messages_processed = 0

    async def start(self):
        """Start background polling."""
        if self._is_running:
            logger.warning(
                f"Storage queue poller already running for {self.queue_name}"
            )
            return

        # Check if polling is enabled
        disable_auto_shutdown = (
            os.getenv("DISABLE_AUTO_SHUTDOWN", "false").lower() == "true"
        )
        if not disable_auto_shutdown:
            logger.info(
                f"Storage queue polling disabled for {self.queue_name} "
                "(DISABLE_AUTO_SHUTDOWN=false)"
            )
            return

        self._is_running = True
        self._stop_event.clear()
        self._total_messages_processed = 0

        # Import process_queue_messages if not provided
        if self.process_queue_messages_func is None:
            try:
                from libs.queue_triggers import process_queue_messages

                self.process_queue_messages_func = process_queue_messages
            except ImportError:
                logger.error(
                    "Could not import process_queue_messages from libs.queue_triggers"
                )
                self._is_running = False
                return

        self._polling_task = asyncio.create_task(self._polling_loop())

        logger.info(
            f"🔄 Started background polling for queue '{self.queue_name}' "
            f"(poll_interval={self.poll_interval}s, max_messages={self.max_messages_per_batch})"
        )

    async def stop(self):
        """Stop background polling."""
        if not self._is_running:
            return

        logger.info(f"Stopping background polling for queue '{self.queue_name}'")

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
            f"✅ Background polling stopped for queue '{self.queue_name}' "
            f"(total messages processed: {self._total_messages_processed})"
        )

    async def _polling_loop(self):
        """Main polling loop - runs until stop event is set."""
        empty_poll_count = 0

        while not self._stop_event.is_set():
            try:
                # Process messages from Storage Queue
                messages_processed = await self.process_queue_messages_func(
                    queue_name=self.queue_name,
                    message_handler=self.message_handler,
                    max_messages=self.max_messages_per_batch,
                )

                if messages_processed > 0:
                    # Reset empty poll counter if we processed messages
                    empty_poll_count = 0
                    self._total_messages_processed += messages_processed

                    logger.info(
                        f"📦 Processed {messages_processed} messages from '{self.queue_name}' "
                        f"(total: {self._total_messages_processed})"
                    )

                    # Short pause before next poll when actively processing
                    await asyncio.sleep(self.poll_interval)
                else:
                    # No messages processed
                    empty_poll_count += 1

                    if empty_poll_count >= self.max_empty_polls:
                        # Queue seems empty, longer sleep
                        logger.debug(
                            f"Queue '{self.queue_name}' empty after {empty_poll_count} attempts, "
                            f"sleeping {self.empty_queue_sleep}s"
                        )
                        await asyncio.sleep(self.empty_queue_sleep)
                        empty_poll_count = 0  # Reset counter after long sleep
                    else:
                        # Short pause before retry
                        await asyncio.sleep(self.poll_interval)

            except asyncio.CancelledError:
                logger.info("Polling loop cancelled")
                break
            except Exception as e:
                logger.error(
                    f"❌ Unexpected error in polling loop for '{self.queue_name}': {e}"
                )
                # Don't crash the loop, just wait and retry
                await asyncio.sleep(self.empty_queue_sleep)
                empty_poll_count = 0

    @property
    def is_running(self) -> bool:
        """Check if poller is currently running."""
        return self._is_running

    @property
    def messages_processed(self) -> int:
        """Get total number of messages processed."""
        return self._total_messages_processed
