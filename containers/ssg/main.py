"""
Static Site Generator Service - FastAPI Application

Markdown generation and static site publishing for processed content.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import ssg

# Create FastAPI application
app = FastAPI(
    title="AI Content Farm - Static Site Generator",
    description="Markdown generation and static site publishing for processed content",
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
app.include_router(ssg.router)


@app.get("/health")
async def health_check():
    """Main application health check"""
    return {
        "status": "healthy",
        "service": "ai-content-farm-ssg",
        "version": "2.0.0"
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "AI Content Farm - Static Site Generator",
        "version": "2.0.0",
        "description": "Markdown generation and static site publishing service",
        "documentation": "/docs",
        "health": "/health",
        "api": "/api/ssg"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
