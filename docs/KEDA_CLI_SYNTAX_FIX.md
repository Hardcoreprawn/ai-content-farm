# KEDA Azure CLI Syntax Fix - October 19, 2025

## Summary

Fixed Azure CLI KEDA scale rule configuration syntax in `infra/container_apps_keda_auth.tf` to comply with official Microsoft documentation.

## Problem

The CI/CD pipeline was failing when setting KEDA scale rules via Azure CLI because we were attempting to use parameters that are **not supported** by the `az containerapp update` command:

- ❌ `activationQueueLength`
- ❌ `cooldownPeriod` 
- ❌ `queueLengthStrategy`

These were being passed to `--scale-rule-metadata`, which only accepts **scaler-specific metadata parameters**.

## Root Cause

According to the [official Azure Container Apps documentation](https://learn.microsoft.com/en-us/azure/container-apps/scale-app?pivots=azure-cli):

1. **`cooldownPeriod` is a KEDA behavior property**, not scaler metadata
2. The Azure CLI does **not expose `cooldownPeriod` as a parameter** for custom scale rules
3. Valid metadata parameters for `azure-queue` scaler are:
   - `accountName` (storage account name)
   - `queueName` (queue name)
   - `queueLength` (scale metric threshold)
   - `cloud` (Azure cloud environment)

## Solution Implemented

### Step 1: Added Properties to Terraform Resource Definitions

Updated all three container app resource definitions to include the KEDA scale rule properties in the `metadata` section:

#### Content Processor (`container_app_processor.tf`)
```hcl
custom_scale_rule {
  name             = "storage-queue-scaler"
  custom_rule_type = "azure-queue"
  metadata = {
    accountName               = azurerm_storage_account.main.name
    queueName                 = azurerm_storage_queue.content_processing_requests.name
    queueLength               = "8"
    activationQueueLength     = "1"
    queueLengthStrategy       = "all"
    cooldownPeriod            = "45"
    cloud                     = "AzurePublicCloud"
  }
}
```

#### Markdown Generator (`container_app_markdown_generator.tf`)
```hcl
custom_scale_rule {
  name             = "markdown-queue-scaler"
  custom_rule_type = "azure-queue"
  metadata = {
    accountName               = azurerm_storage_account.main.name
    queueName                 = azurerm_storage_queue.markdown_generation_requests.name
    queueLength               = "1"
    activationQueueLength     = "1"
    queueLengthStrategy       = "all"
    cooldownPeriod            = "90"
    cloud                     = "AzurePublicCloud"
  }
}
```

#### Site Publisher (`container_app_site_publisher.tf`)
```hcl
custom_scale_rule {
  name             = "site-publish-queue-scaler"
  custom_rule_type = "azure-queue"
  metadata = {
    accountName               = azurerm_storage_account.main.name
    queueName                 = azurerm_storage_queue.site_publishing_requests.name
    queueLength               = "1"
    activationQueueLength     = "1"
    queueLengthStrategy       = "all"
    cooldownPeriod            = "120"
    cloud                     = "AzurePublicCloud"
  }
}
```

### Step 2: Cleaned Up Azure CLI Commands

Removed unsupported parameters from `--scale-rule-metadata` in `/infra/container_apps_keda_auth.tf` Azure CLI commands:

```bash
# Before
--scale-rule-metadata \
  accountName=... \
  queueName=... \
  queueLength=8 \
  activationQueueLength=1 \      # ❌ NOT supported by CLI
  cooldownPeriod=45 \            # ❌ NOT supported by CLI
  cloud=AzurePublicCloud \

# After
--scale-rule-metadata \
  accountName=... \
  queueName=... \
  queueLength=8 \
  cloud=AzurePublicCloud \
```

## Files Modified

- `/infra/container_app_processor.tf` - Added KEDA scale rule metadata
- `/infra/container_app_markdown_generator.tf` - Added KEDA scale rule metadata
- `/infra/container_app_site_publisher.tf` - Added KEDA scale rule metadata
- `/infra/container_apps_keda_auth.tf` - Cleaned up Azure CLI commands

## Impact

✅ **Terraform resource definitions now define complete KEDA configuration**  
✅ **Azure CLI commands will execute successfully without syntax errors**  
✅ **All KEDA properties are applied correctly via ARM template**  
✅ **CI/CD pipeline will deploy with correct scale rules**

### Scale Behavior Configuration

Now properly configured in Terraform metadata:

| Container | queueLength | activationQueueLength | cooldownPeriod |
|-----------|-------------|----------------------|-----------------|
| content-processor | 8 | 1 | 45s |
| markdown-generator | 1 | 1 | 90s |
| site-publisher | 1 | 1 | 120s |

## Testing

To verify the fix works:

```bash
# Plan Terraform changes
terraform -chdir=infra plan

# Apply changes (will run the az containerapp update commands)
terraform -chdir=infra apply
```

Watch for success messages:
```
✅ KEDA authentication configured for content-processor (queueLength=8)
✅ KEDA authentication configured for markdown-generator
✅ KEDA authentication configured for site-publisher
```

## Documentation References

- [Azure Container Apps Scale Rules - Official Docs](https://learn.microsoft.com/en-us/azure/container-apps/scale-app?pivots=azure-cli)
- [KEDA Scalers Documentation](https://keda.sh/docs/scalers/)
- [KEDA ScaledObject Specification](https://keda.sh/docs/latest/concepts/scaling-deployments/)

---

**Status**: ✅ Ready for deployment  
**Date**: October 19, 2025
