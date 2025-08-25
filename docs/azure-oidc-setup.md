# Azure OIDC Authentication Setup for Production Deployment

## Overview
This document outlines the complete setup for secretless Azure authentication using OpenID Connect (OIDC) with managed identity for production deployments.

## Current Status
- ✅ GitHub Actions configured with OIDC permissions
- ✅ Azure variables configured in GitHub repository
- ✅ Azure login action using OIDC in pipeline
- ✅ Azure App Registration created and configured
- ✅ Federated identity credentials configured for all environments
- ✅ RBAC permissions assigned for production deployment
- ✅ Legacy secrets removed (secretless authentication)

## Required Azure Configuration

### 1. Azure App Registration Setup

The app registration (Client ID: 518704f2-75a6-4b7c-8ca4-d2bac366ecc5) should have:

```bash
# Verify the app registration exists and has proper configuration
az ad app show --id 518704f2-75a6-4b7c-8ca4-d2bac366ecc5 --query "{displayName:displayName, appId:appId}"
```

### 2. Federated Identity Credentials

Configure federated credentials for GitHub Actions OIDC:

```bash
# Create federated credential for main branch (production)
az ad app federated-credential create \
  --id 518704f2-75a6-4b7c-8ca4-d2bac366ecc5 \
  --parameters @- << EOF
{
  "name": "github-main-branch",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:Hardcoreprawn/ai-content-farm:ref:refs/heads/main",
  "description": "GitHub Actions OIDC for main branch production deployments",
  "audiences": ["api://AzureADTokenExchange"]
}
EOF

# Create federated credential for develop branch (staging)
az ad app federated-credential create \
  --id 518704f2-75a6-4b7c-8ca4-d2bac366ecc5 \
  --parameters @- << EOF
{
  "name": "github-develop-branch",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:Hardcoreprawn/ai-content-farm:ref:refs/heads/develop",
  "description": "GitHub Actions OIDC for develop branch staging deployments",
  "audiences": ["api://AzureADTokenExchange"]
}
EOF

# Create federated credential for pull requests
az ad app federated-credential create \
  --id 518704f2-75a6-4b7c-8ca4-d2bac366ecc5 \
  --parameters @- << EOF
{
  "name": "github-pull-requests",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:Hardcoreprawn/ai-content-farm:pull_request",
  "description": "GitHub Actions OIDC for pull request testing",
  "audiences": ["api://AzureADTokenExchange"]
}
EOF
```

### 3. Service Principal and RBAC Permissions

```bash
# Get or create service principal for the app registration
SP_OBJECT_ID=$(az ad sp show --id 518704f2-75a6-4b7c-8ca4-d2bac366ecc5 --query objectId -o tsv 2>/dev/null)

if [ -z "$SP_OBJECT_ID" ]; then
  echo "Creating service principal..."
  az ad sp create --id 518704f2-75a6-4b7c-8ca4-d2bac366ecc5
  SP_OBJECT_ID=$(az ad sp show --id 518704f2-75a6-4b7c-8ca4-d2bac366ecc5 --query objectId -o tsv)
fi

# Assign necessary roles for production deployment
SUBSCRIPTION_ID="6b924609-f8c6-4bd2-a873-2b8f55596f67"

# Contributor role for resource management
az role assignment create \
  --assignee-object-id "$SP_OBJECT_ID" \
  --role "Contributor" \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/ai-content-farm-core-rg"

# AcrPush role for container registry
az role assignment create \
  --assignee-object-id "$SP_OBJECT_ID" \
  --role "AcrPush" \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/ai-content-farm-core-rg/providers/Microsoft.ContainerRegistry/registries/aicontentfarm76ko2hacr"

# Key Vault Secrets Officer for secret management
az role assignment create \
  --assignee-object-id "$SP_OBJECT_ID" \
  --role "Key Vault Secrets Officer" \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/ai-content-farm-core-rg/providers/Microsoft.KeyVault/vaults/ai-content-production-kv"
```

### 4. GitHub Repository Security Configuration

#### Remove Legacy Secrets
Since you're using OIDC, you can remove the Azure secrets (but keep the API keys):

```bash
# Remove Azure authentication secrets (keep INFRACOST_API_KEY)
gh secret delete AZURE_CLIENT_ID
gh secret delete AZURE_SUBSCRIPTION_ID  
gh secret delete AZURE_TENANT_ID
```

#### Configure Environment Protection
Set up production environment protection:

```bash
# This needs to be done via GitHub UI at:
# https://github.com/Hardcoreprawn/ai-content-farm/settings/environments
```

Required protection rules for production environment:
- **Required reviewers**: Add yourself as a required reviewer
- **Wait timer**: 0 minutes (optional)
- **Deployment branches**: Only `main` branch
- **Environment secrets**: None needed (using OIDC)

### 5. Terraform Backend Authentication

Ensure your Terraform state storage account also supports OIDC:

```bash
# Assign Storage Blob Data Contributor for Terraform state
az role assignment create \
  --assignee-object-id "$SP_OBJECT_ID" \
  --role "Storage Blob Data Contributor" \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/ai-content-farm-core-rg/providers/Microsoft.Storage/storageAccounts/aicontentstagingstv33ppo"
```

## Validation Steps

### 1. Test OIDC Authentication

```bash
# Test the federated credential by running a simple Azure CLI command in Actions
# This will be tested automatically in the next pipeline run
```

### 2. Verify Permissions

```bash
# Verify the service principal has the required permissions
az role assignment list \
  --assignee 518704f2-75a6-4b7c-8ca4-d2bac366ecc5 \
  --output table
```

### 3. Test Production Deployment

Create a small test change and push to main branch to validate the full pipeline.

## Security Benefits

1. **No Long-lived Secrets**: No client secrets stored in GitHub
2. **Just-in-time Authentication**: Tokens are short-lived and scoped
3. **Auditable**: All authentication requests are logged in Azure AD
4. **Principle of Least Privilege**: Scoped permissions per resource
5. **Environment Separation**: Different credentials for different environments

## Troubleshooting

### Common Issues and Solutions

1. **"AADSTS70021: No matching federated identity record found"**
   - Verify the subject claim matches exactly: `repo:Hardcoreprawn/ai-content-farm:ref:refs/heads/main`
   - Check that the audience is set to `api://AzureADTokenExchange`

2. **"Insufficient privileges to complete the operation"**
   - Verify RBAC permissions are assigned to the service principal
   - Check that the correct resource scopes are used

3. **"The subscription is not registered to use namespace"**
   - Register required resource providers: `az provider register --namespace Microsoft.ContainerService`

### Useful Commands for Debugging

```bash
# Check federated credentials
az ad app federated-credential list --id 518704f2-75a6-4b7c-8ca4-d2bac366ecc5

# Check role assignments
az role assignment list --assignee 518704f2-75a6-4b7c-8ca4-d2bac366ecc5 --output table

# Test authentication (run in GitHub Actions)
az account show
az group list --query "[].name" -o table
```

## Next Steps

1. Execute the Azure configuration commands above
2. Remove legacy GitHub secrets
3. Configure production environment protection
4. Test with a small change to main branch
5. Monitor the deployment for any authentication issues

---
*Last updated: August 25, 2025 - Initial OIDC setup documentation*

## ✅ COMPLETED CONFIGURATION

### Azure App Registration
- **App Name**: `ai-content-farm-github-actions`
- **Client ID**: `effa0588-70ae-4781-b214-20c726f3867e`
- **Tenant ID**: `d1790d70-c02c-4e8e-94ee-e3ccbdb19d19`
- **Subscription ID**: `6b924609-f8c6-4bd2-a873-2b8f55596f67`

### Federated Identity Credentials
Three federated credentials configured for GitHub Actions OIDC:
1. **github-main-branch**: `repo:Hardcoreprawn/ai-content-farm:ref:refs/heads/main`
2. **github-develop-branch**: `repo:Hardcoreprawn/ai-content-farm:ref:refs/heads/develop`
3. **github-pull-requests**: `repo:Hardcoreprawn/ai-content-farm:pull_request`

### Service Principal Permissions
The following RBAC permissions have been assigned:
- **Contributor** on `ai-content-farm-core-rg` (resource management)
- **Key Vault Secrets Officer** on `ai-content-farm-core-kv` (secret management)
- **AcrPush** on `cabb7a9aad51acr` (container registry operations)
- **Storage Blob Data Contributor** on `aicontentstagingstv33ppo` (Terraform state)

### GitHub Configuration
- **Repository Variables**: All Azure identifiers stored as variables (not secrets)
- **Secrets Cleaned**: Removed all Azure authentication secrets
- **Remaining Secrets**: Only `INFRACOST_API_KEY` remains (required for cost analysis)

### Validation
- ✅ App registration exists and is properly configured
- ✅ Service principal has all required permissions
- ✅ Federated credentials cover all workflow scenarios
- ✅ GitHub variables are correctly set
- ✅ Legacy secrets have been removed

**The Azure OIDC authentication is now fully configured and ready for production deployment.**
