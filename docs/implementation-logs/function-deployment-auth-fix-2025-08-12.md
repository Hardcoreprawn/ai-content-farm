# Function Deployment Authorization Fix

**Date**: 2025-08-12  
**Issue**: GitHub Actions CI/CD pipeline failing with 403 AuthorizationFailure during function package deployment  
**Resolution**: Added Storage Blob Data Contributor role assignment for GitHub Actions service principal

## Problem Description

The CI/CD pipeline was failing during the "Deploy Function Package" step with:

```
ERROR: Client-Request-ID=57e07816-77b1-11f0-81dd-6045bdbe24e1 
Retry policy did not allow for a retry: Server-Timestamp=Tue, 12 Aug 2025 19:20:01 GMT
HTTP status code=403, Exception=This request is not authorized to perform this operation.
ErrorCode: AuthorizationFailure
```

## Root Cause Analysis

The GitHub Actions service principal had the following permissions:
- ✅ **Key Vault Secret User** - for accessing application secrets  
- ✅ **Website Contributor** - for Function App deployment operations
- ❌ **Storage Blob Data Contributor** - **MISSING** for function package uploads

The `az functionapp deployment source config-zip` command requires uploading the function package to the underlying storage account, but the GitHub Actions service principal lacked the necessary storage permissions.

## Solution Implementation

Added the missing role assignment in `infra/application/main.tf`:

```terraform
# GitHub Actions Storage Blob Data Contributor for function package uploads (staging only)
resource "azurerm_role_assignment" "github_actions_storage_blob_contributor" {
  count = var.environment == "staging" && var.github_actions_object_id != "" ? 1 : 0

  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = var.github_actions_object_id
  depends_on           = [azurerm_storage_account.main]
}
```

## Deployment

Applied using targeted terraform apply:

```bash
cd /workspaces/ai-content-farm/infra/application
terraform apply -target="azurerm_role_assignment.github_actions_storage_blob_contributor" \
  -var-file="staging.tfvars" -auto-approve
```

**Result**: Role assignment created successfully after 28 seconds

## GitHub Actions Permissions Summary

The GitHub Actions service principal now has complete deployment permissions:

| Resource | Role | Purpose | Status |
|----------|------|---------|--------|
| Key Vault | Secret User | Access application secrets | ✅ Existing |
| Function App | Website Contributor | Deploy function code | ✅ Existing |  
| Storage Account | Storage Blob Data Contributor | Upload function packages | ✅ **ADDED** |

## Verification

- **Committed**: Infrastructure changes pushed to develop branch (commit: 95c5ab1)
- **Pipeline**: New CI/CD run triggered (ID: 16918916102)
- **Expected Result**: Function deployment should now succeed without authorization errors

## Related Resources

- **Infrastructure**: `/workspaces/ai-content-farm/infra/application/main.tf` (lines 561-568)
- **CI/CD Pipeline**: `.github/workflows/consolidated-pipeline.yml` (function deployment step)
- **Previous Fix**: Key Vault permissions added in earlier session
