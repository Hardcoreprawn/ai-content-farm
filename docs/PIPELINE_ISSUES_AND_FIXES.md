# Pipeline Issues and Fixes

**Date**: October 14, 2025  
**Status**: Identified critical issues with cron-based pipeline

## Issues Identified

### 1. **Cron-Based Execution Pattern Misunderstood** 
**Problem**: Monitoring scripts assumed continuous operation, but pipeline runs every 8 hours via cron.
- Pipeline is idle most of the time (expected behavior)
- Containers scale to zero between runs
- Monitoring needs to focus on execution windows, not idle state

**Fix**: Update monitoring to:
- Track execution windows (8-hour intervals)
- Ignore idle periods
- Focus on queue depth during active processing
- Monitor cooldown periods after execution completes

### 2. **Queue Depth Not Moving (Permission Issues)**
**Problem**: Script can't read queue depths - likely authentication issue.
- Default user probably doesn't have Azure Storage Queue permissions
- Portal access keys != programmatic access
- Need proper RBAC roles or connection string

**Fix Options**:
```bash
# Option A: Grant RBAC permissions (recommended)
az role assignment create \
  --assignee <your-user-id> \
  --role "Storage Queue Data Reader" \
  --scope "/subscriptions/<sub-id>/resourceGroups/ai-content-prod-rg/providers/Microsoft.Storage/storageAccounts/<storage-account>"

# Option B: Use connection string (quick fix)
export AZURE_STORAGE_CONNECTION_STRING="<connection-string-from-portal>"
```

### 3. **Duplicate Message Processing**
**Problem**: Messages being processed multiple times - not properly deleted after processing.

**Root Cause**:
- `libs/queue_client.py` has visibility_timeout of 30 seconds
- AI processing takes longer than 30 seconds
- Messages become visible again before processing completes
- No proper dequeue count tracking

**Critical Code Issue** (`libs/queue_client.py:217`):
```python
message_pager = self._queue_client.receive_messages(
    messages_per_page=max_msgs,
    visibility_timeout=30,  # TOO SHORT! AI calls take 30-60+ seconds
)
```

**Fix Required**:
- Increase visibility_timeout to 300 seconds (5 minutes)
- Add dequeue_count tracking
- Implement poison message handling
- Delete messages ONLY after successful processing

### 4. **OpenAI 429 Rate Limit Errors**
**Problem**: Hitting Azure OpenAI rate limits, causing failures and retries.

**Root Causes**:
- Too many concurrent requests to OpenAI
- No proper rate limiting in code
- Retries compound the problem
- Multiple messages processing in parallel hitting same endpoint

**Current Code** (`containers/content-processor/external_api_client.py`):
- Has retry logic but no rate limiting
- No backoff strategy for 429 errors
- No request queuing or throttling

**Fix Required**:
- Implement rate limiter with token bucket algorithm
- Add exponential backoff specifically for 429 errors
- Reduce concurrent processing (max_messages)
- Consider using multiple OpenAI deployments for load balancing

### 5. **Site-Publisher Not Triggering**
**Problem**: Final step in pipeline doesn't execute - site not getting published.

**Root Cause Analysis**:
- markdown-generator should send message to `site-publishing-requests` queue
- Check if messages are actually being sent
- Check if site-publisher is receiving/processing messages
- Cooldown period might be too long (300s per config)

**Investigation Needed**:
```bash
# Check if messages are in queue
az storage queue peek \
  --name site-publishing-requests \
  --account-name <storage-account> \
  --num-messages 32

# Check site-publisher logs
az containerapp logs show \
  --name site-publisher \
  --resource-group ai-content-prod-rg \
  --follow
```

## Priority Fixes

### CRITICAL (Must Fix Immediately)

1. **Fix Message Deletion** - Messages being reprocessed multiple times
   - Update visibility_timeout to 300 seconds
   - Add poison message queue after 3 attempts
   - Ensure delete_message called ONLY on success

2. **Fix OpenAI Rate Limiting** - 429 errors breaking pipeline
   - Implement rate limiter
   - Reduce concurrent processing
   - Add exponential backoff for 429

3. **Fix Site Publisher Trigger** - Final step not executing
   - Verify queue message sent from markdown-generator
   - Check site-publisher KEDA scaling configuration
   - Verify cooldown period not preventing scale-up

### HIGH (Should Fix Soon)

4. **Fix Queue Depth Monitoring** - Can't track pipeline progress
   - Grant proper Azure permissions
   - Update monitoring script to use connection string fallback

5. **Update Monitoring for Cron Pattern** - False assumptions about idle state
   - Track execution windows
   - Focus on active processing time
   - Monitor cooldown effectiveness

### MEDIUM (Nice to Have)

6. **Optimize Cooldown Times** - Balance cost vs responsiveness
   - content-collector: 45s (probably fine)
   - content-processor: 60s (may need adjustment)
   - markdown-generator: 45s (probably fine)
   - site-publisher: 300s (seems excessive, try 60-90s)

## Recommended Configuration Changes

### Queue Configuration (`infra/storage.tf`)
```terraform
# Add message lifecycle properties
resource "azurerm_storage_account_queue_properties" "main" {
  storage_account_id = azurerm_storage_account.main.id

  logging {
    delete  = true
    read    = true
    write   = true
    version = "1.0"
    retention_policy {
      days = 7
    }
  }

  # Global queue settings
  hour_metrics {
    enabled = true
    version = "1.0"
    retention_policy {
      days = 7
    }
  }
}

# Per-queue configuration needed:
# - message_ttl: 604800 (7 days)
# - visibility_timeout: 300 (5 minutes - configurable per receive)
# - max_dequeue_count: 3 (automatic poison message queue)
```

### KEDA Scaling Configuration
```bash
# content-processor: Heavy AI processing
az containerapp update \
  --name content-processor \
  --resource-group ai-content-prod-rg \
  --scale-rule-name queue-scaling \
  --scale-rule-metadata queueLength=5 \  # Reduce from 10
  --min-replicas 0 \
  --max-replicas 2 \  # Reduce concurrency
  --cooldown-period 120  # 2 minutes

# site-publisher: Quick builds
az containerapp update \
  --name site-publisher \
  --resource-group ai-content-prod-rg \
  --scale-rule-name queue-scaling \
  --scale-rule-metadata queueLength=1 \  # Trigger on any message
  --cooldown-period 60  # 1 minute instead of 5
```

### Container Environment Variables
```bash
# Add to all containers processing queues
QUEUE_VISIBILITY_TIMEOUT=300  # 5 minutes
QUEUE_MAX_DEQUEUE_COUNT=3
QUEUE_POISON_QUEUE_ENABLED=true

# Add to content-processor
OPENAI_MAX_CONCURRENT_REQUESTS=2  # Limit concurrent calls
OPENAI_REQUEST_TIMEOUT=60
OPENAI_RATE_LIMIT_RPM=60  # Requests per minute
```

## Testing Plan

### 1. Manual Trigger Test
```bash
# Trigger collection manually
az containerapp exec \
  --name content-collector \
  --resource-group ai-content-prod-rg \
  --command "python -m pytest tests/integration/"

# Watch queue depths in real-time
./scripts/monitor-pipeline-performance.sh --interval 5 --duration 30
```

### 2. Message Flow Test
```bash
# Send test message to each queue
for queue in content-collection-requests content-processing-requests markdown-generation-requests site-publishing-requests; do
  az storage message put \
    --queue-name $queue \
    --content '{"service_name":"test","operation":"health_check","timestamp":"'$(date -Iseconds)'"}' \
    --time-to-live 3600
done

# Monitor processing
watch -n 5 'az containerapp list --resource-group ai-content-prod-rg --query "[].{Name:name, Replicas:properties.runningStatus, Status:properties.provisioningState}" -o table'
```

### 3. Rate Limit Test
```bash
# Generate load to test rate limiting
for i in {1..20}; do
  curl -X POST https://content-processor.whatever.azurecontainerapps.io/process \
    -H "Content-Type: application/json" \
    -d '{"collection_id":"test-'$i'"}' &
done

# Monitor 429 errors in logs
az monitor metrics list \
  --resource <app-insights-resource-id> \
  --metric "requests/failed" \
  --filter "resultCode eq '429'"
```

## Monitoring Improvements

### Execution Window Tracking
```python
# Add to monitoring script
def detect_execution_window():
    """Detect if pipeline is in active execution window."""
    # Check if any containers have replicas > 0
    # Check if any queues have messages
    # Last execution time from Application Insights
    pass

def get_execution_metrics():
    """Get metrics for current/last execution window."""
    return {
        "start_time": "...",
        "end_time": "...",
        "messages_processed": 123,
        "errors": 2,
        "average_processing_time": 45.2,
        "openai_429_count": 5,
    }
```

### Queue Depth Alerting
```bash
# Alert if queue depth growing during execution window
az monitor metrics alert create \
  --name queue-depth-alert \
  --resource-group ai-content-prod-rg \
  --scopes <storage-account-resource-id> \
  --condition "avg QueueMessageCount > 50" \
  --window-size 5m \
  --evaluation-frequency 1m \
  --action-groups <action-group-id>
```

## Next Steps

1. **Immediate**: Fix message deletion and visibility timeout
2. **Today**: Implement OpenAI rate limiting
3. **This Week**: Debug site-publisher triggering
4. **Next Sprint**: Optimize KEDA scaling parameters based on real metrics

## References

- Azure Storage Queue visibility timeout: https://learn.microsoft.com/en-us/azure/storage/queues/storage-queues-introduction#message-visibility
- KEDA Azure Queue scaler: https://keda.sh/docs/2.12/scalers/azure-storage-queue/
- OpenAI rate limits: https://learn.microsoft.com/en-us/azure/ai-services/openai/quotas-limits
- Poison message handling: https://learn.microsoft.com/en-us/azure/storage/queues/storage-queues-introduction#poison-messages
