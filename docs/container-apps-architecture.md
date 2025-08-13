# Container Apps Architecture Guide

## Overview

The AI Content Farm has been migrated from Azure Functions to Azure Container Apps, providing a more maintainable and scalable architecture. This guide documents the complete Container Apps pipeline and how to work with it.

## Architecture

### Service Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Content       │    │   Content       │    │   Content       │
│   Processor     │───▶│   Ranker        │───▶│   Enricher      │
│   (Port 8000)   │    │   (Port 8001)   │    │   (Port 8002)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Scheduler     │    │       SSG       │    │   Blob Storage  │
│   (Port 8003)   │───▶│   (Port 8004)   │───▶│   (Azurite)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │
         ▼
┌─────────────────┐
│     Redis       │
│   (Port 6379)   │
└─────────────────┘
```

### Data Flow

1. **Content Collection** (Content Processor): Collect content from sources (Reddit, RSS, etc.)
2. **Content Ranking** (Content Ranker): Score and rank content based on engagement, monetization potential, etc.
3. **Content Enrichment** (Content Enricher): Add AI-generated summaries, categorization, sentiment analysis
4. **Workflow Orchestration** (Scheduler): Coordinate the entire pipeline
5. **Static Site Generation** (SSG): Convert processed content to markdown for headless CMS
6. **Storage**: All data persisted in Azure Blob Storage (Azurite for local development)
7. **Job Queuing**: Redis for asynchronous job processing

## Services

### 1. Content Processor (SummaryWomble) - Port 8000

**Purpose**: Content collection from various sources

**Key Endpoints**:
- `POST /api/summary-womble/process` - Start content collection job
- `POST /api/summary-womble/status` - Check job status
- `GET /health` - Health check
- `GET /docs` - API documentation

**Supported Sources**:
- Reddit (via PRAW)
- RSS feeds
- Future: Twitter, news APIs

### 2. Content Ranker - Port 8001

**Purpose**: Multi-factor content scoring and ranking

**Key Endpoints**:
- `POST /api/content-ranker/process` - Start ranking job
- `POST /api/content-ranker/status` - Check job status
- `GET /health` - Health check

**Ranking Factors**:
- **Engagement Score**: Comments, votes, shares
- **Monetization Score**: Commercial potential, affiliate opportunities
- **Recency Score**: Time-based relevance
- **Quality Score**: Content length, source authority

### 3. Content Enricher - Port 8002

**Purpose**: AI-powered content enhancement

**Key Endpoints**:
- `POST /api/content-enricher/process` - Start enrichment job
- `POST /api/content-enricher/status` - Check job status
- `GET /health` - Health check

**AI Features**:
- Content summarization
- Category classification
- Sentiment analysis
- Key phrase extraction
- Reading time estimation

### 4. Scheduler - Port 8003

**Purpose**: Workflow orchestration and job scheduling

**Key Endpoints**:
- `POST /api/scheduler/workflows` - Create workflow
- `GET /api/scheduler/workflows/{id}` - Get workflow status
- `GET /api/scheduler/workflows` - List all workflows
- `GET /health` - Health check

**Supported Workflows**:
- **hot-topics**: Complete content pipeline (collect → rank → enrich → publish)
- **content-ranking**: Standalone ranking workflow
- **content-enrichment**: Standalone enrichment workflow

### 5. Static Site Generator (SSG) - Port 8004

**Purpose**: Generate markdown content for headless CMS

**Key Endpoints**:
- `POST /api/ssg/generate` - Generate static site
- `GET /api/ssg/status/{job_id}` - Check generation status
- `GET /api/ssg/preview/{job_id}` - Preview generated content
- `GET /health` - Health check

**Output Formats**:
- Markdown files with frontmatter
- Category pages
- Site configuration (YAML)
- Index pages

### 6. Supporting Services

**Redis (Port 6379)**:
- Job queue management
- Caching
- Session storage

**Azurite (Ports 10000-10002)**:
- Local blob storage emulation
- Development environment only
- Production uses Azure Blob Storage

## Local Development

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- Azure CLI (for production deployment)

### Quick Start

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Hardcoreprawn/ai-content-farm.git
   cd ai-content-farm
   ```

2. **Start all services**:
   ```bash
   docker compose up -d
   ```

3. **Verify services are running**:
   ```bash
   docker compose ps
   ```

4. **Check service health**:
   ```bash
   curl http://localhost:8000/health  # Content Processor
   curl http://localhost:8001/health  # Content Ranker
   curl http://localhost:8002/health  # Content Enricher
   curl http://localhost:8003/health  # Scheduler
   curl http://localhost:8004/health  # SSG
   ```

### Service URLs (Local Development)

- Content Processor: http://localhost:8000
- Content Ranker: http://localhost:8001
- Content Enricher: http://localhost:8002
- Scheduler: http://localhost:8003
- SSG: http://localhost:8004
- Redis: redis://localhost:6379
- Azurite Blob: http://localhost:10000

### API Documentation

Each service provides interactive API documentation:

- Content Processor: http://localhost:8000/docs
- Content Ranker: http://localhost:8001/docs
- Content Enricher: http://localhost:8002/docs
- Scheduler: http://localhost:8003/docs
- SSG: http://localhost:8004/docs

## Configuration

### Environment Variables

All services support the following environment variables:

**Common Variables**:
```bash
ENVIRONMENT=development|staging|production
HOST=0.0.0.0
PORT=<service-port>
```

**Azure Storage** (Production):
```bash
AZURE_STORAGE_CONNECTION_STRING=<connection-string>
AZURE_STORAGE_ACCOUNT_NAME=<account-name>
AZURE_CLIENT_ID=<client-id>
AZURE_CLIENT_SECRET=<client-secret>
AZURE_TENANT_ID=<tenant-id>
```

**Local Development** (Azurite):
```bash
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://azurite:10000/devstoreaccount1;
```

**Redis**:
```bash
REDIS_URL=redis://redis:6379
```

**Content Sources** (Content Processor):
```bash
REDDIT_CLIENT_ID=<reddit-client-id>
REDDIT_CLIENT_SECRET=<reddit-client-secret>
REDDIT_USER_AGENT=<user-agent>
```

### Service Communication

Services communicate via HTTP REST APIs. The Scheduler service orchestrates workflows by calling other services:

```python
# Example: Hot Topics Workflow
1. Scheduler calls Content Processor to collect content
2. Scheduler calls Content Ranker to rank collected content
3. Scheduler calls Content Enricher to enhance ranked content
4. Scheduler calls SSG to generate static content
```

## Testing

### Running Tests

**All Tests**:
```bash
make test
```

**Unit Tests Only**:
```bash
make test-unit
```

**Integration Tests** (requires running services):
```bash
make test-integration
```

**Container Apps Integration Tests**:
```bash
pytest tests/integration/test_container_apps.py -v
```

### Test Categories

- **Unit Tests**: Fast, isolated, no external dependencies
- **Integration Tests**: Test service communication and workflows
- **Function Tests**: Test complete feature functionality

## Deployment

### Local Development

```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# Rebuild services
docker compose up --build

# View logs
docker compose logs -f <service-name>
```

### Production (Azure Container Apps)

Production deployment uses Terraform and GitHub Actions:

1. **Infrastructure deployment**:
   ```bash
   make app-init
   make app-plan
   make app-apply
   ```

2. **Service deployment**:
   - Container images built via GitHub Actions
   - Deployed to Azure Container Apps
   - Auto-scaling based on load

### Environment-Specific Configuration

**Development**:
- Uses Azurite for blob storage
- Redis in Docker
- Hot reload enabled
- Debug logging

**Staging**:
- Azure Blob Storage
- Azure Redis Cache
- Production-like configuration
- Comprehensive monitoring

**Production**:
- Azure Blob Storage
- Azure Redis Cache
- High availability
- Performance monitoring
- Security scanning

## Monitoring and Observability

### Health Checks

All services implement `/health` endpoints for monitoring:

```json
{
  "status": "healthy",
  "service": "content-enricher",
  "version": "2.0.0",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Logging

Services use structured logging with correlation IDs for tracing requests across the pipeline.

### Metrics

Key metrics tracked:
- Request latency per service
- Job processing times
- Error rates
- Queue depths
- Storage operations

## Security

### Authentication

- Production uses Azure Managed Identity
- Local development uses connection strings
- API keys stored in Azure Key Vault

### Network Security

- Services communicate within container network
- External access via Azure Application Gateway
- HTTPS only in production

### Data Protection

- All data encrypted at rest (Azure Blob Storage)
- Secrets managed via Azure Key Vault
- No sensitive data in logs

## Troubleshooting

### Common Issues

**Services not starting**:
```bash
# Check logs
docker compose logs <service-name>

# Check container status
docker compose ps

# Rebuild if needed
docker compose up --build <service-name>
```

**SSL Certificate errors in build**:
```bash
# Use trusted hosts for pip (already configured in Dockerfiles)
pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org
```

**Service communication failures**:
```bash
# Check service URLs in docker-compose.yml
# Verify container networking
docker compose exec <service> curl http://other-service:port/health
```

### Debugging

**Local development debugging**:
```bash
# Run service locally
cd containers/<service-name>
python main.py

# Install dependencies
pip install -r requirements.txt
```

**Container debugging**:
```bash
# Execute into container
docker compose exec <service-name> bash

# Check environment variables
docker compose exec <service-name> env
```

## Migration from Azure Functions

### What Changed

1. **Architecture**: Timer-triggered functions → HTTP-based orchestration
2. **State Management**: Azure Storage Tables → Redis + Blob Storage
3. **Service Communication**: Function bindings → HTTP REST APIs
4. **Deployment**: Function Apps → Container Apps
5. **Scaling**: Function consumption → Container auto-scaling

### Benefits

- **Better local development**: Full environment in Docker Compose
- **Easier testing**: Standard HTTP APIs instead of Function bindings
- **More control**: Custom container configuration
- **Cost predictability**: Container Apps pricing vs Function consumption
- **Technology flexibility**: Not limited to Function runtime constraints

### Legacy Compatibility

- API contracts maintained for existing integrations
- Data formats unchanged
- Environment variable compatibility

## Future Enhancements

### Planned Features

1. **Enhanced AI Integration**: OpenAI, Claude, or other LLM providers
2. **More Content Sources**: Twitter API, news feeds, podcast transcripts
3. **Advanced Analytics**: Content performance tracking, A/B testing
4. **CMS Integration**: Direct publishing to Strapi, Contentful, WordPress
5. **Real-time Processing**: WebSocket support for live content streams

### Scalability Improvements

1. **Message Queues**: Replace direct HTTP calls with async messaging
2. **Caching Layer**: Redis caching for frequently accessed data
3. **Content CDN**: Azure CDN for generated static content
4. **Database Integration**: PostgreSQL for complex queries and analytics

## Support

### Documentation

- API Documentation: Available at `/docs` endpoint for each service
- Architecture Diagrams: `/docs/architecture/`
- Deployment Guides: `/docs/deployment/`

### Getting Help

- GitHub Issues: Bug reports and feature requests
- Wiki: Community-maintained guides and examples
- Discussions: Architecture questions and best practices

---

*This documentation is maintained alongside the codebase. Please update it when making architectural changes.*