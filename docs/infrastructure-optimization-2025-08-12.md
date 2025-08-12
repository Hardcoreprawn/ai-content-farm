# Infrastructure Deployment Optimization - August 12, 2025

## Problem Statement

Our Terraform deployments were experiencing unnecessary resource updates on every run due to configuration drift. Azure was automatically adding properties that weren't defined in our Terraform configuration, causing inefficient deployments and potential instability.

## Issues Identified

### 1. Key Vault Secrets Drift
**Problem**: Azure automatically adds properties that Terraform removes on each run:
- Missing `content_type = "function-key"`
- Azure adds `file-encoding = "utf-8"` tag that gets removed
- Inconsistent tag definitions

**Solution**: 
- Explicitly define `content_type` in Terraform
- Add `file-encoding = "utf-8"` tag to match Azure's automatic behavior
- Use `lifecycle.ignore_changes` to prevent drift on auto-managed properties

### 2. Function App Configuration Drift
**Problem**: Azure automatically adds Application Insights settings:
- `APPINSIGHTS_INSTRUMENTATIONKEY` 
- `APPLICATIONINSIGHTS_CONNECTION_STRING`
- `WEBSITE_RUN_FROM_PACKAGE` gets updated during deployments

**Solution**:
- Explicitly define Application Insights settings in `app_settings`
- Add lifecycle rule to ignore changes to `WEBSITE_RUN_FROM_PACKAGE`

### 3. Storage Account Network Rules
**Problem**: Azure automatically adds `network_rules` block when not explicitly defined.

**Solution**: Explicitly define the `network_rules` block with the default Azure values:
```hcl
network_rules {
  default_action = "Allow"
  bypass         = ["AzureServices"]
}
```

### 4. Null Resource Forced Replacement
**Problem**: Using `timestamp()` in triggers causes resource replacement on every run.

**Solution**: Remove `timestamp()` trigger and only trigger on actual function app changes:
```hcl
triggers = {
  function_app_id = azurerm_linux_function_app.main.id
  # Removed timestamp to prevent forced replacement
}
```

## Changes Made

### File: `/infra/application/main.tf`

1. **Key Vault Secrets** - Added missing properties and lifecycle rules:
   ```hcl
   content_type = "function-key"
   tags = {
     Purpose       = "summarywomble-auth"
     Environment   = var.environment
     ManagedBy     = "terraform"
     file-encoding = "utf-8"  # Azure automatically adds this tag
   }
   
   lifecycle {
     ignore_changes = [value, tags["file-encoding"]]
   }
   ```

2. **Storage Account** - Added explicit network rules:
   ```hcl
   # Azure automatically adds network_rules - explicitly define to prevent drift
   network_rules {
     default_action = "Allow"
     bypass         = ["AzureServices"]
   }
   ```

3. **Function App** - Added lifecycle rules and explicit settings:
   ```hcl
   app_settings = {
     # ... existing settings ...
     # Application Insights settings - Azure adds these automatically, define explicitly to prevent drift
     APPINSIGHTS_INSTRUMENTATIONKEY        = azurerm_application_insights.main.instrumentation_key
     APPLICATIONINSIGHTS_CONNECTION_STRING = azurerm_application_insights.main.connection_string
     # ... other settings ...
   }
   
   lifecycle {
     ignore_changes = [
       app_settings["WEBSITE_RUN_FROM_PACKAGE"]
     ]
   }
   ```

4. **Null Resource** - Removed forced replacement trigger:
   ```hcl
   triggers = {
     function_app_id = azurerm_linux_function_app.main.id
     # Removed timestamp to prevent forced replacement on every run
   }
   ```

## Expected Benefits

1. **Faster Deployments**: No unnecessary resource updates on each run
2. **More Stable Infrastructure**: Reduced configuration drift
3. **Predictable Plans**: Terraform plans will only show actual changes
4. **Reduced Azure API Calls**: Fewer update operations during deployment
5. **Better CI/CD Performance**: Shorter deployment times in pipelines

## Validation

After applying these changes, subsequent `terraform plan` runs should show:
- No updates to Key Vault secrets (unless actual values change)
- No updates to storage account network rules
- No updates to Function App Application Insights settings
- No forced replacement of null resources

## Next Steps

1. Apply these changes to staging environment first
2. Validate that no unexpected drift occurs
3. Apply to production environment
4. Monitor deployment times for improvement
5. Document any additional drift patterns that emerge

## Maintenance Notes

- Review infrastructure drift quarterly using `terraform plan`
- When Azure adds new automatic properties, update Terraform configurations proactively
- Use `lifecycle.ignore_changes` strategically for properties that Azure manages
- Monitor Azure provider updates for changes that might affect resource drift

---
*Optimization completed: August 12, 2025*
*Next review: November 12, 2025*
