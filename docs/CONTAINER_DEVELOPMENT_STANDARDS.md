# Container Development Standards

This document defines the mandatory standards and patterns for all AI Content Farm containers.

## Container Template Structure

Every container MUST follow this exact structure:

```
container-name/
├── Dockerfile                 # Standard container definition
├── requirements.txt          # Python dependencies
├── main.py                   # FastAPI application entry point
├── config.py                 # Configuration and environment handling
├── blob_storage.py           # Blob storage client (shared)
├── service_logic.py          # Core business logic
├── models.py                 # Pydantic models for API
├── health.py                 # Health check implementation
├── .dockerignore            # Docker ignore patterns
└── tests/
    ├── __init__.py
    ├── test_main.py         # API endpoint tests
    ├── test_service.py      # Business logic tests
    └── test_integration.py  # Blob storage integration tests
```

## Standard Dockerfile Template

```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create application directories
RUN mkdir -p /app/temp

# Copy application code
COPY . .

# Create health check script
RUN echo '#!/bin/bash\ncurl -f http://localhost:8000/health || exit 1' > /usr/local/bin/healthcheck.sh && \
    chmod +x /usr/local/bin/healthcheck.sh

# Expose port
EXPOSE 8000

# Health check configuration
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD ["/usr/local/bin/healthcheck.sh"]

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
```

## Standard Requirements Template

```txt
# Core FastAPI dependencies
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.4.2
python-multipart==0.0.6

# Azure dependencies
azure-storage-blob==12.19.0
azure-core==1.29.5
azure-identity==1.15.0

# HTTP client
httpx==0.25.0

# Utilities
python-dateutil==2.8.2
```

## Standard main.py Template

```python
#!/usr/bin/env python3
"""
{Service Name} - Main FastAPI Application

{Brief description of service purpose}
"""

import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Dict, Any

# Import local modules
from config import get_config, validate_environment
from health import HealthChecker
from models import *
from service_logic import ServiceProcessor
from libs.blob_storage import BlobStorageClient, BlobContainers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
config = get_config()
health_checker = HealthChecker()
service_processor = ServiceProcessor()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    logger.info(f"Starting {config.service_name} v{config.version}")
    
    # Validate environment
    if not validate_environment():
        raise RuntimeError("Environment validation failed")
    
    # Initialize blob storage
    try:
        blob_client = BlobStorageClient()
        app.state.blob_client = blob_client
        logger.info("Blob storage client initialized")
    except Exception as e:
        logger.error(f"Failed to initialize blob storage: {e}")
        raise
    
    # Start background tasks
    await service_processor.start()
    
    yield
    
    # Shutdown
    logger.info(f"Shutting down {config.service_name}")
    await service_processor.stop()

# Create FastAPI app
app = FastAPI(
    title=config.service_name,
    description=config.service_description,
    version=config.version,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Internal server error",
            "metadata": {
                "service": config.service_name,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
    )

# Standard endpoints
@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": config.service_name,
        "version": config.version,
        "description": config.service_description,
        "status": "running",
        "endpoints": {
            "health": "/health",
            "status": "/status",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return await health_checker.check_health()

@app.get("/status")
async def get_status():
    """Detailed status endpoint."""
    return await health_checker.get_detailed_status()

# Service-specific endpoints go here
# ...

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=False
    )
```

## Standard config.py Template

```python
#!/usr/bin/env python3
"""
Configuration module for {Service Name}

Handles environment variables, Azure configuration, and validation.
"""

import os
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

@dataclass
class ServiceConfig:
    """Service configuration settings."""
    
    # Service identity
    service_name: str = "{service-name}"
    service_description: str = "{Service description}"
    version: str = "1.0.0"
    
    # Environment
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    
    # Azure Storage
    storage_connection_string: str = field(
        default_factory=lambda: os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
    )
    
    # Service-specific configuration
    # Add service-specific config fields here
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.storage_connection_string:
            raise ValueError("AZURE_STORAGE_CONNECTION_STRING is required")
        
        if self.environment not in ["development", "staging", "production"]:
            raise ValueError(f"Invalid environment: {self.environment}")

def get_config() -> ServiceConfig:
    """Get service configuration."""
    return ServiceConfig()

def validate_environment() -> bool:
    """Validate that the environment is properly configured."""
    try:
        config = get_config()
        
        # Test blob storage connectivity
        from blob_storage import BlobStorageClient
        blob_client = BlobStorageClient()
        
        # Try to list containers (will create if doesn't exist)
        test_container = f"health-check-{config.service_name}"
        blob_client.ensure_container(test_container)
        
        logger.info("Environment validation successful")
        return True
        
    except Exception as e:
        logger.error(f"Environment validation failed: {e}")
        return False
```

## Standard health.py Template

```python
#!/usr/bin/env python3
"""
Health check implementation for {Service Name}
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any
from blob_storage import BlobStorageClient
from config import get_config

logger = logging.getLogger(__name__)

class HealthChecker:
    """Health check implementation."""
    
    def __init__(self):
        self.config = get_config()
        self.start_time = datetime.now(timezone.utc)
        self.request_count = 0
        self.last_activity = datetime.now(timezone.utc)
    
    async def check_health(self) -> Dict[str, Any]:
        """Basic health check."""
        try:
            # Test blob storage connectivity
            blob_client = BlobStorageClient()
            test_container = f"health-check-{self.config.service_name}"
            blob_client.ensure_container(test_container)
            
            self.last_activity = datetime.now(timezone.utc)
            self.request_count += 1
            
            return {
                "status": "healthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "service": self.config.service_name,
                "version": self.config.version
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "service": self.config.service_name,
                "version": self.config.version,
                "error": str(e)
            }
    
    async def get_detailed_status(self) -> Dict[str, Any]:
        """Detailed status information."""
        try:
            # Check dependencies
            dependencies = await self._check_dependencies()
            
            # Calculate uptime
            uptime = (datetime.now(timezone.utc) - self.start_time).total_seconds()
            
            return {
                "status": "healthy" if all(dep["status"] == "healthy" for dep in dependencies.values()) else "degraded",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "service": self.config.service_name,
                "version": self.config.version,
                "environment": self.config.environment,
                "dependencies": dependencies,
                "metrics": {
                    "uptime_seconds": int(uptime),
                    "requests_processed": self.request_count,
                    "last_activity": self.last_activity.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Status check failed: {e}")
            return {
                "status": "error",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "service": self.config.service_name,
                "error": str(e)
            }
    
    async def _check_dependencies(self) -> Dict[str, Dict[str, Any]]:
        """Check status of dependencies."""
        dependencies = {}
        
        # Check blob storage
        try:
            blob_client = BlobStorageClient()
            test_container = f"health-check-{self.config.service_name}"
            blob_client.ensure_container(test_container)
            dependencies["azure_storage"] = {
                "status": "healthy",
                "response_time_ms": 0  # Could measure actual response time
            }
        except Exception as e:
            dependencies["azure_storage"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Add service-specific dependency checks here
        
        return dependencies
```

## Standard models.py Template

```python
#!/usr/bin/env python3
"""
Pydantic models for {Service Name} API
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, field_validator
from enum import Enum

class ProcessingStatus(str, Enum):
    """Processing status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class StandardResponse(BaseModel):
    """Standard API response format."""
    status: str = Field(..., description="Response status")
    message: str = Field(..., description="Human readable message")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Response metadata")
    errors: Optional[List[Dict[str, Any]]] = Field(None, description="Error details")

class ServiceRequest(BaseModel):
    """Base request model."""
    request_id: Optional[str] = Field(None, description="Request identifier")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Request metadata")

class ServiceResponse(BaseModel):
    """Base response model."""
    request_id: Optional[str] = Field(None, description="Request identifier")
    processing_time_ms: Optional[int] = Field(None, description="Processing time in milliseconds")
    blob_name: Optional[str] = Field(None, description="Output blob name")

# Add service-specific models here
```

## Standard blob_storage.py

All containers use the same blob storage client. Copy from `/containers/shared/blob_storage.py`.

## Container-Specific Implementation

### Service Logic Pattern

Each container implements its core business logic in `service_logic.py`:

```python
#!/usr/bin/env python3
"""
{Service Name} business logic implementation
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from libs.blob_storage import BlobStorageClient, BlobContainers, get_timestamped_blob_name

logger = logging.getLogger(__name__)

class ServiceProcessor:
    """Core business logic for {Service Name}."""
    
    def __init__(self):
        self.blob_client = BlobStorageClient()
        self.is_running = False
        self.watch_task = None
    
    async def start(self):
        """Start background processing."""
        if not self.is_running:
            self.is_running = True
            self.watch_task = asyncio.create_task(self._watch_for_new_content())
            logger.info("Service processor started")
    
    async def stop(self):
        """Stop background processing."""
        self.is_running = False
        if self.watch_task:
            self.watch_task.cancel()
            try:
                await self.watch_task
            except asyncio.CancelledError:
                pass
        logger.info("Service processor stopped")
    
    async def _watch_for_new_content(self):
        """Watch for new content to process."""
        while self.is_running:
            try:
                # Check for new blobs to process
                new_blobs = await self._find_unprocessed_blobs()
                
                for blob_info in new_blobs:
                    await self._process_blob(blob_info)
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in content watcher: {e}")
                await asyncio.sleep(30)  # Wait longer on error
    
    async def _find_unprocessed_blobs(self) -> List[Dict[str, Any]]:
        """Find blobs that need processing."""
        # Implementation depends on service
        # Return list of blob info dictionaries
        pass
    
    async def _process_blob(self, blob_info: Dict[str, Any]):
        """Process a single blob."""
        # Implementation depends on service
        pass
    
    async def process_batch(self, input_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process a batch of data."""
        # Core processing logic goes here
        # Returns processing result with blob references
        pass
```

## Testing Standards

### Unit Tests

```python
#!/usr/bin/env python3
"""
Unit tests for {Service Name}
"""

import pytest
import asyncio
from unittest.mock import patch, Mock, AsyncMock
from main import app
from service_logic import ServiceProcessor

class TestServiceProcessor:
    """Test cases for service processor."""
    
    @pytest.fixture
    def processor(self):
        """Create service processor instance."""
        return ServiceProcessor()
    
    @pytest.mark.asyncio
    async def test_process_batch(self, processor):
        """Test batch processing."""
        # Test implementation
        pass
    
    @pytest.mark.asyncio
    async def test_error_handling(self, processor):
        """Test error handling."""
        # Test implementation
        pass

class TestAPI:
    """Test cases for API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi.testclient import TestClient
        return TestClient(app)
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] in ["healthy", "unhealthy"]
    
    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        assert "service" in response.json()
```

### Integration Tests

```python
#!/usr/bin/env python3
"""
Integration tests for {Service Name}
"""

import pytest
import asyncio
from libs.blob_storage import BlobStorageClient, BlobContainers

class TestBlobStorageIntegration:
    """Test blob storage integration."""
    
    @pytest.fixture
    def blob_client(self):
        """Create blob client for testing."""
        return BlobStorageClient()
    
    @pytest.mark.asyncio
    async def test_blob_operations(self, blob_client):
        """Test basic blob operations."""
        # Test upload, download, delete operations
        pass
    
    @pytest.mark.asyncio
    async def test_container_management(self, blob_client):
        """Test container operations."""
        # Test container creation and listing
        pass
```

## Development Checklist

Before submitting a container implementation, verify:

- [ ] Follows standard directory structure
- [ ] Implements all required endpoints (`/`, `/health`, `/status`)
- [ ] Uses standard response formats
- [ ] Implements proper error handling
- [ ] Includes comprehensive logging
- [ ] Uses blob storage for all data persistence
- [ ] Includes unit and integration tests
- [ ] Follows naming conventions for blobs
- [ ] Implements health checks properly
- [ ] Handles graceful shutdown
- [ ] Follows Docker best practices
- [ ] Environment validation on startup
- [ ] Proper dependency management

## Deployment Verification

After deployment, verify:

- [ ] Health endpoint returns healthy status
- [ ] Container can read from expected blob containers
- [ ] Container can write to expected blob containers
- [ ] Service properly integrates with pipeline
- [ ] Logging is working correctly
- [ ] Error handling works as expected
- [ ] Performance meets requirements

This standard ensures consistency, maintainability, and reliability across all AI Content Farm containers.
