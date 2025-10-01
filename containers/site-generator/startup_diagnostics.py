"""
Startup diagnostics for pipeline health checking.

Provides boot-time validation of pipeline components and content flow.
Contains both OOP (legacy) and functional diagnostic implementations.
"""

from __future__ import annotations

import asyncio
import datetime
import logging
from typing import Any, Dict

from article_loading import list_processed_articles
from functional_config import validate_storage_connectivity
from storage_verification import verify_storage_containers

from libs import SecureErrorHandler
from libs.simplified_blob_client import SimplifiedBlobClient

logger = logging.getLogger(__name__)
error_handler = SecureErrorHandler("startup-diagnostics")


async def run_boot_diagnostics(site_generator) -> Dict[str, Any]:
    """Run comprehensive boot-time pipeline diagnostics."""
    try:
        logger.info("🔍 Running boot-time pipeline diagnostics...")

        # Test blob connectivity
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


async def process_startup_queue_messages(process_queue_messages_func):
    """Process any existing queue messages on startup (functional approach)."""
    try:
        logger.info("Starting up - checking for pending queue messages...")

        # Import functional message processor
        from storage_queue_router import process_storage_queue_message

        # Process message handler
        async def process_message(queue_message, message) -> Dict[str, Any]:
            """Process a single message on startup."""
            try:
                result = await process_storage_queue_message(queue_message)

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
        from functional_config import QUEUE_NAME

        messages_processed = await process_queue_messages_func(
            queue_name=QUEUE_NAME,
            max_messages=10,
            message_handler=process_message,
        )

        if messages_processed > 0:
            logger.info(f"✅ Processed {messages_processed} startup messages")
            return True
        else:
            logger.info("ℹ️ No pending messages found during startup")
            return False

    except Exception as e:
        logger.error(f"Startup queue processing failed: {e}")
        return False


# Functional diagnostics implementation


async def run_functional_boot_diagnostics(
    generator_context: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Run comprehensive boot-time diagnostics using functional approach.

    Pure function that validates system health during startup.

    Args:
        generator_context: Generator context with config, blob_client, etc.

    Returns:
        Diagnostic results dictionary with status and details
    """
    try:
        config = generator_context["config"]
        blob_client = generator_context["blob_client"]

        diagnostics = {
            "status": "running",
            "started_at": datetime.datetime.utcnow().isoformat(),
            "checks": {},
            "summary": {},
        }

        # 1. Configuration validation
        logger.info("Running configuration validation...")
        config_check = await asyncio.to_thread(_check_configuration, config)
        diagnostics["checks"]["configuration"] = config_check

        # 2. Storage connectivity
        logger.info("Checking storage connectivity...")
        storage_check = await asyncio.to_thread(
            _check_storage_connectivity, blob_client, config
        )
        diagnostics["checks"]["storage"] = storage_check

        # 3. Container accessibility
        logger.info("Verifying container accessibility...")
        container_check = await asyncio.to_thread(
            _check_required_containers, blob_client, config
        )
        diagnostics["checks"]["containers"] = container_check

        # 4. Content discovery
        logger.info("Testing content discovery...")
        content_check = await asyncio.to_thread(
            _check_content_discovery, blob_client, config
        )
        diagnostics["checks"]["content_discovery"] = content_check

        # Calculate overall status
        all_checks_passed = all(
            check.get("status") == "success" for check in diagnostics["checks"].values()
        )

        diagnostics["status"] = "success" if all_checks_passed else "error"
        diagnostics["completed_at"] = datetime.datetime.utcnow().isoformat()
        diagnostics["summary"] = {
            "total_checks": len(diagnostics["checks"]),
            "passed": sum(
                1
                for check in diagnostics["checks"].values()
                if check.get("status") == "success"
            ),
            "failed": sum(
                1
                for check in diagnostics["checks"].values()
                if check.get("status") != "success"
            ),
            "overall_health": "healthy" if all_checks_passed else "degraded",
        }

        if all_checks_passed:
            logger.info("✅ All boot diagnostics passed")
        else:
            logger.warning(
                f"⚠️  Boot diagnostics completed with {diagnostics['summary']['failed']} failures"
            )

        return diagnostics

    except Exception as e:
        logger.error(f"Boot diagnostics failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "completed_at": datetime.datetime.utcnow().isoformat(),
            "checks": {},
            "summary": {
                "total_checks": 0,
                "passed": 0,
                "failed": 1,
                "overall_health": "critical",
            },
        }


# Private diagnostic functions


def _check_configuration(config) -> Dict[str, Any]:
    """
    Validate configuration completeness and correctness.

    Args:
        config: Site generator configuration object

    Returns:
        Configuration check results
    """
    try:
        # Use configuration's built-in validation
        is_valid = config.validate()

        if is_valid:
            return {
                "status": "success",
                "message": "Configuration validation passed",
                "details": {
                    "site_title": config.SITE_TITLE,
                    "environment": config.ENVIRONMENT,
                    "containers_configured": 3,
                    "urls_configured": bool(config.SITE_URL),
                },
            }
        else:
            return {
                "status": "error",
                "message": "Configuration validation failed",
                "details": {"validation_error": "See logs for details"},
            }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Configuration check failed: {e}",
            "details": {"error": str(e)},
        }


def _check_storage_connectivity(blob_client, config) -> Dict[str, Any]:
    """
    Test basic storage connectivity.

    Args:
        blob_client: Initialized blob storage client
        config: Site generator configuration

    Returns:
        Storage connectivity check results
    """
    try:
        # Use functional validation
        is_connected = validate_storage_connectivity(config)

        if is_connected:
            return {
                "status": "success",
                "message": "Storage connectivity verified",
                "details": {
                    "storage_account": config.AZURE_STORAGE_ACCOUNT_URL,
                    "connection_type": "managed_identity",
                },
            }
        else:
            return {
                "status": "error",
                "message": "Storage connectivity failed",
                "details": {"error": "Cannot connect to storage account"},
            }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Storage connectivity check failed: {e}",
            "details": {"error": str(e)},
        }


def _check_required_containers(blob_client, config) -> Dict[str, Any]:
    """
    Verify all required containers exist and are accessible.

    Args:
        blob_client: Initialized blob storage client
        config: Site generator configuration

    Returns:
        Container accessibility check results
    """
    try:
        required_containers = [
            config.PROCESSED_CONTENT_CONTAINER,
            config.MARKDOWN_CONTENT_CONTAINER,
            config.STATIC_SITES_CONTAINER,
        ]

        verification_result = verify_storage_containers(
            blob_client, required_containers
        )

        if verification_result.get("all_accessible"):
            return {
                "status": "success",
                "message": "All required containers accessible",
                "details": {
                    "containers_checked": len(required_containers),
                    "containers_accessible": len(required_containers),
                    "container_names": required_containers,
                },
            }
        else:
            failed_containers = [
                name
                for name, status in verification_result.get("containers", {}).items()
                if not status.get("accessible", False)
            ]

            return {
                "status": "error",
                "message": f"Container accessibility issues: {failed_containers}",
                "details": {
                    "containers_checked": len(required_containers),
                    "failed_containers": failed_containers,
                    "verification_result": verification_result,
                },
            }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Container check failed: {e}",
            "details": {"error": str(e)},
        }


def _check_content_discovery(blob_client, config) -> Dict[str, Any]:
    """
    Test content discovery functionality.

    Args:
        blob_client: Initialized blob storage client
        config: Site generator configuration

    Returns:
        Content discovery check results
    """
    try:
        # Test discovery in processed content container
        articles = list_processed_articles(
            blob_client=blob_client,
            container_name=config.PROCESSED_CONTENT_CONTAINER,
            max_results=5,
        )

        return {
            "status": "success",
            "message": "Content discovery functional",
            "details": {
                "articles_found": len(articles),
                "container": config.PROCESSED_CONTENT_CONTAINER,
                "sample_articles": [art.get("slug", "unknown") for art in articles[:3]],
            },
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Content discovery failed: {e}",
            "details": {"error": str(e)},
        }
