# Simple Pipeline Reorder: Fix Function Deployment Drift - August 12, 2025

## Current Problem

The pipeline deploys infrastructure first, then uploads function code, causing drift:

1. Terraform sets `WEBSITE_RUN_FROM_PACKAGE = "1"`
2. `az functionapp deployment source config-zip` changes it to SAS URL
3. Next Terraform run sees drift and wants to revert to "1"

## Simple Solution: Reorder Existing Steps

Just move the function zip creation **before** infrastructure deployment.

### Current Pipeline Order
```yaml
jobs:
  deploy-infrastructure:
    # Deploy Terraform with WEBSITE_RUN_FROM_PACKAGE = "1"
    
  deploy-functions:
    # Create zip and upload with az functionapp deployment source config-zip
    # This overwrites the Terraform setting, causing drift
```

### New Pipeline Order  
```yaml
jobs:
  build-functions:
    # Create zip and upload to storage (reuse existing logic)
    # Output the blob URL
    
  deploy-infrastructure:
    # Deploy Terraform with WEBSITE_RUN_FROM_PACKAGE = blob URL
    # No more drift!
```

## Required Changes

### 1. Infrastructure Changes (Minimal)

Add variable for package URL:
```hcl
# variables.tf
variable "function_package_url" {
  description = "URL to function deployment package"
  type        = string
  default     = ""
}
```

Update Function App to use the URL:
```hcl
# main.tf - in azurerm_linux_function_app.main
app_settings = {
  # ... existing settings ...
  WEBSITE_RUN_FROM_PACKAGE = var.function_package_url != "" ? var.function_package_url : "1"
}

# Remove this lifecycle rule (no longer needed):
# lifecycle {
#   ignore_changes = [app_settings["WEBSITE_RUN_FROM_PACKAGE"]]
# }
```

### 2. Pipeline Changes (Reorder Only)

**Move existing function build logic to new job:**
```yaml
build-functions:
  runs-on: ubuntu-latest
  outputs:
    package-url: ${{ steps.upload.outputs.url }}
  steps:
    - name: Create Function Package
      run: |
        cd functions/
        # Reuse existing zip creation logic
        zip -r ../function-app.zip . -x "*.pyc" "*/__pycache__/*" ".python_packages/*"
        
    - name: Upload to Storage
      id: upload
      run: |
        # Upload to existing storage account
        az storage blob upload \
          --account-name $STORAGE_ACCOUNT_NAME \
          --container-name function-releases \
          --name "function-$(date +%Y%m%d%H%M%S).zip" \
          --file ../function-app.zip
          
        # Generate SAS URL for Terraform
        URL=$(az storage blob url \
          --account-name $STORAGE_ACCOUNT_NAME \
          --container-name function-releases \
          --name "function-$(date +%Y%m%d%H%M%S).zip" \
          --sas-token "$(az storage container generate-sas ...)")
          
        echo "url=$URL" >> $GITHUB_OUTPUT
```

**Update infrastructure job to use package URL:**
```yaml
deploy-infrastructure:
  needs: build-functions
  steps:
    - name: Deploy Infrastructure
      run: |
        terraform apply -auto-approve \
          -var-file="staging.tfvars" \
          -var="function_package_url=${{ needs.build-functions.outputs.package-url }}"
```

**Remove the old function deployment job:**
```yaml
# DELETE this entire job:
# deploy-functions:
#   needs: deploy-infrastructure
#   steps:
#     - name: Deploy Functions
#       run: az functionapp deployment source config-zip ...
```

### 3. Storage Container Addition
```hcl
# Add to main.tf
resource "azurerm_storage_container" "function_releases" {
  name                  = "function-releases"
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "private"
}
```

## Benefits

- ✅ **Eliminates drift** - Terraform controls the complete setting
- ✅ **No lifecycle rules needed** - No more fighting Azure's overwrites  
- ✅ **Atomic deployments** - Infrastructure and code deployed together
- ✅ **Rollback capability** - Can change package URL for rollbacks
- ✅ **Minimal changes** - Just reordering existing logic

## Testing Plan

1. Apply storage container changes first
2. Test new pipeline with staging environment
3. Verify no drift in subsequent Terraform runs
4. Apply to production if successful

## Implementation Status - COMPLETE ✅

**Date: August 12, 2025**

### Changes Applied

#### Infrastructure Updates ✅
- **main.tf**: Added `function_package_url` variable support in Function App configuration
- **variables.tf**: Added new variable for passing package URLs
- **Storage Container**: Added `function-releases` container for package hosting
- **Lifecycle Rules**: Removed lifecycle ignore rules (no longer needed)

#### Pipeline Restructure ✅
- **New Jobs**: Created `build-functions` (staging) and `build-functions-production` jobs
- **Job Reordering**: Functions now built before infrastructure deployment
- **Variable Integration**: Package URLs passed to Terraform via `-var="function_package_url=..."`
- **Shell Script Compliance**: Fixed quoting issues for actionlint validation (SC2086, SC2046)

#### Package Management ✅
- **Versioning**: Using `YYYYMMDDHHMMSS-{git-hash}` format for unique identification
- **Storage**: Packages uploaded to `function-releases` container with long-term SAS URLs
- **Integration**: Direct URL reference eliminates Azure CLI property conflicts

### Validation Results ✅
- ✅ actionlint: No errors or warnings
- ✅ yamllint: Valid YAML syntax  
- ✅ Terraform syntax: Valid configuration
- ✅ Shell script compliance: Proper variable quoting implemented

### Files Modified
1. `/.github/workflows/consolidated-pipeline.yml` - Complete pipeline restructure
2. `/infra/application/main.tf` - Function App configuration updates
3. `/infra/application/variables.tf` - New variable definition

### Ready for Deployment
The pipeline has been completely restructured and validated. Ready to push to develop branch for staging deployment testing.

---
*Simple reorder - big impact on deployment stability*
