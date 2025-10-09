"""
FastAPI application for markdown-generator container.

This module provides HTTP endpoints for markdown generation and monitoring.

Version: 1.0.4 - Force rebuild with processor queue fix
Queue Configuration: Watching markdown-generation-requests (Oct 9, 2025)
Architecture: Per-message KEDA scaling from processor
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, Union

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from fastapi import FastAPI, HTTPException, status
from markdown_processor import MarkdownProcessor
from models import (
    HealthCheckResponse,
    MarkdownGenerationBatchRequest,
    MarkdownGenerationRequest,
    MarkdownGenerationResponse,
    MarkdownGenerationResult,
    MetricsResponse,
    ProcessingStatus,
)

from config import configure_logging, get_settings

# Initialize logging
configure_logging()
logger = logging.getLogger(__name__)

# Application state
app_state: Dict[str, Any] = {
    "start_time": datetime.utcnow(),
    "total_processed": 0,
    "total_failed": 0,
    "processing_times": [],
    "last_processed": None,
}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle."""
    logger.info("Starting markdown-generator container")

    # Initialize Azure clients
    settings = get_settings()

    try:
        credential = DefaultAzureCredential()
        blob_service_client = BlobServiceClient(
            account_url=f"https://{settings.storage_account_name}"
            f".blob.core.windows.net",
            credential=credential,
        )

        # Store in app state
        app.state.blob_service_client = blob_service_client
        app.state.settings = settings
        app.state.processor = MarkdownProcessor(blob_service_client, settings)

        logger.info("Azure clients initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize Azure clients: {e}")
        raise

    yield

    # Cleanup
    logger.info("Shutting down markdown-generator container")


# Create FastAPI app
app = FastAPI(
    title="Markdown Generator",
    description="Converts processed JSON articles to markdown format",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """
    Health check endpoint.

    Returns:
        HealthCheckResponse: Current health status
    """
    try:
        # Test storage connection
        storage_healthy = False
        try:
            app.state.blob_service_client.get_account_information()
            storage_healthy = True
        except Exception as e:
            logger.error(f"Storage health check failed: {e}")

        # Queue connection check (simplified)
        queue_healthy = storage_healthy  # Same credential

        return HealthCheckResponse(
            status="healthy" if storage_healthy else "unhealthy",
            timestamp=datetime.utcnow(),
            version="1.0.0",
            storage_connection=storage_healthy,
            queue_connection=queue_healthy,
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Health check failed: {str(e)}",
        )


@app.get("/api/markdown/status", response_model=MetricsResponse)
async def get_status() -> MetricsResponse:
    """
    Get processing metrics and statistics.

    Returns:
        MetricsResponse: Current metrics
    """
    uptime = (datetime.utcnow() - app_state["start_time"]).total_seconds()

    avg_time = 0.0
    if app_state["processing_times"]:
        avg_time = sum(app_state["processing_times"]) / len(
            app_state["processing_times"]
        )

    return MetricsResponse(
        total_processed=app_state["total_processed"],
        total_failed=app_state["total_failed"],
        average_processing_time_ms=avg_time,
        uptime_seconds=uptime,
        last_processed=app_state["last_processed"],
    )


@app.post("/api/markdown/generate", response_model=MarkdownGenerationResponse)
async def generate_markdown(
    request: MarkdownGenerationRequest,
) -> MarkdownGenerationResponse:
    """
    Generate markdown from a single JSON article.

    Args:
        request: Generation request parameters

    Returns:
        MarkdownGenerationResponse: Generation result
    """
    try:
        processor: MarkdownProcessor = app.state.processor

        result = await asyncio.to_thread(
            processor.process_article,
            request.blob_name,
            request.overwrite,
            request.template_name,
        )

        # Update metrics
        if result.status == ProcessingStatus.COMPLETED:
            app_state["total_processed"] += 1
            if result.processing_time_ms:
                app_state["processing_times"].append(result.processing_time_ms)
                # Keep only last 100 times
                if len(app_state["processing_times"]) > 100:
                    app_state["processing_times"].pop(0)
        else:
            app_state["total_failed"] += 1

        app_state["last_processed"] = datetime.utcnow()

        return MarkdownGenerationResponse(
            status=(
                "success" if result.status == ProcessingStatus.COMPLETED else "error"
            ),
            message=result.error_message or "Markdown generated successfully",
            data={
                "blob_name": result.blob_name,
                "markdown_blob_name": result.markdown_blob_name,
                "processing_time_ms": result.processing_time_ms,
            },
            metadata={
                "timestamp": datetime.utcnow().isoformat(),
                "function": "markdown-generator",
                "version": "1.0.0",
            },
        )

    except Exception as e:
        logger.error(f"Markdown generation failed: {e}", exc_info=True)
        app_state["total_failed"] += 1

        return MarkdownGenerationResponse(
            status="error",
            message=f"Markdown generation failed: {str(e)}",
            data={},
            errors=[str(e)],
            metadata={
                "timestamp": datetime.utcnow().isoformat(),
                "function": "markdown-generator",
                "version": "1.0.0",
            },
        )


@app.get("/api/markdown/templates", response_model=MarkdownGenerationResponse)
async def list_templates() -> MarkdownGenerationResponse:
    """
    List available Jinja2 templates.

    Returns:
        MarkdownGenerationResponse: Available templates
    """
    try:
        processor: MarkdownProcessor = app.state.processor
        templates = processor.jinja_env.list_templates(
            filter_func=lambda x: x.endswith(".md.j2")
        )

        return MarkdownGenerationResponse(
            status="success",
            message=f"Found {len(templates)} available templates",
            data={"templates": sorted(templates)},
            metadata={
                "timestamp": datetime.utcnow().isoformat(),
                "function": "markdown-generator",
                "version": "1.0.0",
            },
        )
    except Exception as e:
        logger.exception("Failed to list templates")
        return MarkdownGenerationResponse(
            status="error",
            message=f"Failed to list templates: {str(e)}",
            data={},
            errors=[str(e)],
            metadata={
                "timestamp": datetime.utcnow().isoformat(),
                "function": "markdown-generator",
                "version": "1.0.0",
            },
        )


@app.post("/api/markdown/batch", response_model=MarkdownGenerationResponse)
async def generate_markdown_batch(
    request: MarkdownGenerationBatchRequest,
) -> MarkdownGenerationResponse:
    """
    Generate markdown from multiple JSON articles.

    Args:
        request: Batch generation request

    Returns:
        MarkdownGenerationResponse: Batch processing results
    """
    try:
        processor: MarkdownProcessor = app.state.processor

        # Process articles concurrently
        tasks = [
            asyncio.to_thread(
                processor.process_article,
                blob_name,
                request.overwrite,
                request.template_name,
            )
            for blob_name in request.blob_names
        ]

        results: list[Union[MarkdownGenerationResult, BaseException]] = (
            await asyncio.gather(*tasks, return_exceptions=True)
        )

        # Aggregate results
        successful: list[str] = []
        failed: list[str] = []

        for result in results:
            if isinstance(result, BaseException):
                # Handle exceptions (includes Exception and other BaseException)
                failed.append(str(result))
                app_state["total_failed"] += 1
            else:
                # Type narrowed: result is MarkdownGenerationResult
                if result.status == ProcessingStatus.COMPLETED:
                    if result.markdown_blob_name:
                        successful.append(result.markdown_blob_name)
                    app_state["total_processed"] += 1
                    if result.processing_time_ms:
                        app_state["processing_times"].append(result.processing_time_ms)
                else:
                    failed.append(result.error_message or "Unknown error")
                    app_state["total_failed"] += 1

        app_state["last_processed"] = datetime.utcnow()

        return MarkdownGenerationResponse(
            status="success" if len(failed) == 0 else "partial",
            message=f"Processed {len(successful)} articles, " f"{len(failed)} failed",
            data={
                "successful": successful,
                "failed_count": len(failed),
                "total": len(request.blob_names),
            },
            errors=failed[:10],  # Limit error list
            metadata={
                "timestamp": datetime.utcnow().isoformat(),
                "function": "markdown-generator",
                "version": "1.0.0",
            },
        )

    except Exception as e:
        logger.error(f"Batch generation failed: {e}", exc_info=True)

        return MarkdownGenerationResponse(
            status="error",
            message=f"Batch generation failed: {str(e)}",
            data={},
            errors=[str(e)],
            metadata={
                "timestamp": datetime.utcnow().isoformat(),
                "function": "markdown-generator",
                "version": "1.0.0",
            },
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
