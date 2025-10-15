# Pipeline Monitoring Quick Start - UPDATED FOR REAL ISSUES

**For cron-based pipelines (runs every 8 hours)**

## TL;DR - Run These Now

```bash
# 1. Diagnose current issues
./scripts/diagnose-pipeline-issues.sh

# 2. Fix queue access (if needed - COMMON ISSUE)
export AZURE_STORAGE_CONNECTION_STRING="<from Azure Portal>"

# 3. Monitor next execution window
./scripts/monitor-cron-pipeline.sh
```

## 🚨 Critical Understanding: Cron-Based Execution

**Your pipeline is NOT continuous** - it's SUPPOSED to be idle most of the time:

- ⏰ Runs every **8 hours** via cron scheduler
- 💤 Idle between executions (scales to zero)
- ⏱️ Active for ~10-30 minutes per execution
- 📉 Queue depths will be zero most of the time

**This is normal and expected behavior!**

## Real Issues We Need to Fix

### Issue #1: Can't Read Queue Depths (Permission Problem)

**Symptom**: Script shows 0 for all queues, or "permission denied"  
**Root Cause**: Your user doesn't have Storage Account access by default  

**Quick Fix** - Use access key from Portal:
```bash
# Azure Portal → Storage Account → Access Keys → Copy Connection String
export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=...;AccountKey=..."

# Now try again
./scripts/diagnose-pipeline-issues.sh
```

**Permanent Fix** - Grant RBAC role:
```bash
# Get your user ID
USER_ID=$(az ad signed-in-user show --query id -o tsv)

# Get storage account ID
STORAGE_ID=$(az storage account list \
  --resource-group ai-content-prod-rg \
  --query '[0].id' -o tsv)

# Grant permission
az role assignment create \
  --assignee "$USER_ID" \
  --role "Storage Account Contributor" \
  --scope "$STORAGE_ID"

# Wait 2-3 minutes for propagation, then test:
az storage queue list --account-name <storage-account-name>
```

### Issue #2: Messages Being Processed Multiple Times

**Symptom**: Same content processed repeatedly, duplicate work  
**Root Cause**: `visibility_timeout=30s` but processing takes 60+ seconds  

When visibility timeout is too short:
1. Message becomes visible again before processing finishes
2. Another container picks it up
3. Same work happens twice
4. Costs double, OpenAI rate limits hit

**The Fix** - Update `/workspaces/ai-content-farm/libs/queue_client.py` line ~217:

```python
# CURRENT (WRONG):
message_pager = self._queue_client.receive_messages(
    messages_per_page=max_msgs,
    visibility_timeout=30,  # ❌ TOO SHORT!
)

# CHANGE TO (CORRECT):
message_pager = self._queue_client.receive_messages(
    messages_per_page=max_msgs,
    visibility_timeout=300,  # ✅ 5 minutes - enough for AI processing
)
```

**Better Fix** - Use the new handler:
```python
from libs.queue_message_handler import QueueMessageHandler

handler = QueueMessageHandler(
    queue_client=queue_client,
    visibility_timeout=300,  # 5 minutes
    max_dequeue_count=3,     # Retry max 3 times
    poison_queue_name="processing-poison-messages",
    enable_poison_queue=True  # Move failed messages to separate queue
)

async for message in handler.receive_messages(max_messages=10):
    async with handler.process_message(message):
        # Process message
        result = await process(message.content)
        # Automatically deleted on success
        # Automatically moved to poison queue after 3 failures
```

### Issue #3: OpenAI 429 Rate Limit Errors

**Symptom**: Logs show "429 Too Many Requests", processing fails  
**Root Cause**: Too many containers making concurrent OpenAI calls  

**Quick Fix** - Reduce concurrency:
```bash
# Limit content-processor to fewer replicas
az containerapp update \
  --name content-processor \
  --resource-group ai-content-prod-rg \
  --max-replicas 2 \
  --scale-rule-metadata queueLength=5

# This reduces concurrent OpenAI calls from 10+ to 2-4
```

**Proper Fix** - Implement rate limiting:
```python
from libs.rate_limiter import initialize_openai_rate_limiter, get_openai_rate_limiter

# In container startup (main.py):
initialize_openai_rate_limiter({
    "uksouth": (60, 60),      # 60 requests per 60 seconds
    "westeurope": (60, 60),   # 60 requests per 60 seconds
})

# Before each OpenAI call:
limiter = get_openai_rate_limiter()
async with limiter.use_region("uksouth") as region:
    # This will wait if rate limit exceeded
    response = await openai_client.chat.completions.create(...)
```

### Issue #4: Site Publisher Doesn't Trigger

**Symptom**: Content processed but site never updates  
**Root Cause**: Chain broken somewhere - likely cooldown or missing trigger  

**Check the chain**:
```bash
# 1. Did markdown-generator send the message?
az storage queue metadata show \
  --name site-publishing-requests \
  --connection-string "$AZURE_STORAGE_CONNECTION_STRING"

# 2. Is site-publisher configured correctly?
az containerapp show \
  --name site-publisher \
  --resource-group ai-content-prod-rg \
  --query "properties.template.scale"

# 3. Check recent logs
az containerapp logs show \
  --name site-publisher \
  --resource-group ai-content-prod-rg \
  --tail 50
```

**Common causes**:
1. **Cooldown too long** (300s = 5 minutes!)
   ```bash
   # Reduce to 60s
   az containerapp update \
     --name site-publisher \
     --resource-group ai-content-prod-rg \
     --min-replicas 0 --max-replicas 1
   # Note: cooldownPeriod set via separate CLI command (not in Terraform)
   ```

2. **queueLength threshold too high**
   ```bash
   # Trigger on ANY message
   az containerapp update \
     --name site-publisher \
     --resource-group ai-content-prod-rg \
     --scale-rule-metadata queueLength=1
   ```

3. **Missing environment variable**
   ```bash
   # Check markdown-generator has:
   az containerapp show \
     --name markdown-generator \
     --resource-group ai-content-prod-rg \
     --query "properties.template.containers[0].env[?name=='SITE_PUBLISHING_QUEUE_NAME']"
   ```

### Issue #5: Cooldown Times Not Optimized

**Symptom**: Containers stay running too long after work finishes  
**Root Cause**: Cooldown periods set conservatively (expensive)  

**Current settings** (from Terraform comments):
- content-collector: 45s ✅ OK
- content-processor: 60s ✅ OK  
- markdown-generator: 45s ✅ OK
- site-publisher: **300s** ❌ TOO LONG!

**Why this matters**:
- 5 minutes extra runtime = unnecessary costs
- Delays final publication
- No benefit (site builds fast)

**Fix**:
```bash
# Reduce site-publisher cooldown
az containerapp update \
  --name site-publisher \
  --resource-group ai-content-prod-rg \
  --min-replicas 0 --max-replicas 1
# Then set cooldownPeriod via Azure CLI (limitation of Terraform provider)
```

## Monitoring Commands

### Check If Pipeline Is Running
```bash
# Quick status
az containerapp list \
  --resource-group ai-content-prod-rg \
  --query "[].{Name:name, Replicas:properties.template.scale.currentReplicas}" \
  --output table

# If all show 0 replicas → Pipeline is idle (expected between cron runs)
# If any show >0 replicas → Execution window is active
```

### Monitor Active Execution Window
```bash
# Start monitoring (will wait if idle)
./scripts/monitor-cron-pipeline.sh

# Monitor and export data
./scripts/monitor-cron-pipeline.sh --export execution-$(date +%Y%m%d).csv

# Just check once without waiting
./scripts/monitor-cron-pipeline.sh --window 1
```

### Check Queue Depths (Requires Permissions!)
```bash
# Set connection string first (from Azure Portal)
export AZURE_STORAGE_CONNECTION_STRING="<from-portal>"

# Check all queues
for queue in content-collection-requests content-processing-requests markdown-generation-requests site-publishing-requests; do
  count=$(az storage queue metadata show \
    --name "$queue" \
    --connection-string "$AZURE_STORAGE_CONNECTION_STRING" \
    --query "approximateMessageCount" -o tsv 2>/dev/null || echo "0")
  echo "$queue: $count messages"
done
```

### Check for 429 Errors
```bash
# Get Application Insights name
APP_INSIGHTS=$(az monitor app-insights component list \
  --resource-group ai-content-prod-rg \
  --query "[0].name" -o tsv)

# Query for 429 errors in last 24 hours
az monitor app-insights query \
  --app "$APP_INSIGHTS" \
  --resource-group ai-content-prod-rg \
  --analytics-query "requests | where timestamp > ago(24h) and resultCode == '429' | summarize count() by bin(timestamp, 1h)" \
  --query "tables[0].rows" -o table
```

### Manual Test Trigger
```bash
# Trigger pipeline manually
az storage message put \
  --queue-name content-collection-requests \
  --connection-string "$AZURE_STORAGE_CONNECTION_STRING" \
  --content '{"service_name":"manual-test","operation":"wake_up","timestamp":"'$(date -Iseconds)'"}'

# Watch it process
./scripts/monitor-cron-pipeline.sh --window 30
```

## Recommended KEDA Configuration

Based on your issues, here's the optimal config:

### content-collector (Fast, Cheap)
```bash
queueLength: 10      # Default is fine
minReplicas: 0       # Scale to zero
maxReplicas: 5       # Can burst
cooldown: 45s        # Quick shutdown
```

### content-processor (Heavy, Expensive)
```bash
queueLength: 5       # 🔧 REDUCE from 10 (limit concurrency)
minReplicas: 0       # Scale to zero
maxReplicas: 2       # 🔧 REDUCE from 5 (avoid rate limits)
cooldown: 120s       # 🔧 INCREASE to 2min (processing takes time)
```

### markdown-generator (Medium, Cheap)
```bash
queueLength: 5       # Default is fine
minReplicas: 0       # Scale to zero
maxReplicas: 3       # Moderate burst
cooldown: 45s        # Quick shutdown
```

### site-publisher (Fast, Cheap)
```bash
queueLength: 1       # 🔧 TRIGGER ON ANY MESSAGE
minReplicas: 0       # Scale to zero
maxReplicas: 1       # Only need one
cooldown: 60s        # 🔧 REDUCE from 300s (5min → 1min)
```

### Apply Changes
```bash
# content-processor: Reduce concurrency
az containerapp update \
  --name content-processor \
  --resource-group ai-content-prod-rg \
  --max-replicas 2 \
  --scale-rule-metadata queueLength=5

# site-publisher: Faster trigger
az containerapp update \
  --name site-publisher \
  --resource-group ai-content-prod-rg \
  --scale-rule-metadata queueLength=1
```

## Understanding Metrics

### What to Track During Execution
1. **Queue depths** - Should decrease over time
2. **Replica counts** - Should match queue depth patterns
3. **Processing time** - End-to-end execution window
4. **Error rate** - 429 errors, failed messages
5. **Trigger chain** - Each stage should trigger next

### Healthy Execution Window Looks Like:
```
T+0min:  Cron triggers → collector scales up
T+2min:  Collection done → processor scales up
T+10min: Processing done → markdown scales up
T+12min: Markdown done → publisher scales up
T+15min: Publishing done → all scale to zero
```

### Problem Patterns:
- **Queue growing**: Processing slower than input
- **No scale-up**: KEDA not triggering (check queueLength)
- **Stuck at one stage**: Check logs for errors
- **Long tail**: cooldown too long, wasting money

## Troubleshooting Checklist

### Can't See Queue Depths?
- [ ] Set `AZURE_STORAGE_CONNECTION_STRING` environment variable
- [ ] Or grant "Storage Account Contributor" RBAC role
- [ ] Verify with: `az storage queue list --account-name <name>`

### Messages Being Reprocessed?
- [ ] Update visibility_timeout to 300s in queue_client.py
- [ ] Implement poison message queue
- [ ] Ensure delete_message only on success

### Getting 429 Errors?
- [ ] Reduce max_replicas on content-processor to 2
- [ ] Reduce queueLength to 5
- [ ] Implement rate limiter (libs/rate_limiter.py)
- [ ] Add retry with exponential backoff

### Site Not Publishing?
- [ ] Check markdown-generation-requests queue depth
- [ ] Check site-publishing-requests queue depth
- [ ] Reduce site-publisher cooldown to 60s
- [ ] Set queueLength to 1 for immediate trigger
- [ ] Check site-publisher logs

### Pipeline Idle?
- [ ] This is expected! Runs every 8 hours
- [ ] Check cron schedule in content-collector
- [ ] Or manually trigger with test message

## Next Steps

**Today**:
1. Run `./scripts/diagnose-pipeline-issues.sh`
2. Fix queue access permissions
3. Update visibility_timeout to 300s

**This Week**:
1. Implement rate limiter for OpenAI
2. Fix site-publisher cooldown
3. Test full execution window with monitoring

**Next Sprint**:
1. Optimize KEDA settings based on metrics
2. Implement poison message handling
3. Add alerting for stuck queues

## Reference Files

- **Full issue analysis**: `docs/PIPELINE_ISSUES_AND_FIXES.md`
- **Rate limiter implementation**: `libs/rate_limiter.py`
- **Message handler with proper deletion**: `libs/queue_message_handler.py`
- **Cron-aware monitoring**: `scripts/monitor-cron-pipeline.sh`
- **Diagnostics**: `scripts/diagnose-pipeline-issues.sh`
- **KEDA configuration**: `infra/container_app_*.tf`

---

**Last Updated**: October 14, 2025
**Status**: Addressing real production issues
