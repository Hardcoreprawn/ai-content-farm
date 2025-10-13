"""
Queue processing logic for markdown-generator.

Handles startup queue processing, message handling, and site-publisher signaling.
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Callable, Dict

from models import ProcessingStatus

from libs.queue_client import (
    get_queue_client,
    process_queue_messages,
)

logger = logging.getLogger(__name__)


async def create_message_handler(
    processor: Any,
    app_state: Dict[str, Any],
) -> Callable:
    """
    Create message handler for queue processing.

    Args:
        processor: MarkdownProcessor instance
        app_state: Application state dictionary

    Returns:
        Async message handler function
    """

    async def message_handler(queue_message, message) -> Dict[str, Any]:
        """Process a single markdown generation request from the queue."""
        try:
            # Extract the processed file path from the queue_message (QueueMessageModel)
            payload = queue_message.payload
            files = payload.get("files", [])

            if not files:
                logger.warning(
                    f"No files in message {queue_message.message_id}, payload: {payload}"
                )
                return {"status": "error", "error": "No files in message"}

            # Process the first file (we expect one file per message)
            blob_name = files[0]
            logger.info(f"Processing markdown generation for {blob_name}")

            # Use the processor to generate markdown (async)
            result = await processor.process_article(blob_name)

            if result.status == ProcessingStatus.COMPLETED:
                logger.info(
                    f"Successfully generated markdown: {result.markdown_blob_name}"
                )
                app_state["total_processed"] += 1
                if result.processing_time_ms:
                    app_state["processing_times"].append(result.processing_time_ms)
                return {"status": "success", "result": result.model_dump()}
            else:
                logger.warning(f"Markdown generation failed: {result.error_message}")
                app_state["total_failed"] += 1
                return {"status": "error", "error": result.error_message}

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            app_state["total_failed"] += 1
            return {"status": "error", "error": str(e)}

    return message_handler


async def signal_site_publisher(total_processed: int, output_container: str) -> None:
    """
    Send completion signal to site-publisher queue.

    Args:
        total_processed: Number of markdown files generated
        output_container: Container name where markdown files are stored
    """
    try:
        # Create publish request message
        batch_id = f"collection-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        publish_message = {
            "service_name": "markdown-generator",
            "operation": "site_publish_request",
            "payload": {
                "batch_id": batch_id,
                "markdown_count": total_processed,
                "markdown_container": output_container,
                "trigger": "queue_empty",
                "timestamp": datetime.utcnow().isoformat(),
            },
        }

        # Send to site-publisher queue
        async with get_queue_client("site-publishing-requests") as queue_client:
            result = await queue_client.send_message(publish_message)
            logger.info(
                f"📤 Sent publish request to site-publisher "
                f"(batch_id={batch_id}, message_id={result.get('message_id', 'unknown')})"
            )

    except Exception as e:
        logger.error(
            f"Failed to send completion signal to site-publisher queue: {e}",
            exc_info=True,
        )
        # Don't fail the container - this is not critical
        # Site can be published manually if needed


async def startup_queue_processor(
    queue_name: str,
    message_handler: Callable,
    max_batch_size: int,
    output_container: str,
) -> None:
    """
    Process queue messages continuously with graceful self-termination.

    Signals site-publisher after first batch completes, then continues polling.
    Implements graceful self-termination after MAX_IDLE_TIME as backup to KEDA.

    Args:
        queue_name: Name of the queue to process
        message_handler: Async function to process each message
        max_batch_size: Maximum messages to process per batch
        output_container: Container name for markdown output
    """
    import os
    from datetime import datetime, timezone

    logger.info(f"🔍 Checking queue: {queue_name}")

    # Graceful termination settings
    MAX_IDLE_TIME = int(os.getenv("MAX_IDLE_TIME_SECONDS", "180"))  # 3 minutes default
    last_activity_time = datetime.now(timezone.utc)

    total_processed = 0
    signaled_site_publisher = False
    empty_checks = 0

    while True:
        # Process batch of messages (markdown generation is lightweight)
        messages_processed = await process_queue_messages(
            queue_name=queue_name,
            message_handler=message_handler,
            max_messages=max_batch_size,
        )

        if messages_processed == 0:
            empty_checks += 1

            # Signal site-publisher once after first batch completes
            if total_processed > 0 and not signaled_site_publisher:
                logger.info(
                    f"✅ Markdown queue empty after processing {total_processed} messages - "
                    "signaling site-publisher to build static site"
                )
                await signal_site_publisher(total_processed, output_container)
                signaled_site_publisher = True
                logger.info(
                    f"✅ Processing complete ({total_processed} messages). "
                    "Continuing to poll. KEDA will scale to 0 after cooldown period."
                )

            # Check if we should gracefully terminate
            idle_seconds = (
                datetime.now(timezone.utc) - last_activity_time
            ).total_seconds()
            if idle_seconds >= MAX_IDLE_TIME:
                logger.info(
                    f"🛑 Graceful shutdown: No messages for {int(idle_seconds)}s "
                    f"(max: {MAX_IDLE_TIME}s). Processed {total_processed} messages total."
                )
                break  # Exit loop, trigger cleanup and container shutdown

            # Log every 10th empty check to avoid log spam
            if empty_checks % 10 == 1 and empty_checks > 1:
                logger.info(
                    f"✅ Queue still empty (processed {total_processed} total, "
                    f"idle: {int(idle_seconds)}s/{MAX_IDLE_TIME}s). "
                    "Continuing to poll. KEDA will scale to 0 after cooldown period."
                )

            # Wait longer when queue is empty to reduce polling load
            await asyncio.sleep(10)
        else:
            # Reset idle timer when we process messages
            last_activity_time = datetime.now(timezone.utc)
            empty_checks = 0  # Reset counter when message processed
            total_processed += messages_processed
            logger.info(
                f"📦 Processed {messages_processed} messages (total: {total_processed}). "
                "Checking for more..."
            )

            # Brief pause before checking for next batch
            await asyncio.sleep(2)
