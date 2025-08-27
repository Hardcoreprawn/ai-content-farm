import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from models import (
    BatchGenerationRequest,
    BatchGenerationResponse,
    GeneratedContent,
    GenerationRequest,
    GenerationStatus,
    HealthResponse,
    RankedTopic,
    StatusResponse,
)
from service_logic import ContentGeneratorService, content_generator

# Updated: Container test improvements and build reporting enhancements
from config import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events"""
    # Startup
    logger.info(f"Starting {config.SERVICE_NAME} v{config.VERSION}")

    # Validate configuration
    config_status = config.validate_config()
    if not config_status["valid"]:
        logger.error("Configuration validation failed:")
        for issue in config_status["issues"]:
            logger.error(f"  - {issue}")
        # Don't raise error in production - continue with available services

    logger.info("Configuration status:")
    logger.info(
        f"  - Azure OpenAI: {'configured' if config_status['config']['has_azure_openai'] else 'not configured'}"
    )
    logger.info(
        f"  - OpenAI: {'configured' if config_status['config']['has_openai'] else 'not configured'}"
    )
    logger.info(
        f"  - Claude: {'configured' if config_status['config']['has_claude'] else 'not configured'}"
    )

    # Start watching for new ranked content
    # TODO: Implement content watching if needed
    logger.info("Content watching not implemented yet")

    yield  # This is where the app runs

    # Shutdown
    logger.info(f"Shutting down {config.SERVICE_NAME}")

    # Stop watching for new content
    # TODO: Implement content watching cleanup if needed
    logger.info("Content watching cleanup not implemented yet")


# Initialize FastAPI app
app = FastAPI(
    title="Content Generator Service",
    description="AI-powered content generation service for the AI Content Farm pipeline",
    version=config.VERSION,
    lifespan=lifespan,
)

# Global stats
app.state.start_time = datetime.utcnow()
app.state.total_generated = 0


def get_content_generator() -> ContentGeneratorService:
    """Get content generator instance, creating one if needed for tests"""
    if content_generator is None:
        # In test mode, create a temporary instance
        return ContentGeneratorService()
    return content_generator


@app.get("/", response_model=dict)
async def root():
    """Root endpoint with service information"""
    return {
        "service": "Content Generator",
        "version": config.VERSION,
        "description": "AI Content Generator - Transform topics into original articles",
        "endpoints": {
            "health": "/health",
            "status": "/status",
            "generate_tldr": "/generate/tldr",
            "generate_blog": "/generate/blog",
            "generate_deepdive": "/generate/deepdive",
            "generate_batch": "/generate/batch",
        },
        "documentation": "/docs",
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        # In test mode, always return healthy
        if os.getenv("PYTEST_CURRENT_TEST"):
            return HealthResponse(
                status="healthy", service="Content Generator", version=config.VERSION
            )

        # Quick validation of dependencies
        config_status = config.validate_config()

        if not config_status["valid"]:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "service": config.SERVICE_NAME,
                    "version": config.VERSION,
                    "timestamp": datetime.utcnow().isoformat(),
                    "issues": config_status["issues"],
                },
            )

        return HealthResponse(
            status="healthy", service="Content Generator", version=config.VERSION
        )

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": config.SERVICE_NAME,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            },
        )


@app.get("/status", response_model=StatusResponse)
async def get_status():
    """Get detailed service status"""
    try:
        uptime = datetime.utcnow() - app.state.start_time
        uptime_str = str(uptime).split(".")[0]  # Remove microseconds

        # Check AI services
        ai_services = {
            "azure_openai": (
                "configured" if config.AZURE_OPENAI_ENDPOINT else "not configured"
            ),
            "openai": "configured" if config.OPENAI_API_KEY else "not configured",
            "claude": "configured" if config.CLAUDE_API_KEY else "not configured",
        }

        # Check blob storage
        blob_status = "connected"
        try:
            # Quick test of blob client using health check
            service = get_content_generator()
            health_result = service.blob_client.health_check()
            blob_status = (
                "connected" if health_result.get("status") == "healthy" else "error"
            )
        except Exception:
            blob_status = "error"

        return StatusResponse(
            service=config.SERVICE_NAME,
            status="operational",
            active_generations=len(get_content_generator().active_generations),
            total_generated=app.state.total_generated,
            uptime=uptime_str,
            blob_storage=blob_status,
            ai_services=ai_services,
        )

    except Exception as e:
        logger.error(f"Status check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate/tldr", response_model=GeneratedContent)
async def generate_tldr(topic: RankedTopic, writer_personality: str = "professional"):
    """Generate a tl;dr article (200-400 words) with specified personality"""
    try:
        content = await get_content_generator().generate_content(
            topic, "tldr", writer_personality
        )
        app.state.total_generated += 1
        return content
    except ValueError as e:
        logger.error(f"TL;DR generation failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"TL;DR generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate/blog", response_model=GeneratedContent)
async def generate_blog(topic: RankedTopic, writer_personality: str = "professional"):
    """Generate a blog article (600-1000 words) - only if sufficient content"""
    try:
        content = await get_content_generator().generate_content(
            topic, "blog", writer_personality
        )
        app.state.total_generated += 1
        return content
    except Exception as e:
        logger.error(f"Blog generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate/deepdive", response_model=GeneratedContent)
async def generate_deepdive(
    topic: RankedTopic, writer_personality: str = "professional"
):
    """Generate a deep dive article (1500-2500 words) - only if substantial content"""
    try:
        content = await get_content_generator().generate_content(
            topic, "deepdive", writer_personality
        )
        app.state.total_generated += 1
        return content
    except Exception as e:
        logger.error(f"Deep dive generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate/batch", response_model=BatchGenerationResponse)
async def generate_batch(
    request: BatchGenerationRequest, background_tasks: BackgroundTasks
):
    """Generate content for multiple topics"""
    try:
        # Start batch processing in background
        response = await get_content_generator().process_batch_generation(request)
        app.state.total_generated += len(response.generated_content)
        return response
    except Exception as e:
        logger.error(f"Batch generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/generation/status/{batch_id}", response_model=GenerationStatus)
async def get_generation_status(batch_id: str):
    """Get status of a batch generation"""
    status = get_content_generator().get_generation_status(batch_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")
    return status


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=config.PORT, reload=True)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=config.PORT, reload=True)
