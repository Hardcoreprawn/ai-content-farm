# Content Womble

A humble content collection service for the AI Content Farm pipeline.

## Overview

The Content Womble is the entry point of the AI Content Farm pipeline. This charming service diligently collects, analyzes, and organizes content from various sources (primarily Reddit) following proper FastAPI patterns and standardized response formats.

<!-- Updated: 2025-09-17 - Pipeline deployment verification -->

## Key Features

- **Standardized API**: FastAPI-native with consistent StandardResponse format
- **Multi-source Content Collection**: Reddit API support with extensible collector architecture
- **Content Discovery**: Trending topic analysis and research recommendations
- **Clean Architecture**: Modular design following 300-line file guidelines
- **Comprehensive Testing**: 10/10 test coverage with proper mocking
- **Azure Integration**: Blob storage and Key Vault integration

## API Endpoints

### Standardized Endpoints
- `GET /api/content-womble/health` - Health check with dependency status
- `GET /api/content-womble/status` - Detailed service status 
- `POST /api/content-womble/process` - Process content from sources
- `GET /api/content-womble/docs` - API documentation

### Legacy Endpoints (for compatibility)
- `GET /` - Service information
- `GET /health` - Basic health check
- `POST /discover` - Topic discovery and analysis
- `POST /collect` - Legacy collection endpoint
- `GET /sources` - Available content sources

## File Structure

### Core Application
- `main.py` (197 lines) - FastAPI application setup and routing
- `endpoints.py` (353 lines) - API route handlers and business logic
- `models.py` (104 lines) - Pydantic request/response models

### Specialized Modules  
- `source_collectors.py` (36 lines) - Collector factory
- `reddit_client.py` (204 lines) - Reddit API client with Azure Key Vault
- `discovery.py` (215 lines) - Content analysis and trending topic detection
- `service_logic.py` - Core business logic (retained)
- `keyvault_client.py` - Azure Key Vault integration (retained)

### Collector Framework
- `collectors/base.py` (90 lines) - Abstract base classes and mixins
- `collectors/reddit.py` (274 lines) - Reddit collectors (public API & PRAW)
- `collectors/web.py` (184 lines) - Web content and RSS collectors

### Testing
- `tests/conftest.py` - Test configuration with proper mocking
- `tests/test_standardized_api.py` - Comprehensive API tests (10/10 passing)

## Testing

```bash
# Run all tests
PYTHONPATH=/workspaces/ai-content-farm python -m pytest

# Run specific test suite
PYTHONPATH=/workspaces/ai-content-farm python -m pytest tests/test_standardized_api.py -v

# Run with coverage
PYTHONPATH=/workspaces/ai-content-farm python -m pytest tests/ --cov=.
```

## Development

The Content Womble follows clean architecture principles:
- **Single Responsibility**: Each file has a focused purpose
- **Dependency Injection**: Proper FastAPI dependency patterns
- **Testable**: Comprehensive mocking and isolated unit tests
- **Modular**: Easy to extend with new content sources
- **Standardized**: Consistent API response formats

## Status

✅ **Production Ready** - Fully refactored, tested, and compliant with coding guidelines

✅ **Phase 2A Complete** - Standardized for pipeline integration
- 49/49 tests passing
- Blob storage standardization complete
- Pipeline-ready architecture implemented
