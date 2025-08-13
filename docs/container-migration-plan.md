# Container Apps Migration Plan

**Created:** August 13, 2025  
**Author:** GitHub Copilot  

## Overview

Migrating from Azure Functions to Container Apps architecture based on successful SummaryWomble pattern. This migration addresses reliability issues, improves local development, and enables complex multi-step workflows.

## Architecture Principles

### Contract-First APIs
- **REST-first design**: All services exposed as HTTP endpoints
- **OpenAPI documentation**: Auto-generated API docs at `/docs`
- **Consistent response format**: Standardized JSON responses
- **Health checks**: `/health` endpoint for each service
- **Status tracking**: Job-based processing with status endpoints

### Local Development First
- **Docker Compose**: Complete local environment
- **Mock services**: Local blob storage emulation (Azurite)
- **Environment parity**: Same container images locally and in production
- **Fast iteration**: Hot reload during development

### Pure Functions Architecture
- **Testable**: Business logic separated from HTTP/storage concerns
- **Thread-safe**: Stateless functions for concurrent processing
- **Pluggable**: Interface-based collectors and processors
- **Reusable**: Functions can be composed into different workflows

## Current State Analysis

### ✅ Completed: SummaryWomble
- Container Apps implementation with FastAPI
- Azure Key Vault integration (environment fallback)
- Pure functions content collection model
- Local Docker development environment
- Real Reddit API integration working

### 🔄 Functions to Migrate

#### 1. ContentRanker
**Purpose**: Score and rank collected content based on engagement metrics
**Current**: Blob trigger Azure Function
**New Architecture**: HTTP API with job processing
- `POST /api/content-ranker/process` - Trigger ranking job
- `POST /api/content-ranker/status` - Check job status
- `GET /api/content-ranker/health` - Health check

#### 2. ContentEnricher
**Purpose**: Enhance content with AI-generated summaries and metadata
**Current**: Blob trigger Azure Function  
**New Architecture**: HTTP API with AI integration
- `POST /api/content-enricher/process` - Trigger enrichment job
- `POST /api/content-enricher/status` - Check job status
- `GET /api/content-enricher/health` - Health check

#### 3. GetHotTopics
**Purpose**: Scheduler and orchestrator for content collection
**Current**: Timer trigger Azure Function
**New Architecture**: HTTP API + Scheduler service
- `POST /api/scheduler/hot-topics` - Trigger hot topics collection
- `GET /api/scheduler/status` - View all active jobs
- `GET /api/scheduler/health` - Health check

#### 4. TopicRankingScheduler
**Purpose**: Orchestrate the ranking pipeline
**Current**: Timer trigger Azure Function
**New Architecture**: HTTP API + Workflow orchestration
- `POST /api/scheduler/topic-ranking` - Trigger ranking workflow
- `GET /api/scheduler/workflows` - View workflow status
- `GET /api/scheduler/health` - Health check

#### 5. ContentEnrichmentScheduler
**Purpose**: Orchestrate the enrichment pipeline
**Current**: Timer trigger Azure Function
**New Architecture**: HTTP API + Workflow orchestration
- `POST /api/scheduler/content-enrichment` - Trigger enrichment workflow
- `GET /api/scheduler/workflows/{id}` - View specific workflow
- `GET /api/scheduler/health` - Health check

## Container Services Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Load Balancer / Ingress                     │
└─────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
┌───────▼─────────┐    ┌────────▼────────┐    ┌────────▼────────┐
│   API Gateway   │    │   Scheduler     │    │  CMS Publisher  │
│   Service       │    │   Service       │    │   Service       │
│                 │    │                 │    │                 │
│ - Route APIs    │    │ - Orchestrate   │    │ - Output MD     │
│ - Auth/Cors     │    │ - Timers        │    │ - Headless CMS  │
│ - Rate Limit    │    │ - Job Queue     │    │ - Static Sites  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
┌───────▼─────────┐    ┌────────▼────────┐    ┌────────▼────────┐
│ Content         │    │  Content        │    │  Content        │
│ Collector       │    │  Ranker         │    │  Enricher       │
│                 │    │                 │    │                 │
│ - Reddit API    │    │ - Score Posts   │    │ - AI Summaries  │
│ - LinkedIn API  │    │ - Rank Topics   │    │ - Metadata      │
│ - ArsTechnica   │    │ - Filter        │    │ - Categorize    │
│ - NewStack      │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                        ┌───────▼───────┐
                        │   Storage     │
                        │   Service     │
                        │               │
                        │ - Blob Store  │
                        │ - Metadata DB │
                        │ - Cache Layer │
                        └───────────────┘
```

## Implementation Phases

### Phase 1: Core Services (Parallel - 3 days)
**Goal**: Migrate core content processing functions

#### 1a. ContentRanker Service
- Extract ranking logic from Azure Function
- Create FastAPI service with job processing
- Implement pure functions for scoring algorithms
- Add comprehensive tests

#### 1b. ContentEnricher Service  
- Extract enrichment logic from Azure Function
- Create FastAPI service with AI integration
- Implement pure functions for content enhancement
- Add mock AI services for local development

#### 1c. Storage Service Foundation
- Implement blob storage abstraction
- Create Azurite integration for local development
- Define storage contracts and interfaces

### Phase 2: Orchestration & Scheduling (Parallel - 2 days)
**Goal**: Replace timer-based functions with HTTP orchestration

#### 2a. Scheduler Service
- Implement workflow orchestration
- Create timer-based job scheduling
- Add job queue and status tracking
- Integrate with existing services

#### 2b. API Gateway Service
- Implement request routing
- Add authentication and CORS
- Create unified API documentation
- Add rate limiting and monitoring

### Phase 3: Multi-Source Collection (Parallel - 4 days)
**Goal**: Expand beyond Reddit to multiple content sources

#### 3a. LinkedIn Collector
- Research LinkedIn API requirements
- Implement collector following Reddit pattern
- Add authentication and rate limiting

#### 3b. ArsTechnica/NewStack Collectors
- Implement RSS/web scraping collectors
- Add content parsing and normalization
- Create rate limiting and caching

#### 3c. Collector Registry
- Implement pluggable collector system
- Add dynamic collector discovery
- Create collector configuration management

### Phase 4: CMS Integration (Series - 3 days)
**Goal**: Output processed content to headless CMS

#### 4a. CMS Publisher Service
- Research headless CMS options (Strapi, Contentful, etc.)
- Implement markdown generation from processed content
- Create publishing workflows

#### 4b. Static Site Integration
- Integrate with existing site generator
- Create automated content publishing pipeline
- Add content versioning and rollback

### Phase 5: Testing & Documentation (Parallel - 2 days)
**Goal**: Comprehensive testing and documentation updates

#### 5a. Integration Testing
- Create end-to-end test suites
- Add load testing for all services
- Implement monitoring and alerting

#### 5b. Documentation Updates
- Update all API documentation
- Create deployment guides
- Archive old Azure Functions documentation

## Parallel Work Strategy

### 🔧 Background/Automated Tasks
1. **Documentation Generation**: Auto-generate API docs as services are built
2. **Container Build Pipeline**: Set up automated Docker builds
3. **Infrastructure Preparation**: Terraform modules for Container Apps
4. **Monitoring Setup**: Application Insights integration

### 👥 Human Tasks (Can be parallelized)
1. **Core Service Development**: Different team members on different services
2. **Collector Implementation**: Independent collector development
3. **Testing**: Parallel test development with service implementation
4. **CMS Research**: Evaluate headless CMS options while services are being built

## Local Development Environment

### Docker Compose Services
```yaml
services:
  # Core Services
  content-collector:     # SummaryWomble equivalent
  content-ranker:        # ContentRanker service
  content-enricher:      # ContentEnricher service
  scheduler:            # Orchestration service
  api-gateway:          # Routing and auth
  cms-publisher:        # Markdown output
  
  # Infrastructure
  azurite:              # Local blob storage
  redis:                # Job queue and caching
  postgres:             # Metadata and job storage
  
  # Monitoring
  jaeger:               # Distributed tracing
  prometheus:           # Metrics collection
```

### Development Workflow
1. **Start Environment**: `./scripts/start-dev-environment.sh`
2. **Run Service**: Individual service development with hot reload
3. **Test Integration**: End-to-end testing across all services
4. **Deploy Staging**: Container Apps deployment to Azure

## Documentation Updates Required

### 📝 New Documentation
- `container-apps-architecture.md` - Overall system design
- `api-reference.md` - Complete API documentation
- `local-development-guide.md` - Docker development setup
- `deployment-guide-containers.md` - Container Apps deployment
- `testing-guide-containers.md` - Service testing strategies

### 📋 Updates Required
- `system-design.md` - Update architecture diagrams
- `api-contracts.md` - Update to Container Apps APIs
- `development-standards.md` - Add container development standards
- `security-policy.md` - Update for container security

### 🗄️ Archive Required
- `azure-functions-*.md` - Move to `/docs/archived/`
- Function-specific documentation
- Old deployment guides

## Success Criteria

### ✅ Technical Goals
- [ ] All functions migrated to Container Apps
- [ ] Local development environment fully functional
- [ ] Multi-source content collection working
- [ ] Headless CMS integration complete
- [ ] 100% API test coverage
- [ ] Documentation fully updated

### ✅ Business Goals
- [ ] Improved reliability over Azure Functions
- [ ] Faster development iteration cycles
- [ ] Scalable multi-source content architecture
- [ ] Automated content publishing pipeline
- [ ] Reduced operational complexity

### ✅ Performance Goals
- [ ] <500ms API response times
- [ ] >99.9% uptime for core services
- [ ] Support for 10+ concurrent content collection jobs
- [ ] <5 minute end-to-end content processing time

## Risk Mitigation

### 🚨 Technical Risks
- **Container orchestration complexity**: Start simple, add complexity gradually
- **Service interdependencies**: Clear interface contracts and mocking
- **Local development parity**: Comprehensive Docker Compose setup
- **Data migration**: Careful blob storage migration strategy

### 🚨 Timeline Risks
- **Scope creep**: Stick to MVP for each service, iterate later
- **Testing overhead**: Parallel test development with implementation
- **Documentation lag**: Auto-generate where possible, update iteratively

## Next Steps

1. **Immediate**: Create ContentRanker service following SummaryWomble pattern
2. **Parallel**: Set up local development infrastructure (Azurite, Redis, etc.)
3. **Background**: Use GitHub Copilot coding agent for automated service scaffolding
4. **Planning**: Detailed API contracts for each service before implementation

---

*This migration represents a significant architectural improvement that will enable faster development, better reliability, and support for complex multi-source content workflows.*
