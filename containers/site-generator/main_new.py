#!/usr/bin/env python3
"""
Site Generator - Main FastAPI Application

Generates static websites from ranked content stored in Azure blob storage.
Outputs complete HTML sites to blob storage for hosting.
"""

import logging
import uvicorn
import json
import tempfile
import shutil
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

# Import local modules
from config import get_config, validate_environment
from health import HealthChecker
from models import *
from service_logic import SiteProcessor
from libs.blob_storage import BlobStorageClient, BlobContainers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
config = get_config()
health_checker = HealthChecker()
site_processor = SiteProcessor()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    logger.info(f"Starting {config.service_name} v{config.version}")

    # Validate environment
    if not validate_environment():
        raise RuntimeError("Environment validation failed")

    # Initialize blob storage
    try:
        blob_client = BlobStorageClient()
        app.state.blob_client = blob_client
        logger.info("Blob storage client initialized")
    except Exception as e:
        logger.error(f"Failed to initialize blob storage: {e}")
        raise

    # Start background tasks
    await site_processor.start()

    yield

    # Shutdown
    logger.info(f"Shutting down {config.service_name}")
    await site_processor.stop()

# Create FastAPI app
app = FastAPI(
    title=config.service_name,
    description=config.service_description,
    version=config.version,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Internal server error",
            "metadata": {
                "service": config.service_name,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
    )

# Standard endpoints


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": config.service_name,
        "version": config.version,
        "description": config.service_description,
        "status": "running",
        "endpoints": {
            "health": "/health",
            "status": "/status",
            "generate": "/generate",
            "preview": "/preview/{site_id}",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return await health_checker.check_health()


@app.get("/status")
async def get_status():
    """Detailed status endpoint."""
    return await health_checker.get_detailed_status()

# Site generation endpoints


@app.post("/generate")
async def generate_site(
    request: GenerationRequest,
    background_tasks: BackgroundTasks
) -> StandardResponse:
    """Generate static site from ranked content."""
    try:
        # Generate unique site ID
        site_id = f"site_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        # Start generation in background
        background_tasks.add_task(
            site_processor.generate_site,
            site_id=site_id,
            request=request
        )

        return StandardResponse(
            status="accepted",
            message="Site generation started",
            data={
                "site_id": site_id,
                "preview_url": f"/preview/{site_id}",
                "estimated_completion": "2-5 minutes"
            },
            metadata={
                "service": config.service_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request_id": site_id
            }
        )

    except Exception as e:
        logger.error(f"Site generation request failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start site generation: {str(e)}"
        )


@app.get("/generate/status/{site_id}")
async def get_generation_status(site_id: str) -> StandardResponse:
    """Get status of site generation."""
    try:
        status = await site_processor.get_generation_status(site_id)

        return StandardResponse(
            status="success",
            message="Generation status retrieved",
            data=status,
            metadata={
                "service": config.service_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "site_id": site_id
            }
        )

    except Exception as e:
        logger.error(f"Failed to get generation status: {e}")
        raise HTTPException(
            status_code=404,
            detail=f"Site generation status not found: {str(e)}"
        )


@app.get("/preview/{site_id}")
async def preview_site(site_id: str) -> HTMLResponse:
    """Preview generated site."""
    try:
        blob_client = app.state.blob_client

        # Get site HTML from blob storage
        site_html = blob_client.download_text(
            "published-sites",
            f"{site_id}/index.html"
        )

        return HTMLResponse(content=site_html)

    except Exception as e:
        logger.error(f"Failed to preview site {site_id}: {e}")
        raise HTTPException(
            status_code=404,
            detail=f"Site preview not available: {str(e)}"
        )


@app.get("/sites")
async def list_sites() -> StandardResponse:
    """List all generated sites."""
    try:
        blob_client = app.state.blob_client
        sites = await site_processor.list_available_sites()

        return StandardResponse(
            status="success",
            message="Sites retrieved",
            data={"sites": sites},
            metadata={
                "service": config.service_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "count": len(sites)
            }
        )

    except Exception as e:
        logger.error(f"Failed to list sites: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve sites: {str(e)}"
        )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=False
    )
