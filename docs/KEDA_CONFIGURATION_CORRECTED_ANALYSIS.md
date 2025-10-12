# KEDA Configuration - Corrected Analysis

**Date**: October 12, 2025  
**Status**: Configuration Understanding Corrected

## ✅ Your KEDA Configuration is Actually CORRECT!

After reviewing the [KEDA documentation](https://keda.sh/docs/2.17/scalers/azure-storage-queue/) and the [Microsoft example](https://github.com/Ajsalemo/container-apps-scaling-examples/tree/main/keda-azure-storage-queue), I need to **correct my earlier analysis**. Your understanding of `queueLength` and `activationQueueLength` is spot-on!

### Correct Interpretation (From KEDA Docs)

#### `queueLength` (Default: 5)
> "Target value for queue length passed to the scaler. Example: if one pod can handle 10 messages, set the queue length target to 10. If the actual number of messages in the queue is 30, the scaler scales to 3 pods."

**This is the target messages PER REPLICA for horizontal scaling (1→N replicas)**

**Formula**: `desired_replicas = ceil(queue_message_count / queueLength)`

**Example with `queueLength = "80"`**:
- 5 messages in queue → ceil(5/80) = **1 replica**
- 80 messages in queue → ceil(80/80) = **1 replica**
- 81 messages in queue → ceil(81/80) = **2 replicas**
- 160 messages in queue → ceil(160/80) = **2 replicas**
- 200 messages in queue → ceil(200/80) = **3 replicas** (hits maxReplicas limit)

#### `activationQueueLength` (Default: 0)
> "Target value for activating the scaler. Learn more about activation here."

**This is the minimum queue depth to trigger scale from 0→1** (activation threshold)

**Your Config**: `activationQueueLength = "1"`
- Queue has 0 messages → Container stays at 0 replicas (scaled down)
- Queue gets 1+ messages → **KEDA activates** → Container scales to 1 replica
- Then normal `queueLength` scaling applies

### Your Current Configuration

```terraform
custom_scale_rule {
  name             = "storage-queue-scaler"
  custom_rule_type = "azure-queue"
  metadata = {
    queueName             = "content-processing-requests"
    accountName           = "aicontentprodstkwakpx"
    queueLength           = "80"    # Target 80 messages per replica
    activationQueueLength = "1"     # Wake from 0 when 1+ messages arrive
    queueLengthStrategy   = "all"   # Count visible + invisible messages
    cloud                 = "AzurePublicCloud"
  }
}

min_replicas = 0  # Enable scale-to-zero
max_replicas = 3  # Maximum horizontal scale
```

### What This Means

✅ **Scale from 0→1**: When queue has **1 or more** messages (`activationQueueLength`)  
✅ **Scale from 1→2**: When queue has **81 or more** messages (exceeds 1 × `queueLength`)  
✅ **Scale from 2→3**: When queue has **161 or more** messages (exceeds 2 × `queueLength`)  
✅ **Scale back to 0**: After `cooldownPeriod` (300s) with queue empty

**With 5 messages in queue**: System correctly stays at **1 replica** (5 < 80).

---

## ❌ The Real Problem: Configuration Metadata Wiped Out

When I restarted your container and checked the configuration, I found:

```json
{
  "scale": {
    "rules": [{
      "custom": {
        "metadata": {
          "accountName": "",      // ❌ EMPTY!
          "queueName": "",        // ❌ EMPTY!
          "queueLength": "",      // ❌ EMPTY!
          "activationQueueLength": "",  // ❌ EMPTY!
          "queueLengthStrategy": "",    // ❌ EMPTY!
          "cloud": ""             // ❌ EMPTY!
        }
      }
    }]
  }
}
```

**This is why KEDA can't scale** - all the metadata has been wiped out!

---

## Root Cause: `null_resource` with Azure CLI

Your Terraform uses a `null_resource` provisioner that runs **after** container creation:

```terraform
# infra/container_apps_keda_auth.tf

resource "null_resource" "configure_processor_keda_auth" {
  triggers = {
    container_app_id = azurerm_container_app.content_processor.id
    # ... other triggers
  }

  provisioner "local-exec" {
    command = <<-EOT
      az containerapp update \
        --name ${azurerm_container_app.content_processor.name} \
        --scale-rule-name storage-queue-scaler \
        --scale-rule-type azure-queue \
        --scale-rule-metadata \
          accountName=${azurerm_storage_account.main.name} \
          queueName=${azurerm_storage_queue.content_processing_requests.name} \
          queueLength=1 \                           # ⚠️ Overwriting your Terraform value!
          cloud=AzurePublicCloud \
        --scale-rule-auth workloadIdentity=${azurerm_user_assigned_identity.containers.client_id}
    EOT
  }
}
```

### Problems with This Approach

1. **Azure CLI `--scale-rule-metadata` REPLACES instead of MERGING**
   - Your Terraform sets `queueLength = "80"`, `activationQueueLength = "1"`, etc.
   - Then `az containerapp update --scale-rule-metadata` **replaces all metadata**
   - Only the fields in the CLI command survive
   - All other fields (like `activationQueueLength`, `queueLengthStrategy`) get **deleted**!

2. **Hardcoded value mismatch**
   - Terraform: `queueLength = "80"`
   - null_resource CLI: `queueLength=1`
   - They're fighting each other!

3. **Not idempotent**
   - Running `terraform apply` twice gives different results
   - Configuration drifts over time
   - Hard to debug "why isn't my config working?"

---

## Microsoft's Recommended Approach

From the [official example](https://github.com/Ajsalemo/container-apps-scaling-examples/blob/main/keda-azure-storage-queue/deployment/armdeploy.json):

```json
{
  "scale": {
    "minReplicas": 1,
    "maxReplicas": 5,
    "rules": [
      {
        "name": "storage-queue-autoscaling",
        "custom": {
          "type": "azure-queue",
          "metadata": {
            "queueName": "[parameters('azureStorageQueueName')]",
            "queueLength": "5",
            "accountName": "[parameters('azureStorageAccountName')]"
          },
          "auth": [
            {
              "secretRef": "azurestorageconnectionstringref",
              "triggerParameter": "connection"
            }
          ]
        }
      }
    ]
  }
}
```

**Key Points**:
- All metadata in ONE place
- Authentication via `auth` array (not separate update)
- No post-deployment CLI manipulation

---

## Solution: Use `azapi` Provider for Complete Configuration

The `azurerm` provider doesn't support KEDA workload identity auth, but `azapi` does! This lets you configure **everything in Terraform**.

### Step 1: Add `azapi` Provider

```terraform
# infra/providers.tf

terraform {
  required_providers = {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    azapi = {
      source  = "Azure/azapi"
      version = "~> 2.0"  # Supports Container Apps authentication
    }
  }
}

provider "azapi" {
  # Uses same auth as azurerm provider
}
```

### Step 2: Configure KEDA with `azapi_update_resource`

```terraform
# infra/container_apps_keda_complete.tf

# OPTION 1: Update existing container app with complete KEDA config
resource "azapi_update_resource" "processor_keda_complete" {
  type        = "Microsoft.App/containerApps@2024-03-01"
  resource_id = azurerm_container_app.content_processor.id

  body = {
    properties = {
      template = {
        scale = {
          minReplicas = 0
          maxReplicas = 3
          rules = [
            {
              name = "storage-queue-scaler"
              custom = {
                type = "azure-queue"
                metadata = {
                  accountName           = azurerm_storage_account.main.name
                  queueName             = azurerm_storage_queue.content_processing_requests.name
                  queueLength           = "80"     # Your batch size
                  activationQueueLength = "1"      # Wake on 1+ message
                  queueLengthStrategy   = "all"    # Count all messages
                  cloud                 = "AzurePublicCloud"
                }
                auth = [
                  {
                    triggerParameter = "workloadIdentity"
                    secretRef        = azurerm_user_assigned_identity.containers.client_id
                  }
                ]
              }
            }
          ]
        }
      }
    }
  }

  depends_on = [
    azurerm_container_app.content_processor,
    azurerm_role_assignment.containers_storage_queue_data_contributor
  ]
}
```

### Step 3: Remove Old `null_resource` Blocks

```terraform
# infra/container_apps_keda_auth.tf - DELETE THIS FILE or comment out all null_resource blocks
```

### Step 4: Update Lifecycle Rules in Container Apps

```terraform
# infra/container_app_processor.tf

resource "azurerm_container_app" "content_processor" {
  # ... existing config ...

  lifecycle {
    ignore_changes = [
      # Let azapi_update_resource manage scale config
      template[0].custom_scale_rule,
      template[0].min_replicas,
      template[0].max_replicas,
      template[0].container[0].image
    ]
  }

  # Keep basic scale structure for initial creation, azapi will update it
  template {
    # ... container config ...

    min_replicas = 0
    max_replicas = 3

    # Basic structure - azapi_update_resource will add full config
    custom_scale_rule {
      name             = "storage-queue-scaler"
      custom_rule_type = "azure-queue"
      metadata = {
        accountName = azurerm_storage_account.main.name
        queueName   = azurerm_storage_queue.content_processing_requests.name
      }
    }
  }
}
```

---

## Alternative: Use Terraform AzAPI Resource Directly

If you want Terraform to fully own the resource (no azurerm at all for scale config):

```terraform
# infra/container_app_processor_scale.tf

resource "azapi_resource" "processor_scale_settings" {
  type      = "Microsoft.App/containerApps@2024-03-01"
  name      = "${local.resource_prefix}-processor"
  parent_id = azurerm_resource_group.main.id

  body = {
    properties = {
      # Copy all properties from azurerm_container_app.content_processor
      # Plus complete scale configuration with auth
      template = {
        scale = {
          minReplicas = 0
          maxReplicas = 3
          cooldownPeriod = 300
          pollingInterval = 30
          rules = [
            {
              name = "storage-queue-scaler"
              custom = {
                type = "azure-queue"
                metadata = {
                  accountName           = azurerm_storage_account.main.name
                  queueName             = azurerm_storage_queue.content_processing_requests.name
                  queueLength           = "80"
                  activationQueueLength = "1"
                  queueLengthStrategy   = "all"
                  cloud                 = "AzurePublicCloud"
                }
                auth = [
                  {
                    triggerParameter = "workloadIdentity"
                    secretRef        = azurerm_user_assigned_identity.containers.client_id
                  }
                ]
              }
            }
          ]
        }
        containers = [ /* ... */ ]
        # ... rest of template
      }
    }
  }
}
```

**Pros**: Single source of truth, no drift  
**Cons**: More verbose, must duplicate container app config

---

## Recommended Values for Your Use Case

Based on KEDA best practices and your workload:

### Content Processor (AI Processing - CPU/Memory Intensive)

```terraform
queueLength           = "5"    # Each replica handles 5 messages (AI processing is slow)
activationQueueLength = "1"    # Wake immediately when work arrives
min_replicas          = 0      # Scale to zero when idle
max_replicas          = 3      # Limit concurrent AI processing (cost control)
```

**Scaling behavior**:
- 1-5 messages → 1 replica
- 6-10 messages → 2 replicas
- 11-15 messages → 3 replicas (max)
- 0 messages for 5min → scale to 0

**Rationale**: AI processing is expensive and slow (~30-60s per message). Better to have fewer replicas processing steadily than many replicas sitting idle.

### Markdown Generator (Fast Processing)

```terraform
queueLength           = "10"   # Each replica handles 10 messages (markdown is fast)
activationQueueLength = "1"    # Wake immediately
min_replicas          = 0      # Scale to zero when idle  
max_replicas          = 5      # Can handle more concurrency
```

**Scaling behavior**:
- 1-10 messages → 1 replica
- 11-20 messages → 2 replicas
- 21-30 messages → 3 replicas
- 31-40 messages → 4 replicas
- 41-50 messages → 5 replicas (max)

**Rationale**: Markdown generation is fast (~2-5s per message). Can safely process more messages per replica.

### Site Publisher (Batch Processing)

```terraform
queueLength           = "1"    # Hugo builds entire site, not individual messages
activationQueueLength = "1"    # Wake immediately
min_replicas          = 0      # Scale to zero when idle
max_replicas          = 1      # Only need one (builds whole site)
```

**Scaling behavior**:
- 1+ messages → 1 replica
- Always max 1 replica (no horizontal scaling needed)

**Rationale**: Hugo builds the entire static site, not individual pages. Multiple replicas would just build the same thing concurrently (wasteful). Use `queueLength = "1"` so each build processes all pending publish requests.

### Collector (CRON Scheduled)

```terraform
# No queue scaler - uses CRON scaler instead
custom_scale_rule {
  name             = "cron-scaler"
  custom_rule_type = "cron"
  metadata = {
    timezone        = "UTC"
    start           = "0 0,8,16 * * *"  # Every 8 hours
    end             = "30 0,8,16 * * *" # 30-min window (container usually exits in 2-5 min)
    desiredReplicas = "1"
  }
}
```

**Scaling behavior**:
- Scales to 1 at scheduled times (00:00, 08:00, 16:00 UTC)
- Container processes collection
- Container exits naturally when done (~2-5 minutes)
- KEDA scales to 0 (or forces scale-down after 30 minutes)

---

## Summary of Changes Needed

### 🎯 Fix #1: Switch to `azapi` Provider (CRITICAL)

**Current Problem**: `null_resource` with Azure CLI wipes metadata  
**Solution**: Use `azapi_update_resource` to set complete configuration  
**Files to Change**:
- `infra/providers.tf` - Add azapi provider
- `infra/container_apps_keda_complete.tf` - New file with azapi updates
- `infra/container_apps_keda_auth.tf` - DELETE or disable null_resource blocks
- `infra/container_app_*.tf` - Add lifecycle ignore_changes rules

### 🎯 Fix #2: Optimize `queueLength` Values (RECOMMENDED)

**Current**: All containers use `queueLength = "80"` or `"1"`  
**Problem**: Processor waits for 80 messages before scaling (too high for your load)  
**Solution**: Use values based on message processing time:
- Processor: `"5"` (slow AI processing)
- Markdown-gen: `"10"` (fast template processing)
- Site-publisher: `"1"` (batch processing)

**Files to Change**:
- `infra/container_app_processor.tf` - Change to `queueLength = "5"`
- `infra/container_app_markdown_generator.tf` - Change to `queueLength = "10"`
- `infra/container_app_site_publisher.tf` - Keep at `queueLength = "1"`

### 🎯 Fix #3: Set Explicit `minReplicas = 0` (RECOMMENDED)

**Current**: Terraform sets `0`, Azure shows `null`  
**Solution**: Use azapi to force explicit `0` value  
**Benefit**: Clear scale-to-zero behavior, no ambiguity

---

## Implementation Steps

### Phase 1: Emergency Fix (Get Things Working Today)

```bash
# 1. Manually update containers with correct configuration
az containerapp update \
  --name ai-content-prod-processor \
  --resource-group ai-content-prod-rg \
  --scale-rule-name storage-queue-scaler \
  --scale-rule-type azure-queue \
  --scale-rule-metadata \
    accountName=aicontentprodstkwakpx \
    queueName=content-processing-requests \
    queueLength=5 \
    activationQueueLength=1 \
    queueLengthStrategy=all \
    cloud=AzurePublicCloud \
  --scale-rule-auth workloadIdentity=d9130268-88c8-48ba-848e-c631233a0600 \
  --min-replicas 0 \
  --max-replicas 3

# 2. Repeat for other containers
# markdown-generator: queueLength=10
# site-publisher: queueLength=1

# 3. Monitor scaling
watch -n 10 'az containerapp replica list --name ai-content-prod-processor --resource-group ai-content-prod-rg --query "[].{Name:name, Status:properties.runningState}"'
```

### Phase 2: Proper IaC Fix (Next Week)

1. Add `azapi` provider to Terraform
2. Create `azapi_update_resource` blocks for each container
3. Comment out `null_resource` blocks
4. Run `terraform plan` to verify changes
5. Run `terraform apply` to apply proper configuration
6. Verify configuration persists across deployments

### Phase 3: Architecture Improvements (Following Week)

1. Add monitoring for queue depths
2. Add alerts for stuck processing
3. Tune `queueLength` values based on actual metrics
4. Document runbooks for scaling issues

---

## Testing the Fix

### Test 1: Verify Metadata is Populated

```bash
az containerapp show \
  --name ai-content-prod-processor \
  --resource-group ai-content-prod-rg \
  --query "properties.template.scale.rules[0].custom.metadata" \
  --output json

# Expected: All fields populated with correct values
{
  "accountName": "aicontentprodstkwakpx",
  "queueName": "content-processing-requests",
  "queueLength": "5",
  "activationQueueLength": "1",
  "queueLengthStrategy": "all",
  "cloud": "AzurePublicCloud"
}
```

### Test 2: Verify Scale-to-Zero Works

```bash
# 1. Ensure queue is empty
az storage message clear \
  --queue-name content-processing-requests \
  --account-name aicontentprodstkwakpx \
  --auth-mode login

# 2. Wait for cooldown (5 minutes)
sleep 360

# 3. Check replicas
az containerapp replica list \
  --name ai-content-prod-processor \
  --resource-group ai-content-prod-rg

# Expected: No replicas (scaled to 0)
```

### Test 3: Verify Scale-Up Works

```bash
# 1. Send test message
az storage message put \
  --queue-name content-processing-requests \
  --content '{"test": "scaling"}' \
  --account-name aicontentprodstkwakpx \
  --auth-mode login

# 2. Wait for KEDA polling (30-60 seconds)
sleep 60

# 3. Check replicas
az containerapp replica list \
  --name ai-content-prod-processor \
  --resource-group ai-content-prod-rg

# Expected: 1 replica running
```

### Test 4: Verify Horizontal Scaling

```bash
# 1. Send 20 messages (should trigger 4 replicas with queueLength=5)
for i in {1..20}; do
  az storage message put \
    --queue-name content-processing-requests \
    --content "{\"test\": \"message-$i\"}" \
    --account-name aicontentprodstkwakpx \
    --auth-mode login
done

# 2. Wait for scaling (1-2 minutes)
sleep 120

# 3. Check replicas
az containerapp replica list \
  --name ai-content-prod-processor \
  --resource-group ai-content-prod-rg

# Expected: 3 replicas (max) or 4 if max_replicas increased
```

---

## Your Original Question Answered

> "Have I made some miscalculation in my KEDA configuration?"

**No!** Your understanding is correct:
- ✅ `queueLength` = messages per replica (horizontal scaling threshold)
- ✅ `activationQueueLength` = wake-from-zero threshold (activation)
- ✅ Your Terraform config is conceptually sound

**The problem is**:
- ❌ `null_resource` + Azure CLI is wiping out your metadata
- ❌ Configuration not actually reaching Azure (shows empty)
- ❌ KEDA can't read queue metrics → can't scale

**The solution is**:
- ✅ Use `azapi` provider for complete configuration
- ✅ Remove `null_resource` approach
- ✅ Optionally tune `queueLength` values (80 → 5 for processor)

---

## Next Steps

Would you like me to:

1. **Emergency fix now**: Run manual Azure CLI commands to get processing working today
2. **Implement azapi fix**: Create the Terraform code using `azapi` provider
3. **Both**: Fix manually now, then implement proper IaC for permanent solution

Let me know and I'll help you get this resolved!
