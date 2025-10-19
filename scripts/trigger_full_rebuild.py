#!/usr/bin/env python3
"""
Trigger a full site rebuild by:
1. Optionally clearing the $web container
2. Sending a rebuild message to the queue

Usage:
    python trigger_full_rebuild.py              # Just send rebuild message
    python trigger_full_rebuild.py --delete     # Clear $web and send rebuild message
    python trigger_full_rebuild.py --help       # Show help
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone

from azure.identity.aio import DefaultAzureCredential
from azure.storage.blob.aio import BlobServiceClient
from azure.storage.queue.aio import QueueClient

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def clear_web_container(blob_service_client: BlobServiceClient) -> int:
    """
    Clear all blobs from the $web container.

    Args:
        blob_service_client: Connected BlobServiceClient

    Returns:
        Number of blobs deleted
    """
    logger.info("🗑️  Clearing $web container...")

    container_client = blob_service_client.get_container_client("$web")

    blobs_deleted = 0
    try:
        async for blob in container_client.list_blobs():
            await container_client.delete_blob(blob.name)
            blobs_deleted += 1
            if blobs_deleted % 100 == 0:
                logger.info(f"  Deleted {blobs_deleted} blobs...")
    except Exception as e:
        logger.error(f"Error deleting blob: {e}")
        raise

    logger.info(f"✅ Cleared $web container: {blobs_deleted} blobs deleted")
    return blobs_deleted


async def send_rebuild_message(queue_client: QueueClient) -> str:
    """
    Send a rebuild message to the queue.

    Args:
        queue_client: Connected QueueClient

    Returns:
        Message ID
    """
    logger.info("📤 Sending rebuild message to queue...")

    message_content = {
        "message_id": str(datetime.now(timezone.utc).timestamp()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service_name": "rebuild-trigger",
        "operation": "markdown_generated",
        "payload": {
            "operation": "markdown_generated",
            "force_rebuild": True,
            "content_summary": {
                "files_created": 0,
                "files_failed": 0,
                "force_rebuild": True,
            },
        },
    }

    try:
        response = await queue_client.send_message(json.dumps(message_content))
        logger.info(f"✅ Message sent to queue (ID: {response.id})")
        return response.id
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        raise


async def main():
    """Main function."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Trigger a full site rebuild",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Just send rebuild message (Hugo will handle cleanup)
  %(prog)s

  # Clear $web container first, then rebuild (full clean rebuild)
  %(prog)s --delete
        """,
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Clear the $web container before rebuild (optional, Hugo handles cleanup)",
    )
    args = parser.parse_args()

    try:
        # Get configuration from environment
        storage_account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
        queue_name = os.getenv("STORAGE_QUEUE_NAME", "site-publishing-requests")

        if not storage_account_name:
            logger.error("❌ AZURE_STORAGE_ACCOUNT_NAME environment variable not set")
            sys.exit(1)

        logger.info(f"📋 Configuration:")
        logger.info(f"   Storage Account: {storage_account_name}")
        logger.info(f"   Queue Name: {queue_name}")
        logger.info(f"   Clear $web: {args.delete}")
        logger.info("")

        # Create credentials
        credential = DefaultAzureCredential()

        # Create blob service client
        blob_service_client = BlobServiceClient(
            account_url=f"https://{storage_account_name}.blob.core.windows.net",
            credential=credential,
        )

        # Optionally clear the $web container
        blobs_deleted = 0
        if args.delete:
            blobs_deleted = await clear_web_container(blob_service_client)
        else:
            logger.info(
                "⏭️  Skipping $web container deletion (Hugo will handle cleanup)"
            )

        # Create queue client and send rebuild message
        queue_client = QueueClient(
            account_url=f"https://{storage_account_name}.queue.core.windows.net",
            queue_name=queue_name,
            credential=credential,
        )

        message_id = await send_rebuild_message(queue_client)

        logger.info("")
        logger.info("✨ Full rebuild triggered successfully!")
        if args.delete:
            logger.info(f"   Cleared: {blobs_deleted} blobs from $web")
        else:
            logger.info("   Cleared: none (Hugo will clean up automatically)")
        logger.info(f"   Message ID: {message_id}")
        logger.info("")
        logger.info("ℹ️  The site-publisher will:")
        logger.info("   1. Pick up the rebuild message from the queue")
        logger.info("   2. Perform a full Hugo build of all markdown files")
        if not args.delete:
            logger.info("   3. Hugo will clean up stale files during build")
        logger.info(
            "   "
            + ("4" if not args.delete else "3")
            + ". Deploy the built site to $web container"
        )
        logger.info("")

        # Cleanup
        await blob_service_client.close()
        await credential.close()

    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
