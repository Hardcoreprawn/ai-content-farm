"""
Content Womble - Main FastAPI Application

A humble content collection service for gathering and analyzing digital content.
Updated with standardized tests and security improvements.

Version: 1.1.4 - Force rebuild with processor queue fix
Queue Configuration: Environment variable refactor (Oct 9, 2025)
Type Safety: Comprehensive Pylance error fixes
"""

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any, Dict

from endpoints import (
    storage_queue_router,
    trigger_router,
)
from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.exceptions import HTTPException as StarletteHTTPException

# Application Insights monitoring
from libs.monitoring import configure_application_insights
from libs.shared_models import StandardResponse, create_service_dependency

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Application Insights (will gracefully disable if not configured)
configure_application_insights(service_name="content-collector")

# Create service metadata dependency
service_metadata = create_service_dependency("content-womble")


async def graceful_shutdown(exit_code: int = 0):
    """Gracefully shutdown the container after a brief delay."""
    logger.info(
        f"🛑 SHUTDOWN: Scheduling graceful shutdown in 2 seconds (exit_code: {exit_code})"
    )
    await asyncio.sleep(2)
    logger.info("✅ SHUTDOWN: Graceful shutdown complete")
    os._exit(exit_code)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with automatic startup collection via KEDA cron."""
    logger.info("🚀 Content Womble starting up...")

    # Check if we should run collection on startup (KEDA cron trigger)
    should_collect = os.getenv("AUTO_COLLECT_ON_STARTUP", "true").lower() == "true"

    if should_collect:
        logger.info("⚡ KEDA cron startup detected - running scheduled collection...")
        try:
            import json
            from datetime import datetime, timezone
            from pathlib import Path

            from collectors.collect import collect_mastodon
            from pipeline.stream import stream_collection

            from libs.blob_storage import BlobStorageClient
            from libs.queue_client import get_queue_client

            collection_id = f"keda_{datetime.now(timezone.utc).isoformat()[:19]}"
            collection_blob = f"collections/keda/{collection_id}.json"

            # Load collection template from environment variable
            # Defaults to quality-tech.json for Mastodon sources
            # Can be overridden by setting COLLECTION_TEMPLATE environment variable
            template_name = os.getenv("COLLECTION_TEMPLATE", "quality-tech.json")
            logger.info(f"Using collection template: {template_name}")

            # Try multiple path locations for template file
            # Path precedence: local dev → container /app → alternative mounts (devcontainer, CI/CD)
            possible_paths = [
                # Local development: relative to repo root
                (
                    Path(__file__).parent.parent.parent
                    / "collection-templates"
                    / template_name
                ),
                # Container deployment: /app is the working directory in Docker
                Path("/app/collection-templates") / template_name,
                # Alternative container mount: e.g., devcontainer or CI/CD pipeline
                Path("/workspace/collection-templates") / template_name,
            ]

            template_path = None
            for path in possible_paths:
                if path.exists():
                    template_path = path
                    break

            try:
                if template_path:
                    with open(template_path) as f:
                        template = json.load(f)
                    sources = template.get("sources", {}).get("mastodon", [])
                    logger.info(
                        f"Loaded {len(sources)} Mastodon sources from {template_name}"
                    )
                else:
                    raise FileNotFoundError(f"Template not found: {template_name}")
            except FileNotFoundError:
                logger.warning(
                    f"Collection template '{template_name}' not found, using default Mastodon sources"
                )
                sources = [
                    {"instance": "fosstodon.org", "max_items": 25},
                    {"instance": "techhub.social", "max_items": 15},
                ]

            # Initialize clients for collection and deduplication
            blob_client = BlobStorageClient()
            async with get_queue_client("content-processor-requests") as queue_client:
                # Create async generator for Mastodon sources from template
                async def collect_from_template():
                    """Collect from Mastodon instances configured in template."""
                    for source in sources:
                        instance = source.get("instance", "fosstodon.org")
                        max_items = source.get("max_items", 25)
                        delay = source.get("delay", 1.0)
                        logger.info(
                            f"Collecting from {instance} ({max_items} items)..."
                        )
                        async for item in collect_mastodon(
                            instance=instance, delay=delay, max_items=max_items
                        ):
                            yield item

                # Run streaming pipeline with proper blob client for deduplication
                stats = await stream_collection(
                    collector_fn=collect_from_template(),
                    collection_id=collection_id,
                    collection_blob=collection_blob,
                    blob_client=blob_client,
                    queue_client=queue_client,
                )

                logger.info(
                    f"✅ KEDA startup collection complete - Stats: "
                    f"collected={stats.get('collected', 0)}, "
                    f"published={stats.get('published', 0)}, "
                    f"rejected_quality={stats.get('rejected_quality', 0)}, "
                    f"rejected_dedup={stats.get('rejected_dedup', 0)}"
                )
        except Exception as e:
            logger.error(
                f"❌ KEDA startup collection failed: {e}",
                exc_info=True,
            )
            # Don't fail the entire container - continue to serve manual triggers
            logger.info("Continuing to serve manual collection requests...")
    else:
        logger.info(
            "⏭️  AUTO_COLLECT_ON_STARTUP disabled - container ready for manual triggers"
        )

    logger.info("📡 Content Womble HTTP API ready")

    try:
        yield
    finally:
        logger.info("🛑 Content Womble shutting down...")


# Initialize FastAPI app
app = FastAPI(
    title="Content Womble API",
    description="A humble service for collecting and analyzing digital content",
    version="2.0.1",
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
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # Explicit methods
    allow_headers=["Content-Type", "Authorization"],
)


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


# Standard endpoints are now added via shared library above


# Global exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors with standardized format."""
    error_messages = []
    for error in exc.errors():
        field = " -> ".join([str(loc) for loc in error["loc"]])
        message = error["msg"]
        error_type = error["type"]
        error_messages.append(f"{field}: {message} ({error_type})")

    # Create service metadata for the error response
    metadata = await create_service_dependency("content-womble")()

    return JSONResponse(
        status_code=422,
        content=StandardResponse(
            status="error",
            message="Request validation failed",
            data={},
            errors=error_messages,
            metadata=metadata,
        ).model_dump(),
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 errors with standardized format."""
    # Create service metadata for the error response
    metadata = await create_service_dependency("content-womble")()

    # Dynamically extract available endpoints from the FastAPI app
    available_endpoints = []
    for route in app.routes:
        # Check if this is an APIRoute (which has path and methods)
        if isinstance(route, APIRoute):
            # Filter out automatic endpoints like /openapi.json, /docs, /redoc
            if route.path not in ["/openapi.json", "/docs", "/redoc"]:
                for method in route.methods:
                    if method != "HEAD":  # Skip HEAD methods as they're auto-generated
                        available_endpoints.append(f"{method} {route.path}")

    # Sort endpoints for better readability
    available_endpoints.sort()

    return JSONResponse(
        status_code=404,
        content=StandardResponse(
            status="error",
            message="Endpoint not found",
            data={
                "requested_path": str(request.url.path),
                "requested_method": request.method,
                "available_endpoints": available_endpoints,
                "documentation": {
                    "swagger_ui": "/docs",
                    "redoc": "/redoc",
                    "openapi_spec": "/openapi.json",
                },
            },
            errors=["The requested endpoint does not exist"],
            metadata=metadata,
        ).model_dump(),
    )


@app.exception_handler(405)
async def method_not_allowed_handler(request: Request, exc):
    """Handle 405 Method Not Allowed errors with standardized format."""
    # Create service metadata for the error response
    metadata = await create_service_dependency("content-womble")()

    return JSONResponse(
        status_code=405,
        content=StandardResponse(
            status="error",
            message="Method not allowed",
            data={
                "requested_method": request.method,
                "requested_path": str(request.url.path),
            },
            errors=[f"Method {request.method} not allowed for this endpoint"],
            metadata=metadata,
        ).model_dump(),
    )


# API Routes
# Root, health, and status endpoints are provided by shared library above

# Include routers - Streaming architecture
# Manual trigger endpoint for ad-hoc collection testing
app.include_router(trigger_router)
# Storage Queue endpoints for KEDA cron integration
app.include_router(storage_queue_router)


if __name__ == "__main__":
    import os

    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
# Version bump: Trigger rebuild with latest code (Oct 19, 2025)
