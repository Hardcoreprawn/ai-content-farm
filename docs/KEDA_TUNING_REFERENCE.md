# KEDA Scale Rule Tuning - Quick Reference

**Purpose**: Optimize KEDA autoscaling parameters based on workload characteristics  
**Created**: October 18, 2025  
**Status**: Proposed changes (not yet applied)

---

## Current Configuration (Baseline)

| Container | queueLength | activationQueueLength | cooldown | Max Idle Time | Issues |
|-----------|-------------|----------------------|----------|---------------|--------|
| **content-collector** | 1 | 1 | 45s | 180s | ✅ Good |
| **content-processor** | 16 | 1 | 60s | 180s | ⚠️ Too high |
| **markdown-generator** | 1 | 1 | 90s | 180s | ✅ Good |
| **site-publisher** | 1 | 1 | 300s | 300s | ⚠️ Too long |

**Files**: `infra/container_apps_keda_auth.tf` (null_resource provisioners)

---

## Proposed Configuration (Optimized)

### content-processor (PRIMARY TARGET)
```hcl
# infra/container_apps_keda_auth.tf - line ~50
queueLength=8              # DOWN from 16
activationQueueLength=1    # Keep at 1
cooldown=45                # DOWN from 60s
```

**Rationale**:
- Current: 16 messages per instance = large batches, slow to start
- Proposed: 8 messages per instance = more parallelism via multiple instances
- Processing time: ~30-45s per article → smaller batches = faster throughput
- Cooldown: Match collector (45s) for consistency

**Expected Impact**:
- ✅ Faster processing during collection bursts (more instances active)
- ✅ More responsive scaling (triggers at half the queue depth)
- ⚠️ Slightly higher cost (more instances running briefly)

---

### site-publisher (SECONDARY TARGET)
```hcl
# infra/container_apps_keda_auth.tf - line ~150
queueLength=1              # Keep at 1 (Hugo builds are exclusive)
activationQueueLength=1    # Keep at 1
cooldown=120               # DOWN from 300s (5 min → 2 min)
```

**Rationale**:
- Hugo builds: ~15-30 seconds duration
- Current: 5 minute cooldown is excessive (10x build time)
- Proposed: 2 minutes is still conservative (4x build time)
- Site-publisher should be "always ready" for markdown-generator signals

**Expected Impact**:
- ✅ Faster container availability after markdown completion
- ✅ Reduced "waiting for scale-up" latency
- ⚠️ Minimal cost impact (builds are infrequent)

---

### content-collector (NO CHANGE)
```hcl
# Already optimal
queueLength=1              # Perfect for immediate response
activationQueueLength=1    # Wake up on first message
cooldown=45               # Quick scale-down
```

**Keep as-is**: Collection is the pipeline trigger, needs to be responsive.

---

### markdown-generator (NO CHANGE)
```hcl
# Already well-tuned
queueLength=1              # Markdown generation is lightweight
activationQueueLength=1    # Immediate processing
cooldown=90               # Balanced for stable empty queue pattern
```

**Keep as-is**: Works well with "stable empty queue" signaling pattern.

---

## Workload Characteristics

### content-processor
- **Processing time**: 30-45 seconds per article (AI generation + validation)
- **Arrival pattern**: Burst (85 messages in 10 seconds after collection)
- **Current behavior**: 1 instance handles 16 messages sequentially (~8-12 minutes)
- **Desired behavior**: 2-3 instances handle 8 messages each in parallel (~4-6 minutes)

### site-publisher
- **Build time**: 15-30 seconds (Hugo static site generation)
- **Arrival pattern**: Single message after markdown batch completes
- **Current behavior**: 5 minute cooldown = 10x overkill
- **Desired behavior**: 2 minute cooldown = responsive but conservative

---

## Implementation Plan

### Step 1: Update Terraform
```bash
# Edit infra/container_apps_keda_auth.tf
# Lines to change:

# content-processor (line ~56)
queueLength=8 \              # Change from 16
--cooldown-period 45 \       # Change from 60

# site-publisher (line ~168)
--cooldown-period 120 \      # Change from 300
```

### Step 2: Deploy Changes
```bash
# From workspace root
cd infra

# Review changes
terraform plan

# Apply with auto-approve (or manual review)
terraform apply -auto-approve

# Verify configuration
az containerapp show \
  --name ai-content-prod-processor \
  --resource-group ai-content-prod-rg \
  --query "properties.configuration.scale" \
  --output json
```

### Step 3: Monitor Impact
```bash
# Watch KEDA scaling events
az monitor activity-log list \
  --resource-group ai-content-prod-rg \
  --namespace Microsoft.App/containerApps \
  --start-time 2025-10-18T00:00:00Z \
  --query "[?contains(operationName.value, 'scale')]" \
  --output table

# Check processing queue depth over time
az storage queue list \
  --account-name aicontentprodstorage \
  --output table

# Review Application Insights metrics
# Look for: avg processing time, queue depth, scale-up events
```

---

## Tuning Methodology

### How to Calculate queueLength

**Formula**: `queueLength = desired_concurrency * avg_processing_time / polling_interval`

For content-processor:
- **desired_concurrency**: 2-4 items processing per instance
- **avg_processing_time**: 40 seconds
- **polling_interval**: ~10 seconds (KEDA default)
- **Result**: `2 * 40 / 10 = 8` ✅

### How to Calculate cooldown

**Formula**: `cooldown = max_processing_time * safety_margin`

For content-processor:
- **max_processing_time**: 45 seconds (95th percentile)
- **safety_margin**: 1.0 (no extra buffer needed with streaming)
- **Result**: `45 * 1.0 = 45s` ✅

For site-publisher:
- **max_build_time**: 30 seconds
- **safety_margin**: 4.0 (very conservative)
- **Result**: `30 * 4.0 = 120s` ✅

---

## Testing Checklist

### Before Deployment
- [ ] Review current queue metrics (baseline measurement)
- [ ] Check current container scaling history
- [ ] Document current end-to-end pipeline latency
- [ ] Verify no active processing workload

### During Deployment
- [ ] Terraform apply completes successfully
- [ ] Verify KEDA configuration with `az containerapp show`
- [ ] Check for any error logs in Application Insights
- [ ] Confirm containers are running and healthy

### After Deployment (Monitor for 24-48h)
- [ ] Measure time-to-first-processed-article (target: <2 min)
- [ ] Count number of scale-up events (expect 2-3x increase)
- [ ] Check average queue depth during bursts (target: <16)
- [ ] Verify no message processing failures
- [ ] Compare costs (expect <10% increase)

---

## Rollback Plan

If issues occur after deployment:

### Quick Rollback (1 minute)
```bash
# Revert to previous queueLength values
az containerapp update \
  --name ai-content-prod-processor \
  --resource-group ai-content-prod-rg \
  --scale-rule-name storage-queue-scaler \
  --scale-rule-metadata queueLength=16 \
  --output none

az containerapp update \
  --name ai-content-prod-site-publisher \
  --resource-group ai-content-prod-rg \
  --scale-rule-name site-publish-queue-scaler \
  --scale-rule-metadata cooldown=300 \
  --output none
```

### Git Rollback (5 minutes)
```bash
# Revert Terraform changes
git revert HEAD
git push origin main

# CI/CD will redeploy previous configuration
```

---

## Success Metrics

### Must Achieve
- ✅ No increase in failed messages (error rate stable)
- ✅ No significant cost increase (<10%)
- ✅ Processing throughput improves (measured in articles/hour)

### Should Achieve
- ✅ Time-to-first-processed-article: <2 minutes (down from 3-5 min)
- ✅ Average queue depth during bursts: <16 (smoother distribution)
- ✅ KEDA scale-up events more frequent (2-3x increase)

### Nice to Have
- ✅ Cost reduction from faster processing (fewer container-hours)
- ✅ More predictable latency (less variance)
- ✅ Better resource utilization (70-85% CPU avg)

---

## Alternative Configurations

### Conservative (If concerned about cost)
```hcl
# content-processor
queueLength=12             # Middle ground (vs 16 current, 8 proposed)
cooldown=50                # Slightly faster than current

# site-publisher
cooldown=180               # Split the difference (vs 300 current, 120 proposed)
```

### Aggressive (If cost not a concern)
```hcl
# content-processor
queueLength=4              # Very parallel (up to 20+ instances)
cooldown=30                # Rapid scale-down

# site-publisher
cooldown=60                # Match Hugo build time
```

---

## Related Configuration

### MAX_IDLE_TIME (Container self-termination)
Current: 180 seconds (3 minutes) across all containers

**Recommendation**: Keep at 180s
- KEDA cooldown handles scale-down
- MAX_IDLE_TIME is backup mechanism
- No need to change for this optimization

### Visibility Timeout (Queue message handling)
Current: Not explicitly set (Azure default: 30s)

**Recommendation**: Set explicitly in code
```python
# libs/queue_client.py
visibility_timeout = 90  # content-processor (45s process + 45s buffer)
visibility_timeout = 60  # markdown-generator (15s + 45s buffer)
visibility_timeout = 180 # site-publisher (60s + 120s buffer)
```

---

## References

- **KEDA Azure Queue Scaler**: https://keda.sh/docs/2.11/scalers/azure-storage-queue/
- **Azure Container Apps Scaling**: https://learn.microsoft.com/en-us/azure/container-apps/scale-app
- **Current Configuration**: `/workspaces/ai-content-farm/infra/container_apps_keda_auth.tf`
- **Architecture Docs**: `docs/PIPELINE_OPTIMIZATION_PLAN.md`

---

_Last Updated: October 18, 2025_  
_Status: Pending approval and implementation_
