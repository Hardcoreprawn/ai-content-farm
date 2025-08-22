import asyncio
import logging
import os
from datetime import datetime, timedelta

# Updated: Container test improvements and build reporting enhancements
from config import config
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
from service_logic import content_generator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Content Generator Service",
    description="AI-powered content generation service for the AI Content Farm pipeline",
    version=config.VERSION,
)

# Global stats
app.state.start_time = datetime.utcnow()
app.state.total_generated = 0


@app.get("/", response_model=dict)
async def root():
    """Root endpoint with service information"""
    return {
        "service": config.SERVICE_NAME,
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
            status="healthy", service=config.SERVICE_NAME, version=config.VERSION
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

        # Check AI service status
        ai_services = {}
        if config.OPENAI_API_KEY:
            ai_services["openai"] = "configured"
        if config.CLAUDE_API_KEY:
            ai_services["claude"] = "configured"

        # Check blob storage
        blob_status = "connected"
        try:
            # Quick test of blob client using health check
            health_result = content_generator.blob_client.health_check()
            blob_status = (
                "connected" if health_result.get("status") == "healthy" else "error"
            )
        except Exception:
            blob_status = "error"

        return StatusResponse(
            service=config.SERVICE_NAME,
            status="operational",
            active_generations=len(content_generator.active_generations),
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
        content = await content_generator.generate_content(
            topic, "tldr", writer_personality
        )
        app.state.total_generated += 1
        return content
    except Exception as e:
        logger.error(f"TL;DR generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate/blog", response_model=GeneratedContent)
async def generate_blog(topic: RankedTopic, writer_personality: str = "professional"):
    """Generate a blog article (600-1000 words) - only if sufficient content"""
    try:
        content = await content_generator.generate_content(
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
        content = await content_generator.generate_content(
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
        response = await content_generator.process_batch(request)
        app.state.total_generated += len(response.generated_content)
        return response
    except Exception as e:
        logger.error(f"Batch generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/generation/status/{batch_id}", response_model=GenerationStatus)
async def get_generation_status(batch_id: str):
    """Get status of a batch generation"""
    status = content_generator.get_generation_status(batch_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")
    return status


@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info(f"Starting {config.SERVICE_NAME} v{config.VERSION}")

    # Validate configuration
    config_status = config.validate_config()
    if not config_status["valid"]:
        logger.error("Configuration validation failed:")
        for issue in config_status["issues"]:
            logger.error(f"  - {issue}")
    else:
        logger.info("Configuration validated successfully")

    # Log configuration
    logger.info(f"Service configuration:")
    logger.info(f"  - Port: {config.PORT}")
    logger.info(f"  - AI Model: {config.DEFAULT_AI_MODEL}")
    logger.info(f"  - Blob Storage: {config_status['config']['blob_storage']}")
    logger.info(
        f"  - OpenAI: {'configured' if config_status['config']['has_openai'] else 'not configured'}"
    )
    logger.info(
        f"  - Claude: {'configured' if config_status['config']['has_claude'] else 'not configured'}"
    )

    # Start watching for new ranked content
    await content_generator.start_watching()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info(f"Shutting down {config.SERVICE_NAME}")

    # Stop watching for new content
    await content_generator.stop_watching()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=config.PORT, reload=True)
