"""
FastAPI REST API for site-publisher container.

Provides monitoring, control, and manual                 # Call the publish endpoint logic
                from site_builder import build_and_deploy_site

                result = await build_and_deploy_site(
                    blob_client=blob_service_client,
                    markdown_container="markdown-articles",
                    output_container="web-output",
                    backup_container=settings.backup_container_name,
                    source_blob_path=blob_path,
                ) endpoints.
Pure functional core with thin API layer.
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict

from azure.identity.aio import DefaultAzureCredential
from azure.storage.blob.aio import BlobServiceClient
from error_handling import create_http_error_response, handle_error
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from logging_config import configure_secure_logging
from models import (
    HealthCheckResponse,
    MetricsResponse,
    ProcessingStatus,
    PublishRequest,
    PublishResponse,
)
from site_builder import build_and_deploy_site

from config import get_settings  # type: ignore[attr-defined]
from libs.secure_error_handler import ErrorSeverity

# Configure secure logging
configure_secure_logging()
logger = logging.getLogger(__name__)

# Application metrics (immutable updates only)
app_metrics: Dict[str, Any] = {
    "start_time": datetime.now(timezone.utc),
    "total_builds": 0,
    "successful_builds": 0,
    "failed_builds": 0,
    "last_build_time": None,
    "last_build_duration": None,
}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle with secure initialization."""
    logger.info("Starting site-publisher container")

    try:
        settings = get_settings()

        # Initialize Azure clients with managed identity
        credential = DefaultAzureCredential()
        account_url = (
            f"https://{settings.azure_storage_account_name}.blob.core.windows.net"
        )

        blob_service_client = BlobServiceClient(
            account_url=account_url,
            credential=credential,
        )

        # Store in app state
        app.state.blob_client = blob_service_client
        app.state.settings = settings

        logger.info(
            f"Initialized with storage account: {settings.azure_storage_account_name}"
        )

        # Process queue messages on startup until empty (KEDA scaling pattern)
        import asyncio

        from libs.queue_client import process_queue_messages

        # Message handler for queue polling
        async def message_handler(queue_message, message) -> dict[str, Any]:
            """Process a single site publishing request from the queue."""
            try:
                logger.info(f"Processing queue message {queue_message.message_id}")

                # Call the build and deploy function
                result = await build_and_deploy_site(
                    blob_client=blob_service_client,
                    config=settings,
                )

                if len(result.errors) == 0:
                    app_metrics["successful_builds"] += 1
                    app_metrics["last_build_time"] = datetime.now(
                        timezone.utc
                    ).isoformat()
                    app_metrics["last_build_duration"] = result.duration_seconds
                    logger.info(
                        f"Successfully built site ({result.files_uploaded} files)"
                    )
                    return {
                        "status": "success",
                        "files_uploaded": result.files_uploaded,
                        "duration": result.duration_seconds,
                    }
                else:
                    app_metrics["failed_builds"] += 1
                    logger.warning(f"Build had errors: {result.errors}")
                    return {
                        "status": "error",
                        "errors": result.errors,
                        "files_uploaded": result.files_uploaded,
                    }

            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
                app_metrics["failed_builds"] += 1
                return {"status": "error", "error": str(e)}

        async def startup_queue_processor():
            """Process queue messages continuously, allowing KEDA to manage scaling."""
            logger.info(f"🔍 Checking queue: {settings.queue_name}")

            total_processed = 0
            empty_checks = 0
            while True:
                # Process one message at a time (Hugo builds are resource-intensive)
                messages_processed = await process_queue_messages(
                    queue_name=settings.queue_name,
                    message_handler=message_handler,
                    max_messages=1,
                )

                if messages_processed == 0:
                    empty_checks += 1
                    # Log every 10th empty check to avoid log spam
                    if empty_checks % 10 == 1:
                        if total_processed > 0:
                            logger.info(
                                f"✅ Queue empty after processing {total_processed} messages. "
                                "Continuing to poll. KEDA will scale to 0 after cooldown period."
                            )
                        else:
                            logger.info(
                                "✅ Queue empty on startup. "
                                "Continuing to poll. KEDA will scale to 0 after cooldown period."
                            )
                    # Wait longer when queue is empty to reduce polling load
                    await asyncio.sleep(10)
                else:
                    empty_checks = 0  # Reset counter when message processed
                    total_processed += messages_processed
                    logger.info(
                        f"📦 Processed {messages_processed} messages (total: {total_processed}). "
                        "Checking for more..."
                    )
                    # Brief pause before checking for next message
                    await asyncio.sleep(2)

        # Start the queue processing task
        asyncio.create_task(startup_queue_processor())

        yield

        # Cleanup
        logger.info("Shutting down site-publisher container")
        await blob_service_client.close()
        await credential.close()
        logger.info("Site-publisher shutdown complete")

    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        raise


app = FastAPI(
    lifespan=lifespan,
    title="Site Publisher",
    description="Static site generation with Hugo",
    version="1.0.0",
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler - never expose sensitive data.

    Args:
        request: FastAPI request object
        exc: Exception that was raised

    Returns:
        JSONResponse with sanitized error
    """
    error_response = create_http_error_response(
        status_code=500,
        error=exc,
        error_type="general",
        user_message="An error occurred processing your request",
        context={"path": str(request.url.path)},
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response,
    )


@app.get("/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """
    Health check endpoint.

    Returns:
        HealthCheckResponse with service status
    """
    return HealthCheckResponse(
        status="healthy",
        service="site-publisher",
        version="1.0.0",
        timestamp=datetime.now(timezone.utc),
    )


@app.get("/metrics", response_model=MetricsResponse)
async def get_metrics() -> MetricsResponse:
    """
    Get build metrics.

    Returns:
        MetricsResponse with build statistics
    """
    uptime = (datetime.now(timezone.utc) - app_metrics["start_time"]).total_seconds()

    return MetricsResponse(
        total_builds=app_metrics["total_builds"],
        successful_builds=app_metrics["successful_builds"],
        failed_builds=app_metrics["failed_builds"],
        last_build_time=app_metrics["last_build_time"],
        last_build_duration=app_metrics["last_build_duration"],
        uptime_seconds=uptime,
    )


@app.post("/publish", response_model=PublishResponse)
async def publish_site(request: PublishRequest) -> PublishResponse:
    """
    Manually trigger site publish.

    Security: Input validation via Pydantic model.

    Args:
        request: Publish request parameters

    Returns:
        PublishResponse with build results

    Raises:
        HTTPException: If build fails
    """
    try:
        logger.info("Manual publish triggered")

        # Call pure function
        result = await build_and_deploy_site(
            blob_client=app.state.blob_client, config=app.state.settings
        )

        # Update metrics (immutable style)
        app_metrics["total_builds"] += 1
        if len(result.errors) == 0:
            app_metrics["successful_builds"] += 1
            response_status = ProcessingStatus.COMPLETED
        else:
            app_metrics["failed_builds"] += 1
            response_status = ProcessingStatus.FAILED

        app_metrics["last_build_time"] = datetime.now(timezone.utc)
        app_metrics["last_build_duration"] = result.duration_seconds

        return PublishResponse(
            status=response_status,
            message="Site published" if len(result.errors) == 0 else "Publish failed",
            files_uploaded=result.files_uploaded,
            duration_seconds=result.duration_seconds,
            errors=result.errors,
        )

    except Exception as e:
        # Use shared secure error handler with correlation ID
        error_data = handle_error(
            error=e,
            error_type="general",
            severity=ErrorSeverity.HIGH,
            user_message="Failed to publish site",
            context={"request": request.dict()},
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_data["message"],
        )


@app.get("/status")
async def get_status() -> Dict[str, Any]:
    """
    Get current build status.

    Returns:
        Dict with current status and build count
    """
    return {
        "status": "idle" if app_metrics["total_builds"] == 0 else "ready",
        "last_build": app_metrics["last_build_time"],
        "builds_today": app_metrics["total_builds"],
    }
