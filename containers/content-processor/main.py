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
import os
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

from libs.container_lifecycle import create_lifecycle_manager
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

    # Optional startup diagnostics (enabled via environment variable)
    if os.getenv("RUN_STARTUP_DIAGNOSTICS", "false").lower() == "true":
        logger.info("🔍 Running startup diagnostics...")
        try:
            from endpoints.diagnostics import PipelineDiagnostics

            diagnostics = PipelineDiagnostics()
            result = await diagnostics.run_all_tests(deep_scan=True)

            logger.info(
                f"📊 Startup Diagnostics: {result.overall_status} - {result.summary}"
            )

            if result.overall_status == "failed":
                logger.error("❌ Startup diagnostics failed:")
                for test in result.tests:
                    if test.status == "fail":
                        logger.error(f"  - {test.name}: {test.message}")

                for rec in result.recommendations:
                    logger.error(f"  💡 {rec}")

                # In strict mode, exit on diagnostics failure
                if os.getenv("STRICT_STARTUP_DIAGNOSTICS", "false").lower() == "true":
                    logger.error(
                        "Exiting due to failed startup diagnostics (STRICT_STARTUP_DIAGNOSTICS=true)"
                    )
                    raise SystemExit(1)
            elif result.overall_status == "degraded":
                logger.warning("⚠️ Startup diagnostics have warnings:")
                for test in result.tests:
                    if test.status == "warning":
                        logger.warning(f"  - {test.name}: {test.message}")
            else:
                logger.info("✅ All startup diagnostics passed successfully")

        except Exception as e:
            logger.error(f"❌ Startup diagnostics failed with error: {e}")
            if os.getenv("STRICT_STARTUP_DIAGNOSTICS", "false").lower() == "true":
                raise SystemExit(1)

    # Start background queue processing on startup
    import asyncio

    from endpoints.storage_queue_router import get_storage_queue_router

    from libs.queue_client import process_queue_messages
    from libs.storage_queue_poller import StorageQueuePoller

    # Initialize lifecycle manager
    lifecycle_manager = create_lifecycle_manager("content-processor")

    # Message handler for background poller (takes message_data dict)
    async def message_handler_wrapper(message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Wrapper to convert message_data to QueueMessageModel for router."""
        from libs.queue_client import QueueMessageModel

        try:
            # Convert dict to QueueMessageModel
            queue_message = QueueMessageModel(**message_data)
            router_instance = get_storage_queue_router()
            result = await router_instance.process_storage_queue_message(queue_message)

            if result["status"] == "success":
                logger.info(
                    f"Background: Successfully processed message {queue_message.message_id}"
                )
            else:
                logger.warning(
                    f"Background: Message processing failed: {result.get('error', 'Unknown error')}"
                )

            return result
        except Exception as e:
            logger.error(f"Background: Error processing message: {e}")
            return {"status": "error", "error": str(e)}

    # Process message handler for startup (legacy signature with queue_message, message)
    async def process_message(queue_message, message) -> Dict[str, Any]:
        """Process a single message on startup."""
        try:
            router_instance = get_storage_queue_router()
            result = await router_instance.process_storage_queue_message(queue_message)

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

    # Initialize background poller
    background_poller = StorageQueuePoller(
        queue_name="content-processing-requests",
        message_handler=message_handler_wrapper,
        poll_interval=float(os.getenv("QUEUE_POLL_INTERVAL", "5.0")),
        max_messages_per_batch=10,
        max_empty_polls=3,
        empty_queue_sleep=30.0,
        process_queue_messages_func=process_queue_messages,
    )

    async def startup_queue_processor():
        """Process any existing queue messages on startup using lifecycle manager."""

        # Use lifecycle manager for queue processing
        async def process_messages_wrapper(queue_name: str, max_messages: int):
            return await process_queue_messages(
                queue_name=queue_name,
                message_handler=process_message,
                max_messages=max_messages,
            )

        await lifecycle_manager.handle_startup_queue_processing(
            process_messages_wrapper, "content-processing-requests", max_messages=32
        )

        # Start continuous background polling if enabled
        await background_poller.start()

    # Start the background task
    asyncio.create_task(startup_queue_processor())

    try:
        yield
    finally:
        logger.info("Shutting down Content Processor service")

        # Stop background poller
        await background_poller.stop()

        try:
            # Close API client to prevent unclosed session warnings
            from dependencies import get_api_client

            try:
                api_client = get_api_client()
                await api_client.close()
                logger.info("✅ API client closed")
            except Exception as e:
                logger.warning(f"⚠️ Error closing API client: {e}")

            # Clean up any remaining async resources
            from processor import ContentProcessor

            processor = ContentProcessor()
            await processor.cleanup()
            logger.info("✅ FINAL-CLEANUP: Async resources cleaned up")
        except Exception as e:
            logger.warning(f"⚠️ FINAL-CLEANUP: Error during final cleanup: {e}")


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
