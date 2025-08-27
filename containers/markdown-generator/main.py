"""FastAPI application for markdown generator service."""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from health import HealthChecker
from models import GenerationResult, HealthCheckResponse, MarkdownRequest, ServiceStatus
from service_logic import ContentWatcher, MarkdownGenerator

from config import config
from libs.blob_storage import BlobStorageClient
from libs.shared_models import (
    StandardResponse,
    StandardResponseFactory,
    create_service_dependency,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Service dependency for metadata injection
service_metadata = create_service_dependency("markdown-generator")

# Global service instances
blob_client = None
markdown_generator = None
content_watcher = None
health_checker = None
watcher_task = None


async def start_content_watcher():
    """Start the background content watcher task."""
    global watcher_task

    async def watcher_loop():
        """Background task to watch for new ranked content."""
        while True:
            try:
                result = await content_watcher.check_for_new_ranked_content()
                if result:
                    logger.info(f"Generated markdown: {result}")

                await asyncio.sleep(config.WATCH_INTERVAL)

            except Exception as e:
                logger.error("Content watcher error occurred")
                await asyncio.sleep(30)  # Wait before retrying on error

    watcher_task = asyncio.create_task(watcher_loop())
    logger.info("Content watcher started")


async def stop_content_watcher():
    """Stop the background content watcher task."""
    global watcher_task

    if watcher_task:
        watcher_task.cancel()
        try:
            await watcher_task
        except asyncio.CancelledError:
            pass
        logger.info("Content watcher stopped")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown."""
    global blob_client, markdown_generator, content_watcher, health_checker

    # Startup
    try:
        logger.info(f"Starting {config.SERVICE_NAME} v{config.VERSION}")

        # Validate configuration
        config.validate_required_settings()

        # Initialize blob storage client
        blob_client = BlobStorageClient()

        # Initialize services
        markdown_generator = MarkdownGenerator(blob_client)
        content_watcher = ContentWatcher(blob_client, markdown_generator)
        health_checker = HealthChecker(blob_client)

        # Start content watcher
        await start_content_watcher()

        logger.info("Service startup completed successfully")

    except Exception as e:
        logger.error("Failed to start service")
        raise

    yield

    # Shutdown
    try:
        logger.info("Shutting down service")

        # Stop content watcher
        await stop_content_watcher()

        logger.info("Service shutdown completed")

    except Exception as e:
        logger.error("Error during shutdown")


# Create FastAPI application
app = FastAPI(
    title="Markdown Generator Service",
    description="AI Content Farm markdown generation service",
    version=config.VERSION,
    lifespan=lifespan,
)


@app.get("/", response_model=dict)
async def root():
    """Root endpoint with service information."""
    return {
        "service": config.SERVICE_NAME,
        "version": config.VERSION,
        "status": "running",
        "description": "AI Content Farm markdown generation service",
        "endpoints": {
            "health": "/health",
            "status": "/status",
            "generate": "/generate",
        },
    }


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint."""
    try:
        health_result = await health_checker.check_health()

        # Return appropriate status code based on health
        if health_result["status"] == "healthy":
            return JSONResponse(status_code=200, content=health_result)
        else:
            return JSONResponse(status_code=503, content=health_result)

    except Exception as e:
        logger.error("Health check failed")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "service": config.SERVICE_NAME,
                "error": "Health check failed",
                "blob_storage_healthy": False,
            },
        )


@app.get("/status", response_model=ServiceStatus)
async def get_status():
    """Get detailed service status."""
    try:
        status = await health_checker.get_service_status(content_watcher)
        return status

    except Exception as e:
        logger.error("Failed to get service status")
        raise HTTPException(status_code=500, detail="Failed to get service status")


@app.post("/generate", response_model=GenerationResult)
async def generate_markdown(request: MarkdownRequest):
    """Manually trigger markdown generation from provided content items."""
    try:
        if not request.content_items:
            raise HTTPException(status_code=400, detail="No content items provided")

        # Check if service is initialized
        if markdown_generator is None:
            raise HTTPException(status_code=503, detail="Service not initialized")

        logger.info(
            f"Manual markdown generation requested for {len(request.content_items)} items"
        )

        # Generate markdown
        result = await markdown_generator.generate_markdown_from_ranked_content(
            request.content_items,
            request.template_style or config.MARKDOWN_TEMPLATE_STYLE,
        )

        logger.info(f"Manual generation completed: {result['files_generated']} files")

        return GenerationResult(**result)

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except ValueError as e:
        logger.warning("Invalid request parameters")
        raise HTTPException(status_code=400, detail="Invalid request parameters")
    except Exception as e:
        logger.error("Manual markdown generation failed")
        raise HTTPException(status_code=500, detail="Manual markdown generation failed")


@app.post("/trigger")
async def trigger_check():
    """Manually trigger a check for new ranked content."""
    try:
        result = await content_watcher.check_for_new_ranked_content()

        if result:
            return {
                "status": "success",
                "message": "New content processed and markdown generated",
                "result": result,
            }
        else:
            return {
                "status": "no_new_content",
                "message": "No new ranked content found",
            }

    except Exception as e:
        logger.error("Manual trigger failed")
        raise HTTPException(status_code=500, detail="Manual trigger failed")


@app.get("/watcher/status")
async def get_watcher_status():
    """Get content watcher status."""
    try:
        return content_watcher.get_watcher_status()
    except Exception as e:
        logger.error("Failed to get watcher status")
        raise HTTPException(status_code=500, detail="Failed to get watcher status")


# Standardized API endpoints following FastAPI-native patterns
@app.get(
    "/api/markdown-generator/health",
    response_model=StandardResponse,
    tags=["Standardized API"],
)
async def api_health_check(metadata: dict = Depends(service_metadata)):
    """Standardized health check endpoint with FastAPI-native response model."""
    try:
        # Get health status from the health checker
        health_result = await health_checker.check_health()

        # Create standardized success response
        return StandardResponseFactory.success(
            data=health_result,
            message="Health check completed successfully",
            metadata=metadata,
        )
    except Exception as e:
        logger.error(f"Standardized health check failed: {str(e)}")
        return StandardResponseFactory.error(
            message="Health check failed", errors=[str(e)], metadata=metadata
        )


@app.get(
    "/api/markdown-generator/status",
    response_model=StandardResponse,
    tags=["Standardized API"],
)
async def api_get_status(metadata: dict = Depends(service_metadata)):
    """Standardized service status endpoint with FastAPI-native response model."""
    try:
        # Get detailed service status
        status = await health_checker.get_service_status(content_watcher)

        return StandardResponseFactory.success(
            data=status.model_dump(),
            message="Service status retrieved successfully",
            metadata=metadata,
        )
    except Exception as e:
        logger.error(f"Failed to get standardized service status: {str(e)}")
        return StandardResponseFactory.error(
            message="Failed to get service status", errors=[str(e)], metadata=metadata
        )


@app.post(
    "/api/markdown-generator/process",
    response_model=StandardResponse,
    tags=["Standardized API"],
)
async def api_process_content(
    request: MarkdownRequest, metadata: dict = Depends(service_metadata)
):
    """Standardized content processing endpoint with FastAPI-native response model."""
    try:
        if not request.content_items:
            return StandardResponseFactory.error(
                message="Request validation failed",
                errors=["No content items provided"],
                metadata=metadata,
            )

        # Check if service is initialized
        if markdown_generator is None:
            return StandardResponseFactory.error(
                message="Service not ready",
                errors=["Service not initialized"],
                metadata=metadata,
            )

        logger.info(
            f"Standardized markdown generation requested for {len(request.content_items)} items"
        )

        # Generate markdown
        result = await markdown_generator.generate_markdown_from_ranked_content(
            request.content_items,
            request.template_style or config.MARKDOWN_TEMPLATE_STYLE,
        )

        logger.info(
            f"Standardized generation completed: {result.get('files_generated', 0)} files"
        )

        return StandardResponseFactory.success(
            data=result,
            message=f"Markdown generation completed successfully. Generated {result.get('files_generated', 0)} files",
            metadata=metadata,
        )

    except ValueError as e:
        logger.warning(f"Invalid request parameters in standardized endpoint: {str(e)}")
        return StandardResponseFactory.error(
            message="Invalid request parameters", errors=[str(e)], metadata=metadata
        )
    except Exception as e:
        logger.error(f"Standardized markdown generation failed: {str(e)}")
        return StandardResponseFactory.error(
            message="Markdown generation failed", errors=[str(e)], metadata=metadata
        )


@app.get(
    "/api/markdown-generator/docs",
    response_model=StandardResponse,
    tags=["Standardized API"],
)
async def api_documentation(metadata: dict = Depends(service_metadata)):
    """Standardized API documentation endpoint with FastAPI-native response model."""
    docs_data = {
        "service": "markdown-generator",
        "description": "AI Content Farm markdown generation service with automated content watching",
        "version": config.VERSION,
        "endpoints": {
            "standardized": {
                "/api/markdown-generator/health": "FastAPI-native health check with standardized response format",
                "/api/markdown-generator/status": "Detailed service status with standardized response format",
                "/api/markdown-generator/process": "Process content items into markdown with standardized response format",
                "/api/markdown-generator/docs": "This documentation endpoint with standardized response format",
            },
            "legacy": {
                "/": "Root endpoint with service information",
                "/health": "Legacy health check endpoint",
                "/status": "Legacy service status endpoint",
                "/generate": "Manual markdown generation endpoint",
                "/trigger": "Manual content watch trigger",
                "/watcher/status": "Content watcher status",
            },
        },
        "features": [
            "Automated content watching and processing",
            "Manual markdown generation from ranked content",
            "Multiple template style support",
            "Blob storage integration",
            "Real-time health monitoring",
        ],
        "schemas": {
            "MarkdownRequest": "Input format for processing content items",
            "GenerationResult": "Output format for generation results",
            "StandardResponse": "Standardized response wrapper for all API endpoints",
        },
    }

    return StandardResponseFactory.success(
        data=docs_data,
        message="API documentation retrieved successfully",
        metadata=metadata,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=config.PORT, log_level="info")
