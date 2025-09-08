#!/usr/bin/env python3
"""
Static Site Generator Container

A Python-based JAMStack site generator for AI Content Farm.
Converts processed articles to markdown and generates static HTML sites.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from models import GenerationRequest, GenerationResponse, SiteStatus
from site_generator import SiteGenerator
from starlette.exceptions import HTTPException as StarletteHTTPException

from config import Config
from libs import SecureErrorHandler
from libs.shared_models import (
    StandardResponse,
    create_service_dependency,
    create_success_response,
)
from libs.standard_endpoints import (
    create_standard_404_handler,
    create_standard_health_endpoint,
    create_standard_root_endpoint,
    create_standard_status_endpoint,
)

# Add the project root to Python path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))


# Import standard models from shared library

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create service metadata dependency
service_metadata = create_service_dependency("site-generator")

# Initialize components
config = Config()
site_generator = SiteGenerator()

# Initialize secure error handler for legacy endpoints
error_handler = SecureErrorHandler("site-generator")

# Initialize FastAPI app
app = FastAPI(
    title="AI Content Farm - Site Generator",
    description="Python-based JAMStack static site generator",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Define health check functions for shared library


async def check_blob_connectivity():
    """Check blob storage connectivity for health endpoint with timeout."""
    try:
        # Add timeout to prevent 504 Gateway Timeout errors
        # Health checks should be fast - if blob storage takes too long,
        # it's better to report unhealthy than timeout the whole health endpoint
        result = await asyncio.wait_for(
            site_generator.check_blob_connectivity(), timeout=10.0
        )
        # Extract boolean status from the dict result
        return result.get("status") == "healthy"
    except asyncio.TimeoutError:
        logger.warning("Blob storage health check timed out after 10 seconds")
        return False
    except Exception as e:
        logger.warning(f"Blob storage health check failed: {e}")
        return False


# Add shared standard endpoints
app.add_api_route(
    "/",
    create_standard_root_endpoint(
        service_name="site-generator",
        description="Python-based JAMStack static site generator",
        version="1.0.0",
        service_metadata_dep=service_metadata,
    ),
)

app.add_api_route(
    "/status",
    create_standard_status_endpoint(
        service_name="site-generator",
        version="1.0.0",
        environment=getattr(config, "ENVIRONMENT", "local"),
        service_metadata_dep=service_metadata,
    ),
)

app.add_api_route(
    "/health",
    create_standard_health_endpoint(
        service_name="site-generator",
        version="1.0.0",
        environment=getattr(config, "ENVIRONMENT", "local"),
        dependency_checks={"blob_storage": check_blob_connectivity},
        service_metadata_dep=service_metadata,
    ),
)

# Standard endpoints are now provided by shared library above

# Legacy endpoints for backward compatibility


@app.get("/api/site-generator/status", response_model=StandardResponse)
async def get_status():
    """Get current generator status and metrics."""
    try:
        status = await site_generator.get_status()

        return create_success_response(
            message="Status retrieved successfully",
            data=status.model_dump(),  # Convert Pydantic model to dict
            metadata={
                "function": "site-generator",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "1.0.0",
                "generator_id": site_generator.generator_id,
            },
        )
    except Exception as e:
        error_response = error_handler.create_http_error_response(
            status_code=500,
            error=e,
            error_type="general",
            user_message="Unable to retrieve service status",
        )
        raise HTTPException(status_code=500, detail=error_response)


@app.post("/api/site-generator/generate-markdown", response_model=StandardResponse)
async def generate_markdown(request: GenerationRequest):
    """Generate markdown files from processed content."""
    try:
        logger.info(f"Starting markdown generation from: {request.source}")

        result = await site_generator.generate_markdown_batch(
            source=request.source,
            batch_size=request.batch_size,
            force_regenerate=request.force_regenerate,
        )

        return create_success_response(
            message=f"Generated {result.files_generated} markdown files",
            data=result.model_dump(),  # Convert Pydantic model to dict
            metadata={
                "function": "site-generator",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "1.0.0",
                "generator_id": site_generator.generator_id,
            },
        )
    except Exception as e:
        error_response = error_handler.create_http_error_response(
            status_code=500,
            error=e,
            error_type="general",
            user_message="Markdown generation failed",
            context={"source": request.source, "batch_size": request.batch_size},
        )
        raise HTTPException(status_code=500, detail=error_response)


@app.post("/api/site-generator/generate-site", response_model=StandardResponse)
async def generate_site(request: GenerationRequest):
    """Generate complete static site from markdown content."""
    try:
        logger.info(f"Starting site generation for theme: {request.theme}")

        result = await site_generator.generate_static_site(
            theme=request.theme or "minimal", force_rebuild=request.force_regenerate
        )

        return create_success_response(
            message=f"Generated static site with {result.pages_generated} pages",
            data=result.model_dump(),  # Convert Pydantic model to dict
            metadata={
                "function": "site-generator",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "1.0.0",
                "generator_id": site_generator.generator_id,
            },
        )
    except Exception as e:
        error_response = error_handler.create_http_error_response(
            status_code=500,
            error=e,
            error_type="general",
            user_message="Site generation failed",
            context={"theme": request.theme, "force_rebuild": request.force_regenerate},
        )
        raise HTTPException(status_code=500, detail=error_response)


@app.post("/api/site-generator/wake-up", response_model=StandardResponse)
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

        return create_success_response(
            message=f"Wake-up complete: {markdown_result.files_generated} markdown files, site {'updated' if site_result else 'unchanged'}",
            data={
                "markdown_result": (
                    markdown_result.model_dump() if markdown_result else None
                ),
                "site_result": site_result.model_dump() if site_result else None,
                "wake_up_time": datetime.now(timezone.utc).isoformat(),
            },
            metadata={
                "function": "site-generator",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "1.0.0",
                "generator_id": site_generator.generator_id,
            },
        )
    except Exception as e:
        error_response = error_handler.create_http_error_response(
            status_code=500,
            error=e,
            error_type="general",
            user_message="Wake-up process failed",
        )
        raise HTTPException(status_code=500, detail=error_response)


@app.get("/api/site-generator/preview/{site_id}", response_model=StandardResponse)
async def preview_site(site_id: str):
    """Get preview URL for generated site."""
    try:
        preview_url = await site_generator.get_preview_url(site_id)

        return create_success_response(
            message="Preview URL retrieved",
            data={
                "site_id": site_id,
                "preview_url": preview_url,
                "expires_at": (datetime.now(timezone.utc)).isoformat(),
            },
            metadata={
                "function": "site-generator",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "1.0.0",
            },
        )
    except Exception as e:
        error_response = error_handler.create_http_error_response(
            status_code=404,
            error=e,
            error_type="not_found",
            user_message="Site preview not available",
            context={"site_id": site_id},
        )
        raise HTTPException(status_code=404, detail=error_response)


# Add standardized error handler using FastAPI's built-in patterns
app.add_exception_handler(
    StarletteHTTPException, create_standard_404_handler("site-generator")
)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False, log_level="info")
