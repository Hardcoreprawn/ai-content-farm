# Daily Implementation Plan - Container Standardization

**Date**: September 3, 2025  
**Goal**: Get container application working end-to-end with standardized APIs  
**Status**: Ready to implement

---

## 🎯 **Today's Mission**
Fix the API mess from yesterday's security refactor and get end-to-end pipeline working.

### **What's Working**
- ✅ **content-collector**: Responds to health checks, has working Reddit collection
- ✅ **Security**: All critical vulnerabilities resolved
- ✅ **Infrastructure**: Azure deployment working
- ✅ **Foundation**: Good shared library in `/libs/`

### **What's Broken** 
- ❌ **content-processor**: Returns `{"detail":"Not Found"}` 
- ❌ **API inconsistency**: Each service uses different endpoint patterns
- ❌ **End-to-end**: Pipeline not tested after security refactor

---

## 📋 **Today's Action Plan**

### **Phase 1: Fix & Standardize APIs** ⏱️ *2 hours*

#### **1.1 content-collector API standardization** *(30 min)*
- Update tests for `/health`, `/status`, `/process` endpoints
- Add standard endpoints alongside existing `/api/content-womble/*` 
- Test locally, deploy to Azure, verify working

#### **1.2 Fix content-processor** *(60 min)*  
- Diagnose why it's returning 404s
- Implement standard endpoints (`/health`, `/status`, `/process`)
- Test and deploy

#### **1.3 Verify other containers** *(30 min)*
- Test content-generator and site-generator endpoints
- Document what's working/broken

### **Phase 2: End-to-End Pipeline Test** ⏱️ *1 hour*

#### **2.1 Manual E2E Test**
1. **Trigger collection**: POST to content-collector `/process`
2. **Check processing**: Verify content-processor can handle data  
3. **Test generation**: Verify site-generator produces output
4. **Validate costs**: Check Azure spending

#### **2.2 Fix Any Breaks**
- Address issues found during E2E test
- Ensure complete Reddit → articles → website flow

### **Phase 3: Quick Wins** ⏱️ *1 hour*

#### **3.1 Shared Library Enhancement**
- Move KeyVault client from content-collector to `/libs/`
- Add common config patterns to reduce duplication
- Update containers to use shared patterns

#### **3.2 Documentation Update**
- Update API endpoints in README
- Document working deployment URLs
- Update TODO.md with next priorities

---

## 🔧 **Implementation Decisions**

### **API Standard** (FINAL)
```
GET  /health           # Service health check  
GET  /status           # Detailed service info
GET  /docs             # FastAPI auto-generated docs
POST /process          # Main business logic
GET  /                 # Service overview
```

### **Service Naming** (FINAL)
- **content-collector** (not "content-womble")
- **content-processor** 
- **content-generator**
- **site-generator**

### **Shared Library Scope**
- ✅ **Move**: KeyVault client, common config patterns
- ❌ **Keep separate**: Business logic, container-specific endpoints
- ✅ **Already shared**: StandardResponse, BlobStorageClient

### **Base Image Strategy**  
- **Decision needed**: Use shared base vs individual builds
- **For now**: Keep individual builds, optimize later

---

#### Issue #6: Complete content-collector API migration
```
**Priority**: LOW - Already partially done
**Scope**: Remove old /api/content-womble/* endpoints
**Files**: containers/content-collector/main.py, endpoints.py
**Success**: Only standard endpoints remain
```

## Detailed Implementation Steps

### Step 1: Foundation Work (Issues #2, #3)

#### Shared Base Image Enhancement
```bash
# Create enhanced base image
cd containers/base/
# Build shared base with common dependencies
# Update all container Dockerfiles to use shared base
```

#### Standard Library Enhancement
```python
# Move to libs/
- KeyVaultClient (from content-collector)
- Common config patterns 
- Enhanced error handling
- Standard logging setup
```

### Step 2: Container API Standardization (Issues #1, #4, #5, #6)

#### Standard Endpoint Pattern (Apply to All)
```python
# Replace service-specific endpoints with:
@app.get("/health", response_model=StandardResponse)
@app.get("/status", response_model=StandardResponse)  
@app.post("/process", response_model=StandardResponse)
@app.get("/", response_model=StandardResponse)

# Remove old endpoints:
# /api/{service-name}/health -> /health
# /api/{service-name}/status -> /status
# /api/{service-name}/process -> /process
```

### Step 3: Testing & Deployment Strategy

#### Per-Container Testing
```bash
# 1. Update tests first
# 2. Add standard endpoints alongside old ones
# 3. Test locally with pytest
# 4. Deploy to Azure and verify
# 5. Remove old endpoints
# 6. Final verification
```

#### End-to-End Pipeline Testing
```bash
# Test complete flow:
# Reddit -> content-collector -> content-processor -> site-generator -> website
curl https://ai-content-prod-collector.../health
curl https://ai-content-prod-processor.../health  
curl https://ai-content-prod-site-generator.../health
```

## Success Metrics

### Technical Metrics
- [ ] All containers respond to standard `/health`, `/status` endpoints
- [ ] Code duplication reduced by >50% through shared libraries
- [ ] Build times improved through shared base image
- [ ] Test coverage maintained >80% during migration

### Operational Metrics  
- [ ] End-to-end pipeline functional (Reddit → website)
- [ ] Response times <2s for all health checks
- [ ] Zero deployment failures during migration
- [ ] Cost maintained at ~$30-40/month target

### Documentation Metrics
- [ ] API contracts documented for all endpoints
- [ ] Deployment guides updated
- [ ] Architecture documentation current
- [ ] Issue tracking maintained throughout

---

**Next Action**: Create GitHub issues #1-6 and begin with Issue #1 (content-processor fix)
