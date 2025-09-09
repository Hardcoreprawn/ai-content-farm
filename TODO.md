# TODO - AI Content Farm

**Status**: 🎉 **SCHEDULER DEPLOYED** - MVP Logic App Successfully Deployed to Production  
**Goal**: Enhance content collection scheduler + optimize pipeline performance

## ✅ Recent Achievements

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

#### Testing & Validation 🔄 READY FOR TESTING
- [ ] **Test Logic App triggers content-collector** successfully
- [ ] **Verify managed identity authentication** works
- [ ] **Confirm content flows through** to content-processor
- [x] **Monitor costs and execution frequency** (estimated $1.50/month) ✅ COMPLETED

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
GET  /health              # Health check
GET  /status              # Detailed status  
GET  /docs                # Auto-generated docs
POST /process             # Main business logic (or /generate for content-processor)
GET  /                    # Service info
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
