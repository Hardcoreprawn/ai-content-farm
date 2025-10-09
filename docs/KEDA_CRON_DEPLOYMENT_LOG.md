# KEDA Cron Fix - Deployment Attempt 2

**Date**: October 9, 2025  
**Time**: 09:40 UTC  

## Issue Discovered

### First Deployment Failed (09:21 UTC)
**Error**:
```
ScaleRuleMetadataMissing: The custom scale rule 'cron' doesn't include required metadata:'end'.
```

**Root Cause**: Azure Container Apps **requires** the `end` parameter for KEDA cron scalers. It's not optional.

## Solution Applied

### Updated Configuration
Changed from attempting to remove `end` parameter to using a reasonable 30-minute window:

```terraform
custom_scale_rule {
  name             = "cron-scaler"
  custom_rule_type = "cron"
  metadata = {
    timezone        = "UTC"
    start           = "0 0,8,16 * * *"  # Every 8 hours
    end             = "30 0,8,16 * * *" # Maximum 30-minute window
    desiredReplicas = "1"
  }
}
```

### Why This Works

1. **Azure Requirement Met**: `end` parameter is mandatory, now provided
2. **Natural Completion Still Works**: Container has `DISABLE_AUTO_SHUTDOWN=false`
3. **Early Exit**: Container will shut down when done (typically 2-5 minutes)
4. **Safety Net**: 30-minute max prevents runaway processes
5. **Cost Efficient**: KEDA still scales to 0 after container exits

### Comparison

| Configuration | Window | Behavior |
|--------------|--------|----------|
| **Original** | 10 minutes | Too short, could interrupt collections |
| **Attempted** | No end param | ❌ Azure rejects (required parameter) |
| **Current** | 30 minutes | ✅ Safe window, container auto-exits when done |

## Deployment Status

**Second Deployment**: In Progress (09:39 UTC)
- **Run ID**: 18372121140
- **URL**: https://github.com/Hardcoreprawn/ai-content-farm/actions/runs/18372121140
- **Commit**: `bfec000` - fix(keda): add required end parameter with 30-minute window

**Expected**:
- ✅ Terraform validation passes
- ✅ Security scans pass
- ✅ Deployment succeeds (end parameter now provided)
- ✅ KEDA configuration updated in Azure

## Next Steps After Deployment

### 1. Verify Deployment Success
```bash
# Check deployment status
gh run view 18372121140 --watch

# Expected: All jobs pass, deploy succeeds
```

### 2. Verify Configuration in Azure
```bash
# Check KEDA scaler configuration
az containerapp show \
  --name ai-content-prod-collector \
  --resource-group ai-content-prod-rg \
  --query "properties.template.scale.rules" \
  --output json

# Should show: end = "30 0,8,16 * * *"
```

### 3. Manual Collection Test
Once deployment completes, we can manually trigger a collection to test:

```bash
# Get collector URL
COLLECTOR_URL=$(az containerapp show \
  --name ai-content-prod-collector \
  --resource-group ai-content-prod-rg \
  --query "properties.configuration.ingress.fqdn" \
  --output tsv)

# Trigger collection
curl -X POST "https://${COLLECTOR_URL}/collect" \
  -H "Content-Type: application/json" \
  -d '{
    "template": "tech-news",
    "max_topics": 5
  }'
```

### 4. Monitor Behavior
```bash
# Watch KEDA scaling
./scripts/verify-pipeline.sh
# Select option 3: Watch KEDA scaling

# Stream collector logs
az containerapp logs show \
  --name ai-content-prod-collector \
  --resource-group ai-content-prod-rg \
  --follow
```

**Expected Behavior**:
1. Collector scales from 0 → 1 replica
2. Collection runs (2-5 minutes typically)
3. Container completes and exits
4. KEDA detects exit and scales back to 0
5. This happens **before** the 30-minute window expires

## Key Learnings

1. **Azure Container Apps cron scalers require `end` parameter** - it's mandatory API validation
2. **KEDA upstream docs** might show `end` as optional, but Azure implementation requires it
3. **Auto-shutdown still works** with a generous `end` window - container exits naturally
4. **30 minutes is a safe default** - allows collections to complete while preventing runaway processes

## Documentation Updated

- ✅ `infra/container_app_collector.tf` - Added `end = "30 0,8,16 * * *"`
- ✅ `docs/KEDA_CRON_FIX.md` - Explained Azure requirement
- ✅ `TODO.md` - Updated execution model description
- ✅ This document - Tracking deployment attempts

## Timeline

- **08:35 UTC**: First attempt pushed (tried to remove `end` parameter)
- **09:21 UTC**: Deployment failed - Azure requires `end` parameter
- **09:39 UTC**: Second attempt pushed (30-minute `end` window)
- **09:40 UTC**: Deployment in progress
- **~09:45 UTC**: Expected deployment completion
- **After deployment**: Manual collection trigger test

---

**Status**: Waiting for deployment to complete  
**Next**: Verify deployment success, then trigger manual collection test
