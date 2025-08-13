# AI Content Farm

A secure, enterprise-grade content processing pipeline built on Azure Container Apps. The system collects trending topics from various sources (Reddit, RSS feeds), processes them through AI-powered ranking and enrichment, and generates markdown content for headless CMS integration.

**Architecture**: Migrated from Azure Functions to Container Apps for better maintainability, local development, and scalability.

## 🏗️ Container Apps Architecture

### Services

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

### Complete Pipeline

**Content Collection** → **Content Ranking** → **Content Enrichment** → **Static Site Generation** → **CMS Publishing**

## 🚀 Quick Start

### Local Development

```bash
# Clone repository
git clone https://github.com/Hardcoreprawn/ai-content-farm.git
cd ai-content-farm

# Start all services
docker compose up -d

# Verify services
python scripts/validate_services.py

# View API documentation
open http://localhost:8000/docs  # Content Processor
open http://localhost:8001/docs  # Content Ranker  
open http://localhost:8002/docs  # Content Enricher
open http://localhost:8003/docs  # Scheduler
open http://localhost:8004/docs  # SSG
```

### Service Endpoints

- **Content Processor**: http://localhost:8000 - Content collection (Reddit, RSS)
- **Content Ranker**: http://localhost:8001 - Multi-factor content scoring
- **Content Enricher**: http://localhost:8002 - AI-powered summarization and categorization
- **Scheduler**: http://localhost:8003 - Workflow orchestration
- **SSG**: http://localhost:8004 - Static site generation
- **Redis**: localhost:6379 - Job queuing
- **Azurite**: localhost:10000 - Local blob storage

## 📚 Documentation

**Complete documentation is available in the [`/docs`](docs/) folder:**

- **[Container Apps Architecture Guide](docs/container-apps-architecture.md)** - Complete architecture overview
- **[Documentation Index](docs/README.md)** - Start here for navigation
- **[System Design](docs/system-design.md)** - Architecture and components
- **[API Contracts](docs/api-contracts.md)** - Data format specifications
- **[Deployment Guide](docs/deployment-guide.md)** - Step-by-step deployment
- **[Testing Guide](docs/testing-guide.md)** - Testing procedures

### Legacy Documentation (Azure Functions)
- **[Azure Functions Development Lifecycle](docs/azure-functions-development-lifecycle.md)** - Legacy function development
- **[Security Policy](docs/security-policy.md)** - Governance framework

## ✅ Implementation Status

### Core Services (All Complete)
- **Content Processor** (Port 8000): ✅ Content collection from Reddit, RSS feeds  
- **Content Ranker** (Port 8001): ✅ Multi-factor scoring (engagement, monetization, recency, quality)
- **Content Enricher** (Port 8002): ✅ AI-powered summarization, categorization, sentiment analysis
- **Scheduler** (Port 8003): ✅ Workflow orchestration and job management
- **SSG** (Port 8004): ✅ Static site generation and markdown conversion

### Supporting Infrastructure
- **Redis** (Port 6379): ✅ Job queuing and caching
- **Azurite** (Ports 10000-10002): ✅ Local blob storage emulation
- **Docker Compose**: ✅ Complete local development environment
- **Health Checks**: ✅ All services implement `/health` endpoints
- **API Documentation**: ✅ OpenAPI/Swagger docs at `/docs` for each service

### Pipeline Flow
```
Content Sources → Content Processor → Content Ranker → Content Enricher → SSG → CMS/Static Site
                         ↓                ↓              ↓           ↓
                    Blob Storage    Ranked Topics   Enhanced    Markdown
                                                   Content      Output
```

### Testing & Quality
- **Integration Tests**: ✅ Complete service communication validation
- **Health Monitoring**: ✅ Service validation script
- **Local Development**: ✅ Full pipeline runs locally with Docker Compose
- **Production Ready**: ✅ Azure Container Apps deployment configuration

## 🔄 CI/CD Pipeline

### Container Apps Deployment
Modern Container Apps deployment pipeline:
- **Infrastructure as Code**: Terraform for Azure Container Apps
- **Container Builds**: Multi-stage Docker builds with dependency caching
- **Service Mesh**: Container-to-container communication
- **Auto-scaling**: Based on HTTP metrics and queue depth
- **Blue-Green Deployments**: Zero-downtime deployments

### Testing Pipeline
- **Unit Tests**: Fast, isolated component testing
- **Integration Tests**: Service-to-service communication validation  
- **Health Checks**: Automated service validation
- **Performance Tests**: Load testing and bottleneck identification

### Security & Compliance
- **Security Scanning**: Container image vulnerability scanning
- **Secrets Management**: Azure Key Vault integration
- **Network Security**: Private container networking
- **Cost Governance**: Resource usage monitoring and alerting

### Testing Coverage
- **Unit Tests**: Function-level testing with pytest
- **Function Tests**: Complete function behavior testing
- **Integration Tests**: End-to-end testing against deployed environment
- **Coverage Reporting**: Codecov integration for test coverage tracking
- **PR Feedback**: Automatic test result comments on pull requests

### Pipeline Stages
1. **Changes Detection**: Conditional execution based on modified files
2. **Security & Cost Gates**: Parallel validation (security + cost analysis)
3. **Unit & Function Tests**: Parallel matrix execution for fast feedback
4. **Deploy to Staging**: Automated deployment after all gates pass
5. **Integration Tests**: End-to-end validation against staging environment
6. **Deploy to Production**: Main branch only, after all validations
7. **Deployment Summary**: Comprehensive reporting with test results

### Quality Standards
- ✅ **YAML Validation**: yamllint and actionlint clean
- ✅ **Shell Scripts**: Proper quoting and error handling
- ✅ **Line Endings**: Unix LF format (prevents deployment failures)
- ✅ **Security Scanning**: Comprehensive multi-tool analysis
- ✅ **Cost Governance**: Impact analysis for all infrastructure changes

## 🚀 Quick Start

### Prerequisites
- Azure CLI logged in
- Function app infrastructure deployed (ai-content-staging-func)

### Deploy Function Code (READY NOW)
```bash
cd /workspaces/ai-content-farm/functions
func azure functionapp publish ai-content-staging-func
```

### Test Deployed Function
```bash
curl https://ai-content-staging-func.azurewebsites.net/api/GetHotTopics
```

### Configure Secrets in Key Vaults
```bash
# Use the interactive setup script (recommended)
make setup-keyvault

# Or set manually:
# Application secrets (in application Key Vault)
az keyvault secret set --vault-name "{app-vault-name}" --name reddit-client-id --value "YOUR_ACTUAL_CLIENT_ID"
az keyvault secret set --vault-name "{app-vault-name}" --name reddit-client-secret --value "YOUR_ACTUAL_CLIENT_SECRET"
az keyvault secret set --vault-name "{app-vault-name}" --name reddit-user-agent --value "YourApp/1.0 by YourUsername"

# CI/CD secrets (in CI/CD Key Vault)
az keyvault secret set --vault-name "{cicd-vault-name}" --name infracost-api-key --value "YOUR_INFRACOST_KEY"
```

### Development Setup

1. **Install Prerequisites**:
   ```bash
   # All tools are auto-installed by Makefile
   make verify
   ```

2. **Setup Infracost and Cost Analysis**:
   ```bash
   # Get API key from https://dashboard.infracost.io
   export INFRACOST_API_KEY=your-api-key-here
   
   # Run comprehensive cost analysis
   make cost-analysis
   ```

3. **Deploy Infrastructure**:
   ```bash
   # Deploy to staging with security validation
   make deploy-staging
   ```

4. **Configure Secrets in Key Vault**:
   ```bash
   # Interactive setup of secrets in Azure Key Vault
   make setup-keyvault
   ```

### Local Testing

Test the HTTP-triggered Summary Womble function:
```bash
# Test with default parameters
curl -X POST "http://localhost:7071/api/SummaryWomble" \
  -H "Content-Type: application/json" \
  -d '{"source": "test", "num_posts": 5}'
```

## Architecture Overview

### Core Functions
- **GetHotTopics**: Timer-triggered function (every 6 hours) that initiates content collection
- **SummaryWomble**: HTTP-triggered function with **async job processing system**
- **Content Processing Pipeline**: Automated content ranking, enrichment, and publishing
- **Static Site**: 11ty-generated website for content display
- **Infrastructure**: Secure Azure deployment with Key Vault integration

### Async Job Processing System 🚀

The content collection now uses an advanced asynchronous job processing system:

**Benefits:**
- ⚡ **Instant responses** - No more 5-minute waits
- 📊 **Real-time progress tracking** - See exactly what's happening
- 🔄 **Improved reliability** - Background processing eliminates timeouts
- 📈 **Better scalability** - Handle multiple concurrent requests

**Usage Example:**
```bash
# Start content collection job
curl -X POST "https://ai-content-staging-func.azurewebsites.net/api/summarywomble" \
  -H "x-functions-key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"source": "reddit", "topics": ["technology"], "limit": 10}'

# Response: Job ticket with unique ID
{
  "job_id": "6ce324a8-0502-4b0c-b729-12e10f0f22f6",
  "status": "queued",
  "message": "Content processing started. Use job_id to check status."
}

# Check job status anytime
curl -X POST "https://ai-content-staging-func.azurewebsites.net/api/summarywomble" \
  -H "x-functions-key: YOUR_KEY" \
  -d '{"action": "status", "job_id": "6ce324a8-0502-4b0c-b729-12e10f0f22f6"}'
```

See **[Async Job System Documentation](docs/async-job-system.md)** for complete details.

## Content Processing Pipeline

The AI Content Farm features a complete content processing workflow that transforms raw Reddit topics into publication-ready articles using an advanced async job system:

### 1. Topic Collection (Async)
Content wombles scan Reddit communities for trending topics using job tickets:
- **Instant job tickets** - Get immediate response with job ID
- **Background processing** - Collection happens asynchronously  
- **Real-time status** - Track progress through collection stages
- **Persistent results** - Content stored in Azure Blob Storage

### 2. Topic Ranking
An intelligent ranking system evaluates collected topics based on:
- **Engagement** (40%): Reddit scores and comments
- **Monetization potential** (30%): Commercial keywords and market relevance
- **Freshness** (20%): Content recency and trending status
- **SEO potential** (10%): Title quality and search optimization

### 3. Content Enrichment
Selected topics are enriched with:
- External source content fetching
- Domain credibility assessment
- Citation generation
- Research notes and fact-checking guidance

### 4. Content Publishing
Final articles are generated as SEO-optimized markdown with:
- YAML frontmatter for JAMStack compatibility
- Social sharing metadata
- Monetization-ready structure
- Proper source attribution

**Quick Start**: 
```bash
# Collect topics with job tracking
make collect-topics

# Process collected content
make process-content
```

See **[Content Processing Workflow](docs/content-processing-workflow.md)** for complete documentation.

## Security & Governance

This project implements enterprise-grade security and cost controls:

### Security Scanning
- **Checkov**: Infrastructure security validation
- **TFSec**: Terraform security analysis
- **Terrascan**: Policy compliance checking

### Cost Management
- **Infracost**: Pre-deployment cost estimation
- **Budget Controls**: Automatic cost impact reporting
- **Resource Optimization**: Consumption-based pricing

### Compliance
- **SBOM Generation**: Complete software bill of materials
- **CI/CD Gates**: Mandatory security validation before deployment
- **Audit Trail**: Full change tracking and compliance reporting

## Documentation

- **[DESIGN.md](DESIGN.md)**: Comprehensive architectural overview
- **[SECURITY_POLICY.md](SECURITY_POLICY.md)**: Security and governance controls
- **[FILE_INVENTORY.md](FILE_INVENTORY.md)**: Complete project file reference
- **[PROGRESS.md](PROGRESS.md)**: Development timeline and status
- **[TEST_WOMBLE.md](TEST_WOMBLE.md)**: Testing procedures and examples

## Development Commands

### Core Operations
```bash
make deploy          # Full deployment with security validation
make verify          # Comprehensive pre-deployment checks
make test            # Run all tests and validations
make clean           # Clean all generated artifacts
```

### Content Processing
```bash
make collect-topics    # Run content wombles to collect topics
make process-content   # Full content processing pipeline
make rank-topics       # Rank collected topics for publishing
make enrich-content    # Enrich topics with research (requires FILE=)
make publish-articles  # Generate markdown articles (requires FILE=)
make content-status    # Show content processing status
```

### Infrastructure
```bash
make apply           # Deploy infrastructure after validation
make destroy         # Destroy infrastructure
make cost-estimate   # Generate cost estimates with Infracost
make security-scan   # Run comprehensive security scanning
```

### Security & Compliance
```bash
make security-scan   # Run all security scanners
make cost-estimate   # Generate cost impact analysis
make sbom           # Generate software bill of materials
```

### Individual Tools
```bash
make checkov        # Infrastructure security scan
make tfsec          # Terraform security analysis
make terrascan      # Policy compliance check
```

### Key Vault Management
```bash
make setup-keyvault     # Configure all secrets in Azure Key Vault
make setup-infracost    # Setup Infracost API key specifically
make get-secrets        # Retrieve secrets from Key Vault
make validate-secrets   # Validate Key Vault configuration
```

## Project Structure

```
├── functions/                # Azure Functions application
│   ├── GetHotTopics/         # Timer-triggered function (async job orchestrator)
│   └── SummaryWomble/        # HTTP-triggered function (async content processing)
├── infra/                    # Terraform infrastructure
│   ├── bootstrap/           # GitHub Actions permissions and CI/CD setup
│   └── application/         # Main application infrastructure
├── site/                     # 11ty static site
├── content_processor/        # Content processing pipeline
├── content_wombles/          # Topic collection utilities
├── .github/workflows/        # CI/CD pipelines with security gates
├── docs/                     # Comprehensive documentation
└── Makefile                  # Build automation and dev workflows
```

## Security Features

- **Zero-Trust Architecture**: All connections authenticated and encrypted
- **Key Vault Integration**: Secure credential management
- **RBAC Controls**: Principle of least privilege access
- **Network Security**: Private endpoints and restricted access
- **Compliance Monitoring**: Continuous security validation

## Cost Optimization

- **Consumption Pricing**: Pay-per-execution Azure Functions
- **Storage Tiers**: Lifecycle-managed blob storage
- **Resource Tagging**: Complete cost attribution
- **Budget Alerts**: Proactive cost monitoring

## Contributing

1. **Fork and Clone**: Standard GitHub workflow
2. **Security First**: All changes must pass security validation
3. **Documentation**: Update relevant docs with changes
4. **Testing**: Comprehensive validation required
5. **Cost Impact**: Review cost implications of changes

## Monitoring

- **Application Insights**: Function performance and errors
- **Security Alerts**: Real-time security issue notifications
- **Cost Tracking**: Daily cost analysis and trending
- **Compliance Reports**: Weekly security and compliance status

## Support

- **Security Issues**: See [SECURITY_POLICY.md](SECURITY_POLICY.md)
- **Cost Questions**: Review Infracost reports in pull requests
- **Technical Issues**: Check [DESIGN.md](DESIGN.md) for troubleshooting

---

**Enterprise-Ready**: This project implements production-grade security, compliance, and cost controls suitable for enterprise deployment.
