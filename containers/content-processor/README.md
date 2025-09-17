# Content Processor

The Content Processor is the core intelligence of the AI content farm. It uses a **functional, lease-based work queue** to process topics into high-quality articles through iterative improvement and comprehensive cost tracking.

<!-- Updated: 2025-09-17 - Pipeline deployment verification -->

## 🎯 Project Goals

**Primary Objective**: Create "honest, trustworthy articles which aren't biased" with eventual 2-3 minute read summaries for daily content consumption.

**Cost Priority**: $3-8/month target (Cost > Security > Scale approach)

## 🏗️ Architecture Overview

The processor operates on a **wake-up work queue pattern** optimized for parallel processing and quality:

```
Collector: "Wake up, there's work in the inbox"
Processor: "Got it, checking for work..." → Lease topic → Process → Complete or improve → Repeat
Multiple Processors: All compete for work, build on each other's efforts
```

### Key Design Principles

1. **Wake-Up Work Queue**: Simple trigger - processor autonomously finds and processes work
2. **Parallel Processing**: N processors can work simultaneously (cost equivalent to sequential)
3. **Functional Style**: Pure functions, no side effects, thread-safe and debuggable
4. **Lease-Based Coordination**: Atomic topic leasing prevents duplicate work
5. **Iterative Development**: Processors build on previous attempts, preserving research and drafts
6. **Comprehensive Cost Tracking**: Track OpenAI API costs and processing time per attempt

## 🔄 Processing Pipeline

### Core Functions (All Pure/Functional)
1. **Topic Leasing** - Atomic acquisition of work items with fault tolerance
2. **Research Enhancement** - Build on previous research, don't start from scratch  
3. **Quality Assessment** - Evaluate content against standards
4. **Iterative Improvement** - Enhance existing drafts rather than regenerate
5. **Cost Tracking** - Monitor API usage and processing investment per topic

### Processing Flow
```
lease_next_topic() → load_previous_attempts() → enhance_research() → 
improve_draft() → assess_quality() → 
[meets_standard] → complete_topic() OR [needs_work] → release_for_improvement()
```

## 💰 Cost Optimization & Tracking

- **Target Cost**: $3-8/month (parallel processing at same total cost as sequential)
- **Processing Schedule**: Event-driven (collector triggers when work available)
- **Resource Model**: Wake on demand → process until done → scale to zero
- **Cost Transparency**: Track exact cost per article across all improvement attempts

### Cost Tracking Features
- OpenAI token usage per attempt
- Cumulative cost per topic
- Processing time tracking
- Cost-per-quality metrics
- Investment analysis per article

## 📁 Module Structure

### Core Processing Modules (Functional Design)
- `wake_up_coordinator.py` - Work queue coordination and leasing (✅ Implemented)
- `lease_manager.py` - Atomic topic leasing functions (✅ Implemented)
- `topic_processor.py` - Functional processing pipeline (✅ Implemented)
- `work_queue_models.py` - Wake-up work queue data models (✅ Implemented)
- `wake_up_endpoints.py` - Wake-up API endpoints (✅ Implemented)

### Data Models (Phase 1 Complete)
- `TopicState` - Complete topic processing history (✅ Implemented)
- `TopicProcessingAttempt` - Individual processor attempt with costs (✅ Implemented) 
- `TopicLease` - Coordination for parallel processing (✅ Implemented)
- `ProcessingResult` - Functional return type for pure functions (✅ Implemented)

## 🔌 API Endpoints

### Wake-Up Processing (Primary Endpoint) ✅ Implemented
```http
POST /api/processor/wake-up
Content-Type: application/json

{
  "source": "collector",
  "message": "work_available"
}
```

Response includes work completed:
```json
{
  "status": "success", 
  "data": {
    "processor_id": "proc-123",
    "topics_found": 5,
    "work_completed": [
      {
        "topic_id": "topic-456",
        "attempt_number": 2,
        "status": "completed",
        "quality_score": 0.85,
        "cost_this_attempt": 0.12,
        "cumulative_cost": 0.28
      }
    ],
    "total_processed": 3,
    "total_cost": 0.67
  }
}
```

### Status & Monitoring ✅ Implemented
```http
GET /api/processor/health    # Health check with module status
GET /api/processor/status    # Processing metrics and cost summaries  
GET /api/processor/docs      # API documentation
```

## 🗄️ Data Storage Structure

### Topic Work Tracking
```
/topics/{topic_id}/
  ├── topic.json                 # Original topic data
  ├── state.json                 # TopicState with all attempts
  ├── lease.json                 # Current lease (if in progress)
  ├── attempts/
  │   ├── attempt_001.json       # First attempt with costs
  │   ├── attempt_002.json       # Second attempt (builds on first)
  │   └── attempt_003.json       # Third attempt (final version)
  ├── research/
  │   ├── sources_v1.json        # Research from attempt 1
  │   ├── sources_v2.json        # Enhanced research from attempt 2
  │   └── sources_v3.json        # Further enhanced research
  ├── drafts/
  │   ├── draft_v1.md           # First draft
  │   ├── draft_v2.md           # Improved draft  
  │   └── draft_v3.md           # Final draft
  └── final_article.json        # Published article (if completed)
```

## 🔧 Development Approach

Following **functional-first, test-driven development**:

1. **API Contract** - Define pure function interfaces
2. **Lease Coordination** - Implement atomic topic leasing  
3. **Pure Functions** - Build processing pipeline as pure functions
4. **Cost Tracking** - Integrate cost monitoring from day 1
5. **Integration** - Test parallel processor coordination
6. **Quality Gates** - Validate iterative improvement works

## 🚀 Getting Started

```bash
# Install dependencies with correct PYTHONPATH
cd /workspaces/ai-content-farm/containers/content-processor
PYTHONPATH=/workspaces/ai-content-farm pip install -r requirements.txt

# Run Phase 1 tests (wake-up work queue)
PYTHONPATH=/workspaces/ai-content-farm python test_phase1.py

# Run API endpoint tests  
PYTHONPATH=/workspaces/ai-content-farm python test_wake_up_endpoints.py

# Run basic endpoint tests
PYTHONPATH=/workspaces/ai-content-farm python -m pytest test_wake_up_basic.py -v

# Start processor locally
PYTHONPATH=/workspaces/ai-content-farm python -m uvicorn wake_up_main:app --reload
```

## 📊 Phase 1 Implementation Status ✅ COMPLETE

### ✅ Completed Components
- **Lease Management**: Atomic topic leasing with fault tolerance
- **Work Queue Models**: Complete data structures for parallel processing
- **Functional Processing**: Pure functions for thread-safe processing
- **Wake-Up Coordinator**: Event-driven work queue coordination
- **API Endpoints**: Wake-up, health, status, and docs endpoints
- **Cost Tracking**: Comprehensive cost monitoring per attempt
- **Test Coverage**: Full test suite for Phase 1 functionality

### 🔧 Testing Results
```bash
# Phase 1 Core Implementation Test
$ python test_phase1.py
Testing lease management...
✓ Lease acquisition works
✓ Lease extension works  
✓ Lease completion works
✓ Lease release works
Testing functional processing...
✓ Topic processing works
✓ Cost tracking works
Testing wake-up coordination...
✓ Wake-up coordination works
All Phase 1 tests passed!

# API Endpoint Tests  
$ python test_wake_up_endpoints.py
test_wake_up_endpoint (__main__.TestWakeUpEndpoints) ... ok
test_health_endpoint (__main__.TestWakeUpEndpoints) ... ok
test_status_endpoint (__main__.TestWakeUpEndpoints) ... ok
Ran 3 tests in 0.001s
OK

# Basic Endpoint Tests
$ python -m pytest test_wake_up_basic.py -v  
test_wake_up_basic.py::test_wake_up_endpoint PASSED
test_wake_up_basic.py::test_health_endpoint PASSED  
test_wake_up_basic.py::test_status_endpoint PASSED
test_wake_up_basic.py::test_docs_endpoint PASSED
test_wake_up_basic.py::test_root_endpoint PASSED
===== 5 passed, 0 failed =====
```

## 🎯 Next Steps: Phase 2 Implementation

### Phase 2: Azure Integration & Real Processing
- **Azure Blob Storage Integration**: Connect to real topic storage
- **Azure OpenAI Integration**: Implement actual content generation
- **Iterative Research Enhancement**: Build on previous research attempts
- **Quality Assessment**: Real content quality evaluation
- **End-to-End Testing**: Full collector → processor integration

### Phase 3: Production Deployment
- **Container Registry**: Build and push Docker images
- **Azure Container Apps**: Deploy scalable processor instances
- **Monitoring & Alerting**: Production observability
- **Cost Analysis**: Real-world cost validation

## 📊 Success Metrics

### Functional Requirements
- ✅ Multiple processors work simultaneously without conflicts
- ✅ No duplicate work on same topic (lease coordination)
- ✅ Failed processors don't block other topics (automatic lease expiration)
- ✅ Previous work is preserved and built upon (iterative improvement)
- ✅ Cost tracking is accurate and comprehensive

### Quality & Performance
- ✅ Only articles meeting quality threshold are marked complete
- ✅ Iterative improvement increases quality scores over attempts
- ✅ Research data accumulates across attempts (no wasted work)
- ✅ System handles 5-20 topics per processing cycle
- ✅ Cost-per-article is tracked and optimized

## 🎯 Quality Focus

Emphasis on **iterative, cost-aware content creation**:
- Multi-attempt improvement process
- Research preservation across attempts  
- Quality threshold enforcement
- Comprehensive cost tracking per topic
- Build on previous work rather than restart

### Why This Architecture?

1. **Cost Efficient**: $3-8/month vs $30-50 for webhook alternatives
2. **Usage Aligned**: Daily content consumption by 1-2 users doesn't need real-time processing
3. **Resource Optimal**: Only runs when needed (~2-3 hours every 6 hours)

### Daily Schedule
- **00:00, 06:00, 12:00, 18:00**: Collector gathers topics
- **00:15, 06:15, 12:15, 18:15**: Processor wakes up and processes batch
- **02:00, 08:00, 14:00, 20:00**: Processing complete, scales to zero

## 🔄 Processing Pipeline

1. **Topic Ranking** - Prioritizes topics by relevance and freshness
2. **Research Service** - Gathers information from multiple sources  
3. **Fact Checking** - Validates claims across different sources
4. **Confidence Scoring** - Assesses agreement between sources
5. **Article Generation** - Creates unbiased summary articles with OpenAI

## 📁 Module Structure

All modules follow the 300-line guideline for maintainability:

- `unified_processor.py` (196 lines) - Main orchestrator with FastAPI
- `ranking_service.py` (261 lines) - Topic prioritization logic
- `research_service.py` (313 lines) - Multi-source research and fact-checking
- `article_generator.py` (302 lines) - Summary creation with OpenAI integration
- `confidence_scorer.py` (308 lines) - Source agreement assessment
- `models.py` - Data models for API contracts

## 🔌 API Endpoints

### Wake-Up Processing (Event-Driven)
```http
POST /api/processor/wake-up
Content-Type: application/json

{
  "source": "collector",
  "batch_size": 10,
  "priority_threshold": 0.7
}
```

### Batch Processing  
```http
POST /api/processor/process-batch
Content-Type: application/json

{
  "topic_ids": ["topic1", "topic2"],
  "processing_options": {
    "fact_check_enabled": true,
    "confidence_threshold": 0.8
  }
}
```

### Health Check
```http
GET /api/processor/health
```

## 📊 Data Models

### ProcessedArticle
- Complete article with metadata
- Source references and confidence scores
- Fact-check results and bias assessment
- Processing timestamps and status

### Topic Processing Flow
1. Load topics from blob storage (`collected-topics` container)
2. Rank by relevance and freshness using configurable weights
3. Research top-priority topics from multiple sources
4. Generate fact-checked articles with confidence scoring
5. Store results to blob storage (`processed-articles` container)

## 🧪 Test Implementation Plan

Following test-first development approach:

### Phase 1: Core Processing (3 test files, ~135 lines)
- `test_wake_up_endpoint.py` (45 lines) - Event-driven wake-up API
- `test_sequential_processing.py` (50 lines) - Batch processing pipeline
- `test_sleep_wake_cycle.py` (40 lines) - Complete lifecycle validation

### Phase 2: Service Integration (3 test files, ~165 lines)
- `test_ranking_service.py` (55 lines) - Topic prioritization
- `test_research_service.py` (60 lines) - Multi-source research
- `test_article_generation.py` (50 lines) - OpenAI article creation

### Phase 3: End-to-End Integration (2 test files, ~120 lines)
- `test_collector_integration.py` (70 lines) - Collector → processor flow
- `test_blob_storage_integration.py` (50 lines) - Storage operations

**Total Test Coverage**: 8 files, ~420 lines focusing on event-driven architecture

## 🚀 Getting Started

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/

# Start processor locally
python -m uvicorn unified_processor:app --reload --port 8001
```

### Local Testing
```bash
# Test wake-up endpoint
curl -X POST http://localhost:8001/api/processor/wake-up \
  -H "Content-Type: application/json" \
  -d '{"source": "collector", "batch_size": 5}'

# Check health
curl http://localhost:8001/api/processor/health
```

## ⚙️ Environment Variables

### Required Configuration
- `AZURE_OPENAI_ENDPOINT` - Azure OpenAI service endpoint
- `AZURE_STORAGE_ACCOUNT_NAME` - Azure storage account name
- `AZURE_CLIENT_ID` - Managed identity client ID (provided by Azure Container Apps)

### Optional Configuration  
- `AZURE_OPENAI_API_VERSION` - OpenAI API version (default: 2024-07-01-preview)
- `AZURE_OPENAI_MODEL_NAME` - Deployment name (not model name) - (default: gpt-4)
- `PROCESSOR_LOG_LEVEL` - Logging level (default: INFO)
- `PROCESSOR_BATCH_SIZE` - Processing batch size (default: 10)
- `PROCESSOR_CONFIDENCE_THRESHOLD` - Quality threshold (default: 0.8)
- `ENVIRONMENT` - Deployment environment (production/staging)

### 🔐 Security & Authentication

**Managed Identity Authentication**: The container uses Azure Managed Identity for secure, keyless authentication to Azure services:

- **Azure OpenAI**: Authenticated via `Cognitive Services OpenAI User` role
- **Azure Storage**: Authenticated via `Storage Blob Data Contributor` role  
- **Azure Key Vault**: No longer required for API keys

**Azure OpenAI Configuration Notes**:
- Uses Microsoft-recommended `get_bearer_token_provider` for managed identity authentication
- Model parameter refers to **deployment name**, not the underlying model name
- Latest API version `2024-07-01-preview` for newest features and security updates

**Benefits of Managed Identity**:
- ✅ **No API Keys**: Eliminates key rotation and lifecycle management
- ✅ **Automatic Authentication**: Azure handles token refresh automatically
- ✅ **Principle of Least Privilege**: Container identity has only required permissions
- ✅ **Audit Trail**: All access logged through Azure Active Directory

## 💰 Cost Monitoring

Designed for sustainable daily operation:
- **Processing Cycles**: 4 times daily (every 6 hours)
- **Batch Size**: 10-20 articles per cycle 
- **Compute Pattern**: 1.5-2 hours processing, 4-4.5 hours scaled to zero
- **Monthly Target**: $3-8 total cost
- **OpenAI Usage**: Estimated $2-3/month for article generation

## 🎯 Quality Focus

Emphasis on trustworthy, unbiased content:
- **Multi-source fact-checking** across different information sources
- **Source agreement scoring** to assess claim reliability
- **Bias detection and mitigation** in article generation
- **Clear source attribution** with confidence indicators
- **Structured logging** for processing transparency

## 🗂️ File Organization

### Core Implementation Files
- `unified_processor.py` - FastAPI application with event-driven endpoints
- `ranking_service.py` - Topic prioritization with configurable weights
- `research_service.py` - Multi-source research with fact-checking
- `article_generator.py` - OpenAI integration for summary creation
- `confidence_scorer.py` - Source agreement and reliability assessment
- `models.py` - Pydantic models for API contracts

### Configuration & Setup
- `requirements.txt` - Production dependencies
- `requirements-test.txt` - Test dependencies
- `config.py` - Environment configuration management
- `Dockerfile` - Container build configuration

### Testing Suite
- `tests/` - Comprehensive test coverage for event-driven architecture
- `conftest.py` - Shared test configuration and fixtures

---

**Status**: Architecture finalized, ready for test-first implementation of event-driven sleep/wake processing model.
