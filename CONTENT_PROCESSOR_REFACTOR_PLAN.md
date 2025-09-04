# Content-Processor Refactoring Plan

**Issue**: #390  
**Branch**: feature/content-processor-standardization  
**Status**: Planning Phase

## Refactoring Scope

This document tracks the comprehensive refactoring of content-processor to align with new architectural standards.

## Implementation Phases

### Phase 1: Foundation ✋ READY TO START
- Update requirements.txt with pydantic-settings, tenacity
- Create new config.py using pydantic-settings BaseSettings
- Integrate secure_error_handler.py for consistent error responses

### Phase 2: API Standardization
- Remove /api/processor/* paths, use root-level endpoints
- Integrate standard_endpoints.py for consistent responses
- Add proper OpenAPI documentation
- Implement standard health/status endpoints

### Phase 3: External API Integration
- Add tenacity retry logic for OpenAI/external calls
- Implement proper error handling for API failures
- Add logging consistency with other containers

### Phase 4: Azure Function Integration (NEW)
- Create Azure Function for blob storage trigger
- Add Service Bus queue for topic distribution
- Implement parallel container scaling (one per topic)
- Configure Container Apps auto-scaling (0→N instances)
- Add quality assessment and iteration logic
- Configure function app with proper RBAC permissions

### Phase 5: Testing & Validation
- Update tests for new API structure
- Test end-to-end with content-collector integration
- Test Azure Function trigger integration
- Validate Azure deployment and cost impact
- Security scan with pre-commit hooks (OWASP compliance)

## Additional Requirements

### Code Quality Standards
- ✅ Keep all files <400 lines (functional decomposition)
- ✅ Follow PEP8 with pre-commit linters
- ✅ OWASP security guidelines compliance
- ✅ Functional programming patterns where applicable
- ✅ Container security best practices

### Architecture Pattern
- ✅ **Parallel Processing**: One container instance per topic/article
- ✅ **Auto-scaling**: Azure Container Apps scales 0→N based on queue depth
- ✅ **Event-driven**: Blob storage events trigger function → queue → containers
- ✅ **Quality-driven**: Containers work until quality bar met, then sleep
- ✅ **Cost-efficient**: Pay only for active processing time
- ✅ **Scalable**: Handles 5-10 concurrent articles, scales for future growth

### Processing Flow
```
New Topic Blob → Azure Function → Service Bus Queue → Container Instance (per topic)
                                                   ↓
Container: Process → Quality Check → Iterate until quality bar → Sleep/Terminate
```

## Progress Tracking

This file will be updated as work progresses and removed when refactoring is complete.
