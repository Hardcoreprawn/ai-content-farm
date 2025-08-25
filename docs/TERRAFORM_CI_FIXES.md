# Terraform CI/CD Issues Fixed - August 25, 2025

## Issues Resolved ✅

### 1. Terraform Command Not Found (Exit Code 127)
**Problem**: `terraform: command not found` in GitHub Actions runner
**Solution**: Use Docker with `hashicorp/terraform:latest` image
**Files Changed**: `.github/actions/deploy-to-azure/action.yml`

### 2. Azure Authentication in Docker Container
**Problem**: Terraform Docker container couldn't authenticate to Azure backend
**Solution**: Pass OIDC environment variables to Docker container
```bash
-e ARM_CLIENT_ID \
-e ARM_TENANT_ID \
-e ARM_SUBSCRIPTION_ID \
-e ARM_USE_OIDC \
-e ACTIONS_ID_TOKEN_REQUEST_TOKEN \
-e ACTIONS_ID_TOKEN_REQUEST_URL
```

### 3. Checkov Artifact Upload Path
**Problem**: `No files were found with the provided path: security-results/checkov-results.json`
**Solution**: Fixed Docker output file path and added `if-no-files-found: warn`
**Files Changed**: `.github/actions/security-checkov/action.yml`

## Current Issue 🔄

### Storage Account Permissions (403 Authorization Error)
**Problem**: Service principal lacks permissions for Terraform state storage
**Error**: `This request is not authorized to perform this operation`
**Storage Account**: `aicontentstagingstv33ppo`
**Fix Required**: Grant service principal **Storage Blob Data Contributor** role

## Next Actions
1. Fix storage account permissions (see below)
2. Test full pipeline deployment
3. Remove trivial test comments from code

---
_Pipeline now technically sound - only Azure permissions remain_
