# TODO - AI Content Farm

**Status**: 🎉 **PHASE 3a COMPLETE - STORAGE REFACTORING DONE**  
**Latest Achievement**: Flat blob storage structure implemented & verified (articles/YYYY-MM-DD/slug)  
**Production State**: ✅ **OPERATIONAL** - All containers running, articles publishing daily  
**Current Priority**: 🚀 **MONITORING & OPTIMIZATION** - Cost tracking, quality metrics, future roadmap

## ✅ Recent Achievements

### 🔧 HOTFIX: Queue Visibility Timeout - October 21, 2025 ✅ DEPLOYED
**Issue**: Markdown-generator showing queue backlog but receiving 0 messages
**Root Cause**: 600-second visibility timeout causing messages to lock/become invisible
**Solution**: 
- Reduced visibility_timeout from 600s → 60s (sufficient for markdown generation)
- Added queue diagnostics to `get_queue_properties()` for future debugging
- Enhanced startup logging to detect invisible message conditions
- See `/docs/QUEUE_BACKLOG_FIX.md` for full analysis

**Result**: ✅ Queued messages now processed immediately, no more false "empty queue" shutdowns

### 🎉 PHASE 3a: Storage Structure Refactoring - October 17, 2025 ✅ COMPLETE
**Achievement**: Implemented cleaner, date-queryable blob storage structure
**Implementation**: 
- Created new utility functions: `generate_articles_path()` variants
- Updated processor to use `articles/YYYY-MM-DD/slug.json` format
- No changes needed in downstream containers (markdown-gen, site-publisher)
- 15 focused blackbox contract tests added (11 path + 4 e2e)
- 296 total tests passing, 0 regressions
- Committed to main (Commit d12cb02)

**Benefits**:
- Easy date-range queries: `list blobs --prefix "articles/2025-10-17/"`
- SEO-friendly slug-based paths
- Simpler, queryable directory structure
- No breaking changes to pipeline

### 🎉 PHASE 3 PRODUCTION VERIFICATION - October 17, 2025 ✅ COMPLETE
**Achievement**: All Phase 3 implementations verified active in production
**Verifications**:
- ✅ AI Title Generation working ($0.0017/article cost-optimized)
- ✅ Smart Image Selection working (keyword extraction, relevant results)
- ✅ Article Content Rendering (full 800+ word articles publishing)
- ✅ Site Publishing (pagination, responsive design, performance monitoring)
- ✅ Full Pipeline: Reddit/RSS → Collection → Processing → Markdown → Published Website

**Production Status**:
- 296 tests passing (all containers)
- No regressions detected
- All infrastructure verified working
- Cost tracking active
- Performance monitoring initialized
- Ready for ongoing production operation

## 🎯 Current Work: Monitoring & Optimization

### 📊 Production Monitoring (This Week)
- [ ] Monitor Phase 3 implementations for 24-48 hours
- [ ] Verify cost tracking ($30-40/month target)
- [ ] Check content quality metrics
- [ ] Review error logs for any issues
- [ ] Track Core Web Vitals performance

### � Short-Term Optimization (Next 1-2 Weeks)
- [ ] Fine-tune image selection criteria
- [ ] Optimize article quality scoring
- [ ] Implement content categorization/tagging
- [ ] Create team dashboard for monitoring

### 🔮 Medium-Term Enhancements (Next Month)
- [ ] SEO optimization (schema markup, meta tags)
- [ ] Advanced analytics and insights
- [ ] Community features (sharing, commenting)
- [ ] Content personalization options
**Goal**: Intelligent scheduling with source discovery and optimization

#### Smart Features
- [ ] **Source discovery engine** - identify high-value sources
- [ ] **Adaptive scheduling** - ML-based frequency optimization
- [ ] **Cross-platform preparation** - Bluesky/Mastodon framework
- [ ] **Advanced analytics** - content performance correlation

## 🏗️ Enhanced Architecture with Scheduler

**New Architecture with Scheduler:**
```
```
┌──────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  KEDA Cron   │    │ Content Collector│    │ Content Topics  │
│  (Scheduler) │───▶│  (Auto-scaled)   │───▶│   (Raw JSON)    │
└──────────────┘    └──────────────────┘    └─────────────────┘
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

### Priority 1: Verify KEDA Cron Configuration

```bash
# Verify KEDA cron scaler is configured
az containerapp show \
  --name ai-content-prod-collector \
  --resource-group ai-content-prod-rg \
  --query "properties.configuration.scale" -o json
```

### Priority 2: Monitor KEDA Scaling Events
```bash
# Check container scaling events and execution logs
az monitor activity-log list \
  --resource-group ai-content-prod-rg \
  --query "[?contains(resourceId, 'ai-content-prod-collector')]" \
  --max-events 20

# Check collections in blob storage
az storage blob list \
  --account-name aicontentprodstkwakpx \
  --container-name collected-content \
  --auth-mode login \
  --query "[?contains(name, '$(date +%Y/%m/%d)')]" -o table
```

### Priority 3: Test Manual Collection Trigger
```bash
# Test manual collection via API (for testing/debugging)
curl -X POST https://ai-content-prod-collector.whitecliff-6844954b.uksouth.azurecontainerapps.io/collections \
  -H "Content-Type: application/json" \
  -d '{"template_name": "tech-news"}'

# Verify content-collector health
curl -X GET "https://ai-content-prod-collector.whitecliff-6844954b.uksouth.azurecontainerapps.io/health"
```

### Priority 4: End-to-End Pipeline Testing (Parallel)
```bash
# Test complete flow with KEDA cron scheduler
# 1. KEDA cron triggers content-collector startup at scheduled time
# 2. Content-collector fetches from approved templates
# 3. Content flows through storage queues to content-processor  
# 4. Site generation creates website from processed content
# 5. Monitor costs, performance, and collection frequency
```

## 🎯 Success Metrics

### KEDA Scheduling Success Criteria
- [x] KEDA cron scaler configured for 8-hour intervals ✅ DEPLOYED
- [x] Content-collector scales from 0 to 1 replica on schedule ✅ WORKING
- [ ] Collections use approved templates only (Issue #580)
- [ ] Collection frequency matches 8-hour configuration (Issue #581 - investigate)
- [ ] Content flows through to blob storage and content-processor
- [ ] Total monthly cost remains under budget
- [ ] End-to-end content flow works (KEDA Cron → Collection → Processing → Website)

### Technical Metrics
- ✅ **3-container architecture** running successfully
- ✅ **content-processor** handling both processing AND generation
- ✅ **Test coverage strong** (content-collector: 123 passed, content-processor: 33 passed)
- ✅ **KEDA cron scheduler** triggering collections every 8 hours ✅ DEPLOYED
- 🔄 **Template-based security** for collection sources (Issue #580)
- 🔄 **Collection frequency validation** (Issue #581 - appears more frequent than expected)
- ✅ **Azure costs** under target budget with zero-replica scaling

### Business Metrics
- ✅ **Automated content collection** every 8 hours via KEDA cron
- 🔄 **Template-based content** from approved sources only (Issue #580)
- 🔄 **Quality articles** (TLDR, blog, deepdive formats)
- ✅ **Cost-effective scaling** with zero-replica idle state

## 📊 KEDA Cron Scheduler Configuration

### Current Configuration (Deployed)
- ✅ **container_apps.tf** - KEDA cron scaler and workload identity configuration
- ✅ **container_apps_keda_auth.tf** - KEDA managed identity authentication setup
- ✅ **Cron Expression**: `0 0,8,16 * * *` (every 8 hours at 00:00, 08:00, 16:00 UTC)
- ✅ **Execution Model**: 30-minute max window (container auto-shuts down when done, typically 2-5 min)
- ✅ **Zero-Replica Scaling**: Container scales to 0 after auto-shutdown (cost efficient)

### Active Issues
- 🔄 **Issue #580** - Template-based collection security (prevent arbitrary URL collection)
- 🔄 **Issue #581** - Collection frequency investigation (appears more frequent than 8 hours)

### Template Configuration Example
```json
{
  "sources": [
    {
      "type": "rss",
      "feed_urls": ["https://hnrss.org/frontpage"],
      "limit": 20
    }
  ],
  "deduplicate": true,
  "similarity_threshold": 0.85,
  "save_to_storage": true
}
```

---

**Current Status**: KEDA cron scheduler deployed and operational! Collections automated every 8 hours with zero-cost idle time. Investigating collection frequency issue (#581) and implementing template security (#580). 🚀

## 🚫 What NOT to Do

- ❌ Don't add arbitrary URL collection (security risk - see Issue #580)
- ❌ Don't change KEDA cron schedule without verifying current behavior (Issue #581)
- ❌ Don't create new documentation files (use existing structure)
- ❌ Don't change container architecture without comprehensive testing
- ❌ Don't optimize before proving basic functionality works correctly

## ✅ What's Working (Don't Break)

- Infrastructure: Azure Container Apps with KEDA cron scheduling, Terraform, CI/CD
- Security: Managed identity authentication, OWASP compliance, security scanning
- Content Pipeline: Automated collection every 8 hours via KEDA cron scaler
- content-collector: 123 tests passing, standardized API responses
- content-processor: 33 tests passing, integrated generation capabilities
- Zero-replica scaling: Cost optimization with automatic startup on schedule
- Simplified 3-container architecture (collector → processor → site-generator)

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

## 🧭 Roadmap (Epics)

Short roadmap linking the new umbrella epics created to group related work.

- Epic: Site Generator Improvements — https://github.com/Hardcoreprawn/ai-content-farm/issues/611  
  Labels: `epic`, `site-generator`

- Epic: Content Quality & Publishing — https://github.com/Hardcoreprawn/ai-content-farm/issues/612  
  Labels: `epic`, `content-processor`, `content-pipeline`

- Epic: Infra & CI Reliability — https://github.com/Hardcoreprawn/ai-content-farm/issues/613  
  Labels: `epic`, `infrastructure`

- Epic: Observability & Telemetry — https://github.com/Hardcoreprawn/ai-content-farm/issues/614  
  Labels: `epic`, `infrastructure`, `content-collector`, `content-processor`, `site-generator`

Next steps:
- Link remaining open issues from `output/issue_dry_run_2025-10-14.csv` to the appropriate epic (in-progress).
- For issues that are closed or removed, prune links from epics and update acceptance criteria.
- Optionally open a lightweight milestone or project board to track progress across epics.

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
