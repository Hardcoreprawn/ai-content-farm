#!/usr/bin/env python3
"""
Example: Content Collector with KEDA + Dapr Integration

Shows how to replace Service Bus polling with KEDA work queue processing
while maintaining scale-to-zero capabilities.
"""

import asyncio
import logging
from typing import Any, Dict, List

from fastapi import APIRouter, BackgroundTasks, Depends

from ..libs.keda_dapr_integration import (
    DaprServiceCaller,
    KEDAWorkQueueManager,
    call_service_direct,
    send_work_to_service,
)
from ..libs.standard_endpoints import service_metadata

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/keda", tags=["KEDA Work Queue"])

# Initialize KEDA + Dapr components
work_queue = KEDAWorkQueueManager()
service_caller = DaprServiceCaller()


@router.post("/process-work")
async def process_work_items(
    background_tasks: BackgroundTasks, metadata=Depends(service_metadata)
) -> Dict[str, Any]:
    """
    Process work items from KEDA work queue.

    This endpoint is called when KEDA scales up the container because
    work items are pending in the Cosmos DB work queue.

    Replaces: /process-servicebus-message
    """

    async def process_work_batch():
        """Process a batch of work items"""
        processed = 0
        failed = 0

        # Process up to 10 work items per scaling event
        for _ in range(10):
            work_item = await work_queue.claim_work_item("content-collector")
            if not work_item:
                break  # No more work available

            try:
                logger.info(f"Processing work item: {work_item.id}")

                # Process based on operation type
                if work_item.operation == "collect_content":
                    result = await collect_content_from_sources(work_item.payload)
                elif work_item.operation == "process_reddit":
                    result = await process_reddit_content(work_item.payload)
                else:
                    raise ValueError(f"Unknown operation: {work_item.operation}")

                # Mark work item as completed
                await work_queue.complete_work_item(work_item.id, success=True)
                processed += 1

                # Send results to next service via Dapr (replaces Service Bus)
                if result.get("collected_items"):
                    await send_work_to_service(
                        "content-processor",
                        "process_content",
                        {
                            "items": result["collected_items"],
                            "source_metadata": result.get("metadata", {}),
                        },
                    )

            except Exception as e:
                logger.exception(f"Work item {work_item.id} failed: {e}")
                await work_queue.complete_work_item(work_item.id, success=False)
                failed += 1

        logger.info(f"Work batch complete: {processed} processed, {failed} failed")
        return {"processed": processed, "failed": failed}

    # Start processing in background
    background_tasks.add_task(process_work_batch)

    return {
        "status": "processing",
        "message": "Started processing work items",
        "service": "content-collector",
        "metadata": metadata,
    }


@router.post("/collect-content")
async def trigger_content_collection(
    sources: List[Dict[str, Any]], metadata=Depends(service_metadata)
) -> Dict[str, Any]:
    """
    Trigger content collection by adding work to KEDA queue.

    This replaces Logic App → Service Bus message sending.
    Instead, external systems can call this endpoint directly.
    """

    work_items_created = []

    for source in sources:
        # Create work item for each source
        work_id = await send_work_to_service(
            "content-collector",
            "collect_content",
            {"source": source, "save_to_storage": True, "deduplicate": True},
        )
        work_items_created.append(work_id)

    return {
        "status": "success",
        "message": f"Created {len(work_items_created)} work items",
        "work_item_ids": work_items_created,
        "metadata": metadata,
    }


@router.get("/work-status")
async def get_work_status(metadata=Depends(service_metadata)) -> Dict[str, Any]:
    """Get current work queue status for this service"""

    pending_items = await work_queue.get_pending_work_items("content-collector")

    return {
        "service": "content-collector",
        "pending_work_items": len(pending_items),
        "items": [
            {
                "id": item.id,
                "operation": item.operation,
                "created_at": item.created_at.isoformat(),
                "retry_count": item.retry_count,
            }
            for item in pending_items[:10]  # Show first 10
        ],
        "metadata": metadata,
    }


@router.post("/send-to-processor")
async def send_to_content_processor(
    content_data: Dict[str, Any], metadata=Depends(service_metadata)
) -> Dict[str, Any]:
    """
    Send content directly to processor via Dapr.

    This demonstrates direct service-to-service communication
    replacing Service Bus message routing.
    """

    try:
        # Direct service call via Dapr (with automatic mTLS)
        result = await call_service_direct(
            "content-processor", "process-content-batch", content_data
        )

        return {
            "status": "success",
            "message": "Content sent to processor",
            "processor_response": result,
            "metadata": metadata,
        }

    except Exception as e:
        logger.exception("Failed to send to processor")
        return {
            "status": "error",
            "message": f"Failed to send to processor: {str(e)}",
            "metadata": metadata,
        }


async def collect_content_from_sources(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Example content collection logic.

    This would contain your actual Reddit API calls, etc.
    """
    source = payload.get("source", {})

    # Simulate content collection
    await asyncio.sleep(1)  # Simulate API call

    collected_items = [
        {
            "id": f"item_{i}",
            "title": f"Sample Title {i}",
            "content": f"Sample content from {source.get('type', 'unknown')}",
            "source": source,
        }
        for i in range(3)  # Simulate collecting 3 items
    ]

    return {
        "collected_items": collected_items,
        "metadata": {
            "source_type": source.get("type"),
            "collection_time": "2025-09-12T10:00:00Z",
            "items_collected": len(collected_items),
        },
    }


async def process_reddit_content(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Example Reddit-specific processing"""

    # Your existing Reddit processing logic here
    await asyncio.sleep(0.5)  # Simulate processing

    return {
        "collected_items": [
            {
                "id": "reddit_item_1",
                "title": "Sample Reddit Post",
                "content": "Sample Reddit content",
                "source": {"type": "reddit", "subreddit": "technology"},
            }
        ]
    }


# Health check integration with mTLS
@router.get("/keda-health")
async def keda_health_check(metadata=Depends(service_metadata)) -> Dict[str, Any]:
    """
    Health check that includes KEDA work queue status.

    This helps monitor the new architecture.
    """

    try:
        # Check work queue connectivity
        pending_items = await work_queue.get_pending_work_items("content-collector")

        # Check Dapr connectivity
        dapr_health = await service_caller.invoke_service(
            "content-collector", "health", None  # Self-call to test Dapr
        )

        return {
            "status": "healthy",
            "keda_work_queue": {"connected": True, "pending_items": len(pending_items)},
            "dapr_service_mesh": {"connected": True, "health_response": dapr_health},
            "service": "content-collector",
            "metadata": metadata,
        }

    except Exception as e:
        logger.exception("KEDA health check failed")
        return {
            "status": "unhealthy",
            "error": str(e),
            "service": "content-collector",
            "metadata": metadata,
        }


"""
DEPLOYMENT COMPARISON:

=== BEFORE (Service Bus) ===
Environment Variables:
- SERVICE_BUS_NAMESPACE
- SERVICE_BUS_QUEUE_NAME
- SERVICE_BUS_CONNECTION_STRING

Scaling:
azure_queue_scale_rule {
  queue_name   = "content-collection-requests"
  queue_length = 1
}

=== AFTER (KEDA + Dapr) ===
Environment Variables:
- DAPR_HTTP_PORT=3500
- KEDA_STATE_STORE=keda-work-queue
- CONTENT_PROCESSOR_SERVICE=content-processor-dapr

Scaling:
custom_scale_rule {
  custom_rule_type = "azure-cosmosdb"
  metadata = {
    query = "SELECT VALUE COUNT(1) FROM c WHERE c.service_name = 'content-collector' AND c.status = 'pending'"
    targetValue = "1"
  }
}

=== BENEFITS ===
✅ Scale-to-zero maintained
✅ 80%+ cost reduction
✅ Direct mTLS communication
✅ Simplified deployment
✅ Better performance
✅ No Service Bus management
"""
