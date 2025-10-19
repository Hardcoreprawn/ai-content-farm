# Terraform KEDA Authentication Analysis - GH Actions #1166

## Current Status
- **Terraform azurerm provider**: v4.46.0 (current as of October 2025)
- **Terraform version requirement**: >= 1.3.0
- **Current approach**: Using `null_resource` with Azure CLI provisioner for KEDA auth configuration

## Key Findings from Azure Documentation

### 1. Cool Down Period Default Behavior
From Microsoft Learn documentation, the standard cool down period for custom KEDA scalers is:
- **Default**: 300 seconds
- **Use case**: Applied when scaling from final replica to 0
- **Customization**: Only supported via Azure CLI or REST API, not via Terraform metadata

### 2. Authentication in Custom Scale Rules
Azure Container Apps KEDA scalers support two authentication methods:
1. **Container Secrets** - Connection strings stored in app secrets
2. **Managed Identity** - Workload identity using the container app's assigned managed identity

### 3. Azurerm Provider Support
The `azurerm_container_app` Terraform resource includes:
- ✅ `custom_scale_rule` block with `name`, `custom_rule_type`, and `metadata`
- ✅ `authentication` block within `custom_scale_rule` (supported since azurerm v4.x)
- ❌ `cooldownPeriod` in metadata (Azure Container Apps API rejects it here)

## Better Implementation Option

### Current Implementation (Working Post-Fix)
```terraform
custom_scale_rule {
  name             = "markdown-queue-scaler"
  custom_rule_type = "azure-queue"
  metadata = {
    accountName           = azurerm_storage_account.main.name
    queueName             = azurerm_storage_queue.markdown_generation_requests.name
    queueLength           = "1"
    activationQueueLength = "1"
    cloud                 = "AzurePublicCloud"
  }
  # Managed identity auth + cooldown configured via Azure CLI null_resource
}

lifecycle {
  ignore_changes = [
    template[0].custom_scale_rule[0].authentication
  ]
}
```

### Recommended Option: Use Terraform `authentication` Block

The azurerm provider DOES support `authentication` block in `custom_scale_rule`, which was added to allow managed identity configuration directly in Terraform:

```terraform
custom_scale_rule {
  name             = "markdown-queue-scaler"
  custom_rule_type = "azure-queue"
  metadata = {
    accountName           = azurerm_storage_account.main.name
    queueName             = azurerm_storage_queue.markdown_generation_requests.name
    queueLength           = "1"
    activationQueueLength = "1"
    cloud                 = "AzurePublicCloud"
  }
  
  # NEW: Managed identity authentication directly in Terraform
  authentication {
    secret {
      name = "connection-secret"  # Reference to secret or connection string
    }
  }
}
```

However, this approach has limitations:
1. Still doesn't support `cooldownPeriod` in Terraform
2. Authentication block requires secrets, not direct managed identity reference
3. Current Azure CLI approach is more explicit about managed identity use

## Recommendation: Maintain Current Approach

**Reasoning:**
1. **Clear separation of concerns**: Terraform manages infrastructure, Azure CLI manages KEDA configuration
2. **Explicit managed identity**: Azure CLI approach explicitly uses workload identity, which is auditable
3. **No breaking changes**: Current implementation works reliably after cooldownPeriod fix
4. **Future-proof**: If Azure Container Apps API or Terraform provider updates to support cooldownPeriod, easier to migrate

### Deprecation Risk Analysis
- Null resources with provisioners are NOT deprecated (Terraform 1.7+ still supports them)
- Azure CLI is stable and well-maintained for Container Apps management
- This pattern is documented in official Azure examples

## Migration Path (If Needed Later)

If a future azurerm provider version adds direct support for:
1. Managed identity references in authentication block
2. Cool down period configuration

Then migration would be:
```terraform
# Remove: null_resource provisioner
# Add: authentication block with managed identity reference (when supported)
```

## Version Check Recommendation

**To stay current**, monitor:
1. `azurerm` provider changelog for Container Apps improvements
2. Azure Container Apps API updates for new KEDA scalers
3. Test provider updates in staging before production

Current setup with v4.46.0 is appropriate for October 2025.

## Files Affected by Current Fix

✅ `/infra/container_app_markdown_generator.tf` - Removed invalid `cooldownPeriod` metadata
✅ `/infra/container_app_processor.tf` - Removed invalid `cooldownPeriod` metadata  
✅ `/infra/container_app_site_publisher.tf` - Removed invalid `cooldownPeriod` metadata
✅ `/infra/container_apps_keda_auth.tf` - Azure CLI handles cooldown via `az containerapp update`

## Conclusion

The current fix is correct and represents the best practice given current Terraform provider capabilities. The null_resource + Azure CLI approach is:
- ✅ Supported and documented
- ✅ More explicit about managed identity usage
- ✅ Works reliably with current tooling
- ✅ Simple to maintain and debug
