# Quick Start Guide: AI Content Farm Development

This guide gets you from zero to productive development in under 30 minutes.

**🚀 Now featuring simplified 3-container architecture for faster development!**

## Prerequisites Checklist

- [ ] Docker and Docker Compose installed
- [ ] VS Code with Python extension
- [ ] Basic understanding of FastAPI and async Python
- [ ] Git repository cloned locally

## 5-Minute Environment Setup

```bash
# 1. Start development environment
cd /workspaces/ai-content-farm
docker-compose up -d azurite

# 2. Verify blob storage is working
curl http://localhost:10000/devstoreaccount1

# 3. Install Python dependencies for local development
pip install -r requirements.txt

# 4. Run environment validation
python -c "from libs.blob_storage import BlobStorageClient; print('✅ Blob storage ready')"
```

## Understanding the Simplified Architecture

### The Big Picture (3-Container Design)
```
Reddit/Sources → Content Collector → Content Processor (Enhanced) → Site Generator → Website
     ↓               ↓                      ↓                           ↓
 [collected]    [processed]        [AI Generated Content]      [static-sites]
```

### Key Concepts

1. **Simplified containers**: Only 3 containers for the entire pipeline
2. **Enhanced content-processor**: Combines processing AND AI generation
3. **Blob storage for everything**: No filesystem dependencies, all data stored in Azure blobs
4. **Event-driven**: Services trigger each other when new content is available
5. **Standard APIs**: All containers expose `/health`, `/status`, and service-specific endpoints

### Blob Container Organization
```
collected-content/    # Raw content from sources (Reddit, etc.)
processed-content/    # Processed + AI-generated content
static-sites/         # Generated HTML websites
pipeline-logs/        # Processing logs and metrics
```
enriched-content/     # AI-enhanced content with metadata
ranked-content/       # Prioritized and scored content
generated-content/    # Markdown files ready for publishing
published-sites/      # Complete HTML websites
```

## Your First Container

Let's build a simple example container following our standards:

### 1. Create Container Structure
```bash
mkdir -p containers/example-service/{tests}
cd containers/example-service
```

### 2. Create Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared modules
COPY ../shared/blob_storage.py ./
COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 3. Create requirements.txt
```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.4.2
azure-storage-blob==12.19.0
httpx==0.25.0
```

### 4. Create main.py
```python
#!/usr/bin/env python3
"""
Example Service - Demonstrates standard container structure
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks
    from libs.blob_storage import BlobStorageClient, BlobContainers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global instances
blob_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global blob_client
    # Startup
    logger.info("Starting Example Service")
    blob_client = BlobStorageClient()
    yield
    # Shutdown
    logger.info("Shutting down Example Service")

app = FastAPI(
    title="Example Service",
    description="Demonstrates standard container patterns",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/")
async def root():
    return {
        "service": "example-service",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    try:
        # Test blob storage connectivity
        blob_client.ensure_container("health-check-example")
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@app.get("/status")
async def get_status():
    return {
        "status": "healthy",
        "service": "example-service",
        "blob_containers": ["health-check-example"]
    }

@app.post("/process")
async def process_data(background_tasks: BackgroundTasks):
    """Example processing endpoint."""
    # Process data in background
    background_tasks.add_task(example_processing_task)
    return {"message": "Processing started", "status": "accepted"}

async def example_processing_task():
    """Example background processing."""
    logger.info("Starting background processing")
    
    # Example: Read from one container, process, write to another
    try:
        # Simulated processing
        result = {"processed": True, "timestamp": "2024-01-01T00:00:00Z"}
        
        # Save result to blob storage
        await blob_client.upload_json(
            BlobContainers.PROCESSED_CONTENT,
            "example_result.json",
            result
        )
        
        logger.info("Processing completed successfully")
    except Exception as e:
        logger.error(f"Processing failed: {e}")
```

### 5. Test the Container
```bash
# Build the container
docker build -t example-service .

# Run the container
docker run -d -p 8000:8000 \
  -e AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://host.docker.internal:10000/devstoreaccount1;" \  # pragma: allowlist secret
  example-service

# Test the endpoints
curl http://localhost:8000/health        # Should return {"status": "healthy"}
curl http://localhost:8000/              # Should return service info
curl -X POST http://localhost:8000/process  # Should trigger processing
```

## Working with Existing Containers

### SSG Container (Generate Websites)
```bash
# Check SSG status
curl http://localhost:8002/health

# Generate a site (once implemented)
curl -X POST http://localhost:8002/generate \
  -H "Content-Type: application/json" \
  -d '{"source_blob": "ranked_content_20240101.json"}'

# Preview generated site
curl http://localhost:8002/preview/latest
```

### Content Collector (Fetch from Reddit)
```bash
# Trigger content collection
curl -X POST http://localhost:8001/collect \
  -H "Content-Type: application/json" \
  -d '{"sources": ["reddit"], "topics": ["technology", "programming"]}'

# Check collection status
curl http://localhost:8001/status
```

## Development Workflow

### 1. Make Changes to a Container
```bash
# Edit container code
code containers/ssg/main.py

# Rebuild container
cd containers/ssg
docker build -t ai-content-farm-ssg .

# Update running container
docker-compose up -d ssg
```

### 2. Test Changes
```bash
# Run unit tests
pytest containers/ssg/tests/

# Test specific functionality
curl http://localhost:8002/health

# Run integration tests
pytest tests/test_ssg_integration.py
```

### 3. Validate Pipeline
```bash
# Test complete pipeline
./test-pipeline.sh

# Or test specific stages
python test_web_pipeline.py
```

## Common Development Tasks

### Add a New Processing Stage

1. **Create container structure** (use example above)
2. **Implement processing logic** in service_logic.py
3. **Add to docker-compose.yml**:
   ```yaml
   new-service:
     build: ./containers/new-service
     ports:
       - "8005:8000"
     environment:
       - AZURE_STORAGE_CONNECTION_STRING=${AZURE_STORAGE_CONNECTION_STRING}
   ```
4. **Test integration** with neighboring services

### Debug Container Issues

```bash
# Check container logs
docker-compose logs ssg

# Get shell access to container
docker-compose exec ssg bash

# Check blob storage connectivity
docker-compose exec ssg python -c "from blob_storage import BlobStorageClient; BlobStorageClient().list_containers()"

# Test health endpoints
curl http://localhost:8002/health
```

### Monitor Blob Storage

```bash
# List all containers
curl http://localhost:10000/devstoreaccount1?comp=list

# List blobs in a container
curl "http://localhost:10000/devstoreaccount1/collected-content?restype=container&comp=list"

# Download a blob for inspection
curl "http://localhost:10000/devstoreaccount1/processed-content/example.json"
```

## Troubleshooting Common Issues

### "Connection refused" errors
- Check if Azurite is running: `docker-compose ps azurite`
- Verify connection string in environment variables
- Ensure containers are on same Docker network

### "Container not found" blob errors
- Containers are created automatically on first use
- Check if blob storage client is properly initialized
- Verify container naming follows BlobContainers enum

### Health checks failing
- Check if required dependencies are available
- Verify Azure Storage connection
- Look at container logs for specific errors

### Performance issues
- Check if blob operations are being cached appropriately
- Monitor container resource usage with `docker stats`
- Consider implementing async operations for I/O heavy tasks

## Next Steps

1. **Read the documentation**:
   - System Architecture: `docs/SYSTEM_ARCHITECTURE.md`
   - Container Standards: `docs/CONTAINER_DEVELOPMENT_STANDARDS.md`
   - Migration Guide: `docs/CONTAINER_MIGRATION_GUIDE.md`

2. **Pick a task from the roadmap**: `docs/IMPLEMENTATION_ROADMAP.md`

3. **Start with high-impact changes**:
   - Fix SSG container volume conflicts
   - Implement blob storage in content collector
   - Add health checks to existing containers

4. **Follow the development standards**:
   - Use standard FastAPI structure
   - Implement required endpoints
   - Add comprehensive tests
   - Use blob storage for all persistence

## Getting Help

- **Architecture questions**: Review `docs/SYSTEM_ARCHITECTURE.md`
- **Implementation patterns**: Check `docs/CONTAINER_DEVELOPMENT_STANDARDS.md`
- **Specific container issues**: Look at existing container implementations
- **Testing approaches**: Review `tests/` directory for examples

Remember: Every container should be self-contained, follow the same patterns, and integrate seamlessly with the blob storage architecture. When in doubt, follow the standards documented in this repository.
