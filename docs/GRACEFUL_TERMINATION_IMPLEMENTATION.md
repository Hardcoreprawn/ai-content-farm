# Graceful Self-Termination Implementation

**Date:** October 13, 2025  
**Status:** ✅ Deployed to Production  
**Commits:** 8237627 (code), b5d8f03 (infrastructure)

## Overview

Implemented graceful self-termination across all three queue-based containers as a backup mechanism to KEDA autoscaling. This ensures containers shut down gracefully after a configurable idle timeout, even if KEDA doesn't scale them down as expected.

## Problem Statement

### KEDA Scaling Behavior
KEDA scales based on **queue metrics** (queueLength), not container activity:
- **Polling interval:** 30 seconds (KEDA checks queue length)
- **Cooldown periods:** 
  - markdown-generator: 45s
  - content-processor: 60s
  - site-publisher: 300s (5 minutes)
- **Scale-down timing:** Queue empty time + cooldown period + polling interval

**Example:** With 45s cooldown, actual scale-down takes 75-105 seconds after queue empties.

### Issue
Containers continued polling indefinitely even when queues were empty, leading to:
- Unnecessary compute costs
- Containers running for hours with no work
- No guaranteed shutdown mechanism

## Solution: Graceful Self-Termination

### Implementation Pattern

All three containers now implement the same pattern:

```python
from datetime import datetime, timezone

# At startup
MAX_IDLE_TIME = int(os.getenv("MAX_IDLE_TIME_SECONDS", "180"))
last_activity_time = datetime.utcnow()  # or datetime.now(timezone.utc)

# In polling loop
while True:
    messages = await check_queue()
    
    if messages:
        process_messages(messages)
        last_activity_time = datetime.utcnow()  # Reset timer
    else:
        # Check if idle too long
        idle_seconds = (datetime.utcnow() - last_activity_time).total_seconds()
        if idle_seconds >= MAX_IDLE_TIME:
            logger.info(f"🛑 Graceful shutdown: No messages for {int(idle_seconds)}s")
            break  # Exit polling loop
        
        await asyncio.sleep(10)  # Wait before next check
```

### Configuration

**Environment Variable:** `MAX_IDLE_TIME_SECONDS`

**Configured Values (via Terraform):**
- **content-processor:** 180s (3 minutes)
  - Rationale: 3x the 60s KEDA cooldown period
  - Safety margin for burst workloads
  
- **markdown-generator:** 180s (3 minutes)
  - Rationale: 4x the 45s KEDA cooldown period
  - Allows for queue draining + site-publisher signaling
  
- **site-publisher:** 300s (5 minutes)
  - Rationale: Matches KEDA cooldown period exactly
  - Accounts for longer Hugo build times

## Files Modified

### Container Code
1. **containers/content-processor/main.py**
   - Added datetime import
   - Added MAX_IDLE_TIME tracking in `startup_queue_processor()`
   - Tests: 406 passed, 3 skipped ✅

2. **containers/markdown-generator/queue_processor.py**
   - Added graceful termination with idle timer
   - Preserves site-publisher signaling logic
   - Tests: 63 passed ✅

3. **containers/site-publisher/app.py**
   - Added graceful termination with idle timer
   - Uses timezone-aware datetime
   - Tests: 63 passed, 1 skipped, 1 warning ✅

### Infrastructure
1. **infra/container_app_processor.tf**
   - Added `MAX_IDLE_TIME_SECONDS=180` environment variable

2. **infra/container_app_markdown_generator.tf**
   - Added `MAX_IDLE_TIME_SECONDS=180` environment variable

3. **infra/container_app_site_publisher.tf**
   - Added `MAX_IDLE_TIME_SECONDS=300` environment variable

## Benefits

### Cost Optimization
- **Guaranteed shutdown:** Containers stop after idle period regardless of KEDA behavior
- **No runaway costs:** Prevents containers from running indefinitely
- **Configurable per environment:** Can adjust timeouts based on workload patterns

### Reliability
- **Defense in depth:** Backup mechanism to KEDA autoscaling
- **Graceful cleanup:** FastAPI lifespan handlers run before exit
- **No abrupt termination:** Breaks from loop cleanly

### Operational Excellence
- **Explicit configuration:** No reliance on code defaults
- **Observable behavior:** Clear log messages on shutdown
- **Testable:** All tests passing with new logic

## Behavior Analysis

### Normal Operation
1. Message arrives in queue
2. Container processes message
3. `last_activity_time` resets
4. Container continues polling

### Idle Timeout
1. Queue empty for MAX_IDLE_TIME seconds
2. Container logs graceful shutdown message
3. Breaks from polling loop
4. FastAPI lifespan shutdown handlers run
5. Container exits cleanly

### KEDA Interaction
- **KEDA still primary:** Containers should scale down via KEDA first
- **Termination is backup:** Only triggers if KEDA doesn't scale down
- **Timing relationship:**
  - KEDA expected: 75-105s (45s cooldown)
  - Graceful termination: 180s (default)
  - Termination only if KEDA fails or is delayed

## Testing

### Test Results
```bash
# content-processor
PYTHONPATH=/workspaces/ai-content-farm python -m pytest tests/ -v
# Result: 406 passed, 3 skipped ✅

# markdown-generator
PYTHONPATH=/workspaces/ai-content-farm python -m pytest tests/ -v
# Result: 63 passed ✅

# site-publisher
PYTHONPATH=/workspaces/ai-content-farm python -m pytest tests/ -v
# Result: 63 passed, 1 skipped, 1 warning ✅
```

### Production Verification
To verify in production:

```bash
# Check environment variables
az containerapp show --name ai-content-prod-processor \
  --resource-group ai-content-prod-rg \
  --query "properties.template.containers[0].env[?name=='MAX_IDLE_TIME_SECONDS']" \
  -o table

# Monitor logs for graceful shutdown messages
az containerapp logs show --name ai-content-prod-processor \
  --resource-group ai-content-prod-rg \
  --follow

# Look for: "🛑 Graceful shutdown: No messages for Xs"
```

## Deployment

### CI/CD Pipeline
Both commits pushed to main branch, triggering automated deployment:

1. **Commit 8237627:** Container code changes
   - GitHub Actions: tests → security → build → deploy
   - Container images rebuilt and deployed

2. **Commit b5d8f03:** Terraform infrastructure
   - GitHub Actions: terraform plan → apply
   - Environment variables added to running containers

### Rollout Strategy
- **Zero-downtime:** New environment variables added without disruption
- **Backward compatible:** Default values in code (180s)
- **Immediate effect:** Next container restart picks up new config

## Future Considerations

### Potential Adjustments
- **Increase timeout:** If containers terminate too early during burst workloads
- **Decrease timeout:** If faster cost optimization is needed
- **Per-environment tuning:** Different values for dev/staging/prod

### Monitoring Recommendations
1. Track frequency of graceful shutdowns vs KEDA scale-downs
2. Monitor if timeouts are too aggressive (premature terminations)
3. Analyze cost savings from idle timeout mechanism

### Related Documentation
- `docs/KEDA_SCALING_BEHAVIOR.md` - Understanding KEDA autoscaling
- `AGENTS.md` - Worker/Scheduler pattern and architecture
- `infra/container_apps_keda_auth.tf` - KEDA configuration

## References

- **KEDA Azure Queue Scaler:** https://keda.sh/docs/latest/scalers/azure-storage-queue/
- **Azure Container Apps Scaling:** https://learn.microsoft.com/en-us/azure/container-apps/scale-app
- **Graceful Shutdown Pattern:** FastAPI lifespan events

---

**Last Updated:** October 13, 2025  
**Author:** GitHub Copilot (AI Assistant)  
**Review Status:** Deployed to Production ✅
