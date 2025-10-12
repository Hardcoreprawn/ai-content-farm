# Production Scaling Configuration Audit
**Date**: October 12, 2025  
**Purpose**: Document actual production scaling settings vs Terraform configuration

## Current Production Settings (from Azure)

### Content Collector
- **minReplicas**: 0
- **maxReplicas**: 1 ✅ matches Terraform (was 2)
- **cooldownPeriod**: 45s
- **pollingInterval**: 30s
- **Scale Rule**: CRON
  - Schedule: `0 0,8,16 * * *` (00:00, 08:00, 16:00 UTC)
  - Duration: 30 minutes
  - desiredReplicas: 1

### Content Processor
- **minReplicas**: 0 ✅
- **maxReplicas**: 6 ❌ **MISMATCH** (Terraform: 3, Production: 6)
- **cooldownPeriod**: 60s ❌ **NOT IN TERRAFORM**
- **pollingInterval**: 30s
- **Scale Rule**: azure-queue
  - queueName: content-processing-requests
  - queueLength: 80 ✅
  - queueLengthStrategy: all ✅
  - activationQueueLength: 1 ✅
  - KEDA auth: workloadIdentity configured ✅

### Markdown Generator
- **minReplicas**: 0 ✅
- **maxReplicas**: 1 ❌ **MISMATCH** (Terraform: 5, Production: 1 - user pinned)
- **cooldownPeriod**: 45s ❌ **NOT IN TERRAFORM**
- **pollingInterval**: 30s
- **Scale Rule**: azure-queue
  - queueName: markdown-generation-requests
  - queueLength: 160 ❌ **MISMATCH** (Terraform: 1, Production: 160 - user adjusted)
  - queueLengthStrategy: all ✅
  - activationQueueLength: 1 ✅
  - KEDA auth: workloadIdentity configured ✅

### Site Publisher
- **minReplicas**: 0 ✅
- **maxReplicas**: 1 ❌ **MISMATCH** (Terraform: 2, Production: 1 - user pinned)
- **cooldownPeriod**: 300s ❌ **NOT IN TERRAFORM**
- **pollingInterval**: 30s
- **Scale Rule**: azure-queue
  - queueName: site-publishing-requests
  - queueLength: 1 ✅
  - queueLengthStrategy: all ✅
  - activationQueueLength: 1 ✅
  - KEDA auth: workloadIdentity configured ✅

## Required Terraform Updates

### 1. Add cooldownPeriod to all containers
Azure Container Apps supports `cooldownPeriod` but Terraform azurerm provider **does NOT expose it**. Must use `az containerapp` CLI or Azure portal.

**Workaround Options**:
1. Accept drift (document in SECURITY_EXCEPTIONS.md)
2. Use null_resource with Azure CLI (adds complexity)
3. Wait for azurerm provider update

**Recommendation**: Accept drift, document actual production values

### 2. Update max_replicas

#### Processor: 3 → 6
```terraform
# container_app_processor.tf line 117
max_replicas = 6  # Increased from 3 based on OpenAI rate limiting testing
```

**Justification**: Testing showed 5 concurrent replicas hit OpenAI 429 rate limits. Having 6 max allows for spike handling while staying under rate limits with proper throttling.

#### Markdown-Gen: 5 → 1
```terraform
# container_app_markdown_generator.tf line 101
max_replicas = 1  # Single replica sufficient (processes 35 articles/sec)
```

**Justification**: Markdown generation is extremely fast (21-36ms per article). Single replica can handle 35+ articles/second. Multiple replicas caused duplicate site-publish triggers and race conditions.

#### Site-Publisher: 2 → 1
```terraform
# container_app_site_publisher.tf line 112
max_replicas = 1  # Hugo builds must be sequential (single replica only)
```

**Justification**: Hugo static site builds must be sequential. Multiple replicas would cause file conflicts and corrupt builds. Always keep at 1.

### 3. Update queueLength for Markdown-Gen

```terraform
# container_app_markdown_generator.tf line 111
queueLength = "160"  # Increased from 1 to prevent over-scaling
```

**Justification**: With queueLength=1, markdown-gen scaled to N replicas for N messages. With 160 messages, this meant 160 replicas (cost explosion). At queueLength=160, KEDA scales to 1 replica for up to 160 messages, which is sufficient given processing speed (35/sec = 160 messages in ~5 seconds).

## Production Tuning Summary

### Cost Optimization Changes (User Applied)
1. **Markdown-Gen maxReplicas**: 5 → 1 (-80% potential cost)
2. **Markdown-Gen queueLength**: 1 → 160 (-99% scaling sensitivity)
3. **Site-Publisher maxReplicas**: 2 → 1 (-50% potential cost)
4. **Processor cooldownPeriod**: default(300s) → 60s (faster scale-down)
5. **Markdown-Gen cooldownPeriod**: default(300s) → 45s (faster scale-down)

### Performance Tuning Changes (User Applied)
1. **Processor maxReplicas**: 3 → 6 (handle OpenAI rate limit spikes)
2. **Collector maxReplicas**: 2 → 1 (single collection run sufficient)

## Terraform Configuration Drift

**Acceptable Drift** (not supported by provider):
- `cooldownPeriod` on all containers
- `pollingInterval` on all containers (Terraform uses default 30s)

**Must Fix in Terraform**:
- ✅ Processor max_replicas: 3 → 6
- ✅ Markdown-Gen max_replicas: 5 → 1
- ✅ Markdown-Gen queueLength: 1 → 160
- ✅ Site-Publisher max_replicas: 2 → 1
- ✅ Collector max_replicas: 2 → 1 (already correct)

## Recommendations

1. **Update Terraform immediately** to prevent next deployment reverting production settings
2. **Document cooldownPeriod drift** in SECURITY_EXCEPTIONS.md or similar
3. **Add lifecycle.ignore_changes** for scale-related fields if frequent manual tuning needed
4. **Monitor costs** after Terraform updates to ensure no regressions
5. **Test deployment** in non-prod first to validate Terraform changes

## Next Steps

1. Update Terraform files with corrected values
2. Run `terraform plan` to verify changes
3. Document cooldownPeriod values in comments (can't be managed by Terraform)
4. Add drift monitoring/alerts for critical scaling parameters
5. Consider Azure Policy or automation to prevent manual drift

---
**Last Updated**: October 12, 2025  
**Status**: Pending Terraform Updates  
**Risk**: HIGH - Next deployment will revert production tuning if not fixed
