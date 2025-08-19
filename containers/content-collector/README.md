# Content Collector

Content collection service for the AI Content Farm pipeline.

## Overview

The Content Collector is the entry point of the AI Content Farm pipeline. It fetches, normalizes, filters, and deduplicates content from various sources (primarily Reddit) and stores it in blob storage for downstream processing.

## Key Features

- **Multi-source Content Collection**: Reddit API support with extensible architecture
- **Content Normalization**: Standardizes content format across different sources  
- **Filtering & Deduplication**: Quality criteria filtering and similarity-based deduplication
- **Blob Storage Integration**: Uses shared blob storage library with standardized containers
- **Pipeline Ready**: Event-driven architecture for automated pipeline workflows

## API Endpoints

- `GET /` - Service information
- `GET /health` - Health check
- `GET /status` - Service status and statistics  
- `POST /collect` - Collect content from sources
- `GET /sources` - Available content sources

## File Structure

- `main.py` - FastAPI application and endpoints
- `service_logic.py` - Business logic and blob storage integration
- `collector.py` - Core content collection functions
- `source_collectors.py` - Modular source collectors (Reddit, RSS, etc.)
- `transforms.py` - Content normalization and filtering
- `models.py` - Pydantic request/response models
- `config.py` - Configuration and environment settings
- `keyvault_client.py` - Azure Key Vault integration
- `tests/` - Unit and integration tests

## Testing

```bash
# Run all tests
python -m pytest

# Run specific test suites
python -m pytest tests/test_main.py        # API tests
python -m pytest tests/test_collector.py   # Business logic tests  
python -m pytest tests/test_phase2a_integration.py  # Integration tests
```

## Status

✅ **Phase 2A Complete** - Standardized for pipeline integration
- 49/49 tests passing
- Blob storage standardization complete
- Pipeline-ready architecture implemented
