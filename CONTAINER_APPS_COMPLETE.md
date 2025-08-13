# AI Content Farm - Container Apps Pipeline

## 🎉 COMPLETED IMPLEMENTATION

This repository contains a **fully functional** AI-powered content processing pipeline built with Container Apps architecture. All services have been implemented, tested, and verified working.

## 🏗️ Architecture Overview

```
Content Sources → Content Processor → Content Ranker → Content Enricher → SSG → Published Sites
                       ↓                    ↓              ↓           ↓
                   Hot Topics         Ranked Topics   Enhanced Content  Static Sites
                                          ↑              ↑           ↑
                              Scheduler ←─────────────────────────────┘
                             (Orchestrates the entire pipeline)
```

## 🚀 Services Implemented

### ✅ Content Processor (Port 8000)
- **Purpose**: Collect content from multiple sources (Reddit, RSS, APIs)
- **Features**: Pluggable collectors, async job processing, rate limiting
- **API**: `/api/summary-womble/process`, `/api/summary-womble/status`

### ✅ Content Ranker (Port 8001)  
- **Purpose**: Score and rank content based on engagement, recency, quality
- **Features**: Multi-factor scoring algorithms, configurable weights
- **API**: `/api/content-ranker/process`, `/api/content-ranker/status`

### ✅ Content Enricher (Port 8002)
- **Purpose**: AI-powered content enhancement with summaries and metadata
- **Features**: 
  - AI-generated summaries
  - Sentiment analysis (positive/negative/neutral)
  - Content categorization (Technology, Business, Science, etc.)
  - Key phrase extraction
  - Quality scoring and reading time calculation
- **API**: `/api/content-enricher/process`, `/api/content-enricher/status`

### ✅ Scheduler (Port 8003)
- **Purpose**: Workflow orchestration and multi-step pipeline management
- **Features**:
  - Hot-topics workflow (complete pipeline)
  - Individual workflow components
  - Service-to-service communication
  - Job tracking and status monitoring
- **API**: `/api/scheduler/workflows`, `/api/scheduler/hot-topics`

### ✅ SSG - Static Site Generator (Port 8004)
- **Purpose**: Generate static websites from processed content
- **Features**:
  - Markdown file generation
  - Category pages and site indexes
  - Azure blob storage integration
  - Multiple output formats
- **API**: `/api/ssg/generate`, `/api/ssg/status/{id}`

## 🔧 Local Development

### Quick Start

```bash
# 1. Clone the repository
git clone <repository-url>
cd ai-content-farm

# 2. Start all services
./scripts/start-all-services.sh

# 3. Verify all services are healthy
python test_pipeline.py

# 4. Access API documentation
open http://localhost:8000/docs  # Content Processor
open http://localhost:8001/docs  # Content Ranker
open http://localhost:8002/docs  # Content Enricher  
open http://localhost:8003/docs  # Scheduler
open http://localhost:8004/docs  # SSG
```

### Service Health Checks

```bash
# Check individual service health
curl http://localhost:8000/health  # Content Processor
curl http://localhost:8001/health  # Content Ranker
curl http://localhost:8002/health  # Content Enricher
curl http://localhost:8003/health  # Scheduler
curl http://localhost:8004/health  # SSG
```

## 🧪 Testing

### Integration Test Suite

The repository includes a comprehensive integration test that validates:
- ✅ All services start successfully
- ✅ Health endpoints respond correctly
- ✅ Content enrichment pipeline processes topics end-to-end
- ✅ AI features work (summarization, categorization, sentiment analysis)
- ✅ Workflow orchestration functions properly

```bash
# Run integration tests
python test_pipeline.py
```

### Example API Usage

#### 1. Content Enrichment
```bash
curl -X POST http://localhost:8002/api/content-enricher/process \
  -H "Content-Type: application/json" \
  -d '{
    "source": "reddit",
    "topics": [
      {
        "title": "AI Breakthrough in Natural Language Processing",
        "content": "Researchers have developed a revolutionary new model...",
        "score": 1500,
        "num_comments": 250
      }
    ]
  }'
```

#### 2. Hot Topics Workflow
```bash
curl -X POST http://localhost:8003/api/scheduler/hot-topics \
  -d "targets=technology&targets=programming&limit=10&enable_enrichment=true"
```

#### 3. Static Site Generation
```bash
curl -X POST http://localhost:8004/api/ssg/generate \
  -H "Content-Type: application/json" \
  -d '{
    "config": {"site_title": "My Tech Blog"},
    "content_source": "enriched-content/latest"
  }'
```

## 🏭 Production Deployment

### Container Apps Ready
All services are configured for Azure Container Apps deployment with:
- ✅ Health checks configured
- ✅ Environment variables standardized  
- ✅ Resource requirements optimized
- ✅ Networking properly configured
- ✅ Auto-scaling policies defined

### Environment Variables
```bash
# Azure Storage (production)
AZURE_STORAGE_ACCOUNT_NAME=your-storage-account
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_TENANT_ID=your-tenant-id

# Reddit API (for content collection)
REDDIT_CLIENT_ID=your-reddit-client-id
REDDIT_CLIENT_SECRET=your-reddit-client-secret  
REDDIT_USER_AGENT=your-user-agent
```

## 📚 Documentation

### API Documentation
Each service provides OpenAPI documentation:
- Content Processor: http://localhost:8000/docs
- Content Ranker: http://localhost:8001/docs
- Content Enricher: http://localhost:8002/docs
- Scheduler: http://localhost:8003/docs
- SSG: http://localhost:8004/docs

### Architecture Documentation
- [Container Migration Plan](docs/container-migration-plan.md) - Complete migration details
- [API Contracts](docs/api-contracts.md) - Service interface specifications
- [Development Guide](docs/development-guide.md) - Local development setup

## 🎯 Key Features Implemented

### ✅ Pure Functions Architecture
- Business logic separated from HTTP/storage concerns
- Testable and reusable functions
- Thread-safe stateless processing

### ✅ Contract-First APIs  
- REST-first design with consistent responses
- OpenAPI documentation auto-generated
- Standardized health checks and status tracking

### ✅ Local Development First
- Complete Docker Compose environment
- Hot reload for rapid iteration
- Mock services (Azurite) for offline development

### ✅ AI-Powered Content Enhancement
- Intelligent content summarization
- Sentiment analysis with configurable thresholds
- Automatic categorization based on content analysis
- Quality scoring using multiple factors
- Key phrase extraction for SEO optimization

### ✅ Workflow Orchestration
- Multi-step pipeline management
- Service-to-service communication
- Job tracking with status monitoring
- Configurable workflow definitions

## 📊 Success Metrics

- **Services Implemented**: 5/5 ✅
- **APIs Documented**: 5/5 ✅  
- **Integration Tests**: Passing ✅
- **Local Development**: Fully Functional ✅
- **Production Ready**: Yes ✅

## 🚦 Next Steps

The Container Apps pipeline is **complete and ready for use**. You can:

1. **Deploy to Production**: Use the provided Docker configurations for Azure Container Apps
2. **Extend Content Sources**: Add new collectors for different content platforms
3. **Enhance AI Features**: Integrate additional AI services for content analysis
4. **Scale Services**: Configure auto-scaling based on workload demands
5. **Monitor Performance**: Add observability and logging for production monitoring

---

**🎉 Container Apps Migration: COMPLETED SUCCESSFULLY**