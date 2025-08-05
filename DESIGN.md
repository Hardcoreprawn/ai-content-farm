# AI Content Farm - System Design

## Overview

The AI Content Farm is an automated content aggregation system that collects trending topics from various sources (primarily Reddit) and stores them for analysis and content generation. The system is designed to run both locally for development and in Azure for production automation.

## Architecture

### High-Level Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Sources  │    │   Processing    │    │    Storage     │
│                 │    │                 │    │                 │
│ • Reddit API    │───▶│ • Azure Function│───▶│ • Azure Blob   │
│ • Future: RSS   │    │ • Local Wombles │    │ • Local Files  │
│ • Future: News  │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   Web Frontend  │
                       │                 │
                       │ • Static Site   │
                       │ • Documentation │
                       └─────────────────┘
```

### Technology Stack

- **Cloud Platform**: Microsoft Azure
- **Compute**: Azure Functions (Python 3.11)
- **Storage**: Azure Blob Storage
- **Authentication**: Managed Identity + RBAC
- **Infrastructure**: Terraform
- **API Integration**: PRAW (Python Reddit API Wrapper)
- **Local Development**: Python scripts ("wombles")
- **Documentation**: MkDocs
- **Frontend**: Eleventy (11ty) static site generator

## Core Components

### 1. Azure Function (`azure-function-deploy/`)

**Purpose**: Cloud-based automated content collection
**Status**: ✅ Deployed with managed identity, ❌ Needs Reddit API authentication

**Key Features**:
- Timer-triggered execution (configurable schedule)
- Managed identity for secure Azure storage access
- Comprehensive logging and error handling
- Structured JSON output with metadata

**Current Implementation**:
- Uses basic HTTP requests (fails from Azure due to Reddit's cloud restrictions)
- **Next Step**: Migrate to PRAW with proper Reddit API credentials

### 2. Local Wombles (`content_wombles/`)

**Purpose**: Local development and testing scripts
**Status**: ✅ Fully functional

**Scripts**:
- `get-hot-topics.py`: Main Reddit scraper (works locally)
- `womble_status.py`: Monitor and analyze collected data
- `run_all_wombles.py`: Execute multiple wombles

**Output**: Timestamped JSON files in `output/` directory

### 3. Infrastructure (`infra/`)

**Purpose**: Azure resource management via Infrastructure as Code
**Status**: ✅ Deployed and functional

**Resources**:
- Resource Group: `hot-topics-rg`
- Function App: `hot-topics-func` (with managed identity)
- Storage Account: `hottopicsstorageib91ea`
- Key Vault: `hottopicskv*` (for future credentials)
- Service Plan: Consumption tier for cost efficiency

**Security**:
- Managed identity authentication (no connection strings)
- RBAC with "Storage Blob Data Contributor" role
- Security scanning with Checkov

### 4. Documentation (`docs/`, `site/`)

**Purpose**: Project documentation and potential frontend
**Status**: ✅ Basic structure in place

## Data Flow

### Current Flow (Local)
```
Reddit API ───▶ Local Womble ───▶ JSON Files ───▶ Local Analysis
```

### Target Flow (Production)
```
Reddit API ───▶ Azure Function ───▶ Azure Blob Storage ───▶ Analysis/Frontend
     ▲                                        │
     │                                        ▼
Key Vault                              Static Site Generator
(Credentials)
```

## Data Schema

### Topic Data Structure
```json
{
  "source": "reddit",
  "subject": "technology",
  "fetched_at": "20250805_120000",
  "count": 10,
  "topics": [
    {
      "title": "Topic Title",
      "external_url": "https://external-link.com",
      "reddit_url": "https://reddit.com/r/technology/comments/...",
      "reddit_id": "abc123",
      "score": 1234,
      "created_utc": 1691234567,
      "num_comments": 89,
      "author": "username",
      "subreddit": "technology",
      "fetched_at": "20250805_120000",
      "selftext": "Post content preview..."
    }
  ]
}
```

### File Naming Convention
- Format: `YYYYMMDD_HHMMSS_source_subject.json`
- Example: `20250805_120000_reddit_technology.json`

## Security Model

### Authentication & Authorization
- **Azure Resources**: Managed Identity with RBAC
- **Reddit API**: OAuth2 with client credentials (pending)
- **Key Management**: Azure Key Vault for sensitive credentials

### Access Patterns
- Function App → Storage: Managed Identity + Storage Blob Data Contributor
- Function App → Key Vault: Managed Identity + Key Vault Secrets User (planned)
- Local Development → Storage: Azure CLI authentication

## Deployment Pipeline

### Infrastructure Deployment
```bash
make verify     # Security scan + validation
make apply      # Deploy infrastructure
```

### Function Deployment
```bash
make verify-functions    # Code validation
make deploy-functions   # Deploy to Azure
```

### Security Gates
- Checkov security scanning
- Terraform validation and planning
- Python syntax checking
- JSON validation

## Monitoring & Observability

### Current Capabilities
- Azure Function execution logs
- Storage access patterns
- Local file-based monitoring via `womble_status.py`

### Planned Enhancements
- Application Insights integration
- Custom metrics and alerts
- Cost monitoring

## Development Workflow

### Local Development
1. Run wombles locally: `python content_wombles/get-hot-topics.py`
2. Monitor output: `python content_wombles/womble_status.py`
3. Test changes before cloud deployment

### Cloud Deployment
1. Test infrastructure changes: `make verify`
2. Deploy infrastructure: `make apply`
3. Test function changes: `make verify-functions`
4. Deploy functions: `make deploy-functions`

## Current Challenges & Next Steps

### ❌ Immediate Issues
1. **Reddit API Authentication**: Azure Function can't make anonymous requests
   - Solution: Implement PRAW with OAuth2 credentials
   - Store credentials in Azure Key Vault

### 🔄 In Progress
1. **Documentation Completion**: This design document and project status tracking

### 📋 Planned Features
1. **Additional Data Sources**: RSS feeds, news APIs
2. **Content Analysis**: Trending topic analysis, sentiment analysis
3. **Web Frontend**: Display collected topics, analytics dashboard
4. **Alerting**: Notification for trending topics or system issues

## File Organization

See `FILE_INVENTORY.md` for detailed file-by-file documentation.
