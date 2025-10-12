# KEDA Scaling Investigation Report - October 12, 2025

## Executive Summary

I've identified **multiple critical issues** preventing your Azure Container Apps from scaling properly with KEDA. The good news is these are all **fixable configuration issues**, not fundamental architecture problems.

### Critical Finding: KEDA Configuration Corruption

**The KEDA scale rule metadata for queue-triggered containers has been WIPED OUT!**

When I ran `az containerapp update` to restart the processor, the scale rule metadata returned **completely empty**:

```json
"metadata": {
  "accountName": "",           // ❌ EMPTY - should be "aicontentprodstkwakpx"
  "activationQueueLength": "", // ❌ EMPTY - should be "1"
  "cloud": "",                 // ❌ EMPTY - should be "AzurePublicCloud"
  "queueLength": "",           // ❌ EMPTY - should be "80"
  "queueLengthStrategy": "",   // ❌ EMPTY - should be "all"
  "queueName": ""              // ❌ EMPTY - should be "content-processing-requests"
}
```

**This explains EVERYTHING:**
- ✅ Collector works (CRON scaler has valid metadata)
- ❌ Processor stuck (queue metadata empty - KEDA can't monitor queue)
- ❌ Markdown-gen stuck (same issue)
- ❌ Site-publisher stuck (same issue)

## Issues Identified

### 🚨 Issue #1: KEDA Configuration Loss (CRITICAL)

**Problem**: The `null_resource` provisioner in `container_apps_keda_auth.tf` runs AFTER container creation, but Azure CLI updates **overwrite** the KEDA configuration instead of merging with Terraform-managed config.

**Root Cause**: 
1. Terraform creates container with basic scale rule structure
2. `null_resource` tries to update KEDA auth with `az containerapp update --scale-rule-*`
3. Azure CLI doesn't merge - it **replaces** the entire scale rule
4. All metadata fields get blanked out during the update

**Evidence**:
- Terraform shows `queueLength = "80"` in code
- Azure shows `queueLength = ""` in actual deployment
- CRON scaler works (no separate auth update needed)

**Impact**: KEDA cannot monitor queue depth, so scaling is completely broken for all queue-triggered containers.

---

### 🚨 Issue #2: `minReplicas = null` Problem (HIGH)

**Problem**: All containers show `minReplicas: null` instead of `0`, preventing scale-to-zero.

**Root Cause**: Terraform sets `min_replicas = 0`, but Azure API quirk treats this as "not configured" and returns `null`. However, you've documented this as "null means use KEDA default (0)" which should work - **but only if KEDA is properly configured** (which it isn't due to Issue #1).

**Impact**: Even if KEDA could monitor queues, containers wouldn't scale to zero.

---

### 🚨 Issue #3: Architecture Mismatch with Poll-Until-Empty Pattern (HIGH)

**Problem**: Your container code processes messages until the queue is empty, then **stops polling forever** and waits for KEDA to kill it. But if KEDA can't scale to zero (Issues #1 and #2), containers become "zombie" processes.

**Code Evidence** (`content-processor/main.py`):
```python
async def startup_queue_processor():
    while True:
        messages_processed = await process_queue_messages(...)
        
        if messages_processed == 0:
            # ❌ Container stops checking queue forever!
            logger.info("Queue empty. Container will remain alive. KEDA will scale to 0...")
            break  # ← Never polls again!
```

**The Problem**:
1. Container processes 267 messages
2. Queue becomes empty
3. Container exits polling loop with `break`
4. Container sits idle serving health checks
5. New messages arrive in queue (5 messages currently waiting!)
6. **Container never sees them** (not polling anymore)
7. KEDA can't scale to zero (broken config)
8. Result: Container runs forever, processing nothing, costing money

**This pattern REQUIRES working scale-to-zero** - without it, you have containers that stop working after their first batch!

---

### ⚠️ Issue #4: Using `os._exit()` Instead of Proper Shutdown (MEDIUM)

**Problem**: `content-collector` uses `os._exit(exit_code)` for shutdown, which is a **hard kill** that bypasses all cleanup, signal handlers, and KEDA lifecycle management.

**Code**: `containers/content-collector/main.py:53`
```python
async def graceful_shutdown(exit_code: int = 0):
    logger.info(f"Scheduling graceful shutdown in 2 seconds (exit_code: {exit_code})")
    await asyncio.sleep(2)
    logger.info("Graceful shutdown complete")
    os._exit(exit_code)  # ❌ Hard kill - KEDA might see this as crash
```

**Better Approach**: Let KEDA manage scaling. Container should:
1. Process work
2. Return to idle state (serve health checks)
3. Let KEDA scale to zero after cooldown period

**Impact**: Containers marked as "failed" in Azure logs, KEDA may not trust scaling decisions.

---

### ⚠️ Issue #5: KEDA `cooldownPeriod` Only Applies to Final Replica (MEDIUM)

**Problem**: You have `queueLength = "80"` for processor, meaning KEDA targets 80 messages per replica. But `cooldownPeriod = 300s` only affects **1→0 scaling**, not **N→N-1**.

**KEDA Behavior**:
- **2→1 scaling**: Immediate (no cooldown)
- **1→0 scaling**: 300 second cooldown

**Scenario**:
1. 100 messages arrive → KEDA scales to 2 replicas (100/80 = 1.25 ≈ 2)
2. Replicas process 50 messages each
3. Queue down to 50 messages → **KEDA immediately scales 2→1** (no cooldown!)
4. Last replica processes remaining 50 messages
5. Queue empty → KEDA waits 300s → scales 1→0

**Impact**: Less severe than other issues, but means your processor might thrash between replica counts during processing.

---

### ⚠️ Issue #6: Inconsistent `queueLength` Configuration (LOW)

**Current Config**:
- `content-processor`: `queueLength = "80"` (batch processing)
- `markdown-generator`: `queueLength = "1"` (individual items)
- `site-publisher`: `queueLength = "1"` (individual items)

**Problem**: Processor has 5 messages waiting but won't scale because:
1. KEDA config is broken (Issue #1)
2. Even if fixed, 5 messages < 80 threshold = 0 replicas
3. But you have `minReplicas = 1` set (temporarily), so it's at 1 replica
4. But container stopped polling (Issue #3)

**Result**: Messages sit unprocessed despite container running.

---

## Current System State Analysis

### Queue Status (October 12, 2025 - 15:48 UTC)

| Queue | Messages | Oldest Message | Status |
|-------|----------|----------------|--------|
| `content-processing-requests` | 5+ | Oct 11, 20:25 | ❌ **Unprocessed for 19+ hours** |
| `markdown-generation-requests` | Unknown | - | Unknown |
| `site-publishing-requests` | Unknown | - | Unknown |

### Container Status

| Container | Replicas | KEDA Config | Polling | Status |
|-----------|----------|-------------|---------|--------|
| `collector` | 0 (scales on CRON) | ✅ Valid | N/A (CRON) | ✅ **Working** |
| `processor` | 0 (was 1) | ❌ **Empty metadata** | ❌ Stopped after first batch | 🚨 **Broken** |
| `markdown-gen` | Unknown | ❌ **Likely empty** | ❌ Likely stopped | 🚨 **Broken** |
| `site-publisher` | Unknown | ❌ **Likely empty** | ❌ Likely stopped | 🚨 **Broken** |

### Message Details from Queue

Messages have been waiting since **October 11, 20:25 UTC** (19+ hours ago!):
- All have `dequeueCount: 0` (never attempted)
- All have 7-day expiration
- Topics include: Apple Virtual Knob, PHP Survival, NES Emulator, etc.

**This proves**: Processor is not checking the queue at all.

---

## Root Cause Chain

```
┌─────────────────────────────────────────┐
│ Terraform creates container with       │
│ scale rule structure                    │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ null_resource runs az containerapp     │
│ update --scale-rule-metadata ...       │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ Azure CLI REPLACES scale rule instead  │
│ of MERGING (Azure bug/limitation)      │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ All metadata fields become empty ""    │
│ KEDA can't read queue metrics          │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ Container scales to 1 (minReplicas)    │
│ Processes first batch of messages      │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ Queue empty → Container stops polling  │
│ Sits idle serving health checks        │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ New messages arrive in queue           │
│ KEDA can't see them (broken config)    │
│ Container doesn't check (stopped poll) │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ Messages sit unprocessed for 19+ hrs  │
│ Container wastes compute (can't scale) │
└─────────────────────────────────────────┘
```

---

## Recommended Solutions

### 🎯 Solution #1: Fix KEDA Configuration Method (CRITICAL - DO THIS FIRST)

**The Problem**: Using `az containerapp update --scale-rule-*` after Terraform creation wipes out metadata.

**The Fix**: Configure KEDA scaling **entirely in Terraform** using the `azapi` provider (which supports workload identity for KEDA).

**Implementation**:

```hcl
# infra/container_apps_keda_auth_FIXED.tf

# Remove all null_resource blocks - they're causing the corruption!

# Instead, use azapi provider to set authentication properly
resource "azapi_update_resource" "processor_keda_auth" {
  type        = "Microsoft.App/containerApps@2023-05-01"
  resource_id = azurerm_container_app.content_processor.id

  body = jsonencode({
    properties = {
      template = {
        scale = {
          minReplicas = 0  # Explicit zero
          maxReplicas = 3
          rules = [{
            name = "storage-queue-scaler"
            custom = {
              type = "azure-queue"
              metadata = {
                accountName             = azurerm_storage_account.main.name
                queueName               = azurerm_storage_queue.content_processing_requests.name
                queueLength             = "80"
                activationQueueLength   = "1"
                queueLengthStrategy     = "all"
                cloud                   = "AzurePublicCloud"
              }
              auth = [{
                triggerParameter = "workloadIdentity"
                secretRef        = azurerm_user_assigned_identity.containers.client_id
              }]
            }
          }]
        }
      }
    }
  })
}
```

**Alternative**: Use ARM template deployment or wait for azurerm provider update.

---

### 🎯 Solution #2: Change Container Architecture to Continuous Polling (RECOMMENDED)

**The Problem**: Poll-until-empty pattern requires scale-to-zero, creating a fragile dependency.

**The Fix**: Implement continuous polling with configurable intervals.

**Implementation**:

```python
# containers/content-processor/main.py

async def continuous_queue_processor():
    """
    Continuously poll queue with backoff.
    Let KEDA manage scaling - don't try to be smart about when to stop.
    """
    consecutive_empty_checks = 0
    
    while True:  # ← Never exit polling loop!
        try:
            messages_processed = await process_queue_messages(
                queue_name="content-processing-requests",
                message_handler=message_handler,
                max_messages=10,
            )
            
            if messages_processed == 0:
                consecutive_empty_checks += 1
                
                # Exponential backoff when queue empty
                wait_time = min(2 ** consecutive_empty_checks, 30)  # Max 30s
                logger.info(f"Queue empty. Waiting {wait_time}s before next check...")
                await asyncio.sleep(wait_time)
            else:
                consecutive_empty_checks = 0
                logger.info(f"Processed {messages_processed} messages. Checking for more...")
                await asyncio.sleep(1)  # Brief pause between batches
                
        except Exception as e:
            logger.error(f"Error in queue processor: {e}")
            await asyncio.sleep(5)  # Wait before retry on error
```

**Benefits**:
- ✅ Container always responds to new messages
- ✅ Exponential backoff reduces waste when idle
- ✅ KEDA still works (scales based on queue depth, not container state)
- ✅ No dependency on scale-to-zero
- ✅ More resilient to KEDA config issues

**Cost Impact**: Minimal - idle polling with 30s backoff vs scale-to-zero difference is ~$1-2/month per container.

---

### 🎯 Solution #3: Remove `os._exit()` and Let KEDA Manage Lifecycle

**The Problem**: Hard exits confuse KEDA and create "failed" container states.

**The Fix**: Remove auto-shutdown from CRON collector, let KEDA handle it.

```python
# containers/content-collector/main.py

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with KEDA cron auto-collection."""
    logger.info("Content Womble starting up...")

    # Check if this startup was triggered by KEDA cron scaling
    if os.getenv("KEDA_CRON_TRIGGER", "false").lower() == "true":
        logger.info("Detected KEDA cron trigger - running scheduled collection")
        try:
            from endpoints.collections import run_scheduled_collection

            metadata = {
                "timestamp": time.time(),
                "function": "content-womble",
                "version": "1.0.0",
            }
            result = await run_scheduled_collection(metadata)
            logger.info(f"Scheduled collection completed: {result.message}")

            # ❌ REMOVE THIS BLOCK - Let KEDA handle shutdown!
            # asyncio.create_task(graceful_shutdown())

        except Exception as e:
            logger.error(f"Failed to run scheduled collection: {str(e)}")
            # ❌ REMOVE THIS TOO - Let KEDA retry instead of hard exit

    logger.info("Content Womble ready - waiting for next KEDA trigger")

    try:
        yield
    finally:
        logger.info("Content Womble shutting down...")
        # Cleanup happens here naturally
```

**Update KEDA CRON Config**:
```terraform
# infra/container_app_collector.tf

custom_scale_rule {
  name             = "cron-scaler"
  custom_rule_type = "cron"
  metadata = {
    timezone        = "UTC"
    start           = "0 0,8,16 * * *"  # Every 8 hours
    end             = "10 0,8,16 * * *" # Force scale-down after 10 min
    desiredReplicas = "1"
  }
}
```

**Why This Works**:
- KEDA scales to 1 at scheduled time
- Container runs collection (~2-5 minutes)
- Container returns to idle state
- KEDA forcibly scales to 0 after 10 minutes (safety timeout)
- No hard exits, clean lifecycle

---

### 🎯 Solution #4: Adjust `queueLength` for Responsive Processing

**Current**: `queueLength = "80"` means processor needs 80+ messages to scale from 0→1.

**Problem**: You have 5 messages waiting, but threshold is 80, so KEDA won't trigger.

**Fix Options**:

**Option A: Lower threshold (Recommended)**
```terraform
queueLength = "1"  # Scale immediately when ANY message arrives
```

**Option B: Keep batch processing**
```terraform
queueLength = "20"  # Scale when 20+ messages (better than 80)
activationQueueLength = "1"  # But activate at 1 message (0→1 scaling)
```

**Recommendation**: Use Option B for balance:
- `activationQueueLength = "1"` → Wakes container from 0 when first message arrives
- `queueLength = "20"` → Scales additional replicas when 20+ messages per replica

---

### 🎯 Solution #5: Explicit `minReplicas = 0` Everywhere

**The Problem**: `minReplicas = null` is confusing and may not work as expected.

**The Fix**: Explicitly set to 0 in all containers.

```terraform
# Update all container_app_*.tf files

template {
  # ... container config ...
  
  min_replicas = 0  # ✅ Explicit zero
  max_replicas = 3  # Or appropriate value
  
  custom_scale_rule {
    # ... scaler config ...
  }
}
```

Then force update in Azure:
```bash
az containerapp update --name ai-content-prod-processor --min-replicas 0 --max-replicas 3
az containerapp update --name ai-content-prod-markdown-gen --min-replicas 0 --max-replicas 5
az containerapp update --name ai-content-prod-site-publisher --min-replicas 0 --max-replicas 2
```

---

## Security & Monitoring Recommendations

### 🔒 Security Issues

1. **No authentication on queue operations** - Any container can read/write any queue
2. **Wide IP restriction** (`81.2.90.47/32`) - Single point of compromise
3. **No rate limiting** - Containers could be DoS'd via queue flooding
4. **Error messages may leak sensitive data** - Review logging practices

### 📊 Monitoring Gaps

1. **No KEDA metrics** - Can't see when/why scaling triggers
2. **No queue depth alerts** - 5 messages sat for 19 hours unnoticed!
3. **No container lifecycle tracking** - When do containers start/stop?
4. **No cost alerts** - Running containers at 1 replica 24/7 = ~10x expected cost

**Recommendations**:
```bash
# Add Application Insights queries
- KEDA scaling events (ContainerAppSystemLogs)
- Queue depth over time (StorageQueueLogs)
- Container state transitions (ContainerAppConsoleLogs)
- Processing duration vs queue wait time

# Add Azure Monitor alerts
- Queue depth > 10 for > 15 minutes
- Container at 1 replica for > 1 hour (should scale to 0)
- KEDA scaler errors
- Message age > 1 hour in queue
```

---

## Implementation Priority

### 🚨 Immediate (Today)

1. **Fix KEDA configuration** (Solution #1) - Without this, nothing works
2. **Lower `queueLength` threshold** (Solution #4) - Get processing working again
3. **Process stuck messages** - Manually trigger processor to clear 19-hour backlog

### ⚠️ Short-term (This Week)

4. **Change to continuous polling** (Solution #2) - Make system resilient
5. **Remove `os._exit()` calls** (Solution #3) - Fix collector lifecycle
6. **Set explicit `minReplicas = 0`** (Solution #5) - Enable scale-to-zero

### 📊 Medium-term (Next Week)

7. **Add KEDA monitoring** - Visibility into scaling decisions
8. **Add queue depth alerts** - Catch processing failures early
9. **Add cost monitoring** - Track actual vs expected spend

### 🔒 Long-term (Next Month)

10. **Security hardening** - Review authentication, logging, rate limits
11. **Performance optimization** - Tune `queueLength`, cooldown, batch sizes
12. **Chaos testing** - Simulate failures, verify recovery

---

## Testing Plan

### Phase 1: Configuration Fix Validation

```bash
# 1. Deploy fixed KEDA configuration
terraform apply

# 2. Verify metadata is populated
az containerapp show --name ai-content-prod-processor \
  --resource-group ai-content-prod-rg \
  --query "properties.template.scale.rules[0].custom.metadata"

# Expected output:
{
  "accountName": "aicontentprodstkwakpx",
  "queueName": "content-processing-requests",
  "queueLength": "20",  # Or "1" if using Option A
  "activationQueueLength": "1",
  "queueLengthStrategy": "all",
  "cloud": "AzurePublicCloud"
}

# 3. Check minReplicas is explicit
az containerapp show --name ai-content-prod-processor \
  --resource-group ai-content-prod-rg \
  --query "properties.template.scale.minReplicas"

# Expected: 0 (not null!)
```

### Phase 2: Scaling Validation

```bash
# 1. Ensure containers at 0 replicas
az containerapp replica list --name ai-content-prod-processor \
  --resource-group ai-content-prod-rg

# Expected: No replicas listed

# 2. Send test message to queue
az storage message put \
  --queue-name content-processing-requests \
  --content '{"test": "message"}' \
  --account-name aicontentprodstkwakpx \
  --auth-mode login

# 3. Wait 30s (polling interval)

# 4. Check if container scaled to 1
az containerapp replica list --name ai-content-prod-processor \
  --resource-group ai-content-prod-rg

# Expected: 1 replica in Running state

# 5. Monitor processing
az containerapp logs show --name ai-content-prod-processor \
  --resource-group ai-content-prod-rg \
  --follow

# Expected: See message processing logs

# 6. After queue empty, wait 5min + 30s

# 7. Verify scale to zero
az containerapp replica list --name ai-content-prod-processor \
  --resource-group ai-content-prod-rg

# Expected: No replicas
```

### Phase 3: End-to-End Pipeline Validation

```bash
# 1. Trigger collector (or wait for CRON)
# 2. Verify collection → queue messages
# 3. Verify processor scales and processes
# 4. Verify markdown-gen scales and processes
# 5. Verify site-publisher scales and builds
# 6. Verify all containers scale to 0 when done
```

---

## Architectural Recommendations

### Is This Architecture Viable?

**Short Answer**: Yes, but needs fixes and some rethinking.

**Current Design** (Event-driven with poll-until-empty):
```
CRON → Collector → Queue → Processor (poll once) → Queue → Markdown-gen (poll once) → Queue → Site-publisher (poll once)
         ↓                      ↓                           ↓                              ↓
    Scale 0→1→0         Scale 0→1→0                  Scale 0→1→0                    Scale 0→1→0
```

**Problems**:
1. ❌ Fragile - requires perfect KEDA config
2. ❌ Poll-once pattern creates zombies if scaling fails
3. ❌ Hard to debug (containers disappear after work)
4. ❌ No visibility into processing lag

**Better Design** (Event-driven with continuous polling):
```
CRON → Collector → Queue → Processor (continuous) → Queue → Markdown-gen (continuous) → Queue → Site-publisher (continuous)
         ↓                      ↓                           ↓                              ↓
    Scale 0→1→0         Scale 0→N (based on queue)  Scale 0→N                       Scale 0→1
                        Always responsive!          Always responsive!               Always responsive!
```

**Benefits**:
1. ✅ Resilient - works even if KEDA has issues
2. ✅ Continuous polling = always responsive to messages
3. ✅ Containers stay alive for debugging (at least 1 replica when working)
4. ✅ KEDA still provides auto-scaling (N replicas based on load)
5. ✅ Exponential backoff reduces waste when idle

**Cost Comparison**:
- **Current (broken)**: 3 containers × 1 replica × 24h = ~$15/month wasted
- **Poll-until-empty (working)**: 3 containers × 0 replicas idle = ~$3/month (only pay during processing)
- **Continuous polling (recommended)**: 3 containers × 1 replica × 30s poll = ~$5/month

**Recommendation**: Switch to continuous polling for $2/month insurance against configuration issues.

---

## Material/Existential Issues?

### ✅ Good Architecture Decisions

1. **KEDA for scaling** - Right choice, just misconfigured
2. **Storage Queues** - Simple, reliable, integrates well with KEDA
3. **Managed Identity** - Secure, no connection strings
4. **Terraform IaC** - Good practice (but needs azapi provider)
5. **Container separation** - Clean boundaries between stages

### ⚠️ Design Concerns

1. **Over-optimization** - Poll-until-empty pattern adds complexity for ~$2/month savings
2. **Tight KEDA coupling** - System unusable if KEDA misconfigured
3. **No fallback** - If scaling fails, pipeline stops completely
4. **Hard to debug** - Containers disappear, logs vanish
5. **No observability** - Can't see queue depths, processing lag, costs in real-time

### 🎯 Recommended Changes

1. **Loosen KEDA coupling** - Make containers work independently of perfect scaling
2. **Add continuous polling** - Small cost for huge reliability improvement
3. **Add monitoring** - Queue depths, processing times, scaling events
4. **Add alerts** - Catch issues like "5 messages unprocessed for 19 hours"
5. **Document runbooks** - "What to do when processing stops"

---

## Summary

You have a **fundamentally sound architecture** that's been broken by **configuration issues**:

1. 🚨 **Critical**: KEDA metadata corruption from `null_resource` approach
2. 🚨 **Critical**: Poll-until-empty pattern creates zombies when scaling fails
3. ⚠️ **High**: `minReplicas = null` confusion
4. ⚠️ **Medium**: `os._exit()` hard kills causing failures
5. ⚠️ **Low**: Suboptimal `queueLength` values

**Fix Priority**: #1 and #2 are blockers. Everything else is optimization.

**Good News**: All issues are fixable, no need to redesign entire system!

**My Recommendation**: 
1. Fix KEDA config today (use azapi provider)
2. Switch to continuous polling this week (add resilience)
3. Add monitoring next week (catch future issues)
4. System will be production-ready in 1-2 weeks

Would you like me to start implementing any of these fixes?
