"""
Queue processing logic for markdown-generator.

Handles startup queue processing, message handling, and site-publisher signaling.
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from azure.storage.blob.aio import BlobServiceClient
from jinja2 import Environment
from markdown_processor import process_article
from models import ProcessingStatus

from libs.queue_client import (
    get_queue_client,
    process_queue_messages,
)

logger = logging.getLogger(__name__)


async def create_message_handler(
    blob_service_client: BlobServiceClient,
    settings: Any,  # Settings type
    jinja_env: Environment,
    unsplash_key: Optional[str],
    app_state: Dict[str, Any],
) -> Callable:
    """
    Create message handler for queue processing.

    Args:
        blob_service_client: Azure Blob Service client
        settings: Application settings
        jinja_env: Jinja2 environment (reusable)
        unsplash_key: Optional Unsplash API key
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

            # Call functional API directly
            result = await process_article(
                blob_service_client=blob_service_client,
                settings=settings,
                blob_name=blob_name,
                overwrite=False,
                template_name="default.md.j2",
                jinja_env=jinja_env,
                unsplash_access_key=unsplash_key,
            )

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

    Signals site-publisher after queue has been stable/empty for a period,
    indicating content-processor burst has completed. Prevents excessive
    site rebuilds during bursty traffic from scaled content-processors.

    Implements graceful self-termination after MAX_IDLE_TIME as backup to KEDA.

    Args:
        queue_name: Name of the queue to process
        message_handler: Async function to process each message
        max_batch_size: Maximum messages to process per batch
        output_container: Container name for markdown output
    """
    from datetime import datetime, timezone

    logger.info(f"🔍 Checking queue: {queue_name}")

    # Graceful termination settings
    # 3 minutes default
    MAX_IDLE_TIME = int(os.getenv("MAX_IDLE_TIME_SECONDS", "180"))
    last_activity_time = datetime.now(timezone.utc)

    # Site-publisher signaling with "stable empty queue" pattern
    # Signal only after queue has been empty for this duration (processor burst finished)
    STABLE_EMPTY_DURATION = int(os.getenv("STABLE_EMPTY_DURATION_SECONDS", "30"))
    queue_empty_since = None  # Track when queue first became empty
    total_processed = 0
    total_processed_since_signal = 0  # Track new content since last signal
    empty_checks = 0

    while True:
        # Process batch of messages (markdown generation is lightweight)
        messages_processed = await process_queue_messages(
            queue_name=queue_name,
            message_handler=message_handler,
            max_messages=max_batch_size,
        )

        current_time = datetime.now(timezone.utc)

        if messages_processed == 0:
            empty_checks += 1

            # Track when queue first became empty
            if queue_empty_since is None:
                queue_empty_since = current_time
                logger.info(
                    f"📭 Queue empty after processing {total_processed_since_signal} new messages. "
                    f"Waiting {STABLE_EMPTY_DURATION}s to ensure processor burst complete..."
                )

            # Calculate how long queue has been stable/empty
            stable_empty_seconds = (current_time - queue_empty_since).total_seconds()

            # Signal site-publisher if queue stable AND new content processed since last signal
            if (
                stable_empty_seconds >= STABLE_EMPTY_DURATION
                and total_processed_since_signal > 0
            ):
                logger.info(
                    f"✅ Queue stable for {int(stable_empty_seconds)}s after processing "
                    f"{total_processed_since_signal} new messages - signaling site-publisher"
                )
                await signal_site_publisher(
                    total_processed_since_signal, output_container
                )
                total_processed_since_signal = 0  # Reset counter after signaling
                logger.info(
                    "✅ Site-publisher signaled. Continuing to poll. "
                    "KEDA will scale to 0 after cooldown period."
                )

            # Check if we should gracefully terminate (longer than stable period)
            idle_seconds = (current_time - last_activity_time).total_seconds()
            if idle_seconds >= MAX_IDLE_TIME:
                logger.info(
                    f"🛑 Graceful shutdown: No messages for {int(idle_seconds)}s "
                    f"(max: {MAX_IDLE_TIME}s). Processed {total_processed} messages total."
                )
                break  # Exit loop, trigger cleanup and container shutdown

            # Log every 10th empty check to avoid log spam
            if empty_checks % 10 == 1 and empty_checks > 1:
                current_time_str = current_time.strftime("%H:%M:%S")
                logger.info(
                    f"✅ Queue still empty (processed {total_processed} total, "
                    f"stable: {int(stable_empty_seconds)}s/{STABLE_EMPTY_DURATION}s, "
                    f"idle: {int(idle_seconds)}s/{MAX_IDLE_TIME}s, last checked @ {current_time_str}). "
                    "Continuing to poll. KEDA will scale to 0 after cooldown period."
                )

            # Wait longer when queue is empty to reduce polling load
            await asyncio.sleep(10)
        else:
            # Messages processed - reset all empty/idle timers
            last_activity_time = current_time
            queue_empty_since = None  # Reset: queue no longer empty
            empty_checks = 0
            total_processed += messages_processed
            total_processed_since_signal += messages_processed
            logger.info(
                f"📦 Processed {messages_processed} messages "
                f"(batch total: {total_processed_since_signal}, lifetime: {total_processed}). "
                "Checking for more..."
            )

            # Brief pause before checking for next batch
            await asyncio.sleep(2)
