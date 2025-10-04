# Triggering Site Regeneration - KEDA Scaling Strategy

## Current Setup

### Site-Generator Scaling Configuration
```terraform
# infra/container_apps.tf
min_replicas = 0  # Scales to zero when idle
max_replicas = 2

custom_scale_rule {
  name             = "storage-queue-scaler"
  custom_rule_type = "azure-queue"
  metadata = {
    queueName   = "site-generation-requests"
    queueLength = "1"  # Wakes up on ANY message
  }
}
```

**What this means:**
- ✅ Site-generator scales to **zero** when no work to do (cost optimization)
- ✅ KEDA automatically wakes it up when messages appear in `site-generation-requests` queue
- ✅ HTTP endpoints are **always available** (ingress is configured with `transport = "http"`)
- ❌ No HTTP scaling rule (doesn't need one - queue-based is sufficient)

---

## How to Trigger Site Regeneration

### Option 1: Queue Message (Recommended - How the Pipeline Works)
**Use the queue to trigger site generation:**

```bash
# Get storage account connection
STORAGE_ACCOUNT="ai-content-prod-storage"
QUEUE_NAME="site-generation-requests"

# Send message to queue to trigger site regeneration
az storage message put \
  --queue-name "$QUEUE_NAME" \
  --account-name "$STORAGE_ACCOUNT" \
  --content '{"operation":"generate_site","force_rebuild":true,"trigger_source":"manual"}' \
  --auth-mode login
```

**What happens:**
1. Message added to `site-generation-requests` queue
2. KEDA sees queue length > 0
3. Site-generator scales from 0 → 1 replica (takes ~30-60 seconds)
4. Container picks up message from queue
5. Processes message → regenerates site with NEW deduplication logic
6. After processing, scales back to 0

---

### Option 2: HTTP Endpoint (Direct but Requires Running Container)
**Call the HTTP endpoint directly:**

```bash
# The container needs to be running (min_replicas > 0) OR you need to scale it first

# Option 2a: Scale up temporarily
az containerapp update \
  --name ai-content-prod-site-generator \
  --resource-group ai-content-prod-rg \
  --min-replicas 1 \
  --max-replicas 2

# Wait 30 seconds for container to start...

# Option 2b: Call the endpoint
curl -X POST https://ai-content-prod-site-generator.whitecliff-6844954b.uksouth.azurecontainerapps.io/generate-site \
  -H "Content-Type: application/json" \
  -d '{"theme":"modern-grid","force_regenerate":true}'

# Option 2c: Scale back down (optional - it will auto-scale)
az containerapp update \
  --name ai-content-prod-site-generator \
  --resource-group ai-content-prod-rg \
  --min-replicas 0 \
  --max-replicas 2
```

---

## Recommended Approach: Queue Message

### Why Queue is Better
1. **Zero-to-One Scaling**: KEDA automatically handles scaling
2. **Cost Efficient**: No need to keep container running
3. **Reliable**: Message persists until processed
4. **Consistent**: Same method the pipeline uses
5. **No Wait**: Fire-and-forget (KEDA handles startup)

### Quick Command
```bash
az storage message put \
  --queue-name "site-generation-requests" \
  --account-name "ai-content-prod-storage" \
  --content '{"operation":"generate_site","force_rebuild":true}' \
  --auth-mode login
```

---

## Do You Need HTTP Scaling?

### Current Setup: Queue-Only Scaling
```terraform
custom_scale_rule {
  name             = "storage-queue-scaler"
  custom_rule_type = "azure-queue"
  # Scales based on queue depth
}
```

### Adding HTTP Scaling (If Needed)
```terraform
# OPTIONAL: Add HTTP scaling rule
custom_scale_rule {
  name             = "http-scaler"
  custom_rule_type = "http"
  metadata = {
    concurrentRequests = "10"  # Scale at 10 concurrent requests
  }
}
```

### When to Add HTTP Scaling?

**DON'T ADD if:**
- ✅ Queue-based triggers work fine (your current setup)
- ✅ Site regeneration is batch-oriented (not real-time)
- ✅ Cost optimization is priority (scale-to-zero)

**ADD HTTP scaling if:**
- ❌ You need immediate response to HTTP requests
- ❌ You have high traffic requiring multiple replicas
- ❌ You want to keep containers always warm (min_replicas > 0)

### Your Scenario
**You DON'T need HTTP scaling because:**
1. Site regeneration is a **background job** (not user-facing)
2. Queue messages work perfectly for triggering
3. Containers don't need to stay running (cost optimization)
4. Ingress is already configured for HTTP access when scaled up

---

## Current Status

### Check if Site-Generator is Running
```bash
az containerapp show \
  --name ai-content-prod-site-generator \
  --resource-group ai-content-prod-rg \
  --query "properties.{status:runningStatus,replicas:template.scale}" \
  --output json
```

### Check Queue Depth
```bash
az storage queue stats \
  --name site-generation-requests \
  --account-name ai-content-prod-storage \
  --auth-mode login
```

---

## Action Plan: Trigger Site Regeneration NOW

### Step 1: Send Queue Message
```bash
az storage message put \
  --queue-name "site-generation-requests" \
  --account-name "ai-content-prod-storage" \
  --content '{"operation":"generate_site","force_rebuild":true,"source":"manual-trigger","reason":"deploy-deduplication-fix"}' \
  --auth-mode login
```

### Step 2: Monitor Scaling (Optional)
```bash
# Watch container scale up
watch -n 5 'az containerapp show \
  --name ai-content-prod-site-generator \
  --resource-group ai-content-prod-rg \
  --query "properties.runningStatus" \
  --output tsv'
```

### Step 3: Check Logs
```bash
# Once container is running, check logs
az containerapp logs show \
  --name ai-content-prod-site-generator \
  --resource-group ai-content-prod-rg \
  --tail 50 \
  --follow
```

---

## Summary

**Answer to "Do we need to add HTTP scaling?"**

**NO** - Your current queue-based KEDA scaling is perfect for this use case:
- ✅ Container automatically wakes up on queue messages
- ✅ Processes the generation request
- ✅ Scales back to zero when done
- ✅ HTTP endpoints still work when container is running
- ✅ Cost-optimized (only runs when needed)

**Just send a queue message to trigger regeneration!**

The HTTP ingress is already there - you don't need HTTP *scaling*, you just need to trigger the container (via queue) and it will handle the rest.
