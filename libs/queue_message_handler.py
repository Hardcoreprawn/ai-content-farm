"""
Queue Message Handler with Proper Lifecycle Management

Fixes critical issues:
1. Messages being reprocessed (visibility timeout too short)
2. No poison message handling (infinite retries)
3. Messages not properly deleted after processing

Usage:
    from libs.queue_message_handler import QueueMessageHandler

    handler = QueueMessageHandler(
        queue_client=queue_client,
        visibility_timeout=300,  # 5 minutes
        max_dequeue_count=3,
        poison_queue_name="processing-poison-messages"
    )

    async with handler.receive_message() as message:
        # Process message
        result = await process(message.content)
        # Message automatically deleted on success
        # Moved to poison queue after 3 failures
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from azure.storage.queue.aio import QueueClient
from pydantic import BaseModel

logger = logging.getLogger(__name__)


@dataclass
class QueueMessage:
    """Wrapper for Azure Queue message with metadata."""

    id: str
    pop_receipt: str
    content: dict
    dequeue_count: int
    insertion_time: datetime
    expiration_time: datetime
    time_next_visible: datetime
    raw_message: Any  # Original Azure message object


class QueueMessageHandler:
    """
    Robust queue message handler with proper lifecycle management.

    Features:
    - Extended visibility timeout for long processing
    - Automatic poison message handling
    - Proper message deletion on success
    - Automatic re-queueing on failure
    - Dequeue count tracking
    """

    def __init__(
        self,
        queue_client: QueueClient,
        visibility_timeout: int = 300,  # 5 minutes default
        max_dequeue_count: int = 3,
        poison_queue_name: Optional[str] = None,
        enable_poison_queue: bool = True,
    ):
        """
        Initialize message handler.

        Args:
            queue_client: Azure QueueClient for main queue
            visibility_timeout: How long message is invisible (seconds)
            max_dequeue_count: Max retries before poison queue
            poison_queue_name: Name of poison message queue
            enable_poison_queue: Whether to use poison queue
        """
        self.queue_client = queue_client
        self.visibility_timeout = visibility_timeout
        self.max_dequeue_count = max_dequeue_count
        self.poison_queue_name = poison_queue_name
        self.enable_poison_queue = enable_poison_queue

        # Create poison queue client if enabled
        self._poison_queue_client: Optional[QueueClient] = None
        if enable_poison_queue and poison_queue_name:
            # Extract connection info from main queue client
            # We'll create poison queue client on first use
            pass

        # Statistics
        self.stats = {
            "messages_received": 0,
            "messages_processed": 0,
            "messages_failed": 0,
            "messages_moved_to_poison": 0,
            "average_processing_time": 0.0,
        }

    async def _get_poison_queue_client(self) -> Optional[QueueClient]:
        """Lazy initialization of poison queue client."""
        if not self.enable_poison_queue or not self.poison_queue_name:
            return None

        if self._poison_queue_client is None:
            # Create poison queue client using same credentials as main queue
            # This is a simplified version - in production, use proper client creation
            from azure.identity.aio import DefaultAzureCredential

            account_url = self.queue_client.url.split("?")[0].rsplit("/", 1)[0]
            credential = DefaultAzureCredential()

            self._poison_queue_client = QueueClient(
                account_url=account_url,
                queue_name=self.poison_queue_name,
                credential=credential,
            )

            # Ensure poison queue exists
            try:
                await self._poison_queue_client.create_queue()
                logger.info(f"✅ Created poison queue: {self.poison_queue_name}")
            except Exception as e:
                if "QueueAlreadyExists" not in str(e):
                    logger.warning(
                        f"⚠️  Could not create poison queue {self.poison_queue_name}: {e}"
                    )

        return self._poison_queue_client

    async def receive_messages(
        self, max_messages: int = 1, timeout: Optional[int] = None
    ) -> list[QueueMessage]:
        """
        Receive messages from queue with proper visibility timeout.

        Args:
            max_messages: Maximum messages to receive (1-32)
            timeout: Optional timeout for waiting (seconds)

        Returns:
            List of QueueMessage objects
        """
        try:
            messages = []
            message_pager = self.queue_client.receive_messages(
                messages_per_page=max_messages,
                visibility_timeout=self.visibility_timeout,  # CRITICAL FIX
                timeout=timeout,
            )

            # Properly handle async iterator
            try:
                count = 0
                async for msg in message_pager:
                    try:
                        content = json.loads(msg.content)
                    except json.JSONDecodeError:
                        content = {"raw_content": msg.content}

                    queue_msg = QueueMessage(
                        id=msg.id,
                        pop_receipt=msg.pop_receipt,
                        content=content,
                        dequeue_count=msg.dequeue_count,
                        insertion_time=msg.inserted_on,
                        expiration_time=msg.expires_on,
                        time_next_visible=msg.next_visible_on,
                        raw_message=msg,
                    )

                    messages.append(queue_msg)
                    self.stats["messages_received"] += 1

                    count += 1
                    if count >= max_messages:
                        break

            finally:
                # Properly close async iterator
                if hasattr(message_pager, "aclose"):
                    await message_pager.aclose()
                elif hasattr(message_pager, "close"):
                    await message_pager.close()

            logger.info(
                f"📬 Received {len(messages)} messages "
                f"(visibility: {self.visibility_timeout}s)"
            )
            return messages

        except Exception as e:
            logger.error(f"❌ Failed to receive messages: {e}")
            raise

    async def delete_message(self, message: QueueMessage) -> bool:
        """
        Delete message from queue after successful processing.

        Args:
            message: QueueMessage to delete

        Returns:
            True if deleted successfully
        """
        try:
            await self.queue_client.delete_message(message.id, message.pop_receipt)
            logger.info(f"✅ Deleted message {message.id}")
            self.stats["messages_processed"] += 1
            return True

        except Exception as e:
            logger.error(f"❌ Failed to delete message {message.id}: {e}")
            return False

    async def move_to_poison_queue(self, message: QueueMessage, error: str) -> bool:
        """
        Move message to poison queue after max retries.

        Args:
            message: QueueMessage that failed
            error: Error description

        Returns:
            True if moved successfully
        """
        if not self.enable_poison_queue:
            logger.warning(
                f"⚠️  Poison queue disabled, message {message.id} will retry indefinitely"
            )
            return False

        try:
            poison_client = await self._get_poison_queue_client()
            if not poison_client:
                return False

            # Add metadata about failure
            poison_content = {
                "original_message": message.content,
                "original_id": message.id,
                "dequeue_count": message.dequeue_count,
                "error": error,
                "moved_at": datetime.now(timezone.utc).isoformat(),
                "insertion_time": message.insertion_time.isoformat(),
            }

            # Send to poison queue
            await poison_client.send_message(json.dumps(poison_content))

            # Delete from original queue
            await self.delete_message(message)

            logger.warning(
                f"☠️  Moved message {message.id} to poison queue "
                f"(dequeue count: {message.dequeue_count})"
            )
            self.stats["messages_moved_to_poison"] += 1
            return True

        except Exception as e:
            logger.error(f"❌ Failed to move message to poison queue: {e}")
            return False

    async def should_move_to_poison_queue(self, message: QueueMessage) -> bool:
        """Check if message should be moved to poison queue."""
        return message.dequeue_count >= self.max_dequeue_count

    @asynccontextmanager
    async def process_message(self, message: QueueMessage):
        """
        Context manager for processing a message with automatic cleanup.

        Usage:
            async with handler.process_message(message) as msg:
                # Process message
                result = await do_work(msg.content)
                # Message automatically deleted on success

        On success: Message deleted from queue
        On failure: Message remains in queue (or moved to poison queue)
        """
        start_time = asyncio.get_event_loop().time()
        processing_success = False

        try:
            # Check if this message should go to poison queue
            if await self.should_move_to_poison_queue(message):
                error_msg = f"Max dequeue count reached ({message.dequeue_count})"
                await self.move_to_poison_queue(message, error_msg)
                raise RuntimeError(error_msg)

            yield message

            # If we get here, processing was successful
            processing_success = True

        except Exception as e:
            logger.error(
                f"❌ Error processing message {message.id} "
                f"(attempt {message.dequeue_count}/{self.max_dequeue_count}): {e}"
            )
            self.stats["messages_failed"] += 1
            raise

        finally:
            # Delete message only on success
            if processing_success:
                await self.delete_message(message)

                # Update timing stats
                elapsed = asyncio.get_event_loop().time() - start_time
                current_avg = self.stats["average_processing_time"]
                total_processed = self.stats["messages_processed"]
                self.stats["average_processing_time"] = (
                    (current_avg * (total_processed - 1) + elapsed) / total_processed
                    if total_processed > 0
                    else elapsed
                )

    async def process_batch(
        self,
        processor_func: Callable,
        max_messages: int = 10,
        concurrent: bool = True,
    ) -> Dict[str, int]:
        """
        Process a batch of messages with proper lifecycle management.

        Args:
            processor_func: Async function to process each message
            max_messages: Maximum messages to process in batch
            concurrent: Whether to process messages concurrently

        Returns:
            Dict with processing statistics
        """
        messages = await self.receive_messages(max_messages=max_messages)

        if not messages:
            return {
                "messages_received": 0,
                "messages_processed": 0,
                "messages_failed": 0,
            }

        batch_stats = {
            "messages_received": len(messages),
            "messages_processed": 0,
            "messages_failed": 0,
        }

        if concurrent:
            # Process concurrently
            tasks = [
                self._process_single_message(msg, processor_func) for msg in messages
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    batch_stats["messages_failed"] += 1
                else:
                    batch_stats["messages_processed"] += 1
        else:
            # Process sequentially
            for message in messages:
                try:
                    await self._process_single_message(message, processor_func)
                    batch_stats["messages_processed"] += 1
                except Exception:
                    batch_stats["messages_failed"] += 1

        return batch_stats

    async def _process_single_message(
        self, message: QueueMessage, processor_func: Callable
    ):
        """Process a single message with proper error handling."""
        async with self.process_message(message) as msg:
            await processor_func(msg)

    def get_stats(self) -> Dict[str, Any]:
        """Get handler statistics."""
        return {
            **self.stats,
            "visibility_timeout": self.visibility_timeout,
            "max_dequeue_count": self.max_dequeue_count,
            "poison_queue_enabled": self.enable_poison_queue,
            "poison_queue_name": self.poison_queue_name,
        }

    async def close(self):
        """Close queue clients."""
        if self._poison_queue_client:
            await self._poison_queue_client.close()
