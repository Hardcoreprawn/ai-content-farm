"""
Queue processing operations for site generator.

Handles message processing and routing for site generation tasks.
"""

import logging
from typing import Any, Callable, Dict, Optional

from fastapi import HTTPException

logger = logging.getLogger(__name__)


class QueueMessageProcessor:
    """Handles queue message processing operations."""

    def __init__(self, storage_queue_router):
        """Initialize with storage queue router."""
        self.storage_queue_router = storage_queue_router

    async def process_storage_queue_messages(
        self, request_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process messages from storage queue with optional configuration."""
        try:
            # Default configuration
            queue_name = "site-generator-queue"
            max_messages = 5
            timeout_seconds = 30

            # Override with request data if provided
            if request_data:
                queue_name = request_data.get("queue_name", queue_name)
                max_messages = request_data.get("max_messages", max_messages)
                timeout_seconds = request_data.get("timeout_seconds", timeout_seconds)

            logger.info(
                f"Processing storage queue messages: queue={queue_name}, max={max_messages}, timeout={timeout_seconds}"
            )

            # Message handler for individual messages
            async def message_handler(queue_message, message) -> Dict[str, Any]:
                """Handle individual queue message."""
                try:
                    result = (
                        await self.storage_queue_router.process_storage_queue_message(
                            queue_message
                        )
                    )

                    if result["status"] == "success":
                        logger.info(
                            f"✅ Processed message: {result.get('message', 'No message')}"
                        )
                        return {"status": "success", "data": result}
                    else:
                        logger.warning(
                            f"⚠️  Message processing returned non-success: {result}"
                        )
                        return {"status": "warning", "data": result}

                except Exception as e:
                    logger.error(f"❌ Failed to process message: {e}")
                    return {"status": "error", "error": str(e)}

            # Process queue messages
            results = await self._process_queue_messages(
                queue_name=queue_name,
                max_messages=max_messages,
                message_handler=message_handler,
                timeout_seconds=timeout_seconds,
            )

            return {
                "status": "success",
                "message": f"Processed {results.get('messages_processed', 0)} messages",
                "data": results,
                "metadata": {
                    "queue_name": queue_name,
                    "max_messages": max_messages,
                    "timeout_seconds": timeout_seconds,
                },
            }

        except Exception as e:
            logger.error(f"Queue message processing failed: {e}")
            raise HTTPException(
                status_code=500, detail=f"Queue processing error: {str(e)}"
            )

    async def _process_queue_messages(
        self,
        queue_name: str,
        max_messages: int,
        message_handler: Callable,
        timeout_seconds: int,
    ) -> Dict[str, Any]:
        """Internal queue message processing with timeout."""
        try:
            from libs.queue_client import QueueClient

            queue_client = QueueClient()

            # Get messages from queue
            messages = await queue_client.receive_messages(
                queue_name=queue_name,
                max_messages=max_messages,
                visibility_timeout=timeout_seconds,
            )

            if not messages:
                logger.info(f"No messages found in queue: {queue_name}")
                return {"messages_processed": 0, "messages_found": 0, "results": []}

            logger.info(f"Found {len(messages)} messages in queue: {queue_name}")
            results = []
            processed_count = 0

            # Process each message
            for message in messages:
                try:
                    # Parse queue message
                    queue_message = {
                        "id": message.id,
                        "content": message.content,
                        "pop_receipt": message.pop_receipt,
                        "dequeue_count": message.dequeue_count,
                    }

                    # Process with handler
                    result = await message_handler(queue_message, message)
                    results.append(result)

                    if result["status"] == "success":
                        # Delete processed message
                        await queue_client.delete_message(
                            queue_name=queue_name,
                            message_id=message.id,
                            pop_receipt=message.pop_receipt,
                        )
                        processed_count += 1
                    else:
                        logger.warning(
                            f"Message not deleted due to processing status: {result['status']}"
                        )

                except Exception as e:
                    logger.error(f"Failed to process individual message: {e}")
                    results.append({"status": "error", "error": str(e)})

            return {
                "messages_processed": processed_count,
                "messages_found": len(messages),
                "results": results,
            }

        except Exception as e:
            logger.error(f"Queue message processing failed: {e}")
            raise e
