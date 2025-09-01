#!/usr/bin/env python3
"""
Static Site Generator Container

A Python-based JAMStack site generator for AI Content Farm.
Converts processed articles to markdown and generates static HTML sites.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Dict, List

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from models import GenerationRequest, GenerationResponse, SiteStatus
from site_generator import SiteGenerator

from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AI Content Farm - Site Generator",
    description="Python-based JAMStack static site generator",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Initialize components
config = Config()
site_generator = SiteGenerator()


@app.get("/health")
async def health_check():
    """Standard health check endpoint."""
    try:
        # Check blob storage connectivity
        blob_available = await site_generator.check_blob_connectivity()

        return JSONResponse(
            {
                "status": "healthy",
                "service": "site-generator",
                "version": "1.0.0",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "blob_storage_available": blob_available,
                "containers": {
                    "source": config.PROCESSED_CONTENT_CONTAINER,
                    "markdown": config.MARKDOWN_CONTENT_CONTAINER,
                    "static": config.STATIC_SITES_CONTAINER,
                },
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": "Service temporarily unavailable",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )


@app.get("/api/site-generator/health")
async def api_health_check():
    """Standardized API health check."""
    return await health_check()


@app.get("/api/site-generator/status")
async def get_status():
    """Get current generator status and metrics."""
    try:
        status = await site_generator.get_status()

        return JSONResponse(
            {
                "status": "success",
                "message": "Status retrieved successfully",
                "data": status,
                "errors": None,
                "metadata": {
                    "function": "site-generator",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "version": "1.0.0",
                    "generator_id": site_generator.generator_id,
                },
            }
        )
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/site-generator/generate-markdown")
async def generate_markdown(request: GenerationRequest):
    """Generate markdown files from processed content."""
    try:
        logger.info(f"Starting markdown generation for source: {request.source}")

        result = await site_generator.generate_markdown_batch(
            source=request.source,
            batch_size=request.batch_size,
            force_regenerate=request.force_regenerate,
        )

        return JSONResponse(
            {
                "status": "success",
                "message": f"Generated {result.files_generated} markdown files",
                "data": result,
                "errors": None,
                "metadata": {
                    "function": "site-generator",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "version": "1.0.0",
                    "generator_id": site_generator.generator_id,
                },
            }
        )
    except Exception as e:
        logger.error(f"Markdown generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/site-generator/generate-site")
async def generate_site(request: GenerationRequest):
    """Generate complete static site from markdown content."""
    try:
        logger.info(f"Starting site generation for theme: {request.theme}")

        result = await site_generator.generate_static_site(
            theme=request.theme or "minimal", force_rebuild=request.force_regenerate
        )

        return JSONResponse(
            {
                "status": "success",
                "message": f"Generated static site with {result.pages_generated} pages",
                "data": result,
                "errors": None,
                "metadata": {
                    "function": "site-generator",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "version": "1.0.0",
                    "generator_id": site_generator.generator_id,
                },
            }
        )
    except Exception as e:
        logger.error(f"Site generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/site-generator/wake-up")
async def wake_up():
    """Wake up generator to process new content."""
    try:
        logger.info("Wake-up triggered - checking for new content")

        # Generate markdown from latest processed content
        markdown_result = await site_generator.generate_markdown_batch(
            source="auto-wake-up", batch_size=10
        )

        # Generate static site if we have new content
        site_result = None
        if markdown_result.files_generated > 0:
            site_result = await site_generator.generate_static_site(
                theme="minimal", force_rebuild=False
            )

        return JSONResponse(
            {
                "status": "success",
                "message": f"Wake-up complete: {markdown_result.files_generated} markdown files, site {'updated' if site_result else 'unchanged'}",
                "data": {
                    "markdown_result": markdown_result,
                    "site_result": site_result,
                    "wake_up_time": datetime.now(timezone.utc).isoformat(),
                },
                "errors": None,
                "metadata": {
                    "function": "site-generator",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "version": "1.0.0",
                    "generator_id": site_generator.generator_id,
                },
            }
        )
    except Exception as e:
        logger.error(f"Wake-up failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/site-generator/preview/{site_id}")
async def preview_site(site_id: str):
    """Get preview URL for generated site."""
    try:
        preview_url = await site_generator.get_preview_url(site_id)

        return JSONResponse(
            {
                "status": "success",
                "message": "Preview URL retrieved",
                "data": {
                    "site_id": site_id,
                    "preview_url": preview_url,
                    "expires_at": (datetime.now(timezone.utc)).isoformat(),
                },
                "errors": None,
                "metadata": {
                    "function": "site-generator",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "version": "1.0.0",
                },
            }
        )
    except Exception as e:
        logger.error(f"Preview generation failed: {e}")
        raise HTTPException(status_code=404, detail=str(e))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False, log_level="info")
