#!/usr/bin/env python3
"""
Test script to send individual processing messages directly to the Service Bus queue.
This bypasses the collector and lets us test the individual processing architecture.
"""

import asyncio
import json
import os
from datetime import datetime, timezone

from azure.identity.aio import DefaultAzureCredential
from azure.servicebus import ServiceBusMessage
from azure.servicebus.aio import ServiceBusClient

# Test item data
TEST_ITEMS = [
    {
        "id": "test_item_1",
        "title": "Test Individual Processing Item 1",
        "content": "This is a test item to validate individual processing architecture.",
        "url": "https://example.com/test1",
        "source": "test_source",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "metadata": {"test": True, "individual_processing": True},
    },
    {
        "id": "test_item_2",
        "title": "Test Individual Processing Item 2",
        "content": "This is another test item to validate individual processing works for multiple items.",
        "url": "https://example.com/test2",
        "source": "test_source",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "metadata": {"test": True, "individual_processing": True},
    },
]


async def send_individual_messages():
    """Send individual test messages to the processing queue."""
    # Get Service Bus connection string from environment
    servicebus_connection_string = os.getenv("AZURE_SERVICEBUS_CONNECTION_STRING")

    if not servicebus_connection_string:
        print("❌ AZURE_SERVICEBUS_CONNECTION_STRING environment variable not set")
        print("   You can get this from the Azure portal or CLI:")
        print(
            "   az servicebus namespace authorization-rule keys list --resource-group ai-content-dev-rg --namespace-name ai-content-dev-servicebus --name RootManageSharedAccessKey --query primaryConnectionString -o tsv"
        )
        return

    queue_name = "content-processing-requests"

    async with ServiceBusClient.from_connection_string(
        servicebus_connection_string
    ) as client:

        sender = client.get_queue_sender(queue_name=queue_name)

        try:
            print(f"🚀 Sending {len(TEST_ITEMS)} individual messages to {queue_name}")

            async with sender:
                for i, item in enumerate(TEST_ITEMS, 1):
                    # Create message content (matching the format expected by processor)
                    message_content = {
                        "item": item,
                        "collection_id": f"test_individual_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
                        "collection_metadata": {
                            "test_mode": True,
                            "individual_processing": True,
                            "created_at": datetime.now(timezone.utc).isoformat(),
                        },
                    }

                    # Create Service Bus message
                    message = ServiceBusMessage(
                        body=json.dumps(message_content),
                        content_type="application/json",
                        subject="individual_item_processing",
                        message_id=f"test_individual_{i}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}",
                    )

                    # Send message
                    await sender.send_messages(message)
                    print(f"   ✅ Sent message {i}: {item['title']}")

            print(
                f"🎉 Successfully sent {len(TEST_ITEMS)} individual processing messages!"
            )
            print(
                "   Check the processor logs to see if they're picked up and processed."
            )

        except Exception as e:
            print(f"❌ Error sending messages: {e}")


async def check_queue_status():
    """Check the current queue status."""
    try:
        # We'll use Azure CLI for this since it's simpler than the Management API
        import subprocess

        result = subprocess.run(
            [
                "az",
                "servicebus",
                "queue",
                "show",
                "--resource-group",
                "ai-content-dev-rg",
                "--namespace-name",
                "ai-content-dev-servicebus",
                "--name",
                "content-processing-requests",
                "--query",
                "{messageCount:countDetails.activeMessageCount, deadLetterCount:countDetails.deadLetterMessageCount}",
                "--output",
                "json",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            queue_info = json.loads(result.stdout)
            print(f"📊 Queue Status:")
            print(f"   Active Messages: {queue_info['messageCount']}")
            print(f"   Dead Letter Messages: {queue_info['deadLetterCount']}")
        else:
            print("❌ Failed to get queue status")

    except Exception as e:
        print(f"❌ Error checking queue status: {e}")


if __name__ == "__main__":
    print("🧪 Individual Processing Message Sender")
    print("=" * 50)

    # First check current queue status
    asyncio.run(check_queue_status())
    print()

    # Send test messages
    asyncio.run(send_individual_messages())
    print()

    # Check queue status after sending
    print("Queue status after sending:")
    asyncio.run(check_queue_status())
