"""Storage Queue endpoint for KEDA integration - minimal, clean."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from libs.queue_client import QueueMessageModel, get_queue_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/storage-queue", tags=["storage-queue"])


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
        return {"status": "unhealthy", "error": str(e)}


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
        logger.error(f"Processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
