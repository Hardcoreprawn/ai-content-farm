# TODO - AI Content Farm Refactor

**Status**: ✅ **Topic Intelligence Collector Complete & Deploying!**  
**Goal**: Daily digest at jablab.com with 5 most interesting topics + deep dives

## � **MAJOR BREAKTHROUGH - Phase 1 Complete!**

### ✅ **What We Just Accomplished:**
1. **✅ Topic Intelligence Collector Built** - Focus on trend analysis, not content scraping
2. **✅ Production Code Committed** - All validation checks pass 
3. **✅ CI/CD Pipeline Running** - Deploying to Azure Container Apps
4. **✅ Reddit API Integration** - PRAW with Azure Key Vault for production
5. **✅ Clean Architecture** - Standardized FastAPI responses throughout

### 🚀 **The New Collector Does:**
- **🎯 Listens to conversations** across Reddit, LinkedIn, etc.
- **📊 Identifies trending topics** using engagement clustering
- **🔬 Generates research recommendations** with credible sources
- **📝 Creates original analysis** rather than content aggregation
- **🏗️ Standardized APIs** ready for the next pipeline stage

## 🔄 **Current Status: Deploying**

**CI/CD Pipeline**: Rerunning after Docker timeout (common issue)
**Next**: Once deployed, the collector will be live in Azure at:
- `https://ai-content-prod-collector.victoriousbeach-e62a5683.uksouth.azurecontainerapps.io/`

## 📋 **Phase 2: Processor (Next 1-2 weeks)**
**Goal**: Transform trending topics into research-ready content

- [ ] **Research Engine**: Fact-check and find credible sources for topics
- [ ] **Content Prioritization**: Rank topics by research value and timeliness  
- [ ] **Reference Gathering**: Build citation networks for deep-dive articles
- [ ] **Quality Scoring**: Filter topics suitable for jablab.com audience

## 📋 **Phase 3: Publisher (Following 1-2 weeks)**
**Goal**: Generate beautiful static site at jablab.com

- [ ] **Article Generation**: Create briefing + deep-dive versions
- [ ] **Static Site Builder**: Clean, fast website generation
- [ ] **Domain Integration**: Configure jablab.com to serve content
- [ ] **Automated Pipeline**: Full topic-to-publication flow

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
