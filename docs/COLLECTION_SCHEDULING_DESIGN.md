# Content Collector: Scheduling Architecture Design

## Problem Statement

Current KEDA cron scaler setup is non-functional:
- KEDA cron only manages replica count (scales up/down)
- No mechanism exists to call HTTP endpoints when container starts
- Collections haven't run since Oct 21 despite container updates
- Defeats purpose of scheduling if container never triggers collection

## Previous Pattern (Worked Well)

Your previous setup had a **startup job** pattern:
- Container started
- `lifespan` or startup hook ran default collection immediately
- This automatically triggered when KEDA scaled container up
- Reliable, consistent, no external orchestration needed

**Advantages:**
- ✅ No external service needed (stays within Container Apps)
- ✅ Uses same managed identity as other containers
- ✅ Single model for all 4 containers (consistency)
- ✅ Proven to work from previous implementation

## Proposed Solution: Hybrid Startup + Scheduled Scaling

### Architecture

```
KEDA Cron Scaler (external trigger):
├── 00:00 UTC → Scale to 1 replica
├── 08:00 UTC → Scale to 1 replica
├── 16:00 UTC → Scale to 1 replica
└── (scale down after 30 min cooldown)

Container Startup (internal):
├── FastAPI app starts
├── lifespan() context manager:
│   ├── Run default collection immediately
│   ├── Wait for completion
│   └── Then yield control to FastAPI
└── FastAPI runs as normal (for manual triggers)

Container Shutdown:
├── After cooldown period (~5 min)
├── Scale-down begins
└── Graceful shutdown triggers
```

### Implementation Details

#### 1. Modify lifespan() in main.py

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with automatic startup collection."""
    logger.info("🚀 Content Womble starting up...")
    
    # Check if this is a scheduled startup (env var or assume yes)
    should_collect = os.getenv("AUTO_COLLECT_ON_STARTUP", "true").lower() == "true"
    
    if should_collect:
        logger.info("⚡ Running scheduled collection on startup...")
        try:
            # Import and run the default collection trigger
            from pipeline.stream import run_default_collection
            collection_result = await run_default_collection()
            logger.info(f"✅ Startup collection complete: {collection_result}")
        except Exception as e:
            logger.error(f"❌ Startup collection failed: {e}", exc_info=True)
            # Continue running anyway - don't fail the whole container
    else:
        logger.info("⏭️  Skipping auto-collection (manual mode)")
    
    logger.info("📡 FastAPI server ready for requests")
    
    try:
        yield
    finally:
        logger.info("🛑 Content Womble shutting down...")
```

#### 2. Implement run_default_collection()

```python
# pipeline/stream.py

async def run_default_collection():
    """
    Run default collection with standard parameters.
    This is called on container startup.
    """
    return await trigger_collection(
        subreddits=["technology", "programming", "science"],  # defaults
        instances=[],
        min_score=25,
        max_items=50
    )
```

#### 3. KEDA Configuration (Keep Current)

Keep the cron scaler exactly as-is:
- Schedule: `0 0,8,16 * * * UTC` (00:00, 08:00, 16:00)
- Scale to 1 replica for 30 minutes
- Then scale to 0

**Behavior:**
- KEDA scales container from 0 → 1 at scheduled times
- Container starts, lifespan runs collection
- Collection completes
- Container sits idle for ~30 min
- KEDA scales back to 0

#### 4. Environment Configuration

```bash
# Container App Environment Variables
AUTO_COLLECT_ON_STARTUP=true   # Run collection on startup
DISABLE_HTTP_ENDPOINTS=false   # Keep /docs, /health for debugging
```

### Advantages

| Aspect | Benefit |
|--------|---------|
| **Consistency** | All 4 containers stay in Container Apps (same auth model) |
| **Managed Identity** | Uses existing Azure managed identity - no new auth paradigm |
| **Reliability** | Startup collection runs atomically with container lifecycle |
| **Debugging** | Container stays running for manual triggers if needed |
| **Cost** | Identical to current (~$0.04/month) |
| **Proven** | You've successfully used this pattern before |

### Disadvantages

| Aspect | Issue |
|--------|-------|
| **HTTP API Remains** | Container runs FastAPI even though not always needed |
| **Extra Services** | Container stays idle after collection completes |
| **Cold Start** | ~5-10 seconds for Python + FastAPI startup overhead |

### Alternative: Hybrid with Environment Variable

For maximum flexibility, support three modes:

```python
COLLECTION_MODE:
  - "auto_startup"     → Run on startup only (KEDA scheduled)
  - "http_manual"      → Wait for HTTP trigger (manual testing)
  - "disabled"         → No collection (debugging)
```

## Migration Path

1. **Phase 1: Restore startup collection**
   - Modify `lifespan()` to run collection
   - Add `run_default_collection()` function
   - Keep KEDA cron scaler as-is
   - Test with manual scale-up

2. **Phase 2: Verify scheduling**
   - Wait for next scheduled run (16:00 UTC today)
   - Verify collection appears in blob storage
   - Monitor logs via Application Insights

3. **Phase 3: Fine-tune parameters**
   - Adjust default subreddits if needed
   - Monitor execution time
   - Optimize quality gate thresholds

## Rollback Plan

If issues arise:
- Set `AUTO_COLLECT_ON_STARTUP=false`
- Manually trigger via HTTP endpoint
- Debug and iterate
- No infrastructure changes needed

## Cost Comparison (No Change)

| Scenario | Monthly Cost |
|----------|--------------|
| Current broken setup | $0.04 |
| **Proposed startup collection** | **$0.04** |
| Alternative: Container Apps Job | $0.04 |
| Alternative: Azure Functions | $0.04 |

**Recommendation: Startup Collection Pattern**
- Lowest complexity
- Highest consistency
- Proven to work
- Zero new infrastructure
- Same cost as alternatives
