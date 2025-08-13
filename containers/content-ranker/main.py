"""
Content Ranker Service - FastAPI Application

Container Apps implementation of ContentRanker with pure functions architecture.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import content_ranker

# Create FastAPI application
app = FastAPI(
    title="AI Content Farm - Content Ranker",
    description="Content ranking service with engagement, monetization, recency, and quality scoring",
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
app.include_router(content_ranker.router)


@app.get("/health")
async def health_check():
    """Main application health check"""
    return {
        "status": "healthy",
        "service": "ai-content-farm-content-ranker",
        "version": "2.0.0"
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "AI Content Farm - Content Ranker",
        "version": "2.0.0",
        "description": "Content ranking service with multi-factor scoring algorithms",
        "documentation": "/docs",
        "health": "/health",
        "api": "/api/content-ranker"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
