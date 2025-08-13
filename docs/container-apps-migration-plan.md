# Azure Container Apps Migration Plan

## Overview

Migration from Azure Functions to Azure Container Apps to resolve deployment complexity, programming model conflicts, and improve development experience.

## Current State Analysis

### Function Inventory
- **HTTP Functions** (4): ContentEnricher, ContentRanker, SummaryWomble, TestFunction
- **Timer Function** (1): GetHotTopics
- **Blob Trigger Functions** (2): ContentEnrichmentScheduler, TopicRankingScheduler

### Current Issues
- Azure Functions v1/v4 programming model conflicts
- Complex deployment permissions (403 errors)
- Mixed deployment patterns (Terraform vs Azure CLI)
- Function runtime dependencies and packaging complexity

## Container Apps Benefits

### Technical Advantages
1. **Simplified Deployment**: Standard Docker containers with Terraform
2. **Development Experience**: Same container runs locally and in Azure
3. **No Runtime Conflicts**: Full control over Python environment
4. **Better Debugging**: Standard container troubleshooting
5. **Version Control**: Dockerfile ensures environment consistency
6. **HTTP-First Architecture**: Natural fit for our webhook-based pipeline

### Operational Benefits
1. **Predictable Scaling**: Better control over resource allocation
2. **Cost Transparency**: More predictable pricing model
3. **Infrastructure as Code**: Clean Terraform deployment
4. **Monitoring**: Standard container monitoring tools

## Migration Strategy

### Phase 1: HTTP Functions Migration
**Target**: ContentRanker, SummaryWomble, ContentEnricher, TestFunction

#### Container Structure
```
containers/
├── content-processor/          # Main HTTP API container
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                # FastAPI application
│   ├── routers/
│   │   ├── content_ranker.py
│   │   ├── summary_womble.py
│   │   ├── content_enricher.py
│   │   └── test_function.py
│   └── core/                  # Shared business logic
│       ├── ranker_core.py
│       ├── storage_utils.py
│       └── auth_utils.py
└── job-scheduler/             # Scheduled jobs container
    ├── Dockerfile
    ├── requirements.txt
    ├── scheduler.py
    └── jobs/
        ├── get_hot_topics.py
        ├── content_enrichment_monitor.py
        └── topic_ranking_monitor.py
```

#### API Design
```python
# FastAPI app with standardized endpoints
from fastapi import FastAPI, HTTPException
from routers import content_ranker, summary_womble, content_enricher

app = FastAPI(title="AI Content Farm API")

app.include_router(content_ranker.router, prefix="/api/content-ranker")
app.include_router(summary_womble.router, prefix="/api/summary-womble")
app.include_router(content_enricher.router, prefix="/api/content-enricher")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}
```

### Phase 2: Scheduled Jobs Migration
**Target**: GetHotTopics, ContentEnrichmentScheduler, TopicRankingScheduler

#### Timer Replacement
- **GetHotTopics**: Container App scheduled job (cron: "0 */6 * * *")
- **Monitoring Jobs**: Event Grid + HTTP endpoints for blob notifications

#### Event Grid Integration
```yaml
# Event Grid setup for blob triggers
blob_events:
  - event_type: "Microsoft.Storage.BlobCreated"
    subject_filter: "/blobServices/default/containers/hot-topics/"
    endpoint: "https://content-processor.azurecontainerapps.io/api/content-ranker/blob-created"
```

### Phase 3: Infrastructure Migration

#### Terraform Resources
```hcl
# Container Apps Environment
resource "azurerm_container_app_environment" "main" {
  name                = "${local.resource_prefix}-cae"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
}

# Main Content Processor App
resource "azurerm_container_app" "content_processor" {
  name                         = "${local.resource_prefix}-processor"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode               = "Single"

  template {
    container {
      name   = "content-processor"
      image  = "ai-content-farm/content-processor:latest"
      cpu    = 0.25
      memory = "0.5Gi"

      env {
        name  = "AZURE_STORAGE_CONNECTION_STRING"
        value = azurerm_storage_account.main.primary_connection_string
      }
    }
  }

  ingress {
    external_enabled = true
    target_port     = 8000
  }
}

# Scheduled Job Container App
resource "azurerm_container_app_job" "scheduler" {
  name                         = "${local.resource_prefix}-scheduler"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name

  template {
    container {
      name   = "job-scheduler"
      image  = "ai-content-farm/job-scheduler:latest"
      cpu    = 0.25
      memory = "0.5Gi"
    }
  }

  schedule_trigger_config {
    cron_expression = "0 */6 * * *"  # Every 6 hours
  }
}
```

## Migration Timeline

### Week 1: Foundation
- [ ] Create container structure and Dockerfiles
- [ ] Migrate ContentRanker to FastAPI endpoint
- [ ] Set up local development with Docker Compose
- [ ] Create Container Apps Terraform configuration

### Week 2: Core Migration
- [ ] Migrate SummaryWomble and ContentEnricher
- [ ] Implement health checks and monitoring
- [ ] Deploy to staging environment
- [ ] Test HTTP endpoints

### Week 3: Scheduled Jobs
- [ ] Create job scheduler container
- [ ] Migrate GetHotTopics to scheduled job
- [ ] Set up Event Grid for blob notifications
- [ ] Implement blob monitoring endpoints

### Week 4: Validation & Cleanup
- [ ] End-to-end pipeline testing
- [ ] Performance comparison
- [ ] Remove Azure Functions infrastructure
- [ ] Update documentation

## Development Experience Improvements

### Local Development
```bash
# Simple local development
docker-compose up  # Starts all containers locally
curl http://localhost:8000/api/content-ranker/health

# No Azure Functions Core Tools needed
# No function.json complexity
# Standard Python debugging
```

### CI/CD Pipeline
```yaml
# Simplified GitHub Actions
- name: Build and Push
  run: |
    docker build -t content-processor .
    docker push ${{ env.REGISTRY }}/content-processor:${{ github.sha }}

- name: Deploy to Container Apps
  run: |
    az containerapp update \
      --name content-processor \
      --image ${{ env.REGISTRY }}/content-processor:${{ github.sha }}
```

## Rollback Plan

### Safety Measures
1. **Parallel Deployment**: Run Container Apps alongside Functions initially
2. **Traffic Splitting**: Gradually move traffic from Functions to Container Apps
3. **Feature Flags**: Environment variables to enable/disable new endpoints
4. **Data Validation**: Compare outputs between old and new systems

### Rollback Triggers
- Performance degradation > 20%
- Error rate increase > 5%
- Any data integrity issues
- Critical functionality missing

## Risk Assessment

### Low Risk
- **HTTP Functions**: Direct 1:1 mapping to Container Apps endpoints
- **Business Logic**: Can be preserved exactly as-is
- **Storage Access**: Same managed identity and permissions model

### Medium Risk
- **Timer Functions**: Different scheduling mechanism but well-established patterns
- **Blob Triggers**: Event Grid integration adds complexity but is reliable

### Mitigation Strategies
- **Gradual Migration**: One function at a time
- **Comprehensive Testing**: Unit, integration, and end-to-end tests
- **Monitoring**: Enhanced monitoring during migration period
- **Documentation**: Clear rollback procedures

## Success Metrics

### Technical Metrics
- Deployment success rate > 95%
- Cold start time < 2 seconds
- Error rate < 1%
- Response time < 500ms for HTTP endpoints

### Operational Metrics
- Deployment complexity reduction (measured by deployment steps)
- Development velocity increase
- Troubleshooting time reduction
- Infrastructure drift elimination

## Conclusion

Container Apps migration would significantly improve:
1. **Developer Experience**: Standard Docker development workflow
2. **Deployment Reliability**: No more Azure Functions packaging issues
3. **Operational Simplicity**: Clear, consistent infrastructure patterns
4. **Future Flexibility**: Not locked into Azure Functions programming models

The migration is feasible with manageable risk, particularly given our HTTP-heavy function architecture and existing containerization expertise.
