# AI Content Farm - System Design

**Created:** August 5, 2025  
**Last Updated:** August 5, 2025

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
- **Authentication**: Azure Key Vault for secrets management
- **CI/CD**: GitHub Actions
- **Infrastructure**: Terraform
- **Frontend**: Static site generator (11ty)
- **API Integration**: PRAW (Python Reddit API Wrapper)

### Core Components

#### 1. Data Collection (Wombles)
- **Purpose**: Automated collection of trending topics from various sources
- **Implementation**: Azure Functions with timer and HTTP triggers
- **Primary Source**: Reddit API via PRAW
- **Output**: JSON files with trending topics and metadata

#### 2. Azure Functions Architecture
```
functions/
├── GetHotTopics/          # HTTP-triggered function for testing
│   ├── function.json      # Function configuration
│   └── index.js          # Function implementation
├── host.json             # Function host configuration
├── local.settings.json   # Local development settings
└── package.json          # Dependencies
```

#### 3. Infrastructure Components
- **Resource Group**: Container for all Azure resources
- **Storage Account**: Blob storage for collected data
- **Function App**: Serverless compute for data collection
- **Key Vault**: Secure storage for API keys and secrets
- **Application Insights**: Monitoring and logging

### Security Architecture

#### Key Vault Integration
- **Centralized Secret Management**: All API keys stored in Azure Key Vault
- **Environment Isolation**: Separate Key Vaults for dev/staging/production
- **Access Policies**: Function Apps have read-only access, CI/CD has management access
- **Audit Logging**: Full diagnostic logging for compliance

#### Security Scanning Pipeline
- **Checkov**: Infrastructure security scanning
- **TFSec**: Terraform-specific security checks
- **Terrascan**: Policy compliance validation
- **SBOM Generation**: Software Bill of Materials with Syft
- **Cost Analysis**: Infracost for deployment cost estimation

### Development Workflow

#### Local Development
1. **Setup**: Clone repository and configure local environment
2. **Testing**: Run wombles locally with `python -m wombles.reddit_womble`
3. **Function Testing**: Use HTTP-triggered endpoints for integration testing
4. **Security**: Local security scanning before commits

#### CI/CD Pipeline
1. **Code Quality**: Linting and testing
2. **Security Scanning**: Multi-tool security validation
3. **Cost Estimation**: Infrastructure cost impact analysis
4. **Infrastructure Deployment**: Terraform-based resource provisioning
5. **Function Deployment**: Azure Functions deployment with Key Vault integration

### Data Flow

#### Collection Process
1. **Timer Trigger**: Scheduled function execution (configurable intervals)
2. **API Authentication**: Retrieve Reddit credentials from Key Vault
3. **Data Gathering**: Fetch hot topics from specified subreddits
4. **Data Processing**: Clean and structure collected data
5. **Storage**: Save processed data to Azure Blob Storage
6. **Logging**: Record execution metrics and status

#### Data Structure
```json
{
  "timestamp": "2025-08-05T10:00:00Z",
  "source": "reddit",
  "subreddit": "technology",
  "topics": [
    {
      "title": "Topic Title",
      "score": 1500,
      "url": "https://reddit.com/r/...",
      "created_utc": "2025-08-05T09:30:00Z",
      "num_comments": 250
    }
  ]
}
```

### Deployment Environments

#### Development
- **Purpose**: Local development and testing
- **Configuration**: Local functions runtime, file-based storage
- **Secrets**: Environment variables or local Key Vault

#### Staging
- **Purpose**: Integration testing and validation
- **Configuration**: Azure Functions with staging resource group
- **Secrets**: Staging Key Vault instance

#### Production
- **Purpose**: Live data collection and serving
- **Configuration**: Production Azure Functions with monitoring
- **Secrets**: Production Key Vault with audit logging

### Monitoring and Observability

#### Application Insights
- **Function Execution**: Performance metrics and error tracking
- **API Usage**: Reddit API call patterns and rate limiting
- **Resource Utilization**: Memory, CPU, and execution time metrics

#### Key Vault Diagnostics
- **Access Logging**: Who accessed which secrets when
- **Compliance**: Audit trail for security reviews
- **Alerting**: Notifications for unusual access patterns

### Future Enhancements

#### Additional Data Sources
- **RSS Feeds**: News aggregation from multiple sources
- **News APIs**: Direct integration with news providers
- **Social Media**: Twitter/X API integration

#### Advanced Processing
- **Content Analysis**: AI-powered topic categorization
- **Sentiment Analysis**: Public opinion tracking
- **Trend Prediction**: Machine learning for trend forecasting

#### Enhanced Frontend
- **Interactive Dashboard**: Real-time topic visualization
- **API Endpoints**: Public API for accessing collected data
- **User Management**: Authentication and personalization

### Performance Considerations

#### Scalability
- **Function Scaling**: Automatic scaling based on demand
- **Storage Partitioning**: Efficient data organization for large datasets
- **Caching**: Strategic caching for frequently accessed data

#### Cost Optimization
- **Consumption Plan**: Pay-per-execution model for functions
- **Storage Tiering**: Automated movement to cheaper storage tiers
- **Resource Tagging**: Cost tracking by environment and feature

### Compliance and Governance

#### Data Privacy
- **No Personal Data**: Focus on public, aggregated content only
- **Data Retention**: Automated cleanup of old data
- **API Terms Compliance**: Adherence to Reddit API terms of service

#### Security Standards
- **Infrastructure as Code**: All resources defined in Terraform
- **Secret Rotation**: Automated key rotation capabilities
- **Least Privilege**: Minimal access permissions throughout system

This design provides a solid foundation for automated content collection while maintaining security, scalability, and operational excellence.
