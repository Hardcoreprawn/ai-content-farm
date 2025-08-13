"""
AI Content Farm - Container Apps Edition

FastAPI application for content processing with pluggable collectors.
This replaces the Azure Functions approach with a more maintainable
Container Apps architecture.
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import summary_womble

# Create FastAPI app
app = FastAPI(
    title="AI Content Farm API",
    description="Content collection and processing API with pluggable sources",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(summary_womble.router)


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "AI Content Farm API",
        "version": "2.0.0",
        "status": "healthy",
        "architecture": "container-apps",
        "available_endpoints": {
            "content_collection": "/api/summary-womble/",
            "health_checks": "/health",
            "documentation": "/docs",
            "api_schema": "/openapi.json"
        }
    }


@app.get("/health")
async def health_check():
    """Global health check"""
    return {
        "status": "healthy",
        "service": "ai-content-farm-api",
        "version": "2.0.0"
    }

if __name__ == "__main__":
    import uvicorn

    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))

    # Run the application
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=os.getenv("ENVIRONMENT") == "development"
    )
