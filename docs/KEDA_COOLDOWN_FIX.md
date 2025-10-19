# KEDA Cooldown Period Fix - GH Actions #1166

## Problem
Terraform deployment failed with:
```
ScaleRuleRequestedMetadataNotExist: Unknown metadata properties 'cooldownPeriod' 
for the custom scale rule 'azure-queue'.
```

## Root Cause
The `cooldownPeriod` property was incorrectly defined in the Terraform `custom_scale_rule` metadata block. This property is not supported by the `azurerm_container_app` Terraform resource's metadata field.

While `cooldownPeriod` is a valid KEDA configuration, the `azurerm` Terraform provider (v4.37.0) does not support setting it through the metadata block. It must be configured separately via Azure CLI.

## Solution
Removed `cooldownPeriod` from the metadata hash in three container app Terraform configurations:

1. **`container_app_markdown_generator.tf`**: Removed `cooldownPeriod = "90"`
2. **`container_app_processor.tf`**: Removed `cooldownPeriod = "45"`
3. **`container_app_site_publisher.tf`**: Removed `cooldownPeriod = "120"`

The cooldown periods are still configured via the Azure CLI provisioner in `container_apps_keda_auth.tf`:
- The `null_resource` provisioner executes `az containerapp update` commands after container app creation
- These commands set the cooldown via the `--scale-rule-metadata` parameter directly to Azure API
- The configuration is reapplied whenever container apps or scale rules change

## Files Modified
- `/infra/container_app_markdown_generator.tf`
- `/infra/container_app_processor.tf`
- `/infra/container_app_site_publisher.tf`

## Verification
- ✅ Terraform validation passed
- ✅ All `cooldownPeriod` references removed from metadata blocks
- ✅ Azure CLI provisioners still handle cooldown configuration (no functional change)
- ✅ Comments updated to clarify that cooldownPeriod is configured via null_resource

## Testing
Next deployment should succeed. The container apps will be created with proper KEDA scale rules, and the Azure CLI provisioners will configure authentication and cooldown periods via the `az containerapp update` command.

## Related Documentation
- `infra/container_apps_keda_auth.tf` - KEDA authentication and cooldown configuration via Azure CLI
- Azure Container Apps KEDA scaling documentation
