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
        app_state: Application state dictionary (includes file tracking)

    Returns:
        Async message handler function that returns file creation count
    """

    async def message_handler(queue_message, message) -> Dict[str, Any]:
        """
        Process a single markdown generation request from the queue.

        Returns information about whether NEW FILES were created (not just messages processed).
        """
        try:
            # Extract the processed file path from the queue_message (QueueMessageModel)
            payload = queue_message.payload
            files = payload.get("files", [])

            if not files:
                logger.warning(
                    f"No files in message {queue_message.message_id}, payload: {payload}"
                )
                app_state["total_failed"] += 1
                return {
                    "status": "error",
                    "error": "No files in message",
                    "files_created": 0,
                }

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
                # Track: did we CREATE a new file, or was it a duplicate?
                files_created_count = 1 if result.files_created else 0

                logger.info(
                    f"Successfully processed markdown: {result.markdown_blob_name} "
                    f"(new_file={result.files_created})"
                )
                app_state["total_processed"] += 1
                app_state["total_files_generated"] = (
                    app_state.get("total_files_generated", 0) + files_created_count
                )

                if result.processing_time_ms:
                    app_state["processing_times"].append(result.processing_time_ms)

                return {
                    "status": "success",
                    "files_created": files_created_count,
                    "result": result.model_dump(),
                }
            else:
                logger.warning(f"Markdown generation failed: {result.error_message}")
                app_state["total_failed"] += 1
                return {
                    "status": "error",
                    "error": result.error_message,
                    "files_created": 0,
                }

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            app_state["total_failed"] += 1
            return {"status": "error", "error": str(e), "files_created": 0}

    return message_handler


async def signal_site_publisher(total_processed: int, output_container: str) -> None:
    """
    Send completion signal to site-publisher queue.

    Args:
        total_processed: Number of markdown files generated
        output_container: Container name where markdown files are stored
    """
    try:
        # Create publish request message in correct format for site-publisher
        batch_id = f"collection-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        publish_message = {
            "service_name": "markdown-generator",
            "operation": "markdown_generated",
            "payload": {
                "batch_id": batch_id,
                "markdown_container": output_container,
                "trigger": "queue_empty",
                "timestamp": datetime.utcnow().isoformat(),
            },
            "content_summary": {
                "files_created": total_processed,
                "files_failed": 0,
                "force_rebuild": False,
            },
        }

        # Send to site-publisher queue
        async with get_queue_client("site-publishing-requests") as queue_client:
            result = await queue_client.send_message(publish_message)
            logger.info(
                f"📤 Sent publish request to site-publisher "
                f"(batch_id={batch_id}, files_created={total_processed}, message_id={result.get('message_id', 'unknown')})"
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
    app_state: Dict[str, Any],
) -> None:
    """
    Process queue messages continuously with graceful self-termination.

    Signals site-publisher ONLY after queue has been stable/empty for a period
    AND at least one NEW markdown file was generated.

    This prevents false signals when:
    - Queue had duplicate messages
    - Messages failed to generate markdown
    - No actual new content was produced

    Implements graceful self-termination after MAX_IDLE_TIME as backup to KEDA.

    Args:
        queue_name: Name of the queue to process
        message_handler: Async function to process each message (returns files_created count)
        max_batch_size: Maximum messages to process per batch
        output_container: Container name for markdown output
        app_state: Application state dict (includes total_files_generated counter)
    """
    from datetime import datetime, timezone

    logger.info(f"🔍 Checking queue: {queue_name}")

    # Log queue diagnostics on startup to help debug backlog issues
    try:
        async with get_queue_client(queue_name) as client:
            props = await client.get_queue_properties()
            logger.info(
                f"📊 Queue diagnostics on startup: "
                f"approximate_count={props.get('approximate_message_count', '?')}, "
                f"peeked_visible={props.get('peeked_visible_messages', '?')}"
            )

            # Warning if there's a mismatch (suggests messages are invisible/locked)
            approx = props.get("approximate_message_count", 0)
            peeked = props.get("peeked_visible_messages", 0)
            if approx > 0 and peeked == 0 and approx > 5:
                logger.warning(
                    f"⚠️  DIAGNOSTIC ALERT: Queue has ~{approx} messages but "
                    f"{peeked} are visible. Messages may be locked/invisible from a previous run. "
                    f"This commonly happens when: "
                    f"1) Previous container crashed during processing, 2) Visibility timeout too long, "
                    f"3) Messages failed to complete/delete. "
                    f"Waiting for visibility timeout to expire (~60s)..."
                )
    except Exception as diag_err:
        logger.warning(f"Could not get queue diagnostics on startup: {diag_err}")

    # Graceful termination settings
    MAX_IDLE_TIME = int(os.getenv("MAX_IDLE_TIME_SECONDS", "180"))
    last_activity_time = datetime.now(timezone.utc)

    # Site-publisher signaling with "stable empty queue" pattern
    # Signal only after queue has been empty for this duration (processor burst finished)
    STABLE_EMPTY_DURATION = int(os.getenv("STABLE_EMPTY_DURATION_SECONDS", "30"))
    queue_empty_since = None  # Track when queue first became empty
    total_processed = 0
    files_generated_this_batch = 0  # Track NEW files in current batch
    empty_checks = 0
    last_files_generated_count = 0  # Track previous app_state value

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
                # Get files generated count from app_state
                files_generated_this_batch = (
                    app_state.get("total_files_generated", 0)
                    - last_files_generated_count
                )
                logger.info(
                    f"📭 Queue empty. "
                    f"Generated {files_generated_this_batch} NEW markdown files in batch. "
                    f"Waiting {STABLE_EMPTY_DURATION}s to ensure processor burst complete..."
                )

            # Calculate how long queue has been stable/empty
            stable_empty_seconds = (current_time - queue_empty_since).total_seconds()

            # FIXED: Signal site-publisher ONLY if NEW FILES were actually generated
            if (
                stable_empty_seconds >= STABLE_EMPTY_DURATION
                and files_generated_this_batch
                > 0  # ← KEY FIX: Check FILES, not messages
            ):
                logger.info(
                    f"✅ Queue stable for {int(stable_empty_seconds)}s after generating "
                    f"{files_generated_this_batch} NEW markdown files - signaling site-publisher"
                )
                await signal_site_publisher(
                    files_generated_this_batch, output_container
                )
                last_files_generated_count = app_state.get("total_files_generated", 0)
                files_generated_this_batch = 0  # Reset counter after signaling
                queue_empty_since = None  # Reset for next batch
                logger.info(
                    "✅ Site-publisher signaled. Continuing to poll. "
                    "KEDA will scale to 0 after cooldown period."
                )
            elif (
                stable_empty_seconds >= STABLE_EMPTY_DURATION
                and files_generated_this_batch == 0
            ):
                # Queue empty but NO new files generated - don't signal
                logger.info(
                    f"✅ Queue stable for {int(stable_empty_seconds)}s but NO new markdown files generated. "
                    "Skipping site-publisher signal (no work to do)."
                )
                queue_empty_since = None  # Reset to avoid repeated logging

            # Check if we should gracefully terminate (longer than stable period)
            idle_seconds = (current_time - last_activity_time).total_seconds()
            if idle_seconds >= MAX_IDLE_TIME:
                logger.info(
                    f"🛑 Graceful shutdown: No messages for {int(idle_seconds)}s "
                    f"(max: {MAX_IDLE_TIME}s). Processed {total_processed} messages, "
                    f"generated {files_generated_this_batch} files in last batch."
                )
                break  # Exit loop, trigger cleanup and container shutdown

            # Log every 10th empty check to avoid log spam
            if empty_checks % 10 == 1 and empty_checks > 1:
                current_time_str = current_time.strftime("%H:%M:%S")
                logger.info(
                    f"✅ Queue still empty (processed {total_processed} messages total, "
                    f"generated {files_generated_this_batch} files this batch, "
                    f"stable: {int(stable_empty_seconds)}s/{STABLE_EMPTY_DURATION}s, "
                    f"idle: {int(idle_seconds)}s/{MAX_IDLE_TIME}s, last checked @ {current_time_str}). "
                    "Continuing to poll. KEDA will scale to 0 after cooldown period."
                )

            # Wait longer when queue is empty to reduce polling load
            await asyncio.sleep(10)
        else:
            # Messages processed - reset idle timer and empty queue tracking
            last_activity_time = current_time
            queue_empty_since = None  # Reset: queue no longer empty
            empty_checks = 0
            total_processed += messages_processed

            # Get updated file generation count
            new_files_count = app_state.get("total_files_generated", 0)
            files_in_batch = new_files_count - last_files_generated_count

            logger.info(
                f"📦 Processed {messages_processed} messages, "
                f"generated {files_in_batch} NEW markdown files. "
                "Checking for more..."
            )

            # Brief pause before checking for next batch
            await asyncio.sleep(2)
