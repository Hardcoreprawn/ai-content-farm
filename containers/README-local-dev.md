# Local Development Setup

## Overview
This setup uses official Microsoft Azure Functions Python base images for compatibility and security updates.

## Prerequisites
- Docker and Docker Compose
- `curl` and `jq` (for testing)

## Quick Start

1. **Build and start all services:**
   ```bash
   docker-compose up --build -d
   ```

2. **Test the pipeline:**
   ```bash
   ./test-pipeline.sh
   ```

3. **View logs:**
   ```bash
   docker-compose logs -f
   ```

## Services

| Service | Port | Purpose |
|---------|------|---------|
| content-collector | 8001 | Collects content from Reddit/sources |
| content-processor | 8002 | Cleans and normalizes content |
| content-enricher | 8003 | Adds AI analysis and metadata |

## API Endpoints

### Content Collector (http://localhost:8001)
- `GET /health` - Health check
- `POST /collect` - Collect content from sources

### Content Processor (http://localhost:8002)
- `GET /health` - Health check  
- `POST /process` - Process raw content

### Content Enricher (http://localhost:8003)
- `GET /health` - Health check
- `POST /enrich` - Enrich processed content

## Docker Images
All containers use official Microsoft Azure Functions Python base images:
- `mcr.microsoft.com/azure-functions/python:4-python3.11-slim`

This ensures:
- ✅ Security updates from Microsoft
- ✅ Azure Functions compatibility
- ✅ Official support and documentation
- ✅ Optimized for cloud deployment

## Output
Content files are saved to the `./output` directory and mounted as a volume for easy access.

## Cleanup
```bash
docker-compose down -v  # Remove containers and volumes
docker system prune     # Clean up unused images
```
