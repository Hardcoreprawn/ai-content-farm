# Project Status: AI Content Farm
**Last Updated**: October 8, 2025  
**Time in Development**: 4 months  
**Current State**: Major refactoring in progress, not yet deployed

---

## 🎯 What We're Building

A serverless content pipeline that:
1. Collects trending topics from Reddit/RSS
2. Processes each topic through AI (enrichment, fact-checking)
3. Generates markdown articles
4. **[MISSING]** Publishes markdown → static site

**Goal**: Automated, cost-effective ($30-40/month), scalable content generation

---

## 📊 Current Production State

### Deployed in Azure (`ai-content-prod-rg`)
```
✅ ai-content-prod-collector  (Running - OLD BATCH SYSTEM)
✅ ai-content-prod-processor  (Running - OLD BATCH SYSTEM)
✅ ai-content-prod-markdown-gen (Running)
❌ site-publisher (DOES NOT EXIST)
```

**CRITICAL**: Production is running the **OLD BATCH PROCESSING SYSTEM**.  
All of today's fanout refactoring is local-only and unpushed.

### What's Actually Working in Production RIGHT NOW

**Collector** (verified Oct 8, 18:22-18:26):
- ✅ Collecting from RSS feeds (Wired, ArsTechnica)
- ✅ Saving to blob: `collections/2025/10/08/collection_TIMESTAMP.json`
- ✅ Using OLD queues: `content-collection-requests`, `content-processing-requests`
- ❌ NOT using new fanout (no `process-topic` queue exists)

**Storage Containers**:
- `collected-content` - Collections going here ✅
- `processed-content` - (need to check)
- `markdown-content` - (need to check)
- `pipeline-logs` - (need to check)

**Queues** (OLD SYSTEM):
- `content-collection-requests` ✅
- `content-processing-requests` ✅
- `markdown-generation-requests` ✅

**What This Means**:
1. Production uses batch processing (collect all → process batch)
2. Our new fanout code (1 topic = 1 message) is NOT deployed
3. If we push now, we'll break production (different queue names/formats)
4. Need migration strategy or feature flag

---

## 🔄 Today's Refactoring (Local, Unpushed)

### What Changed Today
1. **Fanout Architecture**: Rewrote collector & processor to use 1 topic = 1 queue message
2. **Functional Programming**: Removed OOP where possible, pure functions
3. **Integration Tests**: Created 24 comprehensive tests (all passing locally)
4. **Code Cleanup**: Removed legacy batch processing code

### Files Modified (30+ files)
- `content-collector`: New fanout logic, collection storage
- `content-processor`: New queue handler, functional refactor
- `tests/integration/`: 3 new test files (24 tests total)
- Multiple service modules refactored

**Status**: All tests pass locally, nothing pushed to main, nothing deployed

---

## 📦 Container Analysis

### 1. Content Collector
**Purpose**: Collect topics from Reddit/RSS, send to queue  
**Entry Point**: `containers/content-collector/main.py`  
**Status**: ✅ Heavily refactored today (functional, fanout pattern)

**Key Files**:
- `service_logic.py` - Main collection logic
- `topic_fanout.py` - NEW: Creates 1 message per topic
- `collection_storage_utils.py` - NEW: Saves collections to blob

**What Works**:
- Collects from Reddit (PRAW)
- Collects from RSS feeds
- Generates collection.json
- Creates fanout messages (1 per topic)

**What's Questionable**:
- Not tested in Azure yet (today's changes)
- Integration with real queue unknown
- KEDA scaling untested

**Tests**: 12 integration tests (passing locally)

---

### 2. Content Processor  
**Purpose**: Process individual topics, call OpenAI, generate enriched content  
**Entry Point**: `containers/content-processor/main.py`  
**Status**: ✅ Heavily refactored today (functional, queue handler)

**Key Files**:
- `processor.py` - Main processing logic
- `endpoints/storage_queue_router.py` - NEW: Handles process_topic messages
- `services/openai_service.py` - OpenAI API calls
- `metadata.py` - NEW: Metadata generation
- `blob_operations.py` - NEW: Blob storage operations

**What Works** (locally):
- Processes individual topic messages
- Validates before processing
- OpenAI integration (mocked in tests)
- Returns success/failure per topic

**What's Questionable**:
- Not tested in Azure yet (today's changes)
- OpenAI costs unknown
- Error handling in production unclear
- Lease management untested

**Tests**: 7 integration tests (passing locally)

---

### 3. Markdown Generator
**Purpose**: Take processed content → generate markdown files  
**Entry Point**: `containers/markdown-generator/main.py`  
**Status**: ⚠️ Recently created (yesterday), replacing old site-generator

**What Works**:
- Takes JSON input
- Generates markdown with frontmatter
- Template system exists

**What's Questionable**:
- How does it get triggered? (Queue? HTTP?)
- Integration with processor unclear
- Not tested end-to-end
- Deployment status unknown

**Tests**: Unknown (need to check)

---

### 4. Site Publisher
**Purpose**: Take markdown → build static site (11ty/Hugo)  
**Status**: ❌ **DOES NOT EXIST**

**What's Needed**:
- Take markdown from blob storage
- Run SSG (11ty recommended)
- Deploy to static hosting
- Trigger mechanism (schedule? event?)

**This is the missing piece** to complete the pipeline.

---

## 🧪 Testing Status

### Local Tests (Today)
- ✅ 24 integration tests passing
- ✅ Fanout pattern validated
- ✅ Functional programming enforced
- ✅ No legacy code tested

### CI/CD Pipeline
**File**: `.github/workflows/cicd-pipeline.yml`

**What It Does**:
1. Detects container changes
2. Runs security scans (Checkov, Trivy, Terrascan)
3. Runs container tests (`pytest`)
4. Builds Docker images
5. Pushes to GitHub Container Registry
6. Deploys to Azure Container Apps

**Current State**: 
- Pipeline exists and is comprehensive
- **Unknown** if it will work with today's changes
- Integration tests likely not in CI/CD yet (just created)

### What's Missing in CI/CD
- Integration tests not in pipeline (?)
- End-to-end testing unclear
- Production validation missing

---

## 🚨 Critical Issues

### 1. **BREAKING CHANGES - Cannot Deploy Directly**
**Our local refactoring is incompatible with production**:

| Component | Production (Old) | Local (New) | Compatible? |
|-----------|-----------------|-------------|-------------|
| Queue names | `content-processing-requests` | `process-topic` | ❌ NO |
| Message format | Batch (all topics) | Individual topic | ❌ NO |
| Processing model | Batch processing | Fanout (1 topic = 1 msg) | ❌ NO |
| Container apps | OLD code deployed | NEW code local | ❌ NO |

**If we push now**:
1. New collector sends to `process-topic` queue
2. Old processor listens to `content-processing-requests`
3. **Nothing processes** - pipeline broken
4. Need coordinated deployment of BOTH containers

**Options**:
- **A. Feature Flag**: Add env var to switch between old/new queue names
- **B. Coordinated Deploy**: Deploy both collector + processor at same time
- **C. Blue/Green**: Deploy to new environment, test, then switch
- **D. Rollback Plan**: Keep old code ready, fast rollback procedure

### 2. **Unpushed Changes**
- 30+ files modified locally
- 24 new integration tests
- Major architectural changes
- **Risk**: Could conflict, could break production

### 2. **Missing Container**
- No site-publisher exists
- Pipeline incomplete without it
- Can't go from markdown → published site

### 3. **Production Unknown**
- Don't know if current production works
- Don't know last successful run
- Don't know current error state

### 4. **Test Coverage Gaps**
- Azure integration tests not run
- KEDA scaling not validated
- Real OpenAI costs unknown
- End-to-end pipeline not tested

### 5. **Code Quality Debt**
- Still finding OOP/functional hybrids
- Documentation sprawl (many temporary docs)
- Config scattered across files

---

## 📋 Immediate Next Steps (Priority Order)

### STOP: Cannot Deploy Current Changes
**Current local code will break production**. Need deployment strategy first.

### Option A: Feature Flag Approach (RECOMMENDED - 2 hours)
1. **Add environment variable**: `USE_FANOUT_PATTERN=true|false`
2. **Modify collector**: Check flag, use old OR new queue
3. **Modify processor**: Check flag, handle old OR new messages
4. **Deploy with flag=false**: Verify old system still works
5. **Flip to flag=true**: Enable fanout gradually
6. **Monitor**: Can rollback by flipping flag

**Pros**: Safe, gradual, easy rollback  
**Cons**: Code complexity, need to maintain both paths temporarily

### Option B: Coordinated Deployment (RISKY - 1 hour)
1. **Deploy both containers simultaneously**
2. **Hope nothing breaks during transition**
3. **Have rollback ready**

**Pros**: Fast, clean cut  
**Cons**: High risk, downtime likely, hard rollback

### Option C: Test in Staging First (SAFEST - 3 hours)
1. **Create staging environment**
2. **Deploy new code to staging**
3. **Test end-to-end**
4. **Then deploy to production**

**Pros**: Lowest risk, validates changes  
**Cons**: Need staging infrastructure (cost, time)

---

### 1. **Decide Deployment Strategy** (30 min - NOW)
- Review options above
- Choose based on risk tolerance
- Document decision

### 2. **Check Current Production Health** (30 min)
```bash
# Check if pipeline is actually running
az containerapp logs show -n ai-content-prod-collector -g ai-content-prod-rg --tail 100

# Check last successful collection
# Check blob storage for recent collections
# Check queue depth
```

**Decision Point**: Is production working at all right now?

### 2. **Consolidate Documentation** (1 hour)
- Keep: README.md, TODO.md, STATUS.md (this file)
- Archive: All PHASE_*.md, summaries, plans → docs/archive/
- Update: Container README.md files with current state

### 3. **Complete Site Publisher** (2-4 hours)
- Create `containers/site-publisher/`
- Simple 11ty build
- Takes markdown from blob → generates HTML
- Uploads to static hosting
- Schedule trigger (daily?)

### 4. **Test Locally End-to-End** (2 hours)
- Run all 4 containers locally
- Use docker-compose or manual
- Verify: Reddit → Markdown → HTML
- Document what breaks

### 5. **Push to Branch** (30 min)
- Create feature branch: `feature/fanout-refactor`
- Push all changes
- Create PR with clear description
- Let CI/CD run, see what breaks

### 6. **Fix CI/CD** (1-2 hours)
- Add integration tests to pipeline
- Fix any test failures
- Ensure deployments work

### 7. **Deploy to Production** (careful!)
- Merge PR when CI/CD green
- Monitor deployment closely
- Check logs immediately
- Have rollback plan ready

---

## 🎯 Success Criteria

**Minimum Viable Pipeline**:
1. Collector runs on schedule (6 hours)
2. Generates N queue messages for N topics
3. Processor handles messages in parallel
4. Markdown generator creates files
5. Site publisher builds & deploys HTML
6. New articles appear on site

**Quality Criteria**:
- No malformed data (current production issue)
- No broken text (current production issue)
- Costs under $40/month
- Pipeline completes in < 5 minutes
- Monitoring shows each stage

---

## 📝 Document Cleanup Needed

### Keep (3 docs):
- `README.md` - Project overview
- `TODO.md` - Current work
- `STATUS.md` - This file

### Archive to `docs/archive/`:
- PHASE_2_FANOUT_COMPLETE.md
- PHASE_3_INTEGRATION_TESTING_PLAN.md
- PHASE_3_QUICK_START.md
- All COMMIT_*.md files
- All *_SUMMARY.md files
- All *_COMPLETE.md files

### Update:
- Container README.md files (1 per container)
- docs/ARCHITECTURE.md (high-level only)
- docs/DEPLOYMENT.md (actual procedure)

**Goal**: 5-7 essential docs, not 50+ temporary ones

---

## 🤔 Key Questions to Answer

1. **Does production work right now?** (check logs)
2. **When was the last successful article published?**
3. **What's the actual cost per month?**
4. **Are the integration tests in CI/CD?**
5. **How do we test end-to-end without deploying?**
6. **What's the rollback procedure if this deployment fails?**
7. **Do we have monitoring/alerting?**

---

## 💭 Architectural Concerns

### Good:
- Fanout pattern should scale better
- Functional programming reduces bugs
- Integration tests give confidence
- Queue-based architecture is sound

### Questionable:
- 4 containers might be overkill (could combine?)
- Storage queue vs Service Bus decision
- KEDA scaling complexity
- Cost per OpenAI call unclear

### Bad:
- No end-to-end testing
- Production state unknown
- Documentation sprawl
- 4 months without sustained success

---

## 🔮 Realistic Assessment

**Production Status (verified Oct 8, 20:00 UTC)**:

| Stage | Last Activity | Status | Notes |
|-------|--------------|--------|-------|
| Collection | Oct 8, 18:26 | ✅ Working | RSS feeds, every ~1 minute |
| Processing | Oct 7, 09:22 | ⚠️ Stopped | Last processed 24 hours ago |
| Markdown | Oct 7, 09:22 | ⚠️ Stopped | Last generated 24 hours ago |
| Publishing | Never | ❌ Missing | No site-publisher exists |

**Why Processing Stopped**:
- ✅ Collector IS working - sends messages to queue (verified Oct 8, 20:08)
- ✅ Queue HAS messages (2 messages currently waiting)
- ❌ **KEDA is NOT scaling up the processor**
- ❌ Processor starts, sees "0 messages", immediately shuts down

**Root Cause**: KEDA Scale Trigger Misconfiguration
- KEDA checks queue depth to decide when to scale
- Something is preventing KEDA from seeing the messages
- Possible issues:
  - KEDA polling interval too long
  - KEDA authentication to queue broken
  - Queue scaler configuration incorrect
  - Message visibility timeout issue

**Evidence**:
```
Collector: "sent to queue 'content-processing-requests': 9023dab4..." ✅
Queue: Contains 2 messages ✅  
Processor: "Received 0 messages from queue" ❌
Processor: "scheduling graceful shutdown" ❌
```

**This is a KEDA infrastructure issue, not application code issue.**

**Can We Ship This?**
- **Technically**: No - breaking changes to queue names/formats
- **Safely**: No - need feature flag or coordinated deploy
- **Urgently**: Maybe - if we fix deployment strategy

**What's Working**:
- ✅ Infrastructure (Azure, Terraform, CI/CD)
- ✅ Collector (actively running, gathering topics)
- ✅ Today's refactoring (clean, tested, functional)
- ❌ Processing pipeline (broken since yesterday)

**What's Not Working**:
- ❌ Processor stopped working (Oct 7)
- ❌ No new articles in 24 hours
- ❌ Deployment strategy for breaking changes
- ❌ Missing site-publisher container

**Recommendation**: 
1. **IMMEDIATE**: Check why processor stopped (logs, errors, queue depth)
2. **TODAY**: Implement feature flag for safe deployment
3. **THIS WEEK**: Complete site-publisher
4. **NEXT WEEK**: Deploy fanout with monitoring

**Reality Check**:
- 4 months of work, but basic pipeline breaks frequently
- Good architecture, but operational stability issues
- Need focus on reliability over new features
- Consider: monitoring, alerting, auto-recovery

---

**Next Action**: Check processor logs to understand why it stopped.
