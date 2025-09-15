#!/usr/bin/env python3
"""Content Processor Service

FastAPI application for AI-powered content processing.
Implements standardized health endpoints and API patterns.

Version: 1.0.2 - Full deployment pipeline test
Pipeline Fix Test: Testing Issue #421 container versioning
Matrix Test: Full container matrix validation (Sep 15, 2025)
"""

import importlib.util
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import endpoints as endpoints_module  # Import the main endpoints.py file
from dependencies import (
    DEPENDENCY_CHECKS,
    get_configuration,
    service_metadata,
    settings,
)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from config import ContentProcessorSettings
from libs.shared_models import StandardError
from libs.standard_endpoints import (
    create_standard_404_handler,
    create_standard_health_endpoint,
    create_standard_root_endpoint,
    create_standard_status_endpoint,
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
    """Application lifespan manager."""
    logger.info("Starting Content Processor service")
    logger.info(f"Service version: {settings.service_version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Log level: {settings.log_level}")

    yield

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


# Add main API routes
app.include_router(endpoints_module.router)

# Add Service Bus endpoints for Phase 1 Security Implementation
try:
    # Simple approach - just skip if not available during development
    logger.info("Service Bus endpoints: Development mode - skipping")
except Exception as e:
    logger.warning(f"Service Bus endpoints not available: {e}")

# Add shared standard endpoints
app.add_api_route(
    "/",
    create_standard_root_endpoint(
        service_name="content-processor",
        description="AI-powered content processing and enhancement service",
        version=settings.service_version,
        service_metadata_dep=service_metadata,
    ),
)

app.add_api_route(
    "/status",
    create_standard_status_endpoint(
        service_name="content-processor",
        version=settings.service_version,
        environment=settings.environment,
        service_metadata_dep=service_metadata,
    ),
)

app.add_api_route(
    "/health",
    create_standard_health_endpoint(
        service_name="content-processor",
        version=settings.service_version,
        environment=settings.environment,
        dependency_checks=DEPENDENCY_CHECKS,
        service_metadata_dep=service_metadata,
    ),
)

# Add standardized 404 error handler
app.add_exception_handler(
    StarletteHTTPException, create_standard_404_handler("content-processor")
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=settings.environment == "development",
    )
