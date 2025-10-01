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
from typing import Any, AsyncGenerator, Callable, Dict, List

import uvicorn

# Functional imports
from content_processing_functions import generate_markdown_batch, generate_static_site
from diagnostic_endpoints import (
    debug_content_discovery,
    debug_force_process,
    debug_pipeline_test,
)
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from functional_config import create_generator_context, load_configuration
from models import GenerationRequest, GenerationResponse, SiteStatus
from starlette.exceptions import HTTPException as StarletteHTTPException
from storage_queue_router import router as storage_queue_router
from theme_api import router as theme_router
from theme_security import create_security_headers

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
_generator_context = None  # Lazy initialization for generator context


def get_generator_context() -> Dict[str, Any]:
    """Get or create generator context - functional approach."""
    global _generator_context
    if _generator_context is None:
        # Create functional generator context
        _generator_context = create_generator_context()
    return _generator_context


# Initialize secure error handler for legacy endpoints
error_handler = SecureErrorHandler("site-generator")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan events."""
    logger.info("Site Generator starting up...")

    # Load configuration and initialize generator context
    from libs.startup_config import load_service_config

    startup_config = await load_service_config("site-generator")
    logger.info(f"� Loaded startup configuration: {startup_config}")

    # Initialize functional generator context
    global _generator_context
    _generator_context = create_generator_context(startup_config)
    logger.info("✅ Generator context initialized successfully")

    # Run boot-time diagnostics
    from startup_diagnostics import run_boot_diagnostics

    context = get_generator_context()
    await run_boot_diagnostics(context)
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
async def add_security_headers(request: Request, call_next: Callable) -> Response:
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


async def check_blob_connectivity() -> bool:
    """
    Check blob storage connectivity for health endpoint with timeout.

    Performs a quick health check of blob storage connectivity with a 5-second
    timeout to ensure health endpoints respond promptly and don't cause gateway timeouts.

    Returns:
        bool: True if blob storage is healthy and accessible, False otherwise

    Examples:
        >>> # In health check endpoint
        >>> is_healthy = await check_blob_connectivity()
        >>> if is_healthy:
        ...     print("Storage is accessible")
        ... else:
        ...     print("Storage connection issues")

        >>> # Timeout handling
        >>> # Function automatically handles timeouts and returns False
        >>> # preventing 504 Gateway Timeout errors in health checks
    """
    try:
        # Add timeout to prevent 504 Gateway Timeout errors
        # Health checks should be fast - use 5-second timeout to stay well under Azure's limits
        from libs.simplified_blob_client import SimplifiedBlobClient

        blob_client = SimplifiedBlobClient()

        # Test connection with timeout - returns dict with status info
        result = await asyncio.wait_for(
            asyncio.to_thread(blob_client.test_connection, 5.0), timeout=5.0
        )

        # Check if connection test was successful (returns "healthy" or "error")
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
        environment="production",  # Use environment from context if needed
        service_metadata_dep=service_metadata,
    ),
)

app.add_api_route(
    "/health",
    create_standard_health_endpoint(
        service_name="site-generator",
        version="1.0.0",
        environment="production",  # Use environment from context if needed
        dependency_checks={"blob_storage": check_blob_connectivity},
        service_metadata_dep=service_metadata,
    ),
)

# Service-specific endpoints


@app.post("/generate-markdown", response_model=StandardResponse)
async def generate_markdown(request: GenerationRequest) -> Dict[str, Any]:
    """Generate markdown files from processed content."""
    try:
        logger.info(f"Starting markdown generation from: {request.source}")

        # Get functional context
        context = get_generator_context()

        result = await generate_markdown_batch(
            source=request.source,
            batch_size=request.batch_size,
            force_regenerate=request.force_regenerate,
            blob_client=context["blob_client"],
            config=context["config_dict"],
            generator_id=context["generator_id"],
        )

        return create_success_response(
            message=f"Generated {result.files_generated} markdown files",
            data=result.model_dump(),  # Convert Pydantic model to dict
            metadata={
                "function": "site-generator",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "1.0.0",
                "generator_id": context["generator_id"],
            },
        ).model_dump()
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
async def generate_site(request: GenerationRequest) -> Dict[str, Any]:
    """Generate complete static site from markdown content."""
    try:
        logger.info(f"Starting site generation for theme: {request.theme}")

        # Get functional context
        context = get_generator_context()

        result = await generate_static_site(
            theme=request.theme or "minimal",
            force_rebuild=request.force_regenerate,
            blob_client=context["blob_client"],
            config=context["config_dict"],
            generator_id=context["generator_id"],
        )

        return create_success_response(
            message=f"Generated static site with {result.pages_generated} pages",
            data=result.model_dump(),  # Convert Pydantic model to dict
            metadata={
                "function": "site-generator",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "1.0.0",
                "generator_id": context["generator_id"],
            },
        ).model_dump()
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
async def wake_up() -> Dict[str, Any]:
    """Wake up generator to process new content."""
    try:
        logger.info("Wake-up triggered - checking for new content")

        # Get functional context
        context = get_generator_context()

        # Generate markdown from latest processed content
        markdown_result = await generate_markdown_batch(
            source="auto-wake-up",
            batch_size=10,
            force_regenerate=False,
            blob_client=context["blob_client"],
            config=context["config_dict"],
            generator_id=context["generator_id"],
        )

        # Generate static site if we have new content
        site_result = None
        if markdown_result.files_generated > 0:
            site_result = await generate_static_site(
                theme="minimal",
                force_rebuild=False,
                blob_client=context["blob_client"],
                config=context["config_dict"],
                generator_id=context["generator_id"],
            )

        return create_success_response(
            message=f"Wake-up complete: {markdown_result.files_generated} markdown files, site {'updated' if site_result else 'unchanged'}",
            data={
                "markdown_files": markdown_result.files_generated,
                "site_updated": site_result is not None,
                "site_pages": site_result.pages_generated if site_result else 0,
            },
            metadata={
                "function": "site-generator",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "1.0.0",
                "generator_id": context["generator_id"],
            },
        ).model_dump()
    except Exception as e:
        error_response = error_handler.create_http_error_response(
            status_code=500,
            error=e,
            error_type="general",
            user_message="Wake-up process failed",
        )
        raise HTTPException(status_code=500, detail=error_response)


@app.get("/preview/{site_id}", response_model=StandardResponse)
async def preview_site(site_id: str) -> Dict[str, Any]:
    """Get preview URL for generated site."""
    try:
        # TODO: Implement functional get_preview_url
        # For now, create a basic preview URL
        context = get_generator_context()
        preview_url = f"https://{context['config'].SITE_DOMAIN}/preview/{site_id}"

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
        ).model_dump()
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
async def debug_content_discovery_endpoint() -> Dict[str, Any]:
    """Debug endpoint: Check what content is discovered in each container."""
    context = get_generator_context()
    result = await debug_content_discovery(context)
    return result.model_dump()


@app.get("/debug/pipeline-test", response_model=StandardResponse)
async def debug_pipeline_test_endpoint() -> Dict[str, Any]:
    """Debug endpoint: Test the complete pipeline with real data."""
    context = get_generator_context()
    result = await debug_pipeline_test(context)
    return result.model_dump()


@app.post("/debug/force-process", response_model=StandardResponse)
async def debug_force_process_endpoint() -> Dict[str, Any]:
    """Debug endpoint: Force process new content end-to-end."""
    context = get_generator_context()
    return await debug_force_process(context)


# Exception handlers
# TODO: Fix type compatibility issue with create_standard_404_handler
# app.add_exception_handler(
#     StarletteHTTPException, create_standard_404_handler("site-generator")
# )

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
