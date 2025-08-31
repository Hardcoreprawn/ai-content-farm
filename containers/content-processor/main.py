#!/usr/bin/env python3
"""
Content Processor FastAPI Application

Clean, functional content processor implementing the wake-up work queue pattern.
Scales 0-3 instances on Azure Container Apps, processes topics into 3000-word articles.

Architecture:
- Event-driven wake-up endpoint
- Functional processing pipeline
- Azure OpenAI integration
- Comprehensive cost tracking
"""

import logging
from contextlib import asynccontextmanager
from typing import Any, Dict

from endpoints import (
    docs_endpoint,
    health_endpoint,
    process_batch_endpoint,
    root_endpoint,
    service_metadata,
    status_endpoint,
    wake_up_endpoint,
)
from fastapi import Depends, FastAPI
from models import ProcessBatchRequest, WakeUpRequest

from libs.shared_models import StandardResponse

# Configure logging (no emojis per agent instructions)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown."""
    logger.info("Content Processor starting - wake-up work queue pattern")
    yield
    logger.info("Content Processor shutting down")


# Create FastAPI app with clean configuration
app = FastAPI(
    title="Content Processor",
    description="Event-driven content processing service for AI content farm",
    version="1.0.0",
    lifespan=lifespan,
)


# Core API endpoints following agent instructions
@app.get("/", response_model=StandardResponse)
async def root(metadata: Dict[str, Any] = Depends(service_metadata)):
    """Root endpoint with service information."""
    return await root_endpoint(metadata)


@app.get("/api/processor/health", response_model=StandardResponse)
async def health(metadata: Dict[str, Any] = Depends(service_metadata)):
    """Health check endpoint."""
    return await health_endpoint(metadata)


@app.post("/api/processor/wake-up", response_model=StandardResponse)
async def wake_up(
    request: WakeUpRequest, metadata: Dict[str, Any] = Depends(service_metadata)
):
    """
    Primary wake-up endpoint for event-driven processing.

    Called by collector when work is available.
    Processor autonomously finds topics, processes them, then scales to zero.
    """
    return await wake_up_endpoint(request, metadata)


@app.post("/api/processor/process-batch", response_model=StandardResponse)
async def process_batch(
    request: ProcessBatchRequest, metadata: Dict[str, Any] = Depends(service_metadata)
):
    """Manual batch processing endpoint for specific topics."""
    return await process_batch_endpoint(request, metadata)


@app.get("/api/processor/status", response_model=StandardResponse)
async def status(metadata: Dict[str, Any] = Depends(service_metadata)):
    """Current processing status and metrics."""
    return await status_endpoint(metadata)


@app.get("/api/processor/docs", response_model=StandardResponse)
async def docs(metadata: Dict[str, Any] = Depends(service_metadata)):
    """API documentation and usage examples."""
    return await docs_endpoint(metadata)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
