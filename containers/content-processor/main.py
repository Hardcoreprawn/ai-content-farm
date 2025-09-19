#!/usr/bin/env python3
"""Content Processor Service

FastAPI application for AI-powered content processing.
Implements standardized health endpoints and API patterns.

Version: 1.0.2 - Full deployment pipeline test
Pipeline Fix Test: Testing Issue #421 container versioning
Matrix Test: Full container matrix validation (Sep 15, 2025)
"""

import asyncio
import importlib.util
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from dependencies import (
    DEPENDENCY_CHECKS,
    get_configuration,
    service_metadata,
    settings,
)
from endpoints import (
    diagnostics_router,
    processing_router,
    servicebus_router,
    storage_queue_router,
)
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.exceptions import HTTPException as StarletteHTTPException

from libs.background_poller import BackgroundPoller
from libs.shared_models import (
    StandardError,
    StandardResponse,
    create_service_dependency,
)

# Add repository root to Python path for local development - MUST BE FIRST
repo_root = Path(__file__).parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global flag to control background polling
_polling_active = False


async def background_service_bus_poller():
    """
    Background task for continuous Service Bus message polling.

    Implements the KEDA pattern:
    1. Wake up on container start
    2. Check queue for messages
    3. Process messages until queue is empty
    4. Sleep briefly and repeat
    5. KEDA scales down when no messages for extended period
    """
    global _polling_active
    _polling_active = True

    logger.info("Starting background Service Bus polling")

    # Get the Service Bus router instance
    from endpoints.servicebus_router import service_bus_router

    poll_interval = 5  # seconds between polls when queue is empty

    while _polling_active:
        try:
            # Call the internal Service Bus processing endpoint
            logger.debug("Polling Service Bus for messages...")

            # Create fake metadata for internal call
            metadata = await create_service_dependency("content-processor")()

            # Process messages using the existing router
            result = await service_bus_router._process_servicebus_message_impl(metadata)

            if result.status == "success" and result.data:
                messages_processed = result.data.messages_processed
                if messages_processed > 0:
                    logger.info(
                        f"Background polling processed {messages_processed} messages"
                    )
                    # If we processed messages, check again immediately
                    continue
                else:
                    logger.debug("No messages found, sleeping...")

            # Sleep before next poll
            await asyncio.sleep(poll_interval)

        except Exception as e:
            logger.error(f"Error in background Service Bus polling: {e}")
            # Sleep longer on error to avoid spam
            await asyncio.sleep(poll_interval * 2)

    logger.info("Background Service Bus polling stopped")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with background Service Bus polling."""
    logger.info("Starting Content Processor service")
    logger.info(f"Service version: {settings.service_version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Log level: {settings.log_level}")

    # Start background Service Bus polling for KEDA scaling
    from endpoints.servicebus_router import service_bus_router as sb_router

    poller = BackgroundPoller(
        service_bus_router=sb_router,
        poll_interval=5.0,  # Check every 5 seconds when processing
        max_poll_attempts=3,  # Try 3 times before longer sleep
        empty_queue_sleep=30.0,  # Sleep 30s when queue consistently empty
    )

    try:
        await poller.start()
        logger.info("Background Service Bus polling started")

        yield

    finally:
        logger.info("Stopping background Service Bus polling")
        await poller.stop()
        logger.info("Shutting down Content Processor service")


# Initialize FastAPI app
app = FastAPI(
    title="Content Processor API",
    description="AI-powered content processing and enhancement service",
    version=settings.service_version,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://*.azurecontainerapps.io",
        "https://localhost:3000",
    ],  # Restrict to known origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # Explicit methods only
    allow_headers=["*"],
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
    metadata = await create_service_dependency("content-processor")()

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
    metadata = await create_service_dependency("content-processor")()

    # Dynamically extract available endpoints from the FastAPI app
    available_endpoints = []
    for route in app.routes:
        # Check if this is an APIRoute (which has path and methods)
        if isinstance(route, APIRoute):
            # Filter out automatic endpoints like /openapi.json, /docs, /redoc
            # Also filter out internal endpoints for security (OWASP compliance)
            if route.path not in [
                "/openapi.json",
                "/docs",
                "/redoc",
            ] and not route.path.startswith("/internal"):
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
    metadata = await create_service_dependency("content-processor")()

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


# Add main API routes
# Includes /, /health, /status, /processing/diagnostics
app.include_router(diagnostics_router)
# /process, /process/types, /process/status
app.include_router(processing_router)
app.include_router(servicebus_router)  # /internal Service Bus endpoints
# /storage-queue Storage Queue endpoints
app.include_router(storage_queue_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=settings.environment == "development",
    )
