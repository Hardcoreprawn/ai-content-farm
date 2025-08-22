# Migration Guide: Service Principal → Managed Identity + OIDC

This guide documents the migration from legacy service principal authentication to modern Azure Managed Identity with OIDC for GitHub Actions.

## 🎯 Security Upgrade Overview

### Before: Service Principal + Client Secret
```bash
❌ Long-lived client secrets stored in GitHub
❌ Manual credential rotation every 2 years
❌ Risk of credential exposure in logs/storage
❌ Complex secret lifecycle management
❌ Shared credentials across environments
```

### After: Managed Identity + OIDC
```bash
✅ Zero stored credentials anywhere
✅ Automatic token rotation (15-minute expiry)
✅ No credential exposure risk
✅ Azure-managed identity lifecycle
✅ Environment-specific scoped access
```

## 🔄 Migration Process

### Automated Migration (Recommended)
```bash
# Run the automated setup script
./scripts/setup-oidc.sh
```

This script will:
1. Deploy managed identity via Terraform
2. Configure federated identity credentials
3. Set GitHub repository variables
4. Clean up legacy secrets
5. Verify the configuration

### Manual Migration Steps

#### 1. Deploy Infrastructure Updates
```bash
cd infra
terraform init
terraform apply
```

The infrastructure now includes:
- `azurerm_user_assigned_identity.github_actions` - Managed identity for CI/CD
- `azurerm_federated_identity_credential.*` - Trust relationship with GitHub
- Role assignments for Contributor, ACR Push, Key Vault access

#### 2. Configure GitHub Repository Variables
Replace secrets with public variables from Terraform outputs:

```bash
# Get values from Terraform
CLIENT_ID=$(terraform output -raw github_actions_client_id)
TENANT_ID=$(terraform output -raw tenant_id)
SUBSCRIPTION_ID=$(terraform output -raw subscription_id)

# Set as repository variables (NOT secrets)
gh variable set AZURE_CLIENT_ID --body "$CLIENT_ID"
gh variable set AZURE_TENANT_ID --body "$TENANT_ID" 
gh variable set AZURE_SUBSCRIPTION_ID --body "$SUBSCRIPTION_ID"
```

#### 3. Remove Legacy Secrets
Delete these GitHub secrets (no longer needed):
- `AZURE_CLIENT_SECRET`
- `AZURE_CREDENTIALS`
- `ARM_CLIENT_ID`
- `ARM_CLIENT_SECRET`
- `ARM_SUBSCRIPTION_ID`
- `ARM_TENANT_ID`

```bash
# Clean up legacy secrets
gh secret delete AZURE_CLIENT_SECRET
gh secret delete AZURE_CREDENTIALS
# ... etc
```

#### 4. Update Workflows
Workflows now use repository variables instead of secrets:

```yaml
# Before
with:
  client-id: ${{ secrets.AZURE_CLIENT_ID }}

# After  
with:
  client-id: ${{ vars.AZURE_CLIENT_ID }}
```

## 🏗️ Technical Implementation

### Federated Identity Credentials
The Terraform creates these trust relationships:

```hcl
# Main branch production deployments
resource "azurerm_federated_identity_credential" "github_main" {
  subject = "repo:Hardcoreprawn/ai-content-farm:ref:refs/heads/main"
}

# Develop branch staging deployments
resource "azurerm_federated_identity_credential" "github_develop" {
  subject = "repo:Hardcoreprawn/ai-content-farm:ref:refs/heads/develop"
}

# Pull request deployments
resource "azurerm_federated_identity_credential" "github_pr" {
  subject = "repo:Hardcoreprawn/ai-content-farm:pull_request"
}
```

### OIDC Token Flow
1. **GitHub Action starts** → GitHub generates short-lived OIDC token
2. **azure/login@v2** → Exchanges GitHub token for Azure access token
3. **Federated Identity** → Verifies repo/branch matches configured subject
4. **Managed Identity** → Grants scoped Azure permissions
5. **Resources accessed** → ACR, Key Vault, Resource Groups, etc.

### Permissions Model
The managed identity has these Azure permissions:
- **Subscription Contributor**: Deploy/manage resources
- **ACR Push**: Build and push container images  
- **Key Vault Secrets Officer**: Manage application secrets
- **Storage Blob Data Contributor**: Access blob storage

## 🔍 Verification Steps

### 1. Check Infrastructure
```bash
# Verify managed identity exists
az identity show --name "ai-content-farm-core-github-actions" \
  --resource-group "ai-content-farm-core-rg"

# Check federated credentials
az identity federated-credential list \
  --name "ai-content-farm-core-github-actions" \
  --resource-group "ai-content-farm-core-rg"
```

### 2. Verify GitHub Configuration
```bash
# Check repository variables are set
gh variable list

# Verify no legacy secrets remain
gh secret list | grep -E "(AZURE_CLIENT_SECRET|AZURE_CREDENTIALS|ARM_)"
```

### 3. Test Authentication
```bash
# Trigger workflow by pushing to main
git push origin main

# Watch for successful OIDC login
# ✅ Azure Login via OIDC
# ✅ Token exchange successful  
# ✅ Deploy to Azure
```

## 🛠️ Troubleshooting

### Common Issues

#### "Failed to get federated token"
**Cause**: Repository/branch mismatch in federated credential subject

**Solution**: Verify these match exactly:
- Repository: `Hardcoreprawn/ai-content-farm`
- Branches: `main`, `develop`
- Pull requests: `pull_request`

#### "Invalid client_id"
**Cause**: GitHub variable not set or incorrect value

**Solution**: 
```bash
# Check current value
gh variable get AZURE_CLIENT_ID

# Reset from Terraform output
CLIENT_ID=$(terraform output -raw github_actions_client_id)
gh variable set AZURE_CLIENT_ID --body "$CLIENT_ID"
```

#### "Insufficient permissions"
**Cause**: Managed identity lacks required role assignments

**Solution**: Verify role assignments exist:
```bash
az role assignment list --assignee "$(terraform output -raw github_actions_principal_id)"
```

#### "Audience mismatch"
**Cause**: Incorrect audience in federated credential

**Solution**: Verify audience is `["api://AzureADTokenExchange"]`

## 📊 Security Improvements

### Attack Surface Reduction
- **Before**: Long-lived secrets in GitHub, risk of exposure
- **After**: No stored credentials, impossible to steal/leak

### Compliance Benefits
- **Audit Trail**: All authentication logged in Azure AD
- **Token Rotation**: Automatic every 15 minutes
- **Principle of Least Privilege**: Scoped to specific repos/branches
- **Zero Trust**: Cryptographic verification of GitHub identity

### Operational Benefits
- **No Secret Management**: No rotation, expiry, or lifecycle concerns
- **Environment Isolation**: Separate identities per environment
- **Fail Secure**: Tokens expire quickly if compromised
- **Centralized Control**: Manage access in Azure AD

## 📚 References

- [Azure Workload Identity Federation](https://docs.microsoft.com/en-us/azure/active-directory/develop/workload-identity-federation)
- [GitHub OIDC with Azure](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-azure)
- [Azure Managed Identities](https://docs.microsoft.com/en-us/azure/active-directory/managed-identities-azure-resources/)

---
*Updated: August 22, 2025 - Completed migration to managed identity with OIDC*
