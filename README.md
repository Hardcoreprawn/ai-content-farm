# AI Content Farm

**An intelligent content aggregation and curation platform** that collects trending topics from Reddit and transforms them into high-quality articles for personal reading and content marketing.

## 🎯 What This Does

**Current State (Working)**:
- ✅ **Collects content** from Reddit automatically every 6 hours
- ✅ **Ranks topics** by engagement and relevance 
- ✅ **Processes content** through AI pipeline
- ✅ **Deploys to Azure** with Container Apps (working but expensive)
- ✅ **Tests locally** with Docker Compose and blob storage emulation
- ✅ **Security scanning** passes all checks (Checkov, Trivy, Terrascan)

**Current Architecture**: 8 containers doing content processing pipeline
**Current Problem**: Over-engineered, expensive (~$77-110/month), confusing

## 🚀 Quick Start

### Test Locally
```bash
# Start the development stack
docker-compose up -d

# Test the pipeline works
make process-content

# Check status
curl http://localhost:8001/health  # Content services
```

### Deploy to Azure
```bash
# Deploy infrastructure and containers
make deploy-staging   # For testing
make deploy-production # For production (main branch only)
```

### Visit Your Website
- **Local**: http://localhost:8006 (static site generator)
- **Azure**: Check Container Apps in Azure portal for public URL

## 📋 What's Next - The Plan

We have a **good plan** to simplify and reduce costs. Here's what we're doing:

### Phase 1: API Standardization (2 weeks)
**Goal**: Make all containers use consistent FastAPI patterns and responses

- ✅ **Plan exists**: FastAPI-native approach in `docs/FASTAPI_NATIVE_MODERNIZATION_PLAN.md`
- 🚧 **Status**: Need to implement shared response models across containers
- 🎯 **Benefit**: Easier monitoring, debugging, and integration

### Phase 2: Container Reduction (2 weeks) 
**Goal**: Reduce from 8 containers down to 4 essential ones

- ✅ **Plan exists**: Container consolidation strategy in `docs/CONTAINER_APPS_COST_OPTIMIZATION.md`
- 🚧 **Status**: Need to merge similar functions and eliminate redundancy
- 🎯 **Benefit**: 40-50% cost reduction (~$40-62/month instead of $77-110)

### Phase 3: Remove Service Bus (1 week)
**Goal**: Replace complex event system with simple polling or HTTP calls

- ✅ **Plan exists**: Multiple options analyzed (webhooks, polling, orchestrator)
- 🚧 **Status**: Choose polling approach based on actual usage patterns
- 🎯 **Benefit**: Eliminate $10/month Service Bus cost, simplify architecture

## 🏗️ Current Architecture

**Working Pipeline**:
```
Reddit → Collector → Ranker → Enricher → Generator → Site → Website
```

**8 Current Containers** (too many):
1. `collector-scheduler` - Timer triggers
2. `content-collector` - Fetch Reddit data  
3. `content-processor` - Clean and format
4. `content-enricher` - Research and fact-check
5. `content-ranker` - Score and prioritize
6. `content-generator` - Write articles
7. `markdown-generator` - Convert to markdown
8. `site-generator` - Build static site

**Proposed 4 Containers** (simpler):
1. **Collector** - Fetch and clean data
2. **Processor** - Rank, enrich, generate content  
3. **Publisher** - Generate markdown and static site
4. **Scheduler** - Timer triggers and orchestration

## � Project Structure

```
├── README.md                 # This file - main overview
├── TODO.md                   # Simple task list (create this)
├── containers/               # 8 container services (current)
├── functions/               # Azure Functions (alternative approach)
├── infra/                   # Terraform infrastructure
├── docs/                    # Detailed documentation
├── scripts/                 # Utility scripts
└── docker-compose.yml       # Local development
```

## 🔧 Common Tasks

```bash
# Development
docker-compose up -d          # Start local stack
make test                     # Run tests
make security-scan           # Security validation

# Content Processing  
make collect-topics          # Fetch from Reddit
make process-content         # Full pipeline
make content-status          # Check pipeline status

# Deployment
make deploy-staging          # Deploy to test environment
make deploy-production       # Deploy to production
make cost-estimate           # Check Azure costs
```

## 📚 Documentation

**Main Documents**:
- `TODO.md` - Simple task list and priorities (need to create)
- `docs/FASTAPI_NATIVE_MODERNIZATION_PLAN.md` - API standardization plan
- `docs/CONTAINER_APPS_COST_OPTIMIZATION.md` - Container reduction plan
- `.github/agent-instructions.md` - Development guidelines

**Key Reference**:
- Container patterns: `docs/development/CONTAINER_DEVELOPMENT_STANDARDS.md`
- System design: `docs/SYSTEM_ARCHITECTURE.md`

## 🎯 Immediate Next Steps

1. **Create TODO.md** - Simple task tracking
2. **Choose approach** - Start with API standardization OR container reduction
3. **Test Azure site** - Find your actual website URL
4. **Document cleanup** - Remove redundant docs in `/docs`

---

**Bottom Line**: You have a working system that's over-engineered. The plan to simplify it is solid and will cut costs in half while making it easier to maintain. Pick a phase and start implementing!
pytest tests/

# Run integration tests
pytest tests/integration/

# Test specific container
pytest containers/content-collector/tests/

# Run pipeline test
./scripts/test-pipeline.sh
```

## 📊 Project Status

### Implementation Progress
- **Architecture**: ✅ Complete - Fully documented and standardized
- **Development Standards**: ✅ Complete - Templates and patterns established
- **Container Framework**: ✅ Complete - Docker infrastructure ready
- **Blob Storage**: ✅ Complete - Azure integration with local development support

### Next Steps (Implementation Roadmap)
1. **Phase 1**: Refactor SSG container to blob storage (remove volume conflicts)
2. **Phase 2**: Migrate existing containers to standard patterns
3. **Phase 3**: Implement event-driven triggers
4. **Phase 4**: Production deployment and monitoring

See [Implementation Roadmap](docs/IMPLEMENTATION_ROADMAP.md) for detailed timeline.

## 📋 Key Documentation

- **[Quick Start Guide](docs/QUICK_START_GUIDE.md)** - Get started with development
- **[Dependency Management](docs/DEPENDENCY_MANAGEMENT.md)** - Version control and package management
- **[Container Development Standards](docs/CONTAINER_DEVELOPMENT_STANDARDS.md)** - Development guidelines
- **[CI/CD Pipeline Design](docs/CICD_PIPELINE_DESIGN.md)** - Automated testing and deployment
- **[Implementation Roadmap](docs/IMPLEMENTATION_ROADMAP.md)** - Project priorities and timeline

## 🤝 Contributing

1. **Read the Documentation**: Start with [Quick Start Guide](docs/QUICK_START_GUIDE.md)
2. **Follow Standards**: Use [Container Development Standards](docs/CONTAINER_DEVELOPMENT_STANDARDS.md)
3. **Check Dependencies**: Follow [Dependency Management](docs/DEPENDENCY_MANAGEMENT.md) guidelines
4. **Test Everything**: Ensure all tests pass before submitting changes

## 📄 License

This project is private and proprietary. All rights reserved.

---

**Built with**: Python, FastAPI, Docker, Azure Storage, and modern DevOps practices  
**Designed for**: Personal content curation with enterprise-grade architecture
# Build status: All CI/CD checks passing
