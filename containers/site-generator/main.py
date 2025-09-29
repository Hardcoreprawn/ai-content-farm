#!/usr/bin/env python3
"""
Static Site Generator Container

A Python-based JAMStack site generator for AI Content Farm.
Converts processed articles to markdown and generates static HTML sites.

Version: 1.0.4 - Full deployment pipeline test
Pipeline Fix Test: Validating dynamic discovery and versioning
Matrix Test: Full container matrix validation - all containers (Sep 15, 2025)
Security Test: Triggering security pipeline validation (Sep 19, 2025)
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import uvicorn
from diagnostic_endpoints import (
    debug_content_discovery,
    debug_force_process,
    debug_pipeline_test,
)
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from models import GenerationRequest, GenerationResponse, SiteStatus
from site_generator import SiteGenerator
from starlette.exceptions import HTTPException as StarletteHTTPException
from storage_queue_router import router as storage_queue_router
from theme_api import router as theme_router
from theme_security import create_security_headers

# Local imports
from config import Config

# Shared library imports
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

# Add project root to Python path
sys.path.append(str(Path(__file__).parent.parent.parent))


# Import standard models from shared library

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize components
service_metadata = create_service_dependency("site-generator")
config = Config()
_site_generator_instance = None  # Lazy initialization for site_generator


def get_site_generator() -> SiteGenerator:
    """Get or create site generator instance - lazy initialization pattern."""
    global _site_generator_instance
    if _site_generator_instance is None:
        _site_generator_instance = SiteGenerator()
    return _site_generator_instance


# Initialize secure error handler for legacy endpoints
error_handler = SecureErrorHandler("site-generator")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for KEDA-triggered site generation."""
    logger.info("Site Generator starting up...")

    # Load configuration and initialize site generator
    from libs.startup_config import load_service_config

    config = await load_service_config("site-generator")
    logger.info(f"� Loaded configuration: {config}")

    site_generator = get_site_generator()
    await site_generator.initialize(config)
    logger.info("✅ SiteGenerator configuration loaded successfully")

    # Run boot-time diagnostics
    from startup_diagnostics import run_boot_diagnostics

    await run_boot_diagnostics(site_generator)
    logger.info("Site Generator ready for KEDA Storage Queue scaling")

    # Start background queue processing on startup
    from shutdown_handler import (
        handle_startup_auto_shutdown,
        handle_startup_error_shutdown,
    )
    from startup_diagnostics import process_startup_queue_messages

    from libs.queue_client import process_queue_messages

    async def startup_queue_processor():
        try:
            processed_messages = await process_startup_queue_messages(
                storage_queue_router, process_queue_messages
            )
            processed_count = 1 if processed_messages else 0
            await handle_startup_auto_shutdown(processed_count)
        except Exception as e:
            logger.error(f"Startup queue processing failed: {e}")
            await handle_startup_error_shutdown()

    asyncio.create_task(startup_queue_processor())

    try:
        yield
    finally:
        logger.info("Site Generator shutting down...")


# Initialize FastAPI app
app = FastAPI(
    title="AI Content Farm - Site Generator",
    description="Python-based JAMStack static site generator",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Add CORS middleware for security
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://*.azurecontainerapps.io",
        "https://localhost:3000",
    ],  # Restrict to known origins
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # Only needed methods for site generator
    allow_headers=["Content-Type", "Authorization"],
)

# Include routers
app.include_router(storage_queue_router)
app.include_router(theme_router)


# Add comprehensive security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)

    # Add all security headers
    security_headers = create_security_headers()
    for header_name, header_value in security_headers.items():
        response.headers[header_name] = header_value

    # Additional headers
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
    )
    return response


# Define health check functions for shared library


async def check_blob_connectivity():
    """Check blob storage connectivity for health endpoint with timeout."""
    try:
        # Add timeout to prevent 504 Gateway Timeout errors
        # Health checks should be fast - use 5-second timeout to stay well under Azure's limits
        result = await asyncio.wait_for(
            get_site_generator().check_blob_connectivity(), timeout=5.0
        )
        # Extract boolean status from the dict result
        return result.get("status") == "healthy"
    except asyncio.TimeoutError:
        logger.warning("Blob storage health check timed out after 5 seconds")
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

# Service-specific endpoints


@app.post("/generate-markdown", response_model=StandardResponse)
async def generate_markdown(request: GenerationRequest):
    """Generate markdown files from processed content."""
    try:
        logger.info(f"Starting markdown generation from: {request.source}")

        result = await get_site_generator().generate_markdown_batch(
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
                "generator_id": get_site_generator().generator_id,
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


@app.post("/generate-site", response_model=StandardResponse)
async def generate_site(request: GenerationRequest):
    """Generate complete static site from markdown content."""
    try:
        logger.info(f"Starting site generation for theme: {request.theme}")

        result = await get_site_generator().generate_static_site(
            theme=request.theme or "minimal", force_rebuild=request.force_regenerate
        )

        return create_success_response(
            message=f"Generated static site with {result.pages_generated} pages",
            data=result.model_dump(),  # Convert Pydantic model to dict
            metadata={
                "function": "site-generator",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "1.0.0",
                "generator_id": get_site_generator().generator_id,
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


@app.post("/wake-up", response_model=StandardResponse)
async def wake_up():
    """Wake up generator to process new content."""
    try:
        logger.info("Wake-up triggered - checking for new content")

        # Generate markdown from latest processed content
        markdown_result = await get_site_generator().generate_markdown_batch(
            source="auto-wake-up", batch_size=10
        )

        # Generate static site if we have new content
        site_result = None
        if markdown_result.files_generated > 0:
            site_result = await get_site_generator().generate_static_site(
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
                "generator_id": get_site_generator().generator_id,
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


@app.get("/preview/{site_id}", response_model=StandardResponse)
async def preview_site(site_id: str):
    """Get preview URL for generated site."""
    try:
        preview_url = await get_site_generator().get_preview_url(site_id)

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
            user_message=f"Site preview not found for ID: {site_id}",
        )
        raise HTTPException(status_code=404, detail=error_response)


# Diagnostic endpoints for pipeline debugging


@app.get("/debug/content-discovery", response_model=StandardResponse)
async def debug_content_discovery_endpoint():
    """Debug endpoint: Check what content is discovered in each container."""
    generator = get_site_generator()
    await generator.initialize()
    return await debug_content_discovery(generator)


@app.get("/debug/pipeline-test", response_model=StandardResponse)
async def debug_pipeline_test_endpoint():
    """Debug endpoint: Test the complete pipeline with real data."""
    generator = get_site_generator()
    await generator.initialize()
    return await debug_pipeline_test(generator)


@app.post("/debug/force-process", response_model=StandardResponse)
async def debug_force_process_endpoint():
    """Debug endpoint: Force process new content end-to-end."""
    generator = get_site_generator()
    await generator.initialize()
    return await debug_force_process(generator)


# Exception handlers
app.add_exception_handler(
    StarletteHTTPException, create_standard_404_handler("site-generator")
)

if __name__ == "__main__":
    import uvicorn

    # Use environment-specific host binding for security
    host = os.environ.get("HOST", "127.0.0.1")  # Default to localhost
    port = int(os.environ.get("PORT", 8080))

    # Allow 0.0.0.0 binding only in container environment
    if os.environ.get("CONTAINER_ENV") == "true":
        host = "0.0.0.0"

    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
