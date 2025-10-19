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
    collections_router,
    diagnostics_router,
    discoveries_router,
    reprocess_router,
    sources_router,
    storage_queue_router,
    templates_router,
)
from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from models import CollectionRequest, DiscoveryRequest, SourceConfig
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
    """Application lifespan manager with KEDA cron auto-collection."""
    logger.info("Content Womble starting up...")

    # Check if this startup was triggered by KEDA cron scaling
    if os.getenv("KEDA_CRON_TRIGGER", "false").lower() == "true":
        logger.info("Detected KEDA cron trigger - running scheduled collection")
        try:
            from endpoints.collections import run_scheduled_collection

            metadata = {
                "timestamp": time.time(),
                "function": "content-womble",
                "version": "1.0.0",
            }
            result = await run_scheduled_collection(metadata)
            logger.info(f"Scheduled collection completed: {result.message}")

            # Check if auto-shutdown is disabled (for development/testing)
            disable_auto_shutdown = (
                os.getenv("DISABLE_AUTO_SHUTDOWN", "false").lower() == "true"
            )

            if disable_auto_shutdown:
                logger.info(
                    "Scheduled collection completed - container will remain active (DISABLE_AUTO_SHUTDOWN=true)"
                )
            else:
                logger.info(
                    "Scheduled collection completed - scheduling graceful shutdown"
                )
                # Schedule graceful shutdown after collection
                asyncio.create_task(graceful_shutdown())

        except Exception as e:
            logger.error(f"Failed to run scheduled collection: {str(e)}")
            disable_auto_shutdown = (
                os.getenv("DISABLE_AUTO_SHUTDOWN", "false").lower() == "true"
            )
            if disable_auto_shutdown:
                logger.warning(
                    "Collection error occurred but container will remain active (DISABLE_AUTO_SHUTDOWN=true)"
                )
            else:
                # Schedule shutdown with error
                asyncio.create_task(graceful_shutdown(exit_code=1))

    # KEDA cron scaling handles scheduling - no background polling needed
    logger.info("Content Womble startup complete - ready for KEDA cron triggers")

    try:
        yield
    finally:
        logger.info("Content Womble shutting down...")


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

# Include routers with proper REST endpoints
app.include_router(
    diagnostics_router
)  # Includes /, /health, /status, /reddit/diagnostics
app.include_router(collections_router)  # /collections endpoints
app.include_router(discoveries_router)  # /discoveries endpoints
app.include_router(sources_router)  # /sources endpoints
app.include_router(templates_router)  # /templates endpoints
app.include_router(reprocess_router)  # /reprocess endpoints
# Storage Queue endpoints for KEDA integration
app.include_router(storage_queue_router)


if __name__ == "__main__":
    import os

    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
# Version bump: Trigger rebuild with latest code (Oct 19, 2025)
