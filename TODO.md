# TODO - Personal Content Curation Platform

**Status**: ✅ Research Complete - Ready for Systematic Implementation  
**Goal**: Standardized, efficient container platform with consistent APIs

## 🔬 Research Completed (September 3, 2025)

### ✅ Standard Library Research Results
- **✅ ADOPT: pydantic-settings** - Replace custom Config classes (better type safety)
- **✅ KEEP: secure_error_handler.py** - OWASP compliance, low maintenance (<1hr/year)
- **✅ ADD: tenacity** - Retry logic for external APIs (Reddit, OpenAI)
- **🔍 RESEARCH: fastapi-utils** - Check vs our custom standard_endpoints.py
- **⏳ LATER: Python 3.12** - 25% performance boost, after standardization

### ✅ Current Container Status Analysis
- **✅ content-collector**: Working (health responds), needs API standardization
- **❌ content-processor**: Broken (404 errors), needs fix + standardization  
- **✅ content-generator**: Working but inconsistent API paths
- **✅ site-generator**: Working but inconsistent API paths

## 🎯 Systematic Implementation Plan

### Phase 1: Foundation & Standards (Days 1-2)
**Container Standardization Priority:**
1. **content-collector** - Working base, standardize APIs first
2. **content-processor** - Fix and standardize (currently broken)
3. **content-generator** - Migrate to standard endpoints
4. **site-generator** - Migrate to standard endpoints

**Standard Library Enhancement:**
- Replace Config classes with pydantic-settings
- Add tenacity for external API retry logic
- Keep secure_error_handler.py (research shows low maintenance)

### Phase 2: API Standardization (Days 2-3)
**Target API Design (ALL containers):**
```
GET  /health              # Standard health check
GET  /status              # Detailed service status
GET  /docs                # FastAPI auto-generated docs  
POST /process             # Main business logic
GET  /                    # Service info & available endpoints
```

**Remove service-specific paths:**
- ❌ `/api/content-womble/health` → ✅ `/health`
- ❌ `/api/processor/health` → ✅ `/health`
- ❌ `/api/content-generator/health` → ✅ `/health`

### Phase 3: Integration & Production (Day 3)
- End-to-end pipeline testing (Reddit → articles → website)
- Azure deployment validation
- Cost verification (~$30-40/month target)
- Performance and security validation

## 🎫 GitHub Issues to Create

### Foundation Issues
1. **Standard Library: Replace Config with pydantic-settings**
2. **Standard Library: Add tenacity for external API retry**
3. **Research: fastapi-utils vs custom standard_endpoints**

### Container Standardization Issues  
4. **content-collector: API standardization (/health, /status, /docs)**
5. **content-processor: Fix deployment + API standardization**
6. **content-generator: Migrate to standard API endpoints**
7. **site-generator: Migrate to standard API endpoints**

### Integration Issues
8. **End-to-end pipeline testing and validation**
9. **Documentation: Update API contracts and deployment guides**

## ✅ What's Working (Keep)
- Content Collection: Reddit API + 4 web sources working
- Infrastructure: Azure Container Apps, Key Vault, CI/CD
- Security: All vulnerabilities resolved, OWASP-compliant error handling
- Deduplication: Working within collection sessions
