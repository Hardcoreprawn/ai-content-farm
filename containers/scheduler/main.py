"""
Scheduler Service - FastAPI Application

Workflow orchestration and scheduling for content processing pipeline.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import scheduler

# Create FastAPI application
app = FastAPI(
    title="AI Content Farm - Scheduler",
    description="Workflow orchestration and scheduling for content processing pipeline",
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
app.include_router(scheduler.router)


@app.get("/health")
async def health_check():
    """Main application health check"""
    return {
        "status": "healthy",
        "service": "ai-content-farm-scheduler",
        "version": "2.0.0"
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "AI Content Farm - Scheduler",
        "version": "2.0.0",
        "description": "Workflow orchestration and scheduling service",
        "documentation": "/docs",
        "health": "/health",
        "api": "/api/scheduler"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
