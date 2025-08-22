# GitHub OIDC Setup Guide

This guide explains how to configure GitHub Actions to use **Azure Managed Identity with OIDC** instead of long-lived service principal secrets for secure, credential-free authentication.

## Issue Context

The production deployment was failing due to authentication issues. We've now implemented the **modern security approach** using:
- ✅ **Azure Managed Identity**: No stored credentials
- ✅ **Federated Identity Credentials**: Direct GitHub-to-Azure OIDC trust
- ✅ **Zero Secrets**: No long-lived credentials stored anywhere

## Architecture

### Old Approach (Insecure)
```
GitHub Secrets (Long-lived) → Service Principal + Secret → Azure
❌ Stored secrets in GitHub
❌ Manual credential rotation required  
❌ Risk of credential exposure
❌ Complex secret management
```

### New Approach (Secure)
```
GitHub OIDC Token → Federated Identity → Managed Identity → Azure
✅ No stored credentials anywhere
✅ Automatic token rotation
✅ Short-lived tokens (15 minutes)
✅ Zero credential management
```

## Required Configuration

### 1. GitHub Repository Variables (NOT Secrets)
These are **public values** from Terraform outputs - no secrets needed:

```bash
AZURE_CLIENT_ID=<managed-identity-client-id>
AZURE_TENANT_ID=<azure-tenant-id>
AZURE_SUBSCRIPTION_ID=<azure-subscription-id>
```

### 2. No GitHub Secrets Required
❌ ~~AZURE_CLIENT_SECRET~~ - Not needed with managed identity
❌ ~~AZURE_CREDENTIALS~~ - Legacy JSON format not needed
✅ **Zero secrets stored in GitHub**

## Setup Steps

### 1. Deploy Infrastructure with Managed Identity
```bash
# Deploy Terraform with federated identity credentials
cd infra
terraform init
terraform apply

# Get the managed identity client ID
terraform output github_actions_client_id
```

### 2. Configure GitHub Repository Variables
Go to **Settings → Secrets and variables → Actions → Variables** and add:

```bash
AZURE_CLIENT_ID=<from terraform output>
AZURE_TENANT_ID=<from terraform output>  
AZURE_SUBSCRIPTION_ID=<from terraform output>
```

### 3. Enable OIDC in Repository
GitHub automatically provides OIDC tokens when:
- ✅ Repository has `id-token: write` permission (already configured)
- ✅ Workflow uses `azure/login@v2` with federated credentials
- ✅ No additional configuration needed

## How It Works

### OIDC Token Flow
1. **GitHub Action starts** → GitHub generates OIDC token
2. **azure/login@v2** → Exchanges GitHub token for Azure token
3. **Federated Identity** → Verifies GitHub repo/branch matches
4. **Managed Identity** → Grants Azure permissions
5. **No secrets involved** → Fully credential-free

### Security Benefits
- 🔒 **Short-lived tokens**: 15-minute expiration
- 🔄 **Automatic rotation**: No manual credential management
- 🎯 **Scoped access**: Limited to specific repo/branch combinations
- 📊 **Full audit trail**: All authentication logged in Azure AD
- 🚫 **No credential exposure**: Nothing to leak or steal

## Terraform Resources

The infrastructure automatically creates:

```hcl
# Managed identity for GitHub Actions
resource "azurerm_user_assigned_identity" "github_actions" {
  name = "ai-content-farm-github-actions"
}

# Federated credentials for main branch
resource "azurerm_federated_identity_credential" "github_main" {
  subject = "repo:Hardcoreprawn/ai-content-farm:ref:refs/heads/main"
}

# Federated credentials for develop branch  
resource "azurerm_federated_identity_credential" "github_develop" {
  subject = "repo:Hardcoreprawn/ai-content-farm:ref:refs/heads/develop"
}

# Federated credentials for pull requests
resource "azurerm_federated_identity_credential" "github_pr" {
  subject = "repo:Hardcoreprawn/ai-content-farm:pull_request"
}
```

## Verification Steps

### 1. Check Infrastructure Deployment
```bash
# Verify managed identity was created
terraform output github_actions_client_id
terraform output tenant_id
terraform output subscription_id
```

### 2. Configure GitHub Variables
Set these as **repository variables** (not secrets):
```bash
gh variable set AZURE_CLIENT_ID --body "$(terraform output -raw github_actions_client_id)"
gh variable set AZURE_TENANT_ID --body "$(terraform output -raw tenant_id)"
gh variable set AZURE_SUBSCRIPTION_ID --body "$(terraform output -raw subscription_id)"
```

### 3. Test OIDC Authentication
```bash
# Push to main branch to trigger production deployment
git push origin main

# Or push to develop for staging deployment
git push origin develop
```

### 4. Monitor Workflow
Watch for successful OIDC authentication:
```
✅ Azure Login via OIDC
✅ Token exchange successful
✅ Deploy to Azure
```

## Troubleshooting

### Common Issues

#### "Failed to get federated token"
- Verify GitHub repository name matches federated credential subject
- Check branch name matches (main/develop)
- Ensure `id-token: write` permission is set in workflow

#### "Managed identity not found"
- Verify Terraform deployment completed successfully
- Check `terraform output github_actions_client_id` returns a value
- Ensure managed identity exists in Azure portal

#### "Access denied"
- Verify managed identity has appropriate role assignments
- Check Key Vault access policies include the managed identity
- Ensure Container Registry permissions are granted

#### "Invalid audience"
- Verify audience is set to `["api://AzureADTokenExchange"]`
- Check issuer URL is `https://token.actions.githubusercontent.com`
- Ensure federated credential configuration is correct

## Security Comparison

### Before (Service Principal + Secret)
```bash
❌ AZURE_CLIENT_SECRET stored in GitHub
❌ Manual rotation required every 2 years
❌ Risk of credential exposure in logs
❌ Shared secret across all environments
❌ Complex secret lifecycle management
```

### After (Managed Identity + OIDC)
```bash
✅ Zero secrets stored anywhere
✅ Automatic token rotation every 15 minutes
✅ No credential exposure risk
✅ Environment-specific identity scoping
✅ Azure-managed identity lifecycle
```

## Related Documentation

- [Azure Managed Identity](https://docs.microsoft.com/en-us/azure/active-directory/managed-identities-azure-resources/)
- [GitHub OIDC with Azure](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-azure)
- [Federated Identity Credentials](https://docs.microsoft.com/en-us/azure/active-directory/develop/workload-identity-federation)

---
*Updated: August 22, 2025 - Migrated to Azure Managed Identity with OIDC (zero stored credentials)*
