# CI/CD Pipeline Fix Validation Plan

## Issues Fixed

### 1. ✅ Missing container_images Variable 
- **Added**: `variable "container_images"` in `infra/variables.tf`
- **Impact**: Eliminates "Value for undeclared variable" warning
- **Test**: Terraform validate passes

### 2. ✅ Dynamic Container Image References
- **Updated**: All container apps now use `var.container_images["container-name"]`
- **Impact**: Deploys commit-specific container images instead of hardcoded `:latest`
- **Test**: Pipeline will deploy the actual built containers

### 3. ⚠️  Resource Group Lock Conflict (Manual Fix Required)
- **Created**: Scripts to handle ACR resource cleanup
- **Scripts**: `scripts/remove-acr-from-state.sh` and `scripts/terraform-resource-cleanup.sh`
- **Impact**: Requires manual execution before next deployment

## Deployment Process

### Phase 1: Clean Up Legacy ACR Resources (Manual)
```bash
# Authenticate to Azure
az login

# Remove ACR resources from Terraform state
./scripts/remove-acr-from-state.sh production

# Verify state cleanup
cd infra && terraform state list | grep -E "(container_registry|acr)"
```

### Phase 2: Test Deployment
```bash
# Commit and push the fixes
git add -A
git commit -m "fix: resolve CI/CD pipeline deployment issues

- Add container_images variable to eliminate Terraform warnings
- Update all container apps to use dynamic image references  
- Create scripts for ACR resource cleanup
- Resolves resource group lock conflicts preventing deployment"

git push origin main
```

### Phase 3: Monitor Pipeline
- Watch GitHub Actions workflow for successful deployment
- Verify containers deploy with commit-specific SHA tags
- Confirm no more ACR-related errors

## Expected Outcomes

1. **No Terraform Warnings**: `container_images` variable properly declared
2. **Commit-Specific Deployments**: Containers use SHA tags from CI build
3. **No Resource Lock Conflicts**: Legacy ACR resources removed from state
4. **Successful Azure Deployment**: Pipeline reaches production environment

## Rollback Plan

If issues persist:
1. Revert terraform changes: `git revert HEAD`
2. Use temporary fix: Deploy with resource lock removal
3. Manual Azure resource cleanup if needed

## Next Steps After Fix

1. Validate deployed container versions match commit SHA
2. Test application functionality in production
3. Monitor deployment metrics and costs
4. Update documentation with new deployment process
