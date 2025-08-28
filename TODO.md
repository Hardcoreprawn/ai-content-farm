# TODO - AI Content Farm

**Status**: Working system that needs simplification
**Goal**: Reduce costs from $77-110/month to $40-62/month while making it easier to maintain

## 🎯 Current Status: API Standardization ~90% Complete!

✅ **Good News**: Your containers are working and have FastAPI docs!
❌ **Issue Found**: Response format inconsistencies causing Pydantic validation errors

### API Standardization Status:
- ✅ **FastAPI docs working**: All containers have `/docs` endpoints
- ✅ **Health endpoints**: All containers respond to `/health`
- ✅ **StandardResponse imported**: Using `libs/shared_models.py`
- ❌ **Pydantic validation failing**: Response objects not matching schema
- ❌ **Inconsistent formats**: Different containers return different response structures

### Site Generation Status:
- ✅ **Local sites working**: Preview at http://localhost:8005/preview/site_XXXXXX
- ✅ **Generation API working**: Can trigger new site generation
- ❌ **Blob upload issue**: Sites not uploading to storage (local or Azure)
- ❌ **Status endpoint broken**: Pydantic validation errors on status checks

## 🚧 Immediate Fixes Needed (Complete API Standardization)

### 1. Fix Pydantic Response Validation (High Priority)
- [ ] **Site Generator**: Fix `/generate/status/{site_id}` endpoint response format
- [ ] **All Containers**: Ensure all endpoints return proper `StandardResponse` format
- [ ] **Health Endpoints**: Standardize health response format across all containers

**Example Issue Found:**
```python
# Current (broken): Returns raw GenerationStatusResponse object  
return GenerationStatusResponse(...)

# Should be (working): Return StandardResponse wrapper
return StandardResponse(
    status="success",
    message="Status retrieved", 
    data=generation_status.dict(),  # Convert to dict
    metadata={...}
)
```

### 2. Fix Site Upload to Storage (Medium Priority)  
- [ ] **Local Storage**: Debug why sites aren't uploading to Azurite blob storage
- [ ] **Azure Storage**: Verify upload works in production environment
- [ ] **Anonymous Access**: Test public access to uploaded sites

### 3. Test Complete Pipeline (Low Priority)
- [ ] **End-to-end**: Collection → Ranking → Generation → Upload → Public Access
- [ ] **Content Flow**: Verify content flows through all containers properly

## 🔍 Technical Details

### Current Container Breakdown:
1. `collector-scheduler` (timer) + `content-collector` (fetch) → **Data Service**
2. `content-processor` (clean) + `content-ranker` (score) + `content-enricher` (research) + `content-generator` (write) → **Content Service**  
3. `markdown-generator` (convert) + `site-generator` (build) → **Publishing Service**
4. **Scheduler Service** (orchestration)

### Resource Optimization:
- Current: 8 containers × 0.5 CPU + 1Gi RAM = expensive
- Target: 4 containers with right-sized resources:
  - Data Service: 0.25 CPU + 0.5Gi (light API work)
  - Content Service: 1.0 CPU + 2Gi (AI processing)  
  - Publishing Service: 0.25 CPU + 0.5Gi (static files)
  - Scheduler: 0.25 CPU + 0.5Gi (orchestration)

## ✅ Immediate Actions

1. **Find your Azure website URL**:
   ```bash
   az containerapp list --query "[?name=='site-generator'].properties.configuration.ingress.fqdn"
   ```

2. **Test current system locally**:
   ```bash
   docker-compose up -d
   make process-content
   open http://localhost:8006
   ```

3. **Choose your approach** (API first OR container reduction first)

4. **Clean up docs** - Too many overlapping documents in `/docs/`

## 📋 Reference

**Key Documents**:
- `docs/FASTAPI_NATIVE_MODERNIZATION_PLAN.md` - API standardization details
- `docs/CONTAINER_APPS_COST_OPTIMIZATION.md` - Container reduction plan  
- `.github/agent-instructions.md` - Development standards

**Cost Analysis**:
- Current: ~$77-110/month (Container Apps + Service Bus + over-allocated resources)
- Target: ~$40-62/month (optimized resources + no Service Bus)
- **Savings**: 40-50% reduction

---

**Decision needed**: Which approach to start with? Pick one and start implementing!
