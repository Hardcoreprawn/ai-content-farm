#!/usr/bin/env python3
"""
Service Bus to KEDA+Dapr Migration Helper

Provides compatibility layer and migration utilities for moving from
Service Bus based architecture to KEDA + Dapr work queue system.
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, Optional

from azure.servicebus.aio import ServiceBusClient

from .keda_dapr_integration import KEDAWorkQueueManager, send_work_to_service

logger = logging.getLogger(__name__)


class ServiceBusMigrationHelper:
    """Helper for migrating from Service Bus to KEDA + Dapr"""

    def __init__(self, service_bus_connection_string: str):
        self.service_bus_connection_string = service_bus_connection_string
        self.work_queue = KEDAWorkQueueManager()

    async def migrate_messages_to_work_queue(self, queue_name: str, service_name: str):
        """Migrate existing Service Bus messages to KEDA work queue"""
        migrated = 0
        failed = 0

        try:
            async with ServiceBusClient.from_connection_string(
                self.service_bus_connection_string
            ) as client:
                receiver = client.get_queue_receiver(queue_name)

                async with receiver:
                    # Receive all pending messages
                    messages = await receiver.receive_messages(max_message_count=100)

                    for message in messages:
                        try:
                            # Parse Service Bus message
                            message_body = json.loads(str(message))

                            # Extract operation and payload
                            operation = message_body.get("operation", "process_message")
                            payload = message_body.get("payload", message_body)

                            # Send to work queue
                            work_id = await send_work_to_service(
                                service_name, operation, payload
                            )

                            # Complete Service Bus message
                            await receiver.complete_message(message)
                            migrated += 1

                            logger.info(
                                f"Migrated message {message.message_id} → work item {work_id}"
                            )

                        except Exception as e:
                            logger.exception(
                                f"Failed to migrate message {message.message_id}: {e}"
                            )
                            failed += 1

        except Exception as e:
            logger.exception(f"Migration failed: {e}")

        logger.info(f"Migration complete: {migrated} migrated, {failed} failed")
        return migrated, failed


# Compatibility decorators for existing endpoints
def servicebus_to_keda_migration(service_name: str, operation: str = "process_message"):
    """Decorator to migrate Service Bus endpoints to KEDA work queue"""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Check if we're in migration mode
            if os.getenv("ENABLE_KEDA_MIGRATION", "false").lower() == "true":
                # Extract payload from Service Bus format
                if "message_data" in kwargs:
                    message_data = kwargs["message_data"]
                    payload = message_data.get("payload", message_data)

                    # Send to KEDA work queue instead
                    work_id = await send_work_to_service(
                        service_name, operation, payload
                    )

                    return {
                        "status": "migrated",
                        "message": f"Message migrated to KEDA work queue",
                        "work_item_id": work_id,
                    }

            # Normal Service Bus processing
            return await func(*args, **kwargs)

        return wrapper

    return decorator


# Updated endpoint examples
"""
# BEFORE (Service Bus):
@router.post("/process-servicebus-message")
async def process_servicebus_message(background_tasks: BackgroundTasks):
    client = await get_service_bus_client()
    messages = await client.receive_messages(max_messages=5)
    # Process messages...

# AFTER (KEDA + Dapr):
@router.post("/process-work")
async def process_work_items(background_tasks: BackgroundTasks):
    # KEDA automatically scaled this container because work is available
    work_queue = KEDAWorkQueueManager()

    # Claim and process work items
    for _ in range(5):  # Process batch
        work_item = await work_queue.claim_work_item("content-processor")
        if not work_item:
            break

        # Process the work
        result = await process_content(work_item.payload)
        await work_queue.complete_work_item(work_item.id, success=True)
"""


# Migration checklist function
def create_migration_checklist() -> Dict[str, Any]:
    """Generate migration checklist for Service Bus → KEDA+Dapr"""
    return {
        "infrastructure": {
            "☐ Deploy Cosmos DB for work queue state": False,
            "☐ Configure KEDA custom scalers": False,
            "☐ Update Container Apps with new scaling rules": False,
            "☐ Deploy mTLS certificates": False,
            "☐ Configure Dapr service discovery": False,
        },
        "application": {
            "☐ Replace Service Bus clients with work queue manager": False,
            "☐ Update message sending to use work queue": False,
            "☐ Replace service-to-service HTTP calls with Dapr invocation": False,
            "☐ Update health endpoints for mTLS validation": False,
            "☐ Test KEDA scaling with work queue": False,
        },
        "testing": {
            "☐ Test scale-to-zero behavior": False,
            "☐ Test scale-up when work items added": False,
            "☐ Test direct service communication": False,
            "☐ Test mTLS certificate rotation": False,
            "☐ Validate cost reduction": False,
        },
        "migration": {
            "☐ Run both systems in parallel": False,
            "☐ Migrate existing messages": False,
            "☐ Redirect new work to KEDA system": False,
            "☐ Monitor performance and costs": False,
            "☐ Decommission Service Bus": False,
        },
        "estimated_timeline": "2-3 weeks",
        "estimated_cost_savings": "$40-60/month",
        "complexity_level": "Medium",
    }


if __name__ == "__main__":
    # Print migration checklist
    checklist = create_migration_checklist()
    print(json.dumps(checklist, indent=2))
