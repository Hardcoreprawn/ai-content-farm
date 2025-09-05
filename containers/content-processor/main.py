#!/usr/bin/env python3
"""Content Processor Service

FastAPI applic# Create shared endpoints
health_endpoint = create_standard_health_endpoint(
    service_name="content-processor",
    version=settings.service_version,
    environment=settings.environment,
    dependency_checks=DEPENDENCY_CHECKS,
    service_metadata_dep=service_metadata,
)

status_endpoint = create_standard_status_endpoint(
    service_name="content-processor",
    environment=settings.environment,
    service_metadata_dep=service_metadata,
)I-powered content processing.
Implements standardized health endpoints and API patterns.
"""

import logging
from contextlib import asynccontextmanager

from dependencies import (
    DEPENDENCY_CHECKS,
    get_configuration,
    service_metadata,
    settings,
)
from endpoints import router
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
    allow_origins=["*"],  # Configure based on environment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add main API routes
app.include_router(router)

# Create shared endpoints using the standard library
health_endpoint = create_standard_health_endpoint(
    service_name="content-processor",
    version=settings.service_version,
    environment=settings.environment,
    dependency_checks=DEPENDENCY_CHECKS,
    service_metadata_dep=service_metadata,
)

status_endpoint = create_standard_status_endpoint(
    service_name="content-processor",
    version=settings.service_version,
    environment=settings.environment,
    service_metadata_dep=service_metadata,
)

root_endpoint = create_standard_root_endpoint(
    service_name="content-processor",
    description="AI-powered content processing and enhancement service",
    version=settings.service_version,
    service_metadata_dep=service_metadata,
)

# Register the shared endpoints
app.get("/health", tags=["Standard Endpoints"])(health_endpoint)
app.get("/status", tags=["Standard Endpoints"])(status_endpoint)
app.get("/", tags=["Standard Endpoints"])(root_endpoint)

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
