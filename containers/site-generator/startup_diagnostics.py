"""
Startup diagnostics for pipeline health checking.

Provides boot-time validation of pipeline components and content flow.
"""

import datetime
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


async def run_boot_diagnostics(site_generator) -> Dict[str, Any]:
    """Run comprehensive boot-time pipeline diagnostics."""
    try:
        logger.info("🔍 Running boot-time pipeline diagnostics...")

        # Test blob connectivity
        from libs.simplified_blob_client import SimplifiedBlobClient

        blob_client = SimplifiedBlobClient()

        # Check processed content
        processed_blobs = await blob_client.list_blobs(
            container="processed-content", prefix="articles/"
        )
        logger.info(
            f"📊 Found {len(processed_blobs)} processed articles in articles/ folder"
        )

        # Check recent content (last 3 days)
        recent_cutoff = (datetime.datetime.now() - datetime.timedelta(days=3)).strftime(
            "%Y%m%d"
        )
        recent_blobs = [
            blob for blob in processed_blobs if recent_cutoff in blob["name"]
        ]
        logger.info(f"📊 Found {len(recent_blobs)} recent articles (last 3 days)")

        # Check markdown content
        markdown_blobs = await blob_client.list_blobs(container="markdown-content")
        logger.info(f"📊 Found {len(markdown_blobs)} existing markdown files")

        # Check if we need to process new content
        pipeline_status = "current"
        if len(recent_blobs) > len(markdown_blobs):
            logger.warning(
                f"⚠️  Pipeline gap detected: {len(recent_blobs)} recent articles but only {len(markdown_blobs)} markdown files"
            )
            logger.info("🔄 This suggests new content needs processing")
            pipeline_status = "gap_detected"
        else:
            logger.info("✅ Pipeline appears current")

        # Test article processing capability
        test_result = "no_content"
        if processed_blobs:
            test_article_name = processed_blobs[0]["name"]
            logger.info(f"🧪 Testing article processing with: {test_article_name}")
            try:
                test_article = await blob_client.download_json(
                    "processed-content", test_article_name
                )
                logger.info(
                    f"✅ Article loading test passed: {test_article.get('title', 'No title')}"
                )
                test_result = "success"
            except Exception as e:
                logger.error(f"❌ Article loading test failed: {e}")
                test_result = f"error: {e}"

        return {
            "processed_articles": len(processed_blobs),
            "recent_articles": len(recent_blobs),
            "markdown_files": len(markdown_blobs),
            "pipeline_status": pipeline_status,
            "test_result": test_result,
            "timestamp": datetime.datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ Boot-time diagnostics failed: {e}")
        logger.warning("⚠️  Proceeding with startup despite diagnostic failure")
        return {"error": str(e), "timestamp": datetime.datetime.now().isoformat()}


async def process_startup_queue_messages(
    storage_queue_router, process_queue_messages_func
):
    """Process any existing queue messages on startup."""
    try:
        logger.info("Starting up - checking for pending queue messages...")

        # Process message handler
        async def process_message(queue_message, message) -> Dict[str, Any]:
            """Process a single message on startup."""
            try:
                result = await storage_queue_router.process_storage_queue_message(
                    queue_message
                )

                if result["status"] == "success":
                    logger.info(
                        f"✅ Processed startup message: {result.get('message', 'No message')}"
                    )
                    return {"status": "success", "data": result}
                else:
                    logger.warning(
                        f"⚠️ Message processing returned non-success: {result}"
                    )
                    return {"status": "warning", "data": result}

            except Exception as e:
                logger.error(f"❌ Failed to process message: {e}")
                return {"status": "error", "error": str(e)}

        # Process queue with our message handler
        results = await process_queue_messages_func(
            queue_name="site-generator-queue",
            max_messages=10,
            message_handler=process_message,
            timeout_seconds=30,
        )

        if results.get("messages_processed", 0) > 0:
            logger.info(
                f"✅ Processed {results['messages_processed']} startup messages"
            )
            return True
        else:
            logger.info("ℹ️ No pending messages found during startup")
            return False

    except Exception as e:
        logger.error(f"Startup queue processing failed: {e}")
        return False
