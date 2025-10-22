"""Storage Queue endpoint for KEDA integration - minimal, clean."""

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from libs.queue_client import QueueMessageModel, get_queue_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/storage-queue", tags=["storage-queue"])


def _sanitize_error_for_response(error: Exception) -> str:
    """Sanitize error message to prevent information disclosure.

    Removes:
    - File paths and URLs
    - Stack trace information
    - Credential/token information

    Returns a generic error message safe for external consumption.

    CodeQL: This is INTENTIONAL - we strip sensitive information from exceptions
    before exposing to external users. All regex patterns are designed to remove
    information leakage (URLs, paths, credentials), not to validate input.

    Security: Error sanitization is a standard best practice for preventing
    information leakage to external API consumers.
    """
    error_msg = str(error)

    # Remove URLs FIRST (before path removal, to avoid matching //)
    # lgtm[py/invalid-string-escape]: Sanitizing output, not validating input
    error_msg = re.sub(r"https?://[^\s]+", "[URL]", error_msg)

    # Remove file paths (anything with /)
    error_msg = re.sub(r"/[^\s]+", "[PATH]", error_msg)

    # Remove Windows paths (anything with \)
    error_msg = re.sub(r"\\[^\s]+", "[PATH]", error_msg)

    # Remove credentials/tokens
    error_msg = re.sub(
        r"(key|token|password|secret|credential)=[^\s&]+",
        r"\1=[REDACTED]",
        error_msg,
        flags=re.IGNORECASE,
    )

    # Limit length to prevent huge error dumps
    if len(error_msg) > 100:
        error_msg = error_msg[:100] + "..."

    # If nothing meaningful remains, use generic message
    if not error_msg or error_msg.isspace():
        return "Internal server error - check logs for details"

    return error_msg


async def process_queue_message(
    msg: QueueMessageModel, proc_queue: Any, blob_client: Any
) -> Dict[str, Any]:
    """Process queue message - pure async function."""
    from collectors.collect import collect_mastodon, collect_reddit
    from pipeline.stream import stream_collection

    logger.info(f"Processing: {msg.operation}")

    try:
        if msg.operation == "wake_up":
            cid = msg.payload.get(
                "collection_id", f"keda_{datetime.now().isoformat()[:19]}"
            )

            async def stream():
                # Collect from Reddit
                async for item in collect_reddit(
                    ["programming", "technology"], delay=2.0, max_items=25
                ):
                    yield item
                # Collect from Mastodon (one instance at a time)
                async for item in collect_mastodon(
                    instance="techhub.social", delay=1.0
                ):
                    yield item

            stats = await stream_collection(
                collector_fn=stream(),
                collection_id=cid,
                collection_blob=f"collections/{cid}.json",
                blob_client=blob_client,
                queue_client=proc_queue,
            )
            return {"status": "success", "collection_id": cid, "stats": stats}

        elif msg.operation == "collect":
            cid = msg.payload.get(
                "collection_id", f"manual_{datetime.now().isoformat()[:19]}"
            )
            subs = msg.payload.get("subreddits", ["programming"])
            instance = msg.payload.get("instance", "techhub.social")

            async def stream():
                # Collect from specified Reddit subreddits
                async for item in collect_reddit(subs, delay=2.0, max_items=25):
                    yield item
                # Collect from specified Mastodon instance
                async for item in collect_mastodon(instance=instance, delay=1.0):
                    yield item

            stats = await stream_collection(
                collector_fn=stream(),
                collection_id=cid,
                collection_blob=f"collections/{cid}.json",
                blob_client=blob_client,
                queue_client=proc_queue,
            )
            return {"status": "success", "collection_id": cid, "stats": stats}

        return {"status": "ignored", "reason": f"Unknown: {msg.operation}"}

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}


@router.get("/health")
async def health() -> Dict[str, Any]:
    """Health check."""
    try:
        async with get_queue_client("content-collection-requests") as c:
            # Just verify we can get the client - no method call needed
            pass
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": "Internal server error - check logs for details"}


@router.post("/process")
async def process_messages(max_messages: int = 10) -> Dict[str, Any]:
    """Process queue messages - KEDA calls this."""
    import uuid

    from libs.queue_client import process_queue_messages

    cid = str(uuid.uuid4())[:8]
    start = datetime.now(timezone.utc)

    try:
        async with get_queue_client("content-collection-requests") as q:
            async with get_queue_client("content-processor-requests") as pq:

                async def handler(msg_data: Dict) -> Dict:
                    """Message handler - pure function."""
                    msg = QueueMessageModel(**msg_data)
                    return await process_queue_message(msg, pq, None)

                count = await process_queue_messages(
                    queue_name="content-collection-requests",
                    message_handler=handler,
                    max_messages=max_messages,
                )

        return {
            "status": "success",
            "message": f"Processed {count} messages",
            "processed": count,
            "timestamp": start.isoformat(),
        }
    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        # Sanitize error message to prevent information disclosure
        safe_error = _sanitize_error_for_response(e)
        raise HTTPException(status_code=500, detail=safe_error)
