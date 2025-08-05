# Key Vault Integration Guide

**Created:** August 5, 2025  
**Last Updated:** August 5, 2025

## Overview

The AI Content Farm project uses Azure Key Vault for secure secrets management, replacing direct GitHub secrets for sensitive configuration. This provides centralized secret management, enhanced security practices, and audit compliance.

## 🔐 Architecture Changes

### Key Vault Integration
- **Azure Key Vault**: Centralized secret storage for each environment
- **Access Policies**: Function Apps can read secrets, deployments can manage secrets
- **Diagnostic Logging**: Full audit trail of Key Vault access (resolves HIGH security finding)
- **Environment Isolation**: Separate Key Vaults for dev/staging/production

### Secret Management Strategy
```
GitHub Secrets (Authentication) → Azure Key Vault (Application Secrets)
├── ARM_CLIENT_ID              → reddit-client-id
├── ARM_CLIENT_SECRET          → reddit-client-secret  
├── ARM_SUBSCRIPTION_ID        → reddit-user-agent
├── ARM_TENANT_ID              → infracost-api-key
└── AZURE_CREDENTIALS          
```

## 🚀 Quick Setup

### 1. Deploy Infrastructure
```bash
# Deploy with Key Vault integration
cd infra
terraform init
terraform plan -var-file="staging.tfvars"
terraform apply -var-file="staging.tfvars"
```

### 2. Configure Secrets
```bash
# Interactive secret setup
make setup-keyvault

# Or manually set secrets
az keyvault secret set --vault-name "your-keyvault" --name "reddit-client-id" --value "your-value"
```

### 3. Validate Integration
```bash
# Test secret retrieval
make get-secrets
make validate-secrets
```

## 📋 Environment Configuration

### Development Environment
```bash
# infra/development.tfvars
environment = "dev"
location = "East US"
reddit_client_id = ""  # Set via Key Vault
reddit_client_secret = ""  # Set via Key Vault
reddit_user_agent = "ai-content-farm:v1.0-dev"
```

### Staging Environment
```bash
# infra/staging.tfvars
environment = "staging"
location = "East US"
reddit_client_id = ""  # Set via Key Vault
reddit_client_secret = ""  # Set via Key Vault
reddit_user_agent = "ai-content-farm:v1.0-staging"
```

### Production Environment
```bash
# infra/production.tfvars
environment = "production"
location = "East US"
reddit_client_id = ""  # Set via Key Vault
reddit_client_secret = ""  # Set via Key Vault
reddit_user_agent = "ai-content-farm:v1.0"
```

## 🔑 Secret Management

### Key Vault Secrets
All secrets include:
- **Content Type**: `text/plain` for compliance
- **Expiration Date**: 1 year from creation (automatic rotation capability)
- **Tags**: Environment and purpose identification
- **Access Policies**: Least privilege access

#### Reddit API Secrets
- `reddit-client-id`: Reddit application client ID
- `reddit-client-secret`: Reddit application client secret
- `reddit-user-agent`: User agent string for API requests

#### CI/CD Secrets
- `infracost-api-key`: Cost estimation API key for infrastructure analysis

### Quick Setup Commands
```bash
# Setup all secrets interactively
make setup-keyvault

# Setup Infracost API key specifically
make setup-infracost

# Test cost estimation with Key Vault integration
make cost-estimate
```

## 💰 Infracost Integration

### Getting Started (Before Infrastructure Deployment)

If you haven't deployed infrastructure yet, you can use environment variables:

```bash
# 1. Get your Infracost API key from https://dashboard.infracost.io
# 2. Set it as environment variable
export INFRACOST_API_KEY=your-api-key-here

# 3. Run cost estimation
make cost-estimate

# 4. Deploy infrastructure
make deploy-staging

# 5. Store key in Key Vault for future use
make setup-infracost
```

### Key Vault Integration (After Infrastructure Deployment)

Once your infrastructure is deployed, the system automatically uses Key Vault:

```bash
# Store Infracost API key in Key Vault
make setup-infracost

# Cost estimation now automatically uses Key Vault
make cost-estimate
```

### Cost Estimation Workflow
```bash
# Option 1: Setup Infracost key specifically
make setup-infracost

# Option 2: Setup all secrets (includes Infracost)
make setup-keyvault

# Run cost estimation (automatically uses Key Vault)
make cost-estimate
```

### Local Development
The Makefile automatically retrieves the Infracost API key from Key Vault:
1. **Environment Detection**: Uses `ENVIRONMENT` variable (defaults to staging)
2. **Key Vault Discovery**: Finds Key Vault in resource group
3. **Secret Retrieval**: Gets `infracost-api-key` secret
4. **Fallback Handling**: Falls back to environment variable if Key Vault unavailable

### CI/CD Integration
GitHub Actions workflows automatically retrieve Infracost API key:
- **Primary**: Key Vault secret retrieval
- **Fallback**: GitHub secret `INFRACOST_API_KEY`
- **Security**: No hardcoded credentials
- **Function Apps**: Read-only access to secrets
- **Deployment Pipelines**: Full secret management access
- **Developers**: No direct Key Vault access (use setup scripts)

## 🔧 CI/CD Integration

### GitHub Actions Workflow
The CI/CD pipeline automatically retrieves secrets from Key Vault:

```yaml
- name: Get secrets from Key Vault
  run: |
    # Discover Key Vault for environment
    KEYVAULT_NAME=$(az keyvault list --resource-group "ai-content-farm-${{ env.ENVIRONMENT }}" --query "[0].name" -o tsv)
    
    # Retrieve secrets with fallback to GitHub secrets
    REDDIT_CLIENT_ID=$(az keyvault secret show --vault-name "$KEYVAULT_NAME" --name "reddit-client-id" --query "value" -o tsv 2>/dev/null || echo "${{ secrets.REDDIT_CLIENT_ID }}")
```

### Secret Fallback Strategy
1. **Primary**: Azure Key Vault (environment-specific)
2. **Fallback**: GitHub Secrets (for reliability)
3. **Local**: Environment variables (development only)

## 🛡️ Security Features

### Compliance & Auditing
- **Diagnostic Logging**: All Key Vault access logged to Azure Monitor
- **Access Policies**: Granular permissions for different roles
- **Secret Rotation**: Built-in expiration and rotation capabilities
- **Environment Isolation**: Separate Key Vaults prevent cross-environment access

### Security Scanning Results
- **Checkov**: All 23 checks passing ✅
- **TFSec**: Infrastructure security validated ✅
- **Terrascan**: Policy compliance verified ✅
- **Key Vault Logging**: HIGH severity issue resolved ✅

### Best Practices Implemented
- Content type specification for all secrets
- Expiration dates for automatic rotation
- Least privilege access policies
- Comprehensive audit logging
- Environment-specific isolation

## 🔄 Secret Rotation Workflow

### Automated Rotation
1. **Expiration Monitoring**: Secrets expire after 1 year
2. **Notification**: Azure Monitor alerts before expiration
3. **Rotation Process**: Update secrets via setup script or Azure portal
4. **Validation**: Automated testing confirms new secrets work

### Manual Rotation
```bash
# Update specific secret
az keyvault secret set --vault-name "your-keyvault" \
  --name "reddit-client-id" \
  --value "new-value" \
  --expires "2026-08-05T00:00:00Z"

# Validate updated secret
make validate-secrets
```

## 🛠️ Management Tools

### Setup Script (`scripts/setup-keyvault.sh`)
Interactive script for configuring Key Vault secrets:
```bash
# Make executable and run
chmod +x scripts/setup-keyvault.sh
./scripts/setup-keyvault.sh
```

Features:
- Environment selection (dev/staging/production)
- Automatic Key Vault discovery
- Interactive secret prompts
- Validation and confirmation
- Error handling and rollback

### Makefile Targets
```bash
# Setup and configure Key Vault secrets
make setup-keyvault

# Retrieve and display current secrets
make get-secrets

# Validate secret accessibility
make validate-secrets

# Deploy infrastructure with Key Vault
make deploy-staging
make deploy-production
```

## 📊 Monitoring & Troubleshooting

### Key Vault Diagnostics
Monitor Key Vault access through Azure Monitor:
- **Audit Logs**: Who accessed what secrets when
- **Performance Metrics**: Response times and availability
- **Security Alerts**: Unusual access patterns
- **Compliance Reports**: Access audit trails

### Common Issues & Solutions

#### Secret Not Found
```bash
# Check Key Vault name and secret existence
az keyvault secret list --vault-name "your-keyvault"
az keyvault secret show --vault-name "your-keyvault" --name "secret-name"
```

#### Access Denied
```bash
# Verify access policy
az keyvault show --name "your-keyvault" --query "properties.accessPolicies"

# Check user permissions
az ad signed-in-user show --query "userPrincipalName"
```

#### Function App Can't Access Secrets
```bash
# Verify Function App managed identity
az functionapp identity show --name "your-function-app" --resource-group "your-rg"

# Check Key Vault access policy for Function App
az keyvault access-policy list --name "your-keyvault"
```

## 🚀 Production Deployment

### Pre-Deployment Checklist
- [ ] Reddit API credentials obtained
- [ ] Infracost API key configured
- [ ] Environment-specific tfvars file created
- [ ] Azure CLI authenticated
- [ ] Terraform initialized

### Deployment Steps
1. **Infrastructure**: `terraform apply -var-file="production.tfvars"`
2. **Secrets**: `make setup-keyvault`
3. **Validation**: `make validate-secrets`
4. **Function Deployment**: GitHub Actions pipeline
5. **Testing**: Verify end-to-end functionality

### Post-Deployment Verification
```bash
# Test Function App secret access
az functionapp config appsettings list --name "your-function-app" --resource-group "your-rg"

# Verify Key Vault logging
az monitor diagnostic-settings list --resource "your-keyvault-resource-id"

# Test secret retrieval in function
# (Function logs should show successful secret access)
```

This Key Vault integration provides enterprise-grade secret management with security, compliance, and operational excellence.
