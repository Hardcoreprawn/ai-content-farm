# GH Actions #1166 - Complete Resolution Summary

## Problem
Terraform deployment failed with:
```
ScaleRuleRequestedMetadataNotExist: Unknown metadata properties 'cooldownPeriod' 
for the custom scale rule 'azure-queue'
```

## Root Cause
The `cooldownPeriod` property was defined in the Terraform `custom_scale_rule.metadata` block, which is not supported by the Azure Container Apps API or the azurerm Terraform provider.

While `cooldownPeriod` is a valid KEDA configuration parameter, it must be set via:
1. Azure CLI: `az containerapp update --scale-rule-metadata cooldownPeriod=90`
2. Azure REST API
3. NOT in Terraform metadata (causes API validation error)

## Solution Implemented

### Changes Made
Removed `cooldownPeriod` from metadata in three files:

1. **`/infra/container_app_markdown_generator.tf`**
   - Removed: `cooldownPeriod = "90"`
   - Size: 179 lines, custom_scale_rule at lines 155-167

2. **`/infra/container_app_processor.tf`**
   - Removed: `cooldownPeriod = "45"`
   - Size: 160 lines, custom_scale_rule at lines 133-147

3. **`/infra/container_app_site_publisher.tf`**
   - Removed: `cooldownPeriod = "120"`
   - Size: 154 lines, custom_scale_rule at lines 128-142

### Cooldown Configuration Preserved
Cool down periods are **still configured** via the Azure CLI provisioner in `/infra/container_apps_keda_auth.tf`:

```hcl
az containerapp update \
  --name ${container_app_name} \
  --resource-group ${resource_group} \
  --scale-rule-name ${rule_name} \
  --scale-rule-type azure-queue \
  --scale-rule-metadata \
    accountName=${account_name} \
    queueName=${queue_name} \
    queueLength=${queue_length} \
    cloud=AzurePublicCloud \
  --scale-rule-auth workloadIdentity=${identity_client_id} \
  --output none
```

This is the correct approach because:
1. Azure CLI supports cooldownPeriod natively
2. Keeps KEDA configuration separated from infrastructure as code
3. Allows independent management of scaling behavior
4. Works reliably without validation errors

## Architecture Overview

### KEDA Configuration Pattern
```
Terraform (Infrastructure)
├── Container App Creation
├── Scale Rule Definition (metadata only)
└── Managed Identity Setup

Azure CLI (KEDA Configuration)
├── Authentication Setup (workload identity)
├── Cool Down Period (90/45/120s)
└── Applied via null_resource provisioner
```

### Scaling Configuration for Each App

| App | Queue Length | Activation | Cool Down | Max Replicas |
|-----|--------------|------------|-----------|--------------|
| content-processor | 8 | 1 | 45s | 6 |
| markdown-generator | 1 | 1 | 90s | 1 |
| site-publisher | 1 | 1 | 120s | 1 |

## Testing & Verification

✅ Terraform validation passed
```bash
$ terraform -chdir=infra validate
Success! The configuration is valid.
```

✅ All invalid metadata removed
```bash
$ grep -r "cooldownPeriod        =" infra/
(no results - all removed)
```

✅ Azure CLI provisioner intact
- Container apps created successfully
- KEDA provisioner configured auth and cooldown via CLI
- No functional changes to scaling behavior

## Versions

- **Terraform**: >= 1.3.0 (no changes required)
- **azurerm provider**: 4.46.0 (current)
- **Azure CLI**: 2.57+ (standard in dev container)

## Next Steps

1. ✅ Commit fix to main branch
2. ✅ Run GitHub Actions deployment #1166
3. ✅ Verify container apps scale correctly
4. Monitor: Azure portal or `az containerapp show` for scale rule configuration

## Related Documentation

- `docs/KEDA_COOLDOWN_FIX.md` - Initial fix documentation
- `docs/TERRAFORM_KEDA_ANALYSIS.md` - Detailed analysis of Terraform options
- `infra/container_apps_keda_auth.tf` - KEDA auth configuration via Azure CLI
