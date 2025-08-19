"""FastAPI application for markdown generator service."""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from config import config
from models import (
    MarkdownRequest,
    GenerationResult,
    ServiceStatus,
    HealthCheckResponse
)
from libs.blob_storage import BlobStorageClient
from service_logic import MarkdownGenerator, ContentWatcher
from health import HealthChecker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
                logger.error(f"Content watcher error: {e}")
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
        logger.error(f"Failed to start service: {e}")
        raise

    yield

    # Shutdown
    try:
        logger.info("Shutting down service")

        # Stop content watcher
        await stop_content_watcher()

        logger.info("Service shutdown completed")

    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI application
app = FastAPI(
    title="Markdown Generator Service",
    description="AI Content Farm markdown generation service",
    version=config.VERSION,
    lifespan=lifespan
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
            "generate": "/generate"
        }
    }


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint."""
    try:
        health_result = await health_checker.check_health()

        # Return appropriate status code based on health
        if health_result["status"] == "healthy":
            return JSONResponse(
                status_code=200,
                content=health_result
            )
        else:
            return JSONResponse(
                status_code=503,
                content=health_result
            )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "service": config.SERVICE_NAME,
                "error": str(e),
                "blob_storage_healthy": False
            }
        )


@app.get("/status", response_model=ServiceStatus)
async def get_status():
    """Get detailed service status."""
    try:
        status = await health_checker.get_service_status(content_watcher)
        return status

    except Exception as e:
        logger.error(f"Failed to get service status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate", response_model=GenerationResult)
async def generate_markdown(request: MarkdownRequest):
    """Manually trigger markdown generation from provided content items."""
    try:
        if not request.content_items:
            raise HTTPException(
                status_code=400,
                detail="No content items provided"
            )

        # Check if service is initialized
        if markdown_generator is None:
            raise HTTPException(
                status_code=503,
                detail="Service not initialized"
            )

        logger.info(
            f"Manual markdown generation requested for {len(request.content_items)} items")

        # Generate markdown
        result = await markdown_generator.generate_markdown_from_ranked_content(
            request.content_items,
            request.template_style or config.MARKDOWN_TEMPLATE_STYLE
        )

        logger.info(
            f"Manual generation completed: {result['files_generated']} files")

        return GenerationResult(**result)

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except ValueError as e:
        logger.warning(f"Invalid request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Manual markdown generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/trigger")
async def trigger_check():
    """Manually trigger a check for new ranked content."""
    try:
        result = await content_watcher.check_for_new_ranked_content()

        if result:
            return {
                "status": "success",
                "message": "New content processed and markdown generated",
                "result": result
            }
        else:
            return {
                "status": "no_new_content",
                "message": "No new ranked content found"
            }

    except Exception as e:
        logger.error(f"Manual trigger failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/watcher/status")
async def get_watcher_status():
    """Get content watcher status."""
    try:
        return content_watcher.get_watcher_status()
    except Exception as e:
        logger.error(f"Failed to get watcher status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=config.PORT,
        log_level="info"
    )
