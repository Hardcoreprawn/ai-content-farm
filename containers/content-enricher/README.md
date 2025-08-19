# Content Enricher Container

A containerized microservice that enriches processed content with sentiment analysis, topic classification, summarization, and trend scoring for the AI Content Farm pipeline.

## 🎯 Current Status (Phase 2C Complete)

**✅ Fully Integrated with Processor → Enricher Pipeline**
- Reads from `PROCESSED_CONTENT` container (content-processor output)
- Enriches content with sentiment analysis, topic classification, and summarization
- Writes to `ENRICHED_CONTENT` container for downstream services
- Supports batch enrichment and individual content processing
- Complete test coverage: **33/33 tests passing + Phase 2C integration tests**

## 🏗️ Architecture

### Service Integration
- **ContentEnricherService**: Central business logic with blob storage integration
- **Pipeline API**: RESTful endpoints for enrichment workflow integration
- **Shared Libraries**: Uses common blob storage abstraction (`../../libs`)
- **Azurite Integration**: Local development with Azure Blob Storage simulation

### Enrichment Capabilities
- **Sentiment Analysis**: Rule-based sentiment detection (positive/negative/neutral)
- **Topic Classification**: Keyword-based topic categorization
- **Content Summarization**: Automated summary generation
- **Trend Scoring**: Time-decay weighted trend calculation
- **Batch Operations**: Processes multiple content items efficiently

## 📡 API Endpoints

### Health & Status
```bash
GET /health                 # Service health check
GET /status                 # Pipeline status with enrichment statistics
```

### Pipeline Enrichment
```bash
POST /enrich/processed      # Enrich individual processed content
POST /enrich/batch         # Enrich unenriched processed content (limit: 5)
```

### Legacy Enrichment (Maintained)
```bash
POST /enrich               # Direct content enrichment
```

## 🚀 Quick Start

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt
pip install -e ../../libs  # Shared blob storage libs

# Start Azurite (in separate terminal)
# (Already running in dev container)

# Start server
python main.py
```

### Test Pipeline
```bash
# Test individual processed content enrichment
curl -X POST http://localhost:8001/enrich/processed \
  -H "Content-Type: application/json" \
  -d @sample_processed.json

# Test batch enrichment
curl -X POST http://localhost:8001/enrich/batch

# Check pipeline status
curl http://localhost:8001/status
```

## 🧪 Testing

```bash
# All tests (33/33 passing + Phase 2C integration tests)
python -m pytest

# Phase 2C integration tests
python -m pytest tests/test_phase2c_integration.py -v

# Legacy API tests
python -m pytest tests/test_main.py

# Core enrichment logic
python -m pytest tests/test_enricher.py
```

## 📊 Pipeline Data Flow

```
Content Processor
      ↓
PROCESSED_CONTENT container
      ↓
Content Enricher (finds unenriched)
      ↓
ContentEnricherService.enrich_processed_content()
      ↓
ENRICHED_CONTENT container
      ↓
[Ready for Content Ranker - Phase 2D]
```

## 🔧 Configuration

### Environment Variables
- `ENVIRONMENT`: `local` (default) or `production`
- `AZURE_STORAGE_CONNECTION_STRING`: For production blob storage
- Local development uses Azurite on port 10000

### Dependencies
- **FastAPI**: Web framework (port 8001)
- **Shared Libs**: Blob storage abstraction
- **Azurite**: Local Azure Storage emulation
- **Pytest**: Testing framework

## 📈 Enrichment Features

### Sentiment Analysis
- **Positive Detection**: "amazing", "fantastic", "incredible", "great"
- **Negative Detection**: "terrible", "awful", "disaster", "worse"
- **Confidence Scoring**: 0.0 to 1.0 confidence levels
- **Multi-text Analysis**: Combines title and content

### Topic Classification
- **Technology Topics**: AI, ML, programming, tech trends
- **Science Topics**: Research, climate, discoveries
- **General Classification**: Fallback categorization
- **Multi-topic Support**: Primary topic + topic list

### Content Summarization
- **Automatic Truncation**: Configurable summary length
- **Word Count Tracking**: Original content metrics
- **Quality Preservation**: Maintains key information

### Trend Scoring
- **Time Decay**: Recent content scores higher
- **Engagement Weighting**: Combines normalized scores
- **Predictive Scoring**: Future trend prediction

## 🔄 Integration Points

### Upstream
- **Content Processor**: Receives processed content via blob storage

### Downstream (Ready for Phase 2D)
- **Content Ranker**: Will consume enriched content
- **Markdown Generator**: Future integration point

## 📋 Files Overview

### Core Files
- `main.py`: FastAPI application with pipeline endpoints
- `service_logic.py`: ContentEnricherService business logic
- `enricher.py`: Content enrichment orchestrator
- `sentiment_analyzer.py`: Sentiment analysis module
- `topic_classifier.py`: Topic classification module
- `content_summarizer.py`: Content summarization module
- `trend_calculator.py`: Trend scoring module

### Testing
- `tests/test_phase2c_integration.py`: Phase 2C pipeline tests
- `tests/test_main.py`: API endpoint tests
- `tests/test_enricher.py`: Business logic tests

### Configuration
- `config.py`: Environment configuration
- `conftest.py`: Test configuration with Azurite

---

**Ready for Phase 2D: Content Ranker Integration** 🚀
