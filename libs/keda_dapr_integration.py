#!/usr/bin/env python3
"""
KEDA + Dapr Work Queue Manager

Replaces Service Bus with direct HTTP + mTLS communication while maintaining
scale-to-zero capabilities through KEDA scaling based on work queue state.

This provides:
- Scale-to-zero when no work items pending
- Event-driven scaling based on queue depth
- Direct mTLS communication between services
- Cost optimization (Cosmos DB much cheaper than Service Bus)
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import aiohttp
from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class WorkItem(BaseModel):
    """Work item for KEDA scaling queue"""

    id: str
    service_name: str  # Target service for processing
    operation: str  # Operation to perform
    payload: Dict[str, Any]
    priority: int = 1
    status: str = "pending"  # pending, processing, completed, failed
    created_at: datetime
    retry_count: int = 0
    max_retries: int = 3


class KEDAWorkQueueManager:
    """Manages work queue for KEDA scaling with Dapr state store"""

    def __init__(
        self, dapr_port: int = 3500, state_store_name: str = "keda-work-queue"
    ):
        self.dapr_port = dapr_port
        self.state_store_name = state_store_name
        self.dapr_url = f"http://localhost:{dapr_port}"

    async def add_work_item(self, work_item: WorkItem) -> bool:
        """Add work item to queue for KEDA scaling"""
        try:
            async with aiohttp.ClientSession() as session:
                # Store work item in Dapr state store
                async with session.post(
                    f"{self.dapr_url}/v1.0/state/{self.state_store_name}",
                    json=[{"key": work_item.id, "value": work_item.dict()}],
                ) as response:
                    if response.status == 204:
                        logger.info(
                            f"Work item {work_item.id} added to queue for {work_item.service_name}"
                        )
                        return True
                    else:
                        logger.error(f"Failed to add work item: {response.status}")
                        return False

        except Exception as e:
            logger.exception(f"Error adding work item: {e}")
            return False

    async def get_pending_work_items(self, service_name: str) -> List[WorkItem]:
        """Get pending work items for a service (used by KEDA for scaling decisions)"""
        try:
            async with aiohttp.ClientSession() as session:
                # Query Dapr state store for pending items
                async with session.post(
                    f"{self.dapr_url}/v1.0/state/{self.state_store_name}/query",
                    json={
                        "filter": {
                            "AND": [
                                {"EQ": {"service_name": service_name}},
                                {"EQ": {"status": "pending"}},
                            ]
                        }
                    },
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return [
                            WorkItem(**item["value"])
                            for item in data.get("results", [])
                        ]
                    else:
                        logger.error(f"Failed to query work items: {response.status}")
                        return []

        except Exception as e:
            logger.exception(f"Error querying work items: {e}")
            return []

    async def claim_work_item(self, service_name: str) -> Optional[WorkItem]:
        """Claim next available work item for processing"""
        try:
            pending_items = await self.get_pending_work_items(service_name)

            if not pending_items:
                return None

            # Get the oldest pending item
            work_item = min(pending_items, key=lambda x: x.created_at)

            # Update status to processing
            work_item.status = "processing"

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.dapr_url}/v1.0/state/{self.state_store_name}",
                    json=[{"key": work_item.id, "value": work_item.dict()}],
                ) as response:
                    if response.status == 204:
                        return work_item
                    else:
                        logger.error(f"Failed to claim work item: {response.status}")
                        return None

        except Exception as e:
            logger.exception(f"Error claiming work item: {e}")
            return None

    async def complete_work_item(self, work_item_id: str, success: bool = True) -> bool:
        """Mark work item as completed or failed"""
        try:
            async with aiohttp.ClientSession() as session:
                # Get current work item
                async with session.get(
                    f"{self.dapr_url}/v1.0/state/{self.state_store_name}/{work_item_id}"
                ) as response:
                    if response.status != 200:
                        logger.error(f"Work item {work_item_id} not found")
                        return False

                    work_item_data = await response.json()
                    work_item = WorkItem(**work_item_data)

                # Update status
                if success:
                    work_item.status = "completed"
                else:
                    work_item.retry_count += 1
                    if work_item.retry_count >= work_item.max_retries:
                        work_item.status = "failed"
                    else:
                        work_item.status = "pending"  # Retry

                # Save updated work item
                async with session.post(
                    f"{self.dapr_url}/v1.0/state/{self.state_store_name}",
                    json=[{"key": work_item.id, "value": work_item.dict()}],
                ) as response:
                    return response.status == 204

        except Exception as e:
            logger.exception(f"Error completing work item: {e}")
            return False


class DaprServiceCaller:
    """Direct service-to-service communication with mTLS via Dapr"""

    def __init__(self, dapr_port: int = 3500):
        self.dapr_port = dapr_port
        self.dapr_url = f"http://localhost:{dapr_port}"

    async def invoke_service(
        self,
        service_name: str,
        method: str,
        data: Optional[Dict] = None,
        http_verb: str = "POST",
    ) -> Dict:
        """Invoke another service via Dapr with automatic mTLS"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.dapr_url}/v1.0/invoke/{service_name}/method/{method}"

                async with session.request(
                    http_verb, url, json=data, timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        raise HTTPException(
                            status_code=response.status,
                            detail=f"Service {service_name} returned {response.status}: {error_text}",
                        )

        except aiohttp.ClientTimeout:
            raise HTTPException(
                status_code=504, detail=f"Timeout calling service {service_name}"
            )
        except Exception as e:
            logger.exception(f"Error calling service {service_name}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to call service {service_name}: {str(e)}",
            )


# FastAPI integration for work queue management
def create_keda_work_queue_router():
    """Create FastAPI router for KEDA work queue management"""
    from fastapi import APIRouter

    router = APIRouter(prefix="/keda", tags=["KEDA Work Queue"])
    work_queue = KEDAWorkQueueManager()
    service_caller = DaprServiceCaller()

    @router.post("/work-items")
    async def add_work_item(work_item: WorkItem) -> Dict[str, Any]:
        """Add work item to KEDA scaling queue"""
        work_item.id = work_item.id or f"{work_item.service_name}-{int(time.time())}"
        work_item.created_at = datetime.now(timezone.utc)

        success = await work_queue.add_work_item(work_item)

        if success:
            return {
                "status": "success",
                "message": f"Work item added for {work_item.service_name}",
                "work_item_id": work_item.id,
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to add work item")

    @router.get("/work-items/{service_name}")
    async def get_pending_work_items(service_name: str) -> Dict[str, Any]:
        """Get pending work items for a service (used by KEDA)"""
        items = await work_queue.get_pending_work_items(service_name)

        return {
            "service_name": service_name,
            "pending_count": len(items),
            "items": [item.dict() for item in items],
        }

    @router.post("/process-work/{service_name}")
    async def process_work_items(
        service_name: str, background_tasks: BackgroundTasks
    ) -> Dict[str, Any]:
        """Process work items for a service (called by scaled container)"""

        async def process_work():
            """Background task to process work items"""
            processed = 0
            failed = 0

            # Process up to 5 items per scaling event
            for _ in range(5):
                work_item = await work_queue.claim_work_item(service_name)
                if not work_item:
                    break

                try:
                    # Call the service to process the work item
                    result = await service_caller.invoke_service(
                        service_name, work_item.operation, work_item.payload
                    )

                    await work_queue.complete_work_item(work_item.id, success=True)
                    processed += 1
                    logger.info(f"Work item {work_item.id} processed successfully")

                except Exception as e:
                    logger.exception(f"Work item {work_item.id} failed: {e}")
                    await work_queue.complete_work_item(work_item.id, success=False)
                    failed += 1

            logger.info(
                f"Work processing complete: {processed} processed, {failed} failed"
            )

        background_tasks.add_task(process_work)

        return {
            "status": "processing",
            "message": f"Started processing work items for {service_name}",
        }

    @router.post("/invoke/{service_name}/{method}")
    async def invoke_service_direct(
        service_name: str, method: str, data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Direct service invocation via Dapr (for synchronous calls)"""
        result = await service_caller.invoke_service(service_name, method, data)
        return result

    return router


# Helper functions for service integration
async def send_work_to_service(
    service_name: str, operation: str, payload: Dict[str, Any], priority: int = 1
) -> str:
    """
    Send work to a service via KEDA work queue

    This replaces Service Bus message sending
    """
    work_queue = KEDAWorkQueueManager()

    work_item = WorkItem(
        id=f"{service_name}-{operation}-{int(time.time())}",
        service_name=service_name,
        operation=operation,
        payload=payload,
        priority=priority,
        created_at=datetime.now(timezone.utc),
    )

    success = await work_queue.add_work_item(work_item)

    if success:
        return work_item.id
    else:
        raise Exception(f"Failed to send work to {service_name}")


async def call_service_direct(
    service_name: str, method: str, data: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Direct synchronous service call via Dapr

    This replaces HTTP calls to service endpoints
    """
    service_caller = DaprServiceCaller()
    return await service_caller.invoke_service(service_name, method, data)


# Configuration for different scaling patterns
KEDA_SCALING_CONFIGS = {
    "content-collector": {
        "min_replicas": 0,
        "max_replicas": 3,
        "scale_trigger_count": 1,  # Scale up when 1+ work items pending
        "operations": ["collect_content", "process_reddit", "process_sources"],
    },
    "content-processor": {
        "min_replicas": 0,
        "max_replicas": 5,
        "scale_trigger_count": 1,
        "operations": ["process_content", "analyze_content", "generate_embeddings"],
    },
    "site-generator": {
        "min_replicas": 0,
        "max_replicas": 2,
        "scale_trigger_count": 1,
        "operations": ["generate_site", "update_content", "publish_changes"],
    },
}


if __name__ == "__main__":
    # Example usage
    import asyncio

    async def test_work_queue():
        # Send work to content collector
        work_id = await send_work_to_service(
            "content-collector",
            "collect_content",
            {
                "sources": [{"type": "reddit", "subreddits": ["technology"]}],
                "save_to_storage": True,
            },
        )
        print(f"Work sent: {work_id}")

        # Direct service call
        result = await call_service_direct("content-processor", "health", None)
        print(f"Service health: {result}")

    asyncio.run(test_work_queue())
