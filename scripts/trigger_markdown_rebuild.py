#!/usr/bin/env python3
"""
Trigger markdown rebuild for recent articles.

Scans processed-content container for JSON articles and queues the latest N
for markdown regeneration. Defaults to 25 articles to avoid rate limiting
on image fetching and focus on quality content.

Usage:
    python trigger_markdown_rebuild.py              # Rebuild latest 25
    python trigger_markdown_rebuild.py --count 50   # Rebuild latest 50
    python trigger_markdown_rebuild.py --help       # Show help
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


async def list_processed_articles(
    blob_service_client: BlobServiceClient, limit: int = 25
) -> list[str]:
    """
    List latest processed articles in processed-content container.

    Args:
        blob_service_client: Connected BlobServiceClient
        limit: Maximum articles to return (default: 25 to avoid rate limiting)

    Returns:
        List of blob names (paths) to processed articles, sorted by recency
    """
    logger.info("📋 Scanning processed-content container...")

    container_client = blob_service_client.get_container_client("processed-content")

    articles = []
    try:
        async for blob in container_client.list_blobs(results_per_page=1000):
            if blob.name.endswith(".json"):
                # Use getattr with fallback for compatibility with different Azure SDK versions
                timestamp = getattr(blob, "creation_time", None) or getattr(
                    blob, "last_modified", None
                )
                articles.append((blob.name, timestamp))
    except Exception as e:
        logger.error(f"Error listing blobs: {e}")
        raise

    # Sort by creation/modification time, newest first
    articles.sort(key=lambda x: x[1], reverse=True)

    # Extract just the names, limited to requested count
    article_names = [name for name, _ in articles[:limit]]

    logger.info(
        f"✅ Found {len(articles)} total articles, queuing {len(article_names)} latest"
    )
    return article_names


async def queue_articles_for_markdown(
    queue_client: QueueClient, article_paths: list[str]
) -> dict[str, int]:
    """
    Queue articles for markdown generation.

    Args:
        queue_client: Connected QueueClient
        article_paths: List of blob paths to process

    Returns:
        Dict with queued count and message IDs
    """
    logger.info(f"📤 Queuing {len(article_paths)} articles for markdown generation...")

    message_content = {
        "operation": "wake_up",
        "content_type": "json",
        "service_name": "markdown-rebuild-trigger",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "files": article_paths,
            "files_count": len(article_paths),
            "force_rebuild": True,
        },
    }

    queued = 0
    try:
        response = await queue_client.send_message(json.dumps(message_content))
        logger.info(f"✅ Message sent to queue (ID: {response.id})")
        queued = 1
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        raise

    return {
        "queued": queued,
        "message_id": response.id,
        "articles_in_batch": len(article_paths),
    }


async def main():
    """Main function."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Trigger markdown rebuild for recent articles",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Rebuild latest 25 articles (default, rate-limit friendly)
  %(prog)s

  # Rebuild latest 50 articles
  %(prog)s --count 50

  # Rebuild only latest 5 (quick test)
  %(prog)s --count 5

  # Show help
  %(prog)s --help
        """,
    )
    parser.add_argument(
        "--count",
        type=int,
        default=25,
        help="Number of latest articles to rebuild (default: 25, rate-limit friendly)",
    )
    args = parser.parse_args()

    try:
        # Get configuration from environment
        storage_account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
        queue_name = os.getenv("MARKDOWN_QUEUE_NAME", "markdown-generation-requests")

        if not storage_account_name:
            logger.error("❌ AZURE_STORAGE_ACCOUNT_NAME environment variable not set")
            sys.exit(1)

        logger.info("📋 Configuration:")
        logger.info(f"   Storage Account: {storage_account_name}")
        logger.info(f"   Queue Name: {queue_name}")
        logger.info(f"   Articles to rebuild: {args.count} (latest)")
        logger.info("")

        # Create credentials
        credential = DefaultAzureCredential()

        # Create blob service client
        blob_service_client = BlobServiceClient(
            account_url=f"https://{storage_account_name}.blob.core.windows.net",
            credential=credential,
        )

        # List latest processed articles
        articles = await list_processed_articles(blob_service_client, limit=args.count)

        if not articles:
            logger.warning("⚠️  No processed articles found")
            return

        # Create queue client
        queue_client = QueueClient(
            account_url=f"https://{storage_account_name}.queue.core.windows.net",
            queue_name=queue_name,
            credential=credential,
        )

        # Queue articles for markdown generation
        result = await queue_articles_for_markdown(queue_client, articles)

        logger.info("")
        logger.info("✨ Markdown rebuild triggered successfully!")
        logger.info(f"   Articles queued: {result['articles_in_batch']}")
        logger.info(f"   Message ID: {result['message_id']}")
        logger.info("")
        logger.info("ℹ️  The markdown-generator will:")
        logger.info("   1. Pick up the message from the queue")
        logger.info("   2. Process each article and generate markdown")
        logger.info("   3. Save markdown to markdown-content container")
        logger.info("   4. Signal site-publisher when complete")
        logger.info("")

        # Cleanup
        await blob_service_client.close()
        await queue_client.close()
        await credential.close()

    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
