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
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from models import GenerationRequest, GenerationResponse, SiteStatus
from site_generator import SiteGenerator
from starlette.exceptions import HTTPException as StarletteHTTPException
from storage_queue_router import router as storage_queue_router

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

# Lazy initialization for site_generator to avoid startup failures
_site_generator_instance = None


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
    logger.info("Site Generator ready for KEDA Storage Queue scaling")

    # Start background queue processing on startup
    import asyncio

    from storage_queue_router import storage_queue_router

    from libs.queue_client import process_queue_messages

    async def startup_queue_processor():
        """Process any existing queue messages on startup."""
        try:
            logger.info("Starting up - checking for pending queue messages...")

            # Process message handler
            async def process_message(queue_message, message) -> Dict[str, Any]:
                """Process a single message on startup."""
                try:
                    result = await storage_queue_router.process_storage_queue_message(
                        queue_message
                    )

                    if result["status"] == "success":
                        logger.info(
                            f"Startup: Successfully processed message {queue_message.message_id}"
                        )
                    else:
                        logger.warning(
                            f"Startup: Message processing failed: {result.get('error', 'Unknown error')}"
                        )

                    return result
                except Exception as e:
                    logger.error(f"Startup: Error processing message: {e}")
                    return {"status": "error", "error": str(e)}

            # Process up to 5 messages on startup
            processed_count = await process_queue_messages(
                queue_name="site-generation-requests",
                message_handler=process_message,
                max_messages=5,
            )

            if processed_count > 0:
                logger.info(f"Startup: Processed {processed_count} pending messages")
                logger.info(
                    "Startup: All messages processed - scheduling graceful shutdown"
                )
                # Schedule graceful shutdown after processing
                asyncio.create_task(graceful_shutdown())
            else:
                logger.info(
                    "Startup: No pending messages found - scheduling graceful shutdown"
                )
                # Schedule shutdown if no work to do
                asyncio.create_task(graceful_shutdown())

        except Exception as e:
            logger.error(f"Startup queue processing failed: {e}")
            # Schedule shutdown with error
            asyncio.create_task(graceful_shutdown(exit_code=1))

    async def graceful_shutdown(exit_code: int = 0):
        """Gracefully shutdown the container after a brief delay."""
        await asyncio.sleep(2)  # Brief delay to ensure logs are flushed
        logger.info(f"Gracefully shutting down container with exit code {exit_code}")
        os._exit(exit_code)

    # Start the background task
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

# Include storage queue router for KEDA-triggered processing
app.include_router(storage_queue_router)


# Add security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
    )
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
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


# Exception handlers
app.add_exception_handler(
    StarletteHTTPException, create_standard_404_handler("site-generator")
)

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
