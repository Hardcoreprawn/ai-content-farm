# TODO - AI Content Farm

**Status**: 🎉 **STORAGE QUEUE MIGRATION COMPLETE** - Full end-to-end automation working!  
**Achievement**: Successfully migrated from Service Bus to Storage Queues with managed identity  
**Current Priority**: � **SCHEDULER ENHANCEMENT** - Multi-topic intelligence and optimization  
**Goal**: Enhanced scheduler capabilities → Content quality improvements → Performance optimization

## ✅ Recent Achievements

### 🎉 MIGRATION COMPLETE: Storage Queue Integration - Issue #513 ✅ RESOLVED
**Achievement**: Successfully completed Storage Queue migration for both containers
**Resolution**: All authentication conflicts resolved, full automation working
**Implementation**: Content-collector → blob save → queue message → KEDA scale → content-processor
**Testing**: 123 tests passing (content-collector), 33 tests passing (content-processor)
**Security**: OWASP-compliant error handling and input sanitization implemented

### 🔧 Infrastructure Status - ✅ COMPLETE ✅  
**Target**: Storage Queues with KEDA scaling - **FULLY IMPLEMENTED AND TESTED**

#### ✅ Infrastructure Complete
- ✅ **Storage Queues exist** (`content-processing-requests`, `site-generation-requests`)
- ✅ **KEDA scaling configured** on content-processor with `azure-queue` scaler  
- ✅ **Managed identity authentication** working for blob storage and queues
- ✅ **Storage Queue client** available in libs package

#### ✅ Application Integration Complete
- ✅ **Content-collector** saves to blob storage successfully
- ✅ **Queue automation working** - collector sends processing requests automatically
- ✅ **Storage queue routers** - both containers have working storage queue endpoints
- ✅ **KEDA scaling ready** - confirmed working configuration with lazy loading for tests
- ✅ **Service Bus legacy code removed** - clean migration completed

#### 🔄 Next Steps for Full Automation  
- [ ] **Fix queue automation** in content-collector (Issue #513)
- [ ] **Add manual API endpoints** to processor/generator (Issue #512)
- [ ] **Test end-to-end pipeline** with both manual and automatic triggers
- [ ] **Verify KEDA scaling** triggers correctly with queue messages

### 🎯 Phase 1: MVP Infrastructure - ✅ COMPLETED ✅
**Achievement**: **Infrastructure and basic collection functionality operational**

**Infrastructure Validation (2025-09-17):**
- ✅ **Storage Queues deployed** with KEDA scaling configuration
- ✅ **Content collection working** (BBC test: 3 items saved successfully)
- ✅ **Dependency consolidation** implemented via libs package
- ✅ **Environment detection** fixed (prod vs dev resource groups)
- ✅ **CI/CD pipeline** validates builds and tests successfully  
- ✅ **6-hour recurrence schedule** operational and validated

### Major Accomplishments Complete
1. **✅ Architecture Simplified** - Reduced from 4 to 3 containers (25% complexity reduction)
2. **✅ Content-Generator Merged** - AI generation functionality integrated into content-processor
3. **✅ API Standardization** - All containers use shared library pattern with consistent responses
4. **✅ Zero Regression** - All existing functionality preserved during integration
5. **✅ Enhanced Capabilities** - content-processor now handles both processing AND AI generation
6. **✅ Scheduler Design** - Comprehensive Azure Logic App scheduler design completed
7. **✅ MVP Scheduler Deployed** - Production Logic App with 6-hour recurrence successfully deployed

## 🎯 Current Priority: Build Content Collection Scheduler

### 🚀 Phase 1: MVP Scheduler (Week 1) - ✅ COMPLETED
**Goal**: Basic working scheduler calling content-collector on fixed intervals

#### Infrastructure Tasks ✅ COMPLETED
- [x] **Add Logic App Terraform resources** (`infra/scheduler.tf`) ✅ COMPLETED
- [x] **Configure managed identity and RBAC permissions** ✅ COMPLETED
- [x] **Create Azure Table Storage for topic configuration** ✅ COMPLETED
- [x] **Deploy initial infrastructure with Terraform** ✅ COMPLETED

#### Logic App Development ✅ COMPLETED
- [x] **Create basic Logic App workflow** (6-hour recurrence) ✅ COMPLETED
- [x] **Implement managed identity authentication** to content-collector ✅ COMPLETED
- [x] **Multi-topic collection** (Technology, Programming, Science topics) ✅ COMPLETED
- [x] **Basic error handling and logging** ✅ COMPLETED

#### Testing & Validation 🎉 PHASE 1 COMPLETE
- [x] **Test Logic App triggers content-collector** successfully ✅ DEPLOYED
- [x] **Verify managed identity authentication** works ✅ DEPLOYED  
- [x] **Logic App workflow deployed via Terraform** ✅ DEPLOYED
- [x] **6-hour recurrence trigger active** ✅ VERIFIED
- [x] **HTTP action calls content-collector API** ✅ VERIFIED
- [x] **Monitor costs and execution frequency** (estimated $1.50/month) ✅ COMPLETED
- [x] **Scheduler budget recreated after lock management** ✅ COMPLETED
- [x] **Resource group lock properly restored** ✅ VERIFIED
- [x] **Manual test of end-to-end workflow** ✅ **SUCCESSFULLY TESTED**
- [x] **End-to-end validation complete** ✅ **30 Reddit posts collected successfully**
- [x] **Dynamic Terraform references working** ✅ **Container App FQDN properly linked**
- [x] **Budget lifecycle optimization** ✅ **Prevents unnecessary recreation**

### 🔒 Security Review Required (URGENT PRIORITY)
**Goal**: Review and harden security after IP restrictions removal  
**Issue**: #433 - Comprehensive Security Review & Hardening Required

#### 🚨 Critical Security Items 
- [ ] **Container App Access Control** - Currently open to all internet traffic
- [ ] **Azure Service Tags Implementation** - Replace removed IP restrictions with Logic Apps service tag
- [ ] **API Key Authentication** - Implement proper authentication/authorization  
- [ ] **Logic App Permission Audit** - Apply principle of least privilege
- [ ] **Security Monitoring** - Enable access logs and incident detection

**⚠️ IMPORTANT**: Security hardening should be completed before proceeding with Phase 2 enhancements.

### 🎯 Phase 2: Multi-Topic Intelligence (Week 2-3) - 🚀 ACTIVE
**Goal**: Expand to multiple topics with dynamic configuration and workflow improvements

#### Topic Management
- [ ] **Implement 5-6 topic configurations** (Technology, Programming, Science, Bees, etc.)
- [ ] **Dynamic subreddit mapping** per topic
- [ ] **Topic-specific collection criteria**
- [ ] **Schedule variation by topic priority**

#### Enhanced Workflow
- [ ] **For-each loop to process multiple topics**
- [ ] **Dynamic request building** based on topic config
- [ ] **Parallel execution** for independent topics
- [ ] **Improved error handling** per topic

### ⚡ Phase 3: Advanced Orchestration (Week 4+) - FUTURE
**Goal**: Intelligent scheduling with source discovery and optimization

#### Smart Features
- [ ] **Source discovery engine** - identify high-value sources
- [ ] **Adaptive scheduling** - ML-based frequency optimization
- [ ] **Cross-platform preparation** - Bluesky/Mastodon framework
- [ ] **Advanced analytics** - content performance correlation

## 🏗️ Enhanced Architecture with Scheduler

**New Architecture with Scheduler:**
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Logic App     │    │ Content Collector│    │ Content Topics  │
│   Scheduler     │───▶│    (HTTPS)       │───▶│   Storage       │
│                 │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │
         ▼                        ▼
┌─────────────────┐    ┌──────────────────┐
│   Schedule      │    │    Collection    │
│   Configuration │    │    Analytics     │
│   Storage       │    │    Feedback      │
└─────────────────┘    └──────────────────┘
```

**Content Pipeline (Unchanged):**
```
Reddit/Web → content-collector → content-processor → site-generator → jablab.com
                                      ↑
                              Enhanced with AI Generation
                           (Processing + TLDR/Blog/Deepdive)
```

## 📋 Immediate Actions (This Week)

### Priority 1: Deploy Scheduler Infrastructure
```bash
# Deploy scheduler infrastructure
cd /workspaces/ai-content-farm/infra
terraform plan
terraform apply

# Verify Logic App creation
az logic workflow list --resource-group <resource-group>
```

### Priority 2: Configure Logic App Workflow
```bash
# Deploy Logic App workflow definition
az logic workflow create \
  --resource-group <resource-group> \
  --name <logic-app-name> \
  --definition @docs/scheduler/logic-app-workflow.json
```

### Priority 3: Test Scheduler → Content-Collector Integration
```bash
# Test manual Logic App trigger
az logic workflow trigger run \
  --resource-group <resource-group> \
  --name <logic-app-name> \
  --trigger-name Recurrence

# Verify content-collector receives authenticated requests
curl -X GET "https://<content-collector-url>/health"
```

### Priority 4: End-to-End Pipeline Testing (Parallel)
```bash
# Test complete flow with scheduler
# 1. Scheduler triggers content collection
# 2. Content flows through content-processor  
# 3. Site generation creates website
# 4. Monitor costs and performance
```

## 🎯 Success Metrics

### Phase 1 Success Criteria
- [ ] Logic App executes every 4 hours without errors
- [ ] Content-collector receives valid authenticated requests
- [ ] Content flows through to blob storage and content-processor
- [ ] Total additional monthly cost < $2
- [ ] End-to-end content flow works (Scheduler → Reddit → Website)

### Technical Metrics
- ✅ **3-container architecture** running successfully
- ✅ **content-processor** handling both processing AND generation
- ✅ **10/13 tests passing** (3 skipped for future features)
- 🔄 **Logic App scheduler** triggering collections (Phase 1)
- 🔄 **End-to-end pipeline** working (Scheduler → Reddit → Website)
- 🔄 **Azure costs** under $40/month (including scheduler)

### Business Metrics
- 🔄 **Automated content collection** every 4-6 hours
- 🔄 **Topic-based content** from multiple subreddits
- 🔄 **Quality articles** (TLDR, blog, deepdive formats)
- 🔄 **Cost-effective scaling** with Logic App pay-per-execution

## 📊 Scheduler Design Documents

### Created Documentation
- ✅ **SCHEDULER_DESIGN.md** - Comprehensive scheduler architecture and design
- ✅ **SCHEDULER_IMPLEMENTATION.md** - Detailed 3-phase implementation roadmap
- ✅ **scheduler.tf** - Complete Terraform infrastructure for Logic App
- ✅ **logic-app-workflow.json** - Basic Logic App workflow definition

### Topic Configuration Example
```json
{
  "topic_id": "technology",
  "display_name": "Technology", 
  "schedule": { "frequency_hours": 4, "priority": "high" },
  "sources": {
    "reddit": {
      "subreddits": ["technology", "programming", "MachineLearning"],
      "limit": 20, "sort": "hot"
    }
  },
  "criteria": { "min_score": 50, "min_comments": 10 }
}
```

---

**Current Status**: Scheduler infrastructure designed and ready for implementation! Moving from manual to automated content collection. 🚀

## 🚫 What NOT to Do

- ❌ Don't add new features until basic scheduler works
- ❌ Don't create new documentation files (use existing structure)
- ❌ Don't over-engineer the Logic App workflow initially
- ❌ Don't change container architecture during scheduler implementation
- ❌ Don't optimize before proving scheduler functionality

## ✅ What's Working (Don't Break)

- Infrastructure: Azure Container Apps, Terraform, CI/CD
- Security: Most scans passing, OWASP compliance
- content-processor: 32/36 tests passing, mostly standardized
- Basic container deployment and service discovery
- Simplified 3-container architecture

## 🛠️ Technical Standards (Consistently Applied)

### Standard API Pattern
```
# Common endpoints (all services)
GET  /                    # Service info with available endpoints
GET  /health              # Health check  
GET  /status              # Detailed operational status
GET  /docs                # Auto-generated API docs

# Service-specific business logic endpoints
## Content Collector ✅ IMPLEMENTED
POST /collections         # Create/trigger collections
POST /discoveries         # Content discovery
GET  /sources             # List available sources

## Content Processor ❌ MISSING - See Issue #512
POST /process             # Process collected content
POST /generate            # AI content generation
GET  /queue/status        # Processing queue status

## Site Generator ❌ MISSING - See Issue #512
POST /generate            # Generate static sites
POST /publish             # Publish generated content
GET  /sites               # List generated sites
```

### Standard Response Format
```json
{
  "status": "success|error",
  "message": "Human readable message", 
  "data": { /* response data */ },
  "metadata": { /* service metadata */ }
}
```

### Enhanced Content-Processor Endpoints
```
# Content Processing (existing)
POST /process                            # Core content processing
POST /wake-up                            # Wake up work queue
GET  /process/status                     # Queue status

# AI Content Generation (newly integrated)
POST /generate/tldr                      # Generate TLDR articles (200-400 words)
POST /generate/blog                      # Generate blog posts (600-1000 words)  
POST /generate/deepdive                  # Generate deep analysis (1200+ words)
POST /generate/batch                     # Start batch generation
GET  /generation/status/{batch_id}       # Get batch status
```

## 📋 Immediate Actions (This Week)

### Priority 1: End-to-End Pipeline Testing
```bash
# Test complete flow
cd /workspaces/ai-content-farm
docker-compose up -d

# 1. Test content collection
curl -X POST "http://localhost:8001/collect"

# 2. Test content processing + generation
curl -X POST "http://localhost:8002/generate/blog" \
  -H "Content-Type: application/json" \
  -d '{"topic": "AI trends", "source_material": "Latest developments"}'

# 3. Test site generation
curl -X POST "http://localhost:8003/generate-site"
```

### Priority 2: Real AI Integration
```bash
# Set up Azure OpenAI or OpenAI API keys
export OPENAI_API_KEY="your-key-here"  # pragma: allowlist secret
export AZURE_OPENAI_ENDPOINT="your-endpoint"
export AZURE_OPENAI_API_KEY="your-key"  # pragma: allowlist secret

# Test real AI generation
curl -X POST "http://localhost:8002/generate/tldr" \
  -H "Content-Type: application/json" \
  -d '{"topic": "Climate change solutions", "source_material": "Recent research"}'
```

### Priority 3: Clean Architecture Validation
```bash
# Verify 3-container setup works
docker-compose ps
# Should show: content-collector, content-processor, site-generator

# Verify no content-generator references remain
grep -r "content-generator" . --exclude-dir=docs/archived --exclude-dir=.git
# Should only show archived references
```

## 🎯 Success Metrics

### Technical Metrics:
- ✅ **3-container architecture** running successfully
- ✅ **content-processor** handling both processing AND generation
- ✅ **10/13 tests passing** (3 skipped for future features)
- 🔄 **End-to-end pipeline** working (Reddit → Website)
- 🔄 **Real AI integration** generating quality content
- 🔄 **Azure costs** under $40/month

### Business Metrics:
- 🔄 **Working website** with generated content
- 🔄 **Daily content generation** from Reddit trends
- 🔄 **Quality articles** (TLDR, blog, deepdive formats)
- 🔄 **SEO optimization** driving organic traffic

---

**Current Status**: Architecture simplification complete! Ready for end-to-end pipeline testing and real AI integration. 🚀

## 🚫 What NOT to Do

- ❌ Don't add new features until basic pipeline works
- ❌ Don't create new documentation files  
- ❌ Don't refactor multiple containers simultaneously
- ❌ Don't change infrastructure until containers work
- ❌ Don't optimize before proving functionality

## ✅ What's Working (Don't Break)

- Infrastructure: Azure Container Apps, Terraform, CI/CD
- Security: Most scans passing, OWASP compliance
- content-processor: 32/36 tests passing, mostly standardized  
- Basic container deployment and service discovery
