# Key Vault Separation Architecture

**Created:** August 7, 2025  
**Status:** Implemented

## Overview

The AI Content Farm project now uses a **separated key vault architecture** that properly isolates CI/CD concerns from application runtime concerns. This improves security, follows the principle of least privilege, and simplifies infrastructure management.

## Architecture

### 🏗️ **Two-Vault Design**

#### **1. CI/CD Key Vault** (`ai-content-cicd-kv{suffix}`)
- **Location**: Bootstrap resource group (`ai-content-farm-bootstrap`)
- **Purpose**: Store CI/CD pipeline secrets only
- **Secrets**: 
  - `infracost-api-key` - For cost estimation in GitHub Actions
- **Access**: 
  - ✅ GitHub Actions service principal (Get, List)
  - ✅ Bootstrap admin (Full access for setup)
- **Lifecycle**: Managed with bootstrap Terraform

#### **2. Application Key Vault** (`{prefix}appkv{suffix}`)
- **Location**: Application resource group (`{prefix}-rg`)
- **Purpose**: Store application runtime secrets only
- **Secrets**:
  - `reddit-client-id` - Reddit API credentials
  - `reddit-client-secret` - Reddit API credentials  
  - `reddit-user-agent` - Reddit API user agent
- **Access**:
  - ✅ Function App managed identity (Get, List)
  - ✅ Application admin (Full access for setup)
  - ❌ GitHub Actions (NO ACCESS)
- **Lifecycle**: Managed with application Terraform

## Benefits

### 🔒 **Security Improvements**
- **Principle of Least Privilege**: Each component only accesses secrets it needs
- **Reduced Blast Radius**: Compromise of one component doesn't expose all secrets
- **Clear Audit Trail**: Separate logging and monitoring per concern
- **No Cross-Contamination**: CI/CD can't access app secrets, apps can't access CI/CD secrets

### 🏗️ **Architecture Improvements**
- **Separation of Concerns**: Clear boundary between deployment and runtime
- **Independent Lifecycles**: Bootstrap and application deployments are decoupled
- **Simplified Dependencies**: No more remote state lookups between bootstrap and application
- **Easier Testing**: Can test application infrastructure without bootstrap dependencies

### 💰 **Cost Impact**
- **Negligible**: ~$0.02/year additional cost per environment
- **Well Worth It**: Security benefits far outweigh minimal cost

## Migration from Previous Architecture

### **What Changed**

#### **Bootstrap Infrastructure** (`/infra/bootstrap/`)
- ✅ **Added**: CI/CD Key Vault with Infracost API key
- ✅ **Added**: GitHub Actions access policy for CI/CD vault
- ✅ **Added**: Outputs for CI/CD vault information

#### **Application Infrastructure** (`/infra/application/`)
- ✅ **Removed**: GitHub Actions access policy from application vault
- ✅ **Removed**: `infracost-api-key` secret from application vault
- ✅ **Removed**: Bootstrap remote state dependency
- ✅ **Updated**: Application vault naming to include 'app' identifier
- ✅ **Simplified**: Secret dependencies (no more GitHub Actions references)

#### **GitHub Actions Workflow** (`.github/workflows/`)
- ✅ **Updated**: Now looks for CI/CD vault in bootstrap resource group
- ✅ **Improved**: Better error handling and logging
- ✅ **Simplified**: No more searching multiple resource groups

#### **Setup Scripts** (`scripts/setup-keyvault.sh`)
- ✅ **Enhanced**: Handles both application and CI/CD vaults
- ✅ **Improved**: Clear separation of secret types
- ✅ **Better UX**: Shows which vault each secret goes to

## Usage

### **Deploy Infrastructure**
```bash
# 1. Deploy bootstrap (includes CI/CD vault)
cd infra/bootstrap
terraform apply

# 2. Deploy application (includes application vault)
cd ../application
terraform apply
```

### **Configure Secrets**
```bash
# Interactive setup for both vaults
make setup-keyvault

# Manual setup
# Application secrets (in application vault)
az keyvault secret set --vault-name "{app-vault}" --name "reddit-client-id" --value "your-id"

# CI/CD secrets (in CI/CD vault)  
az keyvault secret set --vault-name "{cicd-vault}" --name "infracost-api-key" --value "your-key"
```

### **Verify Setup**
```bash
# Check application vault
az keyvault secret list --vault-name "{app-vault}"

# Check CI/CD vault
az keyvault secret list --vault-name "{cicd-vault}"
```

## Troubleshooting

### **GitHub Actions Can't Access CI/CD Vault**
- Verify bootstrap infrastructure is deployed
- Check GitHub Actions service principal has access policy
- Ensure CI/CD vault exists in bootstrap resource group

### **Function App Can't Access Application Secrets**
- Verify application infrastructure is deployed
- Check Function App managed identity has access policy
- Ensure application vault exists in application resource group

### **Setup Script Can't Find Vaults**
- Deploy infrastructure first: `make apply`
- Check resource group names match environment
- Verify you're logged into correct Azure subscription

## Files Modified

- `/infra/bootstrap/main.tf` - Added CI/CD Key Vault
- `/infra/bootstrap/outputs.tf` - Added CI/CD vault outputs
- `/infra/application/main.tf` - Removed GitHub Actions access, updated naming
- `/infra/application/variables.tf` - Added GitHub Actions client ID variable
- `/infra/application/outputs.tf` - Removed bootstrap dependency
- `/.github/workflows/consolidated-pipeline.yml` - Updated vault discovery
- `/scripts/setup-keyvault.sh` - Enhanced for dual-vault setup

---

This separation provides a robust, secure, and maintainable foundation for the AI Content Farm project's secret management.
