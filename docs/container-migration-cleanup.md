# Container Migration Cleanup Plan

**Date**: August 14, 2025  
**Status**: Legacy Azure Functions cleanup required

## Overview

The project has successfully migrated 3 of 6 services to containerized FastAPI microservices, but legacy Azure Functions infrastructure and references remain that need cleanup.

## Completed Migrations ✅

### Content Collector (SummaryWombles)
- **Status**: ✅ Complete containerized FastAPI service
- **Tests**: 44 tests passing (100%)
- **Location**: `containers/content-collector/`
- **API**: FastAPI with health, status, and process endpoints
- **Migration Notes**: Successfully converted from Azure Function to standalone container

### Content Processor  
- **Status**: ✅ Complete containerized FastAPI service
- **Tests**: 42 tests passing (100%)
- **Location**: `containers/content-processor/`
- **Migration Notes**: Fully containerized with comprehensive test coverage

### Content Enricher
- **Status**: ✅ Complete containerized FastAPI service  
- **Tests**: 33 tests passing (100%)
- **Location**: `containers/content-enricher/`
- **Migration Notes**: AI-powered enhancement service now containerized

## Legacy Cleanup Required 🔴

### Infrastructure (Terraform)
**File**: `infra/main.tf`
**Issues**:
- Lines 198-206: `azurerm_service_plan` resource still defined
- Lines 208-238: `azurerm_linux_function_app` resource still defined
- Lines 247-255: Role assignments for function app managed identity
- Function app configuration with Python runtime settings

**Action Required**: Remove all Azure Function App resources and related dependencies

### CI/CD Pipelines
**Files**: 
- `.github/workflows/staging-deployment.yml` (lines 219-223)
- `.github/workflows/production-deployment.yml` (lines 225-232)

**Issues**:
- Azure Functions Core Tools installation commands
- `func azure functionapp publish` deployment commands
- References to non-existent `azure-function-deploy` directory
- Function-based integration tests

**Action Required**: Replace with container deployment workflows

### Key Vault Configuration
**File**: `infra/main.tf`
**Issues**:
- `azurerm_key_vault_secret.contentranker_function_key`
- `azurerm_key_vault_secret.summarywomble_function_key`
- Function key placeholders and content types

**Action Required**: Replace with container-appropriate secrets (API keys, connection strings)

### Documentation Updates
**Files**: 
- `.github/agent-instructions.md`
- Various docs referencing Azure Functions patterns

**Issues**:
- Architecture documentation still describes Azure Functions patterns
- Development workflows reference function deployment
- Agent instructions mention Azure Functions as primary architecture

**Action Required**: Update to reflect containerized microservices architecture

## Remaining Container Implementation 🟡

### Content Ranker
- **Status**: 🟡 Directory structure exists, needs implementation
- **Location**: `containers/content-ranker/`
- **Next Steps**: Implement ranking algorithms and FastAPI endpoints

### Scheduler  
- **Status**: 🟡 Directory structure exists, needs implementation
- **Location**: `containers/scheduler/`
- **Next Steps**: Implement job scheduling and workflow management

### Static Site Generator
- **Status**: 🟡 Directory structure exists, needs implementation  
- **Location**: `containers/ssg/`
- **Next Steps**: Implement site generation and templating system

## Migration Benefits Achieved ✅

1. **Dependency Management**: No more Azure Functions runtime dependency issues
2. **Local Development**: Full local testing with FastAPI dev servers
3. **Container Portability**: Services can run anywhere Docker is supported
4. **Test Coverage**: 119 comprehensive tests across implemented containers
5. **API Standardization**: Consistent FastAPI patterns across all services
6. **Development Speed**: Faster development cycles with local containers

## Next Actions Priority

1. **HIGH**: Clean up legacy Azure Functions infrastructure
2. **HIGH**: Update CI/CD pipelines for container deployment  
3. **MEDIUM**: Implement remaining 3 containers
4. **MEDIUM**: Update all documentation to reflect container architecture
5. **LOW**: Optimize container images and deployment strategies

## Technical Debt Removed

- ❌ Azure Functions runtime dependencies
- ❌ Python package conflicts in Functions environment
- ❌ Azure Functions cold start delays
- ❌ Functions-specific debugging challenges
- ❌ Azure Functions pricing unpredictability

## Architecture Evolution

```
BEFORE (Azure Functions):
Timer Trigger → Azure Function → Blob Storage → Another Function

AFTER (Containers):
Scheduler Container → HTTP API → Content Processor → HTTP API → Enricher
```

The new architecture provides better separation of concerns, easier testing, and more flexible deployment options.
