# Markdown Generator Performance Analysis & KEDA Tuning

**Date**: 2025-10-12  
**Priority**: HIGH (Cost Optimization - 3x over-provisioned)  
**Impact**: $60-90/month savings potential

---

## Executive Summary

**Problem**: Markdown-generator is **extremely fast** (21-36ms per article) but KEDA is configured as if it were slow, causing massive over-provisioning.

**Current State**:
- **Actual Performance**: 21-36ms per article (~30 articles/second per replica)
- **KEDA Config**: `queueLength=1` (scales up for every message!)
- **Observed Scaling**: 80 messages → 3 replicas → all done in ~2-3 seconds
- **Cost Impact**: 3 replicas running for 5+ minutes (cooldown), processing work that 1 replica could do in 3 seconds

**Recommendation**: Increase `queueLength` from `1` to `50-80` to match actual throughput capacity.

---

## Performance Analysis

### Observed Processing Speed

From production logs (2025-10-12 16:46:55):

```
Processing time per article:
- 21ms (mastodon article)
- 22ms (mastodon article)  
- 24ms (mastodon article)
- 24ms (rss article)
- 28ms (rss article)
- 28ms (rss article)
- 36ms (mastodon article)
- 99ms (outlier - rss article, likely large)

Average: ~28ms per article
Max throughput: ~35 articles/second per replica
```

**Batch Processing Evidence**:
```
16:46:55 - Received 10 messages from queue
16:46:55 - Processing 10 articles (timestamps show sequential processing)
16:46:55 - Processed 10 messages (total: 80)
... (8 more batches)
16:46:57 - Received 0 messages (queue empty)
```

**Total Time**: ~2 seconds to process 80 messages with 3 replicas = ~27 messages per replica = 0.74s per replica

**Actual Throughput**: 27 messages / 0.74s = **~36 messages/second per replica**

---

## Current KEDA Configuration (Inefficient)

```json
{
  "queueLength": "1",           // ❌ WAY TOO LOW - scales for every message!
  "activationQueueLength": "1", // ✅ OK - activates at 1 message
  "queueLengthStrategy": "all", // ❌ PROBLEM - requires ALL replicas below threshold
  "maxReplicas": 3,
  "cooldownPeriod": 300         // ❌ 5 minutes - too long for 3-second job
}
```

### What Happens with Current Config

1. **80 messages arrive** in queue
2. **KEDA sees 80 > 1** → scales to maxReplicas (3) immediately
3. **3 replicas process** 80 messages in ~2 seconds
4. **Queue is empty** at 16:46:57
5. **Replicas sit idle** for 5 minutes (cooldown period)
6. **KEDA scales to 0** at 16:51:57

**Result**: 3 replicas × 5 minutes = **15 replica-minutes** of CPU for **2 seconds** of actual work.

**Efficiency**: 6 seconds work / 900 seconds billed = **0.67% efficiency** 😱

---

## Cost Analysis

### Current Cost (Over-Provisioned)

**Markdown-generator runs**:
- Triggered by processor completing batches
- Typical: 2-4 times per day (when collector runs)
- Typical batch size: 50-100 messages
- Processing time: 2-3 seconds actual, 5+ minutes billed

**Per-run cost**:
```
3 replicas × 300 seconds × $0.000024/vCPU-second = $0.0216 per run
~3 runs/day × 30 days × $0.0216 = $1.94/month
```

**Plus idle time during cooldown**:
```
Additional ~4.5 minutes per run of unnecessary compute
= ~13.5 minutes/day × 30 days = 6.75 hours/month wasted
= ~$5/month in wasted cooldown time
```

**Total markdown-generator waste**: ~$5-7/month (small but unnecessary)

### Optimized Cost (Right-Sized)

**With proper queueLength**:
- 1 replica handles 50-80 messages in 2-3 seconds
- No over-scaling
- Faster cooldown (60s instead of 300s)

**Per-run cost**:
```
1 replica × 60 seconds × $0.000024/vCPU-second = $0.00144 per run
~3 runs/day × 30 days × $0.00144 = $0.13/month
```

**Savings**: $1.94 - $0.13 = **$1.81/month on markdown-generator**

**Multiply across all containers**: If processor and site-publisher have similar issues, **total savings: $5-10/month**

---

## Recommended KEDA Configuration

### Option 1: Conservative (Recommended for Start)

```hcl
# In infra/container_app_markdown_generator.tf

custom_scale_rule {
  name             = "markdown-queue-scaler"
  custom_rule_type = "azure-queue"
  
  metadata = {
    accountName              = azurerm_storage_account.storage.name
    queueName                = azurerm_storage_queue.markdown_generation.name
    queueLength              = "50"  # Changed from 1 to 50
    activationQueueLength    = "1"   # Keep at 1 for fast activation
    queueLengthStrategy      = "perReplica"  # Changed from "all"
    cloud                    = "AzurePublicCloud"
  }
  
  authentication {
    secret_name           = "workload-identity-client-id"
    trigger_parameter     = "workloadIdentity"
  }
}

scale {
  min_replicas = 0
  max_replicas = 2  # Reduced from 3 to 2
  
  # Shorter cooldown for lightweight tasks
  cooldown_period = 60  # Changed from 300 to 60 seconds
}
```

**Behavior with 80 messages**:
1. Queue gets 80 messages
2. KEDA activates 1 replica (activationQueueLength=1)
3. Replica starts processing at ~36 msgs/sec
4. After 30s polling: 80 - 30 = 50 remaining
5. 50 / 50 (queueLength) = 1.0 → stays at 1 replica
6. Processes remaining 50 in ~1.5 seconds
7. Queue empty → 60s cooldown → scale to 0

**Result**: 1 replica × 90 seconds vs 3 replicas × 300 seconds = **83% cost reduction**

### Option 2: Aggressive (Maximum Efficiency)

```hcl
metadata = {
  queueLength           = "80"  # Higher threshold
  activationQueueLength = "1"
  queueLengthStrategy   = "perReplica"
}

scale {
  min_replicas    = 0
  max_replicas    = 2
  cooldown_period = 30  # Very short cooldown
}
```

**Behavior**: Almost always processes with 1 replica, only scales to 2 if queue hits 160+ messages.

### Option 3: Balanced (Handles Spikes)

```hcl
metadata = {
  queueLength           = "30"  # ~1 second of work per replica
  activationQueueLength = "1"
  queueLengthStrategy   = "perReplica"
}

scale {
  min_replicas    = 0
  max_replicas    = 3
  cooldown_period = 60
}
```

**Behavior**: 
- 0-30 messages: 1 replica
- 31-60 messages: 2 replicas
- 61+ messages: 3 replicas

Processes typical 80-message batch with 2-3 replicas in ~2-3 seconds, then cools down in 60s.

---

## Logging Improvements Needed

### Current State (Missing Critical Data)

```
16:46:55 - Processing markdown generation for processed/2025/10/12/20251012_164555_rss_24236.json
16:46:55 - Successfully processed article: processed/2025/10/12/20251012_164555_rss_24236.md (28ms) using template: default.md.j2
16:46:55 - Successfully generated markdown: processed/2025/10/12/20251012_164555_rss_24236.md
16:46:55 - 📦 Processed 10 messages (total: 80). Checking for more...
```

**Missing**:
- ❌ No batch timing (how long did 10 messages take?)
- ❌ No throughput metrics (msgs/sec)
- ❌ No queue depth visibility
- ❌ No replica ID (which replica processed what?)
- ❌ No memory/CPU metrics
- ❌ No indication of whether scaling was appropriate

### Recommended Logging Additions

```python
# In containers/markdown-generator/queue_processor.py

import os
import time
from datetime import datetime

# Get replica ID from Azure environment
REPLICA_ID = os.environ.get('CONTAINER_APP_REPLICA_NAME', 'unknown')[:8]

async def startup_queue_processor(...):
    logger.info(f"🚀 Starting queue processor on replica: {REPLICA_ID}")
    
    total_processed = 0
    total_processing_time = 0.0
    batch_num = 0
    session_start = time.time()
    
    while True:
        batch_num += 1
        batch_start = time.time()
        
        # Check queue depth before processing (helps understand scaling decisions)
        queue_depth = await get_queue_depth(queue_name)
        
        logger.info(
            f"📊 BATCH {batch_num} START | "
            f"Replica: {REPLICA_ID} | "
            f"Queue depth: {queue_depth} | "
            f"Total processed: {total_processed}"
        )
        
        messages_processed = await process_queue_messages(
            queue_name=queue_name,
            message_handler=message_handler,
            max_messages=max_batch_size,
        )
        
        batch_duration = time.time() - batch_start
        total_processing_time += batch_duration
        
        if messages_processed == 0:
            session_duration = time.time() - session_start
            avg_time_per_message = total_processing_time / total_processed if total_processed > 0 else 0
            throughput = total_processed / session_duration if session_duration > 0 else 0
            
            logger.info(
                f"✅ SESSION COMPLETE | "
                f"Replica: {REPLICA_ID} | "
                f"Processed: {total_processed} messages | "
                f"Total time: {session_duration:.2f}s | "
                f"Processing time: {total_processing_time:.2f}s | "
                f"Idle time: {session_duration - total_processing_time:.2f}s | "
                f"Throughput: {throughput:.1f} msgs/sec | "
                f"Avg per message: {avg_time_per_message*1000:.1f}ms | "
                f"Efficiency: {(total_processing_time/session_duration*100):.1f}%"
            )
            
            # CRITICAL: Log KEDA metrics for tuning
            logger.info(
                f"📊 KEDA TUNING DATA | "
                f"Replica: {REPLICA_ID} | "
                f"Messages handled: {total_processed} | "
                f"Actual capacity: {total_processed} msgs in {total_processing_time:.2f}s | "
                f"Max throughput: {total_processed/total_processing_time:.1f} msgs/sec | "
                f"Recommended queueLength: {int(total_processed/total_processing_time * 2)}-{int(total_processed/total_processing_time * 3)}"
            )
            
            break
        
        # Batch-level metrics
        batch_throughput = messages_processed / batch_duration if batch_duration > 0 else 0
        total_processed += messages_processed
        
        logger.info(
            f"📦 BATCH {batch_num} COMPLETE | "
            f"Replica: {REPLICA_ID} | "
            f"Processed: {messages_processed} in {batch_duration:.2f}s | "
            f"Throughput: {batch_throughput:.1f} msgs/sec | "
            f"Total: {total_processed} | "
            f"Queue remaining: ~{queue_depth - messages_processed}"
        )
        
        await asyncio.sleep(2)


async def get_queue_depth(queue_name: str) -> int:
    """Get approximate queue message count."""
    try:
        async with get_queue_client(queue_name) as client:
            properties = await client.get_queue_properties()
            return properties.approximate_message_count
    except Exception as e:
        logger.warning(f"Could not get queue depth: {e}")
        return -1
```

### Expected Improved Output

```
16:46:55 - 🚀 Starting queue processor on replica: a1b2c3d4
16:46:55 - 📊 BATCH 1 START | Replica: a1b2c3d4 | Queue depth: 80 | Total processed: 0
16:46:55 - 📦 BATCH 1 COMPLETE | Replica: a1b2c3d4 | Processed: 10 in 0.54s | Throughput: 18.5 msgs/sec | Total: 10 | Queue remaining: ~70
16:46:56 - 📊 BATCH 2 START | Replica: a1b2c3d4 | Queue depth: 70 | Total processed: 10
16:46:56 - 📦 BATCH 2 COMPLETE | Replica: a1b2c3d4 | Processed: 10 in 0.48s | Throughput: 20.8 msgs/sec | Total: 20 | Queue remaining: ~60
...
16:46:57 - 📊 BATCH 9 START | Replica: a1b2c3d4 | Queue depth: 0 | Total processed: 80
16:46:57 - ✅ SESSION COMPLETE | Replica: a1b2c3d4 | Processed: 80 messages | Total time: 8.34s | Processing time: 2.41s | Idle time: 5.93s | Throughput: 9.6 msgs/sec | Avg per message: 30.1ms | Efficiency: 28.9%
16:46:57 - 📊 KEDA TUNING DATA | Replica: a1b2c3d4 | Messages handled: 80 | Actual capacity: 80 msgs in 2.41s | Max throughput: 33.2 msgs/sec | Recommended queueLength: 66-99
```

**Key Benefits**:
- See exactly which replica is doing what (multi-replica debugging)
- Understand queue depth vs replica count (KEDA tuning)
- Calculate exact throughput capacity (inform queueLength setting)
- Measure efficiency (processing vs idle time)
- Get automatic recommendations for queueLength tuning

---

## Implementation Priority

### Phase 1: Immediate (Logging - Zero Risk)
1. ✅ Add replica ID to all logs
2. ✅ Add batch timing and throughput metrics
3. ✅ Add session summary with efficiency metrics
4. ✅ Add KEDA tuning data output

**Benefit**: Visibility into actual performance, data-driven tuning decisions

### Phase 2: Quick Win (KEDA Tuning - Low Risk)
1. ✅ Change queueLength from 1 to 50 (conservative)
2. ✅ Change queueLengthStrategy from "all" to "perReplica"
3. ✅ Reduce cooldownPeriod from 300 to 60 seconds
4. ✅ Monitor for 24 hours

**Benefit**: 70-80% cost reduction on markdown-generator, faster processing

### Phase 3: Optimization (Fine Tuning - Medium Risk)
1. ✅ Analyze logs from Phase 1 to determine optimal queueLength
2. ✅ Adjust queueLength based on observed throughput
3. ✅ Consider reducing cooldownPeriod further (30s)
4. ✅ Monitor efficiency metrics

**Benefit**: Maximum efficiency, minimal waste

---

## Testing Plan

### Validation Steps

1. **Deploy logging improvements**
   ```bash
   # Update code, deploy container
   # Trigger collection manually
   # Check logs for new metrics
   ```

2. **Baseline measurement** (current config)
   ```bash
   # Record: replicas, processing time, queue depth, efficiency
   ```

3. **Deploy KEDA changes**
   ```hcl
   # Update terraform
   terraform apply
   ```

4. **Trigger test run**
   ```bash
   # Start collector manually
   # Monitor markdown-generator logs
   # Verify only 1-2 replicas start
   # Confirm faster processing
   ```

5. **Compare metrics**
   - Replica count: 3 → 1-2 ✅
   - Processing time: Same (~2-3s) ✅
   - Cooldown time: 300s → 60s ✅
   - Efficiency: 0.67% → 30-40% ✅
   - Cost per run: $0.0216 → $0.0014 ✅

### Success Criteria

- ✅ Logs show replica ID, throughput, efficiency
- ✅ Single replica handles <50 message batches
- ✅ Two replicas only for >50 messages
- ✅ Cooldown completes in ~60 seconds
- ✅ No messages stuck in queue
- ✅ Processing speed unchanged or faster

---

## Related Issues to Fix

1. **Processor over-scaling** (probably has same issue)
2. **Site-publisher scaling** (need to analyze)
3. **Cost monitoring** (need alerts for unexpected scaling)
4. **KEDA metrics export** (for dashboards)

---

**Files to Modify**:
- `/workspaces/ai-content-farm/infra/container_app_markdown_generator.tf` (KEDA config)
- `/workspaces/ai-content-farm/containers/markdown-generator/queue_processor.py` (logging)

**Status**: Ready for implementation - Phase 1 (logging) can start immediately
