# Content-Processor Refactoring Plan

**Issue**: #390  
**Branch**: feature/content-processor-standardization  
**Status**: Planning Phase

## Refactoring Scope

This document tracks the comprehensive refactoring of content-processor to align with new architectural standards.

## Implementation Phases

### Phase 1: Foundation ✋ **IN PROGRESS**
- ✅ **SHARED**: Add pydantic-settings and tenacity to shared-versions.toml
- ✅ **SHARED**: Update requirements.txt using config/shared-versions.toml
- ✅ **TESTS**: Write tests for new API structure FIRST (test-driven development)
- 🔄 **SHARED**: Create new config.py using pydantic-settings BaseSettings  
- 🔄 **SHARED**: Integrate libs/secure_error_handler.py for consistent error responses

### Phase 2: API Standardization
- Remove /api/processor/* paths, use root-level endpoints
- **SHARED**: Integrate libs/standard_endpoints.py for consistent responses
- **FASTAPI**: Add proper OpenAPI documentation (auto-generated)
- **SHARED**: Implement standard health/status endpoints using standard_endpoints.py

### Phase 3: External API Integration
- Add tenacity retry logic for OpenAI/external calls
- Implement proper error handling for API failures
- Add logging consistency with other containers
- **NEW**: Configure multi-region OpenAI endpoints (UK South + West Europe)
- **NEW**: Add model selection and routing logic
- **NEW**: Implement article scoring and evaluation framework
- **NEW**: Add cost tracking per model/prompt combination

### Phase 4: Azure Function Integration (NEW)
- **EXISTING**: Use existing Azure Function infrastructure pattern from functions/static-site-deployer/
- **AZURE**: Add Service Bus namespace + queue (Terraform managed)
- **AZURE**: Configure existing Container Apps auto-scaling with Service Bus rules
- **AZURE**: Leverage existing Container App Environment (no new infrastructure)
- Add quality assessment and iteration logic
- **AZURE**: Use existing RBAC pattern from current function apps

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

### Future Experimentation Infrastructure
- ✅ **Model Evaluation**: Framework for scoring quality, cost, voice consistency
- ✅ **Multi-Region Support**: UK South (existing) + West Europe (advanced models)
- ✅ **Writing Voices**: Consistent character profiles and style management
- ✅ **A/B Testing**: Infrastructure for model comparison experiments
- ✅ **Cost Optimization**: Intelligent model selection based on topic complexity
- ✅ **Scalable Design**: Foundation supports future AI model additions

### Architecture Pattern
- ✅ **Parallel Processing**: One container instance per topic/article
- ✅ **Auto-scaling**: Azure Container Apps scales 0→N based on queue depth
- ✅ **Event-driven**: Blob storage events trigger function → queue → containers
- ✅ **Quality-driven**: Containers work until quality bar met, then sleep
- ✅ **Cost-efficient**: Pay only for active processing time
- ✅ **Scalable**: Handles 5-10 concurrent articles, scales for future growth
- ✅ **Multi-model**: Support multiple AI models with evaluation and scoring
- ✅ **Multi-region**: UK South (primary) + West Europe (advanced models)
- ✅ **Experimentation-ready**: Model comparison, cost tracking, voice consistency

### Processing Flow
```
New Topic Blob → Azure Function → Service Bus Queue → Container Instance (per topic)
                                                   ↓
Container: Model Selection → Process → Quality/Cost Evaluation → Iterate → Sleep/Terminate
                    ↓
            UK South (Cheaper) ←→ West Europe (Advanced)
                    ↓
            Model Scoring & Voice Consistency Tracking
```

### AI Model Strategy (Future-Ready Infrastructure)
- **UK South**: Standard models (cost-efficient, existing setup)
- **West Europe**: Advanced models (GPT-4, Claude-3, etc.)
- **Primary/Secondary**: Failover capability between regions
- **Model Evaluation**: Score quality, cost, voice consistency per model
- **Writing Voices**: Consistent character profiles across models
- **Experimentation**: A/B testing framework for model comparison

## ✅ **MAXIMIZING SHARED/OFF-THE-SHELF COMPONENTS**

### **Shared Internal Components (100% Reuse)**
- ✅ **libs/standard_endpoints.py**: Health, status, docs endpoints
- ✅ **libs/secure_error_handler.py**: OWASP-compliant error handling  
- ✅ **libs/shared_models.py**: Standard response models
- ✅ **config/shared-versions.toml**: Centralized dependency management
- ✅ **Existing Container App Environment**: No new infrastructure needed

### **Azure Off-The-Shelf Services (Managed)**
- ✅ **Azure Container Apps**: Auto-scaling, 0→N instances (existing)
- ✅ **Azure Service Bus**: Message queuing, retry logic, dead letter
- ✅ **Azure Functions**: Blob triggers, event processing (existing pattern)
- ✅ **Azure Blob Storage**: Topic storage, results storage (existing)
- ✅ **Azure Key Vault**: Secret management (existing)
- ✅ **Azure OpenAI**: Multi-region AI models (existing + new West Europe)

### **Standard Python Libraries (Off-The-Shelf)**
- ✅ **pydantic-settings**: Configuration management (replacing custom)
- ✅ **tenacity**: Retry logic for external APIs (replacing custom)
- ✅ **FastAPI**: Auto-generated OpenAPI docs (built-in)
- ✅ **uvicorn**: Production ASGI server (existing)

### **Minimal Custom Development Required**
- ⚡ **Model selection logic**: Topic complexity → model routing
- ⚡ **Quality assessment**: Article scoring framework  
- ⚡ **Service Bus integration**: Message processing in container
- ⚡ **Cost tracking**: Per-model usage metrics

## Progress Tracking

This file will be updated as work progresses and removed when refactoring is complete.
