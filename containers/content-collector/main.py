"""
Content Womble - Main FastAPI Application

A humble content collection service for gathering and analyzing digital content.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any, Dict

from endpoints import (
    api_documentation_endpoint,
    api_process_content_endpoint,
    discover_topics_endpoint,
    get_sources_endpoint,
    health_endpoint,
    reddit_diagnostics_endpoint,
    root_endpoint,
)
from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from models import (
    CollectionRequest,
    DiscoveryRequest,
    LegacyCollectionRequest,
    SourceConfig,
)

from libs.shared_models import StandardResponse, create_service_dependency

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create service metadata dependency
service_metadata = create_service_dependency("content-womble")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    logger.info("Content Womble starting up...")
    yield
    logger.info("Content Womble shutting down...")


# Initialize FastAPI app
app = FastAPI(
    title="Content Womble API",
    description="A humble service for collecting and analyzing digital content",
    version="2.0.0",
    lifespan=lifespan,
)


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

    return JSONResponse(
        status_code=404,
        content=StandardResponse(
            status="error",
            message="Endpoint not found",
            data={
                "requested_path": str(request.url.path),
                "available_endpoints": [
                    "/api/content-womble/health",
                    "/api/content-womble/status",
                    "/api/content-womble/process",
                    "/api/content-womble/docs",
                    "/api/content-womble/reddit-diagnostics",
                ],
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
@app.get("/", response_model=StandardResponse)
async def root(metadata: Dict[str, Any] = Depends(service_metadata)):
    """Service information and capabilities."""
    return await root_endpoint(metadata)


@app.post("/discover", response_model=StandardResponse)
async def discover_topics(
    request: DiscoveryRequest, metadata: Dict[str, Any] = Depends(service_metadata)
):
    """Discover trending topics from configured sources."""
    return await discover_topics_endpoint(request, metadata)


@app.post("/collect", response_model=StandardResponse)
async def collect_content(
    request: LegacyCollectionRequest,
    metadata: Dict[str, Any] = Depends(service_metadata),
):
    """Legacy collection endpoint for backward compatibility."""
    # Convert to standardized format and process
    standardized_request = CollectionRequest(
        sources=[SourceConfig(**source) for source in request.sources],
        deduplicate=request.deduplicate,
        similarity_threshold=request.similarity_threshold,
        save_to_storage=request.save_to_storage,
    )
    return await api_process_content_endpoint(standardized_request, metadata)


@app.get("/sources", response_model=StandardResponse)
async def get_available_sources(metadata: Dict[str, Any] = Depends(service_metadata)):
    """Get available content sources and their capabilities."""
    return await get_sources_endpoint(metadata)


# Standardized API endpoints
@app.get("/api/content-womble/health", response_model=StandardResponse)
async def api_health_check(metadata: Dict[str, Any] = Depends(service_metadata)):
    """Standardized health check endpoint."""
    return await health_endpoint(metadata)


@app.post("/api/content-womble/process", response_model=StandardResponse)
async def api_process_content(
    request: CollectionRequest, metadata: Dict[str, Any] = Depends(service_metadata)
):
    """Standardized content processing endpoint."""
    return await api_process_content_endpoint(request, metadata)


@app.get("/api/content-womble/docs", response_model=StandardResponse)
async def api_documentation(metadata: Dict[str, Any] = Depends(service_metadata)):
    """API documentation endpoint."""
    return await api_documentation_endpoint(metadata)


@app.get("/api/content-womble/reddit-diagnostics", response_model=StandardResponse)
async def api_reddit_diagnostics(metadata: Dict[str, Any] = Depends(service_metadata)):
    """Reddit API diagnostics endpoint."""
    return await reddit_diagnostics_endpoint(metadata)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
