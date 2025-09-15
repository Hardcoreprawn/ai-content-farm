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

from dependencies import (
    DEPENDENCY_CHECKS,
    get_configuration,
    service_metadata,
    settings,
)
from endpoints import diagnostics_router, processing_router, servicebus_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse

from libs.shared_models import StandardError

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
# Includes /, /health, /status, /processing/diagnostics
app.include_router(diagnostics_router)
# /process, /process/types, /process/status
app.include_router(processing_router)
app.include_router(servicebus_router)  # /internal Service Bus endpoints


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=settings.environment == "development",
    )
