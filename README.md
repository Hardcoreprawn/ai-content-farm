# AI Content Farm

**An intelligent, event-driven content aggregation and curation system** that collects interesting articles from various sources and presents them as high-quality static websites. Built with Docker microservices and Azure blob storage for scalability and reliability.

> **Latest Update (Aug 22, 2025)**: Enhanced CI/CD pipeline with parallel security scanning, modular action architecture, and optimized dependency caching for improved maintainability and performance.

## 🎯 Vision

Create a **personal content curation platform** that automatically:
- **🧹 Aggregates Quality Content**: Collect from Reddit, HackerNews, and other sources
- **🤖 AI-Enhanced Processing**: Smart ranking, enrichment, and fact-checking
- **📚 Generates Static Sites**: Beautiful, fast-loading websites for consumption
- **🔄 Event-Driven Automation**: Fully automated pipeline with minimal manual intervention
- **☁️ Cloud-Native Design**: Scalable, secure, and cost-effective

## 🏗️ Architecture

**Event-Driven Microservices Pipeline**:
```
Sources → Collector → Processor → Enricher → Ranker → Generator → SSG → Website
   ↓         ↓          ↓          ↓         ↓         ↓        ↓        ↓
[Reddit]  [collected] [processed] [enriched] [ranked] [markdown] [sites] [preview]
```

### Core Components
- **6 Microservices**: Each stage runs in its own Docker container
- **Azure Blob Storage**: All data persistence through standardized blob containers
- **Event-Driven Triggers**: Services automatically trigger when new content is available
- **Standard APIs**: FastAPI-based services with health checks and monitoring
- **Local Development**: Full stack runs locally with Azurite blob storage emulation

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.11+
- Azure CLI (for production deployment)

### Development Setup
```bash
# 1. Clone and setup environment
git clone https://github.com/Hardcoreprawn/ai-content-farm.git
cd ai-content-farm
./scripts/setup-local-dev.sh

# 2. Start the development stack
docker-compose up -d

# 3. Test the pipeline
./scripts/test-pipeline.sh

# 4. View generated content
open http://localhost:8002  # SSG preview service
```

## 📚 Documentation

### 🚀 Getting Started
- **[Quick Start Guide](docs/QUICK_START_GUIDE.md)** - Get productive in 30 minutes
- **[System Architecture](docs/SYSTEM_ARCHITECTURE.md)** - Complete system design

### 👨‍💻 Development
- **[Container Standards](docs/CONTAINER_DEVELOPMENT_STANDARDS.md)** - Development patterns and templates
- **[Implementation Roadmap](docs/IMPLEMENTATION_ROADMAP.md)** - Current development plan
- **[Testing Guide](docs/testing-guide.md)** - Quality assurance practices

### 🚀 Deployment
- **[Deployment Guide](docs/deployment-guide.md)** - Production deployment
- **[Security Policy](docs/security-policy.md)** - Security best practices

## 🔧 Development

### Container Services
```bash
# Individual service endpoints (when running)
curl http://localhost:8001/health   # Content Collector
curl http://localhost:8002/health   # Content Processor  
curl http://localhost:8003/health   # Content Enricher
curl http://localhost:8004/health   # Content Ranker
curl http://localhost:8005/health   # Markdown Generator
curl http://localhost:8006/health   # Static Site Generator
```

### Development Workflow
```bash
# Make changes to a container
code containers/ssg/main.py

# Rebuild and restart
docker-compose up -d --build ssg

# Test changes
curl http://localhost:8006/health
pytest containers/ssg/tests/
```

## 🧪 Testing

```bash
# Run all tests
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
