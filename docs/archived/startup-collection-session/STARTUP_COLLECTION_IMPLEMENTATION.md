# Content Collector: Startup Job Implementation

## Summary

Implemented **startup collection pattern** for content-collector container. When KEDA cron scaler brings the container online (0:00, 8:00, 16:00 UTC), the container now automatically:

1. Runs collection using the **quality-tech template** (Mastodon sources)
2. Streams items through quality gates
3. Saves collected items to blob storage
4. Sends valid items to processor queue
5. Logs completion statistics
6. Gracefully allows FastAPI HTTP server to run for manual triggers (or exit if no triggers needed)

## Changes Made

### File: `/workspaces/ai-content-farm/containers/content-collector/main.py`

**Modified**: `lifespan()` context manager (lines 56-125)

**Before**: 
- Just logged startup/shutdown
- No actual collection logic

**After**:
- Checks `AUTO_COLLECT_ON_STARTUP` environment variable (defaults to `true`)
- If enabled:
  1. Creates collection ID with `keda_` prefix + ISO timestamp
  2. Initializes queue client for `content-processor-requests`
  3. Creates async generator collecting from two Mastodon instances:
     - `fosstodon.org` (primary, up to 25 items)
     - `techhub.social` (secondary, up to 15 items)
  4. Runs `stream_collection()` orchestrator (handles quality review, dedup, blob save, queue send)
  5. Logs statistics (collected, published, rejected_quality, rejected_dedup)
  6. Catches and logs any errors without failing the container
- Logs "HTTP API ready" message
- Yields to allow FastAPI to serve HTTP requests
- Logs graceful shutdown on container exit

## Configuration

### Environment Variables

```bash
# Enable/disable startup collection (default: true)
AUTO_COLLECT_ON_STARTUP=true|false
```

### KEDA Cron Schedule (Already Configured)

```
Schedule: 0 0,8,16 * * * UTC
Scale: 0 → 1 replica at schedule times
Scale: 1 → 0 after ~30 min cooldown
```

When KEDA scales up:
1. Container starts
2. `lifespan()` runs startup collection
3. Items collected, quality-filtered, saved to blob, queued to processor
4. Container remains running, ready for manual HTTP triggers
5. After cooldown period, KEDA scales back to 0

## Data Flow

```
KEDA Cron Event (00:00/08:00/16:00 UTC)
        ↓
Container startup
        ↓
lifespan() → collect_quality_tech()
        ↓
collect_mastodon(fosstodon.org) → 25 items
collect_mastodon(techhub.social) → 15 items
        ↓
stream_collection() → quality gate + dedup + save + queue
        ↓
Blob Storage: collections/keda/keda_2025-10-23T16:00:00.json
Queue: content-processor-requests (valid items)
        ↓
FastAPI HTTP server ready
        ↓
KEDA cooldown → scale down
```

## Collection Template Used

**Template**: `quality-tech.json` (Production-recommended)

- **Mastodon instances**: fosstodon.org, techhub.social
- **Content focus**: Systems engineering, architecture, research papers
- **Reasoning**: Higher quality technical content vs. consumer gadget reviews
- **Quality gates**: Validation, readability, technical relevance checks
- **Dedup window**: 14 days (prevents republishing)

**Note**: Reddit collection is currently disabled (pending OAuth implementation). Uses Mastodon-only sources.

## Logging

**Sample startup logs**:
```
🚀 Content Womble starting up...
⚡ KEDA cron startup detected - running scheduled collection...
Collection ID: keda_2025-10-23T16:00:00
Collection Blob: collections/keda/keda_2025-10-23T16:00:00.json
Collecting from fosstodon.org...
Collecting from techhub.social...
✅ KEDA startup collection complete - Stats: collected=37, published=28, rejected_quality=9, rejected_dedup=0
📡 Content Womble HTTP API ready
```

**If collection is disabled**:
```
🚀 Content Womble starting up...
⏭️  AUTO_COLLECT_ON_STARTUP disabled - container ready for manual triggers
📡 Content Womble HTTP API ready
```

## Failure Handling

- **Collection errors don't crash container**: Logged and continue to manual HTTP mode
- **Partial collection**: If one instance fails, other continues
- **Queue client errors**: Logged, item skipped, pipeline continues
- **All errors**: Detailed error logs for debugging via Application Insights

## Verification Steps

1. **Check container loads**:
   ```bash
   cd /workspaces/ai-content-farm/containers/content-collector
   python -c "from main import app; print('✅ App loads')"
   ```

2. **Check tests still pass**:
   ```bash
   python -m pytest tests/ -v
   ```

3. **Watch for next scheduled collection** (16:00 UTC today or next scheduled time):
   - Monitor Azure Container Apps logs
   - Check blob storage: `collections/keda/keda_*.json`
   - Check queue: `content-processor-requests`
   - Check processed articles in `processed-content` container

4. **Manual trigger still works**:
   ```bash
   curl -X POST https://<container-url>/api/collect/trigger \
     -H "x-api-key: $COLLECTION_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"instances": ["fosstodon.org"], "max_items": 10}'
   ```

## Advantages of This Approach

✅ **Consistency**: All 4 containers use Container Apps (same auth model, managed identity)
✅ **Reliability**: Startup collection runs atomically with container lifecycle
✅ **Cost**: Zero additional cost (~$0.04/month same as alternatives)
✅ **Simplicity**: No new Azure services to manage
✅ **Flexibility**: Can disable with `AUTO_COLLECT_ON_STARTUP=false` for debugging
✅ **Proven**: Restores pattern you successfully used before
✅ **Observable**: Comprehensive logging and stats tracking

## Next Steps

1. **Deploy this change** to production (via PR merge to main)
2. **Monitor first scheduled collection** at next cron time
3. **Verify blob storage** contains collected items
4. **Verify processor** receives and processes items
5. **Check published articles** appear in published-content container
6. **Adjust parameters** if needed (instances, max_items, delays)

## Rollback

If issues arise, simply set:
```bash
AUTO_COLLECT_ON_STARTUP=false
```

No code changes needed - container will remain in manual-trigger-only mode.
