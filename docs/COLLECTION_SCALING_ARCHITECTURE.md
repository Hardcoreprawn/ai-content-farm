# Collection Scaling Architecture Analysis
**Created**: October 13, 2025  
**Context**: Evaluating parallel vs sequential collection strategies

---

## Current Architecture

### Single Container with Multiple Sources
```
KEDA Cron (every 8hrs) → content-collector (1 replica)
                              ↓
                    Sequential Collection:
                    1. Mastodon (all hashtags)
                    2. RSS (all feeds)  
                    3. Web (all sites)
                    4. Reddit (BLOCKED)
                              ↓
                    Storage Queue → content-processor
```

**Current Behavior**:
- Single container scales 0→1 on cron schedule (00:00, 08:00, 16:00 UTC)
- Collects from ALL sources sequentially in one run
- Auto-shuts down when complete (~2-5 minutes)
- KEDA cooldown: 45 seconds

---

## Your Question: Multiple Containers vs Single Container?

### Option A: Multiple Specialized Containers (What You Proposed)
```terraform
# Separate container apps for each source
content-collector-reddit    (every 12 hours, disabled currently)
content-collector-mastodon  (every 4 hours)
content-collector-rss       (every 8 hours)
content-collector-web       (every 24 hours)
```

**Pros**:
- ✅ Independent scaling per source
- ✅ Different schedules for different sources (Mastodon every 4hrs, Web daily)
- ✅ Isolated failures (Reddit down ≠ Mastodon blocked)
- ✅ Easier rate limit management per source
- ✅ Clearer logs and debugging (one source per container)
- ✅ Can disable problematic sources without affecting others

**Cons**:
- ❌ 4x infrastructure complexity (4 container apps, 4 KEDA scalers)
- ❌ Higher baseline cost (4 separate apps, even at scale-to-zero)
- ❌ More Terraform to maintain
- ❌ Duplicate code/config across containers
- ❌ More complex monitoring (4 apps to watch)

**Cost Estimate**: ~$20-30/month (4 apps × $5-8 each for scale-to-zero + execution time)

---

### Option B: Single Container with Source-Specific Endpoints (Functional Decomposition)
```python
# Current architecture enhanced with targeted collection
POST /collections/collect           # Collect from ALL sources
POST /collections/collect/mastodon  # Collect only Mastodon
POST /collections/collect/rss       # Collect only RSS
POST /collections/collect/web       # Collect only web
POST /collections/collect/reddit    # Collect only Reddit (when fixed)
```

**KEDA Configuration**:
```terraform
# Multiple cron scalers on SINGLE container app
custom_scale_rule {
  name = "mastodon-cron"
  custom_rule_type = "cron"
  metadata = {
    start = "0 0,4,8,12,16,20 * * *"  # Every 4 hours
    end   = "15 0,4,8,12,16,20 * * *" # 15 min window
    desiredReplicas = "1"
  }
  # Trigger: POST /collections/collect/mastodon via env var
}

custom_scale_rule {
  name = "rss-cron"
  custom_rule_type = "cron"  
  metadata = {
    start = "0 0,8,16 * * *"  # Every 8 hours
    end   = "20 0,8,16 * * *"  # 20 min window
    desiredReplicas = "1"
  }
  # Trigger: POST /collections/collect/rss via env var
}

custom_scale_rule {
  name = "web-cron"
  custom_rule_type = "cron"
  metadata = {
    start = "0 6 * * *"  # Once daily at 06:00 UTC
    end   = "30 6 * * *"  # 30 min window
    desiredReplicas = "1"  
  }
  # Trigger: POST /collections/collect/web via env var
}
```

**Implementation**:
```python
# In main.py lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan with source-specific KEDA triggers."""
    logger.info("Content Womble starting up...")
    
    # Check which KEDA trigger activated this instance
    trigger_source = os.getenv("KEDA_TRIGGER_SOURCE", "all")
    
    if os.getenv("KEDA_CRON_TRIGGER", "false").lower() == "true":
        logger.info(f"KEDA cron trigger detected: {trigger_source}")
        
        # Route to appropriate collection function
        if trigger_source == "mastodon":
            await run_mastodon_collection()
        elif trigger_source == "rss":
            await run_rss_collection()
        elif trigger_source == "web":
            await run_web_collection()
        elif trigger_source == "reddit":
            await run_reddit_collection()
        else:
            # Default: collect from all sources
            await run_scheduled_collection()
        
        # Auto-shutdown after collection
        asyncio.create_task(graceful_shutdown())
    
    yield  # Container stays running for HTTP requests
```

**Pros**:
- ✅ Single container app (low complexity)
- ✅ Source-specific scheduling via multiple KEDA cron scalers
- ✅ Isolated failures (handled at function level)
- ✅ Easier debugging (logs show which trigger fired)
- ✅ Functional decomposition (pure collection functions per source)
- ✅ Cost-efficient (one app, multiple triggers)
- ✅ Easy to add/remove sources (just add/remove scalers)

**Cons**:
- ⚠️ Multiple KEDA triggers might cause overlapping scale-ups (need careful scheduling)
- ⚠️ Container could be running when multiple triggers fire close together
- ⚠️ Slightly more complex KEDA configuration

**Cost Estimate**: ~$8-12/month (single app, multiple triggers, same scale-to-zero efficiency)

---

### Option C: Hybrid - Storage Queue Pattern (Best of Both Worlds)
```
Azure Logic App (or KEDA cron) → Storage Queue Messages
                                       ↓
                            content-collector (KEDA queue scaler)
                                       ↓
                            Process queue messages:
                            {"source": "mastodon", "config": {...}}
                            {"source": "rss", "config": {...}}
                            {"source": "web", "config": {...}}
```

**How it works**:
1. **Scheduler** (Logic App/Function/Cron): Enqueues messages on schedule
   - "Collect from Mastodon" every 4 hours
   - "Collect from RSS" every 8 hours
   - "Collect from Web" every 24 hours

2. **Collector**: Scales based on queue depth (KEDA queue scaler)
   - Scales 0→1 when messages arrive
   - Processes each source independently
   - Auto-scales 1→0 when queue empty

3. **Benefits**:
   - Decouples scheduling from collection
   - Natural retry/DLQ for failures
   - Can manually trigger collections (enqueue message)
   - Parallel processing if needed (scale to N replicas)

**Pros**:
- ✅ True functional decomposition (messages = work units)
- ✅ Built-in retry and dead-letter handling
- ✅ Can process multiple sources in parallel (scale to 2-3 replicas)
- ✅ Manual triggering (just enqueue a message)
- ✅ Clear separation of scheduling and work
- ✅ Easy debugging (inspect queue messages)
- ✅ Cost-efficient (queue triggers are cheap)

**Cons**:
- ⚠️ Requires scheduler component (Logic App or separate function)
- ⚠️ Slightly more moving parts
- ⚠️ Queue storage costs (negligible, ~$0.01/month)

**Cost Estimate**: ~$8-12/month (same as Option B, plus ~$1 for Logic App)

---

## Recommendation: Option C (Queue Pattern) 🏆

### Why Queue Pattern is Best

**Functional Programming Benefits**:
```python
# Pure function for collection
async def collect_from_source(source_config: dict) -> CollectionResult:
    """
    Pure collection function - no side effects, testable.
    
    Args:
        source_config: {"source": "mastodon", "hashtags": [...], "limit": 50}
    
    Returns:
        CollectionResult with items collected
    """
    collector = CollectorFactory.create(source_config["source"])
    items = await collector.collect(source_config)
    return CollectionResult(items=items, source=source_config["source"])

# Queue message handler
async def process_collection_message(message: dict):
    """Handle queue message and collect from specified source."""
    result = await collect_from_source(message["config"])
    await store_results(result)
```

**Easy Debugging**:
1. Check queue for pending messages: `az storage queue show`
2. Inspect message content: `az storage message peek`
3. Test collection locally: `POST /collections/collect/mastodon`
4. Monitor queue metrics in Azure portal

**Flexible Scheduling**:
```javascript
// Logic App runs every 4 hours (Mastodon)
{
  "recurrence": { "frequency": "Hour", "interval": 4 },
  "actions": {
    "enqueue_mastodon_collection": {
      "type": "ApiConnection",
      "inputs": {
        "host": { "connection": { "name": "azurequeues" } },
        "method": "post",
        "path": "/messages",
        "body": {
          "source": "mastodon",
          "hashtags": ["technology", "programming", "AI"],
          "limit": 50
        }
      }
    }
  }
}
```

---

## Implementation Plan (Queue Pattern)

### Phase 1: Add Source-Specific Collection Functions (Week 1)
```python
# In containers/content-collector/endpoints/collections.py

@router.post("/collect/mastodon")
async def collect_mastodon(
    hashtags: list[str],
    limit: int = 50,
    metadata: dict = Depends(service_metadata)
):
    """Collect only from Mastodon."""
    config = {"source": "mastodon", "hashtags": hashtags, "limit": limit}
    result = await collect_from_source(config)
    return StandardResponse(
        status="success",
        message=f"Collected {len(result.items)} items from Mastodon",
        data=result.dict()
    )

@router.post("/collect/rss")
async def collect_rss(...): ...

@router.post("/collect/web")
async def collect_web(...): ...
```

### Phase 2: Add Queue Message Handler (Week 1)
```python
# In containers/content-collector/endpoints/storage_queue_router.py

@router.post("/queue/collection-requests")
async def handle_collection_request(message: dict):
    """
    Process collection request from queue.
    
    Message format:
    {
        "source": "mastodon",
        "config": {"hashtags": [...], "limit": 50},
        "scheduled_at": "2025-10-13T08:00:00Z"
    }
    """
    source = message["source"]
    config = message["config"]
    
    # Route to appropriate collection function
    if source == "mastodon":
        result = await collect_from_source({"source": "mastodon", **config})
    elif source == "rss":
        result = await collect_from_source({"source": "rss", **config})
    # ... etc
    
    logger.info(f"Collected {len(result.items)} items from {source}")
    return result
```

### Phase 3: Update KEDA Scaler to Queue-Based (Week 1)
```terraform
# In infra/container_app_collector.tf

# Replace cron scaler with queue scaler
custom_scale_rule {
  name             = "queue-scaler"
  custom_rule_type = "azure-queue"
  metadata = {
    queueName   = "collection-requests"
    queueLength = "1"  # Scale 0->1 when 1+ messages
    accountName = azurerm_storage_account.main.name
  }
  
  authentication {
    secret_name       = "storage-connection-string"
    trigger_parameter = "connection"
  }
}
```

### Phase 4: Create Scheduler (Week 2)
**Option A**: Azure Logic App (no code, visual designer)
**Option B**: Azure Function with timer trigger (Python code)
**Option C**: GitHub Actions cron (enqueue via API call)

**Recommendation**: Logic App for simplicity

```json
// Logic App definition (pseudo-code)
{
  "mastodon-scheduler": {
    "trigger": { "recurrence": "0 0,4,8,12,16,20 * * *" },
    "action": { "enqueue": "collection-requests", "message": {...} }
  },
  "rss-scheduler": {
    "trigger": { "recurrence": "0 0,8,16 * * *" },
    "action": { "enqueue": "collection-requests", "message": {...} }
  }
}
```

---

## Testing Strategy

### Local Testing
```bash
# Test individual source collection
curl -X POST http://localhost:8080/collections/collect/mastodon \
  -H "Content-Type: application/json" \
  -d '{"hashtags": ["python"], "limit": 10}'

# Simulate queue message
az storage message put \
  --queue-name collection-requests \
  --content '{"source": "mastodon", "config": {"hashtags": ["python"], "limit": 10}}'
```

### Production Testing
1. Enqueue test message manually
2. Watch container scale 0→1
3. Check logs for collection progress
4. Verify results in blob storage
5. Confirm container scales 1→0 when queue empty

---

## Migration Path (Low Risk)

### Week 1: Add queue handler (no breaking changes)
- Keep existing cron scaler
- Add queue message handler endpoint
- Test queue pattern alongside cron

### Week 2: Parallel running
- Schedule some collections via queue (Mastodon)
- Keep others via cron (RSS, Web)
- Monitor and compare

### Week 3: Full cutover
- Migrate all collections to queue pattern
- Remove cron scalers
- Add Logic App schedulers

### Week 4: Cleanup
- Remove old cron-based code
- Update documentation
- Optimize queue configuration

---

## Comparison Matrix

| Criterion | Multiple Containers | Multiple KEDA Crons | Queue Pattern |
|-----------|---------------------|---------------------|---------------|
| Complexity | 🔴 High | 🟡 Medium | 🟢 Low |
| Cost | 🔴 $20-30/mo | 🟢 $8-12/mo | 🟢 $8-12/mo |
| Debuggability | 🟡 Medium | 🟡 Medium | 🟢 High |
| Flexibility | 🟢 High | 🟡 Medium | 🟢 High |
| Testability | 🟡 Medium | 🟡 Medium | 🟢 High |
| Functional | 🟡 Medium | 🟡 Medium | 🟢 High |
| Scalability | 🟢 High | 🟡 Limited | 🟢 High |
| Retry Logic | 🔴 Manual | 🔴 Manual | 🟢 Built-in |

**Winner**: Queue Pattern ✅

---

## Next Steps

1. **Decision**: Choose Option C (Queue Pattern)?
2. **Prototype**: Add queue handler to collector (1 day)
3. **Test**: Enqueue test messages, verify collection works
4. **Migrate**: Move one source to queue pattern (Mastodon first)
5. **Scale**: Migrate remaining sources once proven

**Ready to implement?** I can start with Phase 1 (source-specific endpoints) right now.
