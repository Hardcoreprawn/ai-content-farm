# KEDA Scale-to-Zero Investigation

**Date**: October 11, 2025  
**Issue**: Containers with KEDA queue scalers not scaling to 0 despite empty queues

## Summary

Containers are staying at 1 replica even after queues have been empty for >1 hour, despite having `min_replicas = 0` configured in Terraform and KEDA `cooldownPeriod = 300s` (5 minutes).

## Expected Behavior (Per Microsoft/KEDA Documentation)

### Scale-to-Zero Process
1. **Polling** (every 30s): KEDA checks event source (Azure Storage Queue)
2. **Queue Empty**: No messages found (queueLength < 1)
3. **Cooldown Period** (300s): Wait 5 minutes after last message to ensure stability
4. **Scale to 0**: KEDA scales container from 1 → 0 replicas
5. **Scale Up**: When new message arrives, KEDA scales 0 → 1 replica

### Key Documentation Quotes

**Microsoft Azure Container Apps**:
> "Cool down period is how long after the last event was observed before the application scales down to its minimum replica count."
>
> "Cool down period only takes effect when scaling in from the final replica to 0."
>
> "You aren't billed usage charges if your container app scales to zero."

**Default Values**:
- Polling interval: 30 seconds
- Cool down period: 300 seconds (5 minutes)
- Min replicas: **0** (enables scale-to-zero)
- Max replicas: Configured per container

## Current Configuration

### Terraform Configuration (Correct)
```terraform
# infra/container_app_processor.tf
min_replicas = 0
max_replicas = 3

custom_scale_rule {
  name             = "storage-queue-scaler"
  custom_rule_type = "azure-queue"
  metadata = {
    queueName     = "content-processing-requests"
    accountName   = "aicontentprodstkwakpx"
    queueLength   = "1"  # Scale up when >= 1 message
    cloud         = "AzurePublicCloud"
  }
  # Managed identity auth configured separately
}
```

### Azure Actual State
```bash
$ az containerapp show --query "template.scale"
{
  "minReplicas": null,  # Azure API quirk - null means "use KEDA default" (0)
  "maxReplicas": 3,
  "cooldownPeriod": 300,
  "pollingInterval": 30,
  "rules": [{
    "custom": {
      "type": "azure-queue",
      "metadata": {
        "queueName": "content-processing-requests",
        "queueLength": "1"
      }
    }
  }]
}
```

**Terraform Drift Check**: `terraform plan` shows **No changes** - configuration matches infrastructure.

## Observed Behavior

### Container Status (October 11, 2025, 14:20 UTC)

| Container | Scaler Type | Queue Messages | Replicas | Last Activity | Expected | Actual |
|-----------|-------------|----------------|----------|---------------|----------|--------|
| collector | **cron** | N/A | **0** ✅ | 13:50 (30 min ago) | Scale 0→1→0 | **Working!** |
| processor | azure-queue | 5 (unprocessed) | **1** ❌ | 12:35 (1h45m ago) | Scale 0→1, process, →0 | **Stuck at 1** |
| markdown-gen | azure-queue | 0 | **1** ❌ | 13:48 (32 min ago) | Scale to 0 after 5min | **Stuck at 1** |
| site-publisher | azure-queue | 0 | **1** ❌ | 13:07 (1h13m ago) | Scale to 0 after 5min | **Stuck at 1** |

### Key Findings

1. **Cron scaler works perfectly** - Collector scales 0→1→0 as expected
2. **ALL queue scalers stuck at 1 replica** - None are scaling to 0
3. **Processor not processing** - 5 messages in queue since 13:51, all with `dequeueCount: 0`
4. **Container stays alive for health checks** - Logs show periodic GET / requests

### Processor Logs
```
2025-10-11T12:35:53Z - Queue empty after processing 267 messages. Container will stay alive for HTTP requests. KEDA will scale to 0 when queue remains empty.
2025-10-11T12:49:00Z - INFO: 100.100.0.201:35262 - "GET / HTTP/1.1" 200 OK
2025-10-11T13:56:35Z - INFO: 100.100.0.201:43524 - "GET / HTTP/1.1" 200 OK
2025-10-11T14:16:38Z - INFO: 100.100.0.201:57652 - "GET / HTTP/1.1" 200 OK
```

**Timeline**:
- **12:35:53**: Queue empty, container says "KEDA will scale to 0"
- **12:40:53**: 5 minutes passed (cooldown period complete)
- **13:51:19**: New messages arrive (1h15m after queue empty)
- **14:20:00**: Still at 1 replica, messages NOT processed

## Root Cause Analysis

### Hypothesis 1: Poll-Until-Empty Pattern Conflict ❌
**Theory**: Container processes until empty, then stops polling. KEDA can't scale because container isn't "idle".

**Evidence Against**:
- Code shows `asyncio.create_task(startup_queue_processor())` runs **once** on startup
- After queue empty, task exits and container just serves HTTP health checks
- Container IS idle - not continuously polling
- Logs show no queue checking after 12:35:53

**Verdict**: Not the issue. Container is properly idle after processing.

### Hypothesis 2: Ingress Health Probes Preventing Scale-Down ⚠️
**Theory**: External ingress with health probes keeps container "active" from KEDA's perspective.

**Evidence**:
- All containers have `external_enabled = true`
- Health check GET / requests every ~1 hour
- Microsoft docs say ingress WITH scale rules should work

**Questions**:
- Are health probes frequent enough to reset cooldown period?
- Is there a minimum probe interval that interferes with scale-to-zero?

**Needs Investigation**: Check Azure health probe configuration

### Hypothesis 3: Managed Identity Auth Keeping Connection Open ⚠️
**Theory**: Workload identity authentication maintains persistent connection to Azure services.

**Evidence**:
- All queue scalers use workload identity for authentication
- KEDA needs to query queue every 30s for metrics
- Possible Azure AD token refresh keeping sessions alive

**Needs Investigation**: Check if KEDA connection pooling prevents scale-down

### Hypothesis 4: Azure API Bug with minReplicas=null 🎯
**Theory**: Azure API showing `minReplicas: null` instead of `0` means it's not actually configured for scale-to-zero.

**Evidence**:
- `terraform show` indicates `min_replicas = 0` is set
- Azure API returns `"minReplicas": null`
- Terraform says no drift, but Azure behavior doesn't match

**Action**: Force explicit update to Azure

## Comparison: Working vs Broken

### ✅ Collector (Working - Scales to 0)
- Scaler: **cron** (time-based)
- Ingress: external_enabled = true
- Replicas: Currently 0
- Behavior: Scales 0→1 on schedule, processes, returns to 0

### ❌ Processor (Broken - Stuck at 1)
- Scaler: **azure-queue** (event-based)
- Ingress: external_enabled = true
- Replicas: Currently 1 (for 1h45m)
- Behavior: Never scales to 0, even after 5+ minute cooldown

**Key Difference**: Cron vs Queue scaler type!

## Action Plan

### ✅ Phase 1: Force Configuration Update (COMPLETED)
**Problem**: Azure API showed `minReplicas: null` instead of `0`, preventing scale-to-zero.

**Solution**: Force explicit update via Azure CLI:
```bash
az containerapp update --name ai-content-prod-processor --min-replicas 0 --max-replicas 3
az containerapp update --name ai-content-prod-markdown-gen --min-replicas 0 --max-replicas 5
az containerapp update --name ai-content-prod-site-publisher --min-replicas 0 --max-replicas 5
```

**Result**: `minReplicas` now explicitly set to `0` in Azure. ✅

**Next**: Wait for cooldown period (5 minutes) to see if containers scale to 0.

### 🚨 CRITICAL: Processor Architecture Depends on Scale-to-Zero

**The poll-until-empty pattern REQUIRES scale-to-zero to work properly:**

1. **Container Startup**: `asyncio.create_task(startup_queue_processor())` runs
2. **Processing Loop**: Polls queue, processes all messages until empty
3. **Loop Exit**: `break` when `messages_processed == 0` 
4. **Idle State**: Container serves HTTP health checks, but **NEVER POLLS QUEUE AGAIN**
5. **KEDA Must Terminate**: After cooldown (5 min), KEDA scales to 0, **killing the container**
6. **New Message Arrives**: KEDA detects message in queue
7. **Fresh Container**: KEDA scales 0→1, starting **NEW container instance**
8. **Fresh Startup**: New container runs `startup_queue_processor()` again, processes messages

**If scale-to-zero fails, the container becomes permanently deaf to new messages!**

This is exactly what happened:
- **12:35:53**: Processor finished processing 267 messages, queue empty, stopped polling
- **13:51:19**: 5 NEW messages arrived (1h15m later)
- **14:20:00**: Messages still unprocessed (29 minutes), processor deaf to queue
- **Root cause**: Container never terminated, never restarted, never ran startup processor again

**Immediate Action Required**:
1. Monitor processor for scale-to-zero after fixing minReplicas
2. If still doesn't scale to 0, we need to restart containers manually to clear the 5 messages
3. If scale-to-zero works, processor will restart and process messages automatically

### ❌ Phase 2: Scale-to-Zero Still Failing

**Test Results** (October 11, 2025, 14:58 UTC):
- ✅ Container restarted at 14:30:45 UTC
- ✅ Processed 196 messages successfully
- ✅ Queue empty at 14:49:45 UTC
- ❌ Expected scale-to-zero at 14:54:45 UTC (cooldown 300s)
- ❌ **Still at 1 replica at 14:58:37 UTC (3m52s past expected)**

**Evidence of Idle Container**:
- Last queue check: 14:49:45 UTC
- Only activity: Health checks at 14:50:02 and 14:58:56 (9 min apart)
- Queue confirmed empty
- No processing activity

**Root Cause Identified**: Missing `activationQueueLength` parameter!

Per KEDA documentation:
> `activationQueueLength` - Target value for activating the scaler. Learn more about activation here. (Default: `0`, Optional)
>
> **Activation only occurs when this value is greater than the set value**

Without `activationQueueLength`, KEDA may not properly detect when queue is at 0 for deactivation (scale to 0).

### Phase 3: Add Missing KEDA Parameters 🔧
Try to force Azure to recognize `minReplicas = 0`:

```bash
# Option A: Update via Azure CLI
az containerapp update \
  --name ai-content-prod-processor \
  --resource-group ai-content-prod-rg \
  --min-replicas 0 \
  --max-replicas 3

# Option B: Terraform taint and reapply
cd infra
terraform taint azurerm_container_app.processor
terraform apply
```

### Phase 2: Investigate Health Probe Configuration 🔍
Check if health probes are interfering:

```bash
# Check probe settings
az containerapp show \
  --name ai-content-prod-processor \
  --query "properties.configuration.ingress.healthProbeSettings"

# Consider: Disable external ingress for queue-based containers
# They only need HTTP for manual testing, not for KEDA operation
```

### Phase 3: Test Without Ingress 🧪
Temporarily disable ingress on one container to test if that's the issue:

```terraform
# Test on site-publisher (least critical)
ingress {
  external_enabled = false  # Disable public access
  target_port      = 8000
  traffic_weight {
    percentage      = 100
    latest_revision = true
  }
}
```

### Phase 4: Add Explicit Activation Threshold 🎯
KEDA documentation mentions `activationThreshold` for queue scalers:

```terraform
custom_scale_rule {
  name             = "storage-queue-scaler"
  custom_rule_type = "azure-queue"
  metadata = {
    queueName              = "content-processing-requests"
    queueLength            = "1"   # Target for scaling 1→N
    activationQueueLength  = "1"   # Threshold for activating 0→1
    accountName            = "aicontentprodstkwakpx"
    cloud                  = "AzurePublicCloud"
  }
}
```

## Questions for Documentation/Community

1. **Is `external_enabled = true` compatible with scale-to-zero for queue scalers?**
   - Cron scaler scales to 0 with external ingress enabled
   - Queue scalers don't scale to 0 with same config
   
2. **What is the actual meaning of `minReplicas: null` in Azure API?**
   - Terraform says `min_replicas = 0`
   - Azure returns `"minReplicas": null`
   - Behavior suggests it's treating as `minReplicas = 1`

3. **Do health probes reset the KEDA cooldown period?**
   - Health checks every ~1 hour
   - Cooldown is 5 minutes
   - Should not interfere, but needs confirmation

4. **Why is processor not processing new messages?** 🚨 **CRITICAL ARCHITECTURAL ISSUE**
   - Startup queue processor runs **once on container startup**, then exits
   - Container stays alive but **NEVER polls queue again**
   - Pattern requires: process → idle → KEDA terminates → new message → KEDA starts fresh container
   - **If KEDA doesn't scale to 0, container becomes permanently deaf to new messages**
   - This is why the 5 messages from 13:51 are still unprocessed at 14:20 (29 minutes later)

## References

- [Azure Container Apps Scale Rules](https://learn.microsoft.com/en-us/azure/container-apps/scale-app)
- [KEDA Azure Queue Scaler](https://keda.sh/docs/2.15/scalers/azure-storage-queue/)
- [KEDA Scaling Deployments](https://keda.sh/docs/2.15/concepts/scaling-deployments/)
- [Azure Container Apps Billing](https://learn.microsoft.com/en-us/azure/container-apps/billing)

## Next Steps

1. ✅ Document current behavior and configuration
2. ⏳ Force minReplicas update via Azure CLI
3. ⏳ Test with ingress disabled
4. ⏳ Add activationQueueLength parameter
5. ⏳ Contact Microsoft support if issue persists
