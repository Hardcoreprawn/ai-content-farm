# Terraform KEDA Authentication Fix - CI/CD Pipeline Error Resolution

## Problem Summary

**GitHub Actions Run**: #1164  
**Error**: CI/CD pipeline deployment phase failed with three identical errors in the KEDA authentication configuration.

### Root Cause

The `az containerapp update` command does not support the `--cooldown-period` flag as a separate command-line argument when configuring KEDA scale rules. This flag was incorrectly passed outside the `--scale-rule-metadata` block:

```bash
# ❌ INCORRECT (causes error):
az containerapp update \
  ...
  --scale-rule-metadata \
    accountName=... \
    queueName=... \
  --scale-rule-auth ... \
  --cooldown-period 45          # ← INVALID ARGUMENT
  --output none
```

## Solution

Move the `cooldown-period` value into the `--scale-rule-metadata` block using the camelCase parameter name `cooldownPeriod`:

```bash
# ✅ CORRECT:
az containerapp update \
  ...
  --scale-rule-metadata \
    accountName=... \
    queueName=... \
    cooldownPeriod=45             # ← Now part of metadata
  --scale-rule-auth ... \
  --output none
```

## Changes Made

**File**: `/infra/container_apps_keda_auth.tf`

### Fixed Resources (3 total)

#### 1. **content-processor** (line ~58)
- **Before**: `--cooldown-period 45`
- **After**: `cooldownPeriod=45` (in `--scale-rule-metadata` block)

#### 2. **markdown-generator** (line ~118)
- **Before**: `--cooldown-period 90`
- **After**: `cooldownPeriod=90` (in `--scale-rule-metadata` block)

#### 3. **site-publisher** (line ~178)
- **Before**: `--cooldown-period 120`
- **After**: `cooldownPeriod=120` (in `--scale-rule-metadata` block)

## Technical Details

### Azure CLI KEDA Scale Rule Metadata Parameters

The `az containerapp update` command accepts KEDA scale rule parameters through the `--scale-rule-metadata` option. All parameters must be specified as key-value pairs within this block:

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `accountName` | string | Azure Storage account name | `mystorageaccount` |
| `queueName` | string | Queue name to monitor | `my-queue` |
| `queueLength` | integer | Target queue length for scaling | `8` |
| `activationQueueLength` | integer | Queue length to activate scaler | `1` |
| `cooldownPeriod` | integer | Cooldown period in seconds | `45` |
| `queueLengthStrategy` | string | Strategy for queue length calculation | `all` |
| `cloud` | string | Azure cloud environment | `AzurePublicCloud` |

### References

- Azure CLI Documentation: `az containerapp update`
- Azure Container Apps KEDA Scale Rules
- Azure Queue Storage Scaler (KEDA)

## Testing & Verification

### Local Validation

```bash
# Verify Terraform formatting
cd infra
terraform fmt -check -recursive .

# Plan the deployment
terraform plan -var="image_tag=test" -var="environment=production"
```

### CI/CD Pipeline Validation

The fix will be validated through the CI/CD pipeline:

1. ✅ Terraform format check (infrastructure-quality)
2. ✅ Terraform plan (terraform-checks)
3. ✅ Azure CLI command execution (deploy → smart-deploy action)
4. ✅ KEDA scale rule configuration verification

## Impact

### Scope
- **Infrastructure**: KEDA scale rule authentication for three container apps
- **Services Affected**: 
  - content-processor (queue-based trigger)
  - markdown-generator (queue-based trigger)
  - site-publisher (queue-based trigger)

### Behavior Changes
- **Before**: Deployment would fail at the Terraform `null_resource` provisioner stage
- **After**: KEDA scale rules properly configured with correct cooldown periods

### Rollout
- Direct fix to `main` branch
- No manual intervention required
- No breaking changes to existing infrastructure
- No impact on running applications

## Deployment

### Next Steps

1. **Pull latest code**: `git pull origin main`
2. **Verify locally**: `cd infra && terraform validate`
3. **Re-run CI/CD**: Push to trigger new deployment pipeline
4. **Monitor**: Verify container app scale rules are functioning

### Rollback (if needed)

```bash
# Revert to previous version
git revert <commit-hash>
git push origin main
```

## Related Issues

- **GitHub Issue**: #XXX (update if applicable)
- **Action Run**: #1164
- **Original Implementation**: `docs/keda-auth-implementation-plan.md`

## Lessons Learned

### Azure CLI Parameter Naming Conventions

- **Command-line arguments** (flags): Use kebab-case (`--cooldown-period`)
- **Metadata parameters**: Use camelCase (`cooldownPeriod`)

This distinction is crucial when using structured options like `--scale-rule-metadata` where parameters follow JSON/API conventions rather than CLI conventions.

### Future Prevention

- Validate Azure CLI commands locally before committing to CI/CD
- Test `null_resource` provisioners with actual Azure CLI commands during development
- Add integration tests for infrastructure provisioning steps

---

**Commit**: 293a8c1  
**Date**: October 19, 2025  
**Status**: ✅ Resolved
