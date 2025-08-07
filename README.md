# AI Content Farm

A secure, enterprise-grade Azure Functions application that fetches trending topics from Reddit and processes them for AI-generated content. Features comprehensive security scanning, cost governance, and compliance controls.

## 📚 Documentation

**Complete documentation is available in the [`/docs`](docs/) folder:**

- **[Documentation Index](docs/README.md)** - Start here for navigation
- **[System Design](docs/system-design.md)** - Architecture and components
- **[Deployment Guide](docs/deployment-guide.md)** - Step-by-step deployment
- **[Key Vault Integration](docs/key-vault-integration.md)** - Secrets management
- **[Cost Analysis](docs/cost-analysis.md)** - Detailed cost breakdown and projections
- **[Content Processing Workflow](docs/content-processing-workflow.md)** - Complete content pipeline documentation
- **[Testing Guide](docs/testing-guide.md)** - Function testing procedures
- **[Security Policy](docs/security-policy.md)** - Governance framework

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

### Configure Reddit Credentials
```bash
# Set real values in Key Vault
az keyvault secret set --vault-name aicontentstagingkvt0t36m --name reddit-client-id --value "YOUR_ACTUAL_CLIENT_ID"
az keyvault secret set --vault-name aicontentstagingkvt0t36m --name reddit-client-secret --value "YOUR_ACTUAL_CLIENT_SECRET"
az keyvault secret set --vault-name aicontentstagingkvt0t36m --name reddit-user-agent --value "YourApp/1.0 by YourUsername"
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

- **GetHotTopics**: Timer-triggered function (daily Reddit scan)
- **SummaryWomble**: HTTP-triggered function (flexible data collection)
- **Content Processing Pipeline**: Automated content ranking, enrichment, and publishing
- **Static Site**: 11ty-generated website for content display
- **Infrastructure**: Secure Azure deployment with Key Vault integration

## Content Processing Pipeline

The AI Content Farm features a complete content processing workflow that transforms raw Reddit topics into publication-ready articles:

### 1. Topic Collection
Content wombles scan Reddit communities for trending topics, collecting engagement metrics and source information.

### 2. Topic Ranking
An intelligent ranking system evaluates topics based on:
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

**Quick Start**: `make collect-topics && make process-content`

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
├── azure-function-deploy/     # Azure Functions application
│   ├── GetHotTopics/         # Timer-triggered function
│   └── SummaryWomble/        # HTTP-triggered function
├── infra/                    # Terraform infrastructure
├── site/                     # 11ty static site
├── .github/workflows/        # CI/CD pipelines
├── docs/                     # Additional documentation
└── Makefile                  # Comprehensive build automation
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
