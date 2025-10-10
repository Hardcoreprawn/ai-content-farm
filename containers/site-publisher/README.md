# Site Publisher Container

Static site generation with Hugo for AI Content Farm.

## Overview

The site-publisher container builds static HTML sites from markdown content using Hugo static site generator. It follows a pure functional architecture with security-first design.

## Architecture

- **Pure Functional**: No classes (except Pydantic models), all pure functions
- **Security First**: OWASP-compliant, path traversal prevention, no command injection
- **FastAPI REST**: Health checks, metrics, manual triggering
- **Hugo**: Go-based SSG for 10-100x faster builds than Python alternatives
- **Python 3.13**: 4 years of security support (until Oct 2029)

## Features

- ✅ Queue-triggered site builds (KEDA scaling 0→1)
- ✅ Manual build triggering via REST API
- ✅ Multi-stage Docker build (Go + Python)
- ✅ Non-root container user (security)
- ✅ Managed identity authentication
- ✅ Secure error handling with UUID correlation IDs
- ✅ Structured logging with sensitive data filtering

## API Endpoints

### GET /health
Health check endpoint.

**Response**: 200 OK
```json
{
  "status": "healthy",
  "service": "site-publisher",
  "version": "1.0.0",
  "timestamp": "2025-10-10T14:30:00Z"
}
```

### GET /metrics
Build metrics and statistics.

**Response**: 200 OK
```json
{
  "total_builds": 42,
  "successful_builds": 40,
  "failed_builds": 2,
  "last_build_time": "2025-10-10T14:00:00Z",
  "last_build_duration": 45.2,
  "uptime_seconds": 86400
}
```

### POST /publish
Manually trigger site build and deployment.

**Request**:
```json
{
  "trigger_source": "manual",
  "force_rebuild": false
}
```

**Response**: 200 OK
```json
{
  "status": "completed",
  "message": "Site published",
  "files_uploaded": 156,
  "duration_seconds": 45.2,
  "errors": []
}
```

### GET /status
Current build status.

**Response**: 200 OK
```json
{
  "status": "ready",
  "last_build": "2025-10-10T14:00:00Z",
  "builds_today": 3
}
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AZURE_STORAGE_ACCOUNT_NAME` | Yes | - | Azure Storage account name |
| `MARKDOWN_CONTAINER` | No | `markdown-content` | Container with markdown files |
| `OUTPUT_CONTAINER` | No | `$web` | Container for static website |
| `BACKUP_CONTAINER` | No | `$web-backup` | Container for backups |
| `QUEUE_NAME` | No | `site-publishing-requests` | Queue name for triggers |
| `HUGO_VERSION` | No | `0.138.0` | Hugo version (pinned) |
| `HUGO_THEME` | No | `PaperMod` | Hugo theme name |
| `HUGO_BASE_URL` | No | - | Base URL for static site |
| `LOG_LEVEL` | No | `INFO` | Logging level |

## Development

### Local Setup

```bash
# Create virtual environment
python3.13 -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export AZURE_STORAGE_ACCOUNT_NAME=teststorage
export HUGO_BASE_URL=https://test.example.com

# Run tests
pytest tests/ -v

# Run locally
uvicorn app:app --reload --port 8000
```

### Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Run specific test file
pytest tests/test_security.py -v

# Run with markers
pytest tests/ -m "not integration" -v
```

### Docker Build

```bash
# Build container
docker build -t site-publisher:latest .

# Run container
docker run -p 8000:8000 \
  -e AZURE_STORAGE_ACCOUNT_NAME=teststorage \
  -e HUGO_BASE_URL=https://test.example.com \
  site-publisher:latest

# Test health endpoint
curl http://localhost:8000/health
```

## Security Features

### Input Validation
- ✅ Blob name validation (path traversal prevention)
- ✅ Path validation (ensure files stay in allowed directories)
- ✅ File size limits (DOS prevention)
- ✅ File count limits (DOS prevention)

### Command Execution
- ✅ No `shell=True` (prevents command injection)
- ✅ Explicit subprocess arguments
- ✅ Hugo version pinned (no 'latest')

### Error Handling
- ✅ UUID correlation IDs for error tracking
- ✅ Automatic sensitive data sanitization
- ✅ OWASP-compliant (CWE-209, CWE-754, CWE-532)
- ✅ Stack traces only for critical errors

### Logging
- ✅ Structured JSON format
- ✅ Sensitive data filtering
- ✅ No file paths in logs
- ✅ Application Insights integration

## Implementation Status

### Phase 1: Container Structure ✅ COMPLETE
- [x] File structure created
- [x] FastAPI application (`app.py`)
- [x] Configuration (`config.py`)
- [x] Models (`models.py`)
- [x] Security functions (`security.py`)
- [x] Error handling (`error_handling.py`)
- [x] Logging configuration (`logging_config.py`)
- [x] Hugo configuration (`hugo-config/config.toml`)
- [x] Dockerfile (multi-stage with Hugo)
- [x] Requirements.txt
- [x] Basic tests (`tests/test_security.py`)

### Phase 2: Core Functions (Next)
- [ ] Implement `download_markdown_files()`
- [ ] Implement `build_site_with_hugo()`
- [ ] Implement `deploy_to_web_container()`
- [ ] Complete `build_and_deploy_site()` composition

### Phase 3: Testing
- [ ] Unit tests for all functions
- [ ] Integration tests with real Hugo
- [ ] Security tests (path traversal, command injection)
- [ ] Coverage > 80%

### Phase 4: Deployment
- [ ] Terraform infrastructure
- [ ] KEDA queue scaler
- [ ] CI/CD pipeline integration
- [ ] Production deployment

## Hugo Configuration

Using **PaperMod** theme:
- Clean, minimal design
- Built-in search
- SEO-optimized
- Dark mode support
- RSS feed generation

Configuration: `hugo-config/config.toml`

## Project Structure

```
site-publisher/
├── app.py                    # FastAPI REST API
├── config.py                 # Pydantic settings
├── models.py                 # Data models
├── security.py               # Security validation
├── site_builder.py           # Pure functions for building
├── error_handling.py         # Error handling wrapper
├── logging_config.py         # Logging configuration
├── hugo-config/
│   └── config.toml          # Hugo configuration
├── requirements.txt
├── Dockerfile               # Multi-stage build
└── tests/
    ├── conftest.py          # Test fixtures
    └── test_security.py     # Security tests
```

## References

- [Hugo Documentation](https://gohugo.io/documentation/)
- [Hugo PaperMod Theme](https://github.com/adityatelange/hugo-PaperMod)
- [Design Document](../../docs/SITE_PUBLISHER_DESIGN.md)
- [Security Implementation](../../docs/SITE_PUBLISHER_SECURITY_IMPLEMENTATION.md)
- [Python Version Strategy](../../docs/PYTHON_VERSION_STRATEGY.md)

---

**Status**: Phase 1 Complete ✅  
**Next**: Phase 2 - Implement core site building functions
