"""
Content Enricher Service - FastAPI Application

AI-powered content enhancement with summaries, categorization, and metadata extraction.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import content_enricher

# Create FastAPI application
app = FastAPI(
    title="AI Content Farm - Content Enricher",
    description="AI-powered content enhancement with summaries, categorization, and metadata extraction",
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
app.include_router(content_enricher.router)


@app.get("/health")
async def health_check():
    """Main application health check"""
    return {
        "status": "healthy",
        "service": "ai-content-farm-content-enricher",
        "version": "2.0.0"
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "AI Content Farm - Content Enricher",
        "version": "2.0.0",
        "description": "AI-powered content enhancement service",
        "documentation": "/docs",
        "health": "/health",
        "api": "/api/content-enricher"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
