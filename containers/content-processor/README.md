# Content Processor Container

A containerized microservice that processes collected content and transforms it into structured, analyzed data for the AI Content Farm pipeline.

## 🎯 Current Status (Phase 2B Complete)

**✅ Fully Integrated with Blob Storage Pipeline**
- Reads from `COLLECTED_CONTENT` container (content-collector output)
- Processes Reddit posts with engagement scoring and content classification
- Writes to `PROCESSED_CONTENT` container for downstream services
- Supports batch processing and individual collection processing
- Complete test coverage: **48/48 tests passing**

## 🏗️ Architecture

### Service Integration
- **ContentProcessorService**: Central business logic with blob storage integration
- **Pipeline API**: RESTful endpoints for processing workflow integration
- **Shared Libraries**: Uses common blob storage abstraction (`../../libs`)
- **Azurite Integration**: Local development with Azure Blob Storage simulation

### Processing Capabilities
- **Reddit Content**: Advanced processing with engagement scoring, content type detection
- **Generic Content**: Fallback processing for non-Reddit sources
- **Batch Operations**: Processes multiple collections efficiently
- **Duplicate Prevention**: Tracks processed collections to avoid reprocessing

## 📡 API Endpoints

### Health & Status
```bash
GET /health         # Service health check
GET /status         # Pipeline status with processing statistics
```

### Pipeline Processing
```bash
POST /process/collection    # Process individual collection
POST /process/batch        # Process unprocessed collections (limit: 5)
```

### Legacy Processing (Maintained)
```bash
POST /process              # Direct Reddit data processing
```

## 🚀 Quick Start

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt
pip install -e ../../libs  # Shared blob storage libs

# Start Azurite (in separate terminal)
# (Already running in dev container)

# Run tests
python -m pytest

# Start server
python main.py
```

### Test Pipeline
```bash
# Test individual collection processing
curl -X POST http://localhost:8000/process/collection \
  -H "Content-Type: application/json" \
  -d @sample_collection.json

# Test batch processing
curl -X POST http://localhost:8000/process/batch

# Check pipeline status
curl http://localhost:8000/status
```

## 🧪 Testing

```bash
# All tests (48/48 passing)
python -m pytest

# Phase 2B integration tests
python -m pytest tests/test_phase2b_integration.py -v

# Legacy API tests
python -m pytest tests/test_main.py

# Core processing logic
python -m pytest tests/test_processor.py
```

## 📊 Pipeline Data Flow

```
Content Collector
      ↓
COLLECTED_CONTENT container
      ↓
Content Processor (finds unprocessed)
      ↓
ContentProcessorService.process_collected_content()
      ↓
PROCESSED_CONTENT container
      ↓
[Ready for Content Enricher - Phase 2C]
```

## 🔧 Configuration

### Environment Variables
- `ENVIRONMENT`: `local` (default) or `production`
- `AZURE_STORAGE_CONNECTION_STRING`: For production blob storage
- Local development uses Azurite on port 10000

### Dependencies
- **FastAPI**: Web framework
- **Shared Libs**: Blob storage abstraction
- **Azurite**: Local Azure Storage emulation
- **Pytest**: Testing framework

## � Performance & Reliability

- **Processing Speed**: Handles large batches efficiently
- **Error Resilience**: Graceful handling of malformed data
- **Resource Management**: Configurable batch limits
- **Monitoring**: Real-time statistics tracking

## � Integration Points

### Upstream
- **Content Collector**: Receives collections via blob storage

### Downstream (Ready for Phase 2C)
- **Content Enricher**: Will consume processed content
- **Content Ranker**: Future integration point

## � Files Overview

### Core Files
- `main.py`: FastAPI application with pipeline endpoints
- `service_logic.py`: ContentProcessorService business logic
- `processor.py`: Reddit content processing functions
- `config.py`: Environment configuration

### Testing
- `tests/test_phase2b_integration.py`: Phase 2B pipeline tests
- `tests/test_main.py`: API endpoint tests
- `tests/test_processor.py`: Business logic tests
- `tests/test_integration.py`: Infrastructure integration tests

### Documentation
- `PHASE_2B_COMPLETION_SUMMARY.md`: Detailed Phase 2B completion report

---

**Ready for Phase 2C: Content Enricher Integration** 🚀
