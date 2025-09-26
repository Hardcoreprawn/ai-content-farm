#!/usr/bin/env python3
"""Content Processor Service

FastAPI application for AI-powered content processing.
Implements standardized health endpoints and API patterns.

Version: 1.0.2 - Full deployment pipeline test
Pipeline Fix Test: Testing Issue #421 container versioning
Matrix Test: Full container matrix validation (Sep 15, 2025)
Security Test: Triggering security pipeline validation (Sep 19, 2025)
"""

import asyncio
import importlib.util
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict

from dependencies import (
    DEPENDENCY_CHECKS,
    get_configuration,
    service_metadata,
    settings,
)
from endpoints import (
    diagnostics_router,
    processing_router,
    storage_queue_router,
)
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.exceptions import HTTPException as StarletteHTTPException

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for KEDA-triggered processing."""
    logger.info("Starting Content Processor service")
    logger.info(f"Service version: {settings.service_version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Log level: {settings.log_level}")
    logger.info("Content Processor ready for KEDA Storage Queue scaling")

    # Start background queue processing on startup
    import asyncio

    from endpoints.storage_queue_router import get_storage_queue_router

    from libs.queue_client import process_queue_messages

    async def startup_queue_processor():
        """Process any existing queue messages on startup."""
        try:
            logger.info("Starting up - checking for pending queue messages...")

            # Process message handler
            async def process_message(queue_message, message) -> Dict[str, Any]:
                """Process a single message on startup."""
                try:
                    router_instance = get_storage_queue_router()
                    result = await router_instance.process_storage_queue_message(
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

            # Process up to 50 messages on startup (content processor handles more than site generator)
            processed_count = await process_queue_messages(
                queue_name="content-processing-requests",
                message_handler=process_message,
                max_messages=50,
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
        logger.info(
            f"Scheduling graceful shutdown in 5 seconds (exit_code: {exit_code})"
        )
        await asyncio.sleep(5)
        logger.info("Graceful shutdown complete")
        import os

        os._exit(exit_code)

    # Start the background task
    asyncio.create_task(startup_queue_processor())

    try:
        yield
    finally:
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
