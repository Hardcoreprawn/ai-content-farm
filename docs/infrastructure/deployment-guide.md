# Deployment Guide

**Created:** August 5, 2025  
**Last Updated:** August 5, 2025

This guide explains how to safely deploy changes to staging and production environments using the security-first pipeline with Azure Key Vault integration.

## 🚀 Quick Start

### For Development
```bash
# Make changes to your code
git add .
git commit -m "Your change description"

# Test everything locally
make verify

# Push to feature branch for staging deployment
git push origin feature/your-feature-name
```

### For Production
```bash
# Ensure you're on main branch
git checkout main
git merge develop

# Final verification
make security-scan

# Push to trigger production pipeline (requires manual approval)
git push origin main
```

## 🌍 Environment Strategy

### Development (Local)
- **Purpose**: Local testing and development
- **Security**: Basic validation
- **Branch**: Any branch
- **Command**: `make verify`
- **Secrets**: Environment variables or local Key Vault

### Staging
- **Purpose**: Integration testing and validation
- **Security**: Comprehensive scanning with Key Vault integration
- **Branches**: `develop`, `feature/*`
- **URL**: `https://ai-content-staging-func.azurewebsites.net`
- **Auto-Deploy**: Yes (after security validation)
- **Key Vault**: Staging environment Key Vault

### Production
- **Purpose**: Live system
- **Security**: Strict validation with full audit logging
- **Branch**: `main` only
- **URL**: `https://ai-content-prod-func.azurewebsites.net`
- **Auto-Deploy**: Manual approval required
- **Key Vault**: Production environment Key Vault

## 🔐 Security Pipeline

### Pre-Deployment Security Checks
1. **Checkov**: Infrastructure security scanning
2. **Trivy**: Infrastructure security validation
3. **Terrascan**: Policy compliance verification
4. **SBOM Generation**: Software Bill of Materials
5. **Cost Analysis**: Infracost deployment impact
6. **Key Vault Validation**: Secret accessibility testing

### Security Score Requirements
- **Staging**: Security warnings allowed (monitoring)
- **Production**: Zero HIGH severity issues required

### Current Security Status
- ✅ **Checkov**: 23/23 checks passing
- ✅ **Trivy**: No critical issues
- ✅ **Terrascan**: Compliance verified
- ✅ **Key Vault**: Audit logging enabled

## 📋 Deployment Process

### 1. Pre-Deployment Setup

#### First-Time Setup
```bash
# Configure Azure CLI
az login
az account set --subscription "your-subscription-id"

# Setup Terraform
cd infra
terraform init

# Configure Key Vault secrets
make setup-keyvault
```

#### Environment Configuration
Create environment-specific variable files:
- `infra/development.tfvars`
- `infra/staging.tfvars`
- `infra/production.tfvars`

### 2. Staging Deployment

#### Automatic Deployment (Recommended)
```bash
# Push to develop or feature branch
git checkout develop
git push origin develop
```

#### Manual Deployment
```bash
# Deploy infrastructure
cd infra
terraform plan -var-file="staging.tfvars"
terraform apply -var-file="staging.tfvars"

# Configure secrets
make setup-keyvault

# Deploy functions
cd ../functions
func azure functionapp publish ai-content-staging-func
```

### 3. Production Deployment

#### Automatic Deployment with Approval
```bash
# Merge to main (triggers approval workflow)
git checkout main
git merge develop
git push origin main

# Approve deployment in GitHub Actions UI
# Navigate to: Repository → Actions → Production Deployment → Review
```

#### Manual Production Deployment
```bash
# Deploy infrastructure
cd infra
terraform plan -var-file="production.tfvars"
terraform apply -var-file="production.tfvars"

# Configure production secrets
ENVIRONMENT=production make setup-keyvault

# Deploy functions
cd ../functions
func azure functionapp publish ai-content-prod-func
```

## 🔑 Key Vault Integration

### Secret Management in Deployment

#### CI/CD Secret Retrieval
The deployment pipeline automatically:
1. Authenticates to Azure using GitHub secrets
2. Discovers environment-specific Key Vault
3. Retrieves application secrets from Key Vault
4. Falls back to GitHub secrets if Key Vault unavailable

#### Secret Configuration
```bash
# Interactive secret setup for environment
./scripts/setup-keyvault.sh

# Manual secret configuration
az keyvault secret set --vault-name "your-keyvault" \
  --name "reddit-client-id" \
  --value "your-reddit-client-id" \
  --expires "2026-08-05T00:00:00Z"
```

### Environment-Specific Key Vaults
- **Development**: `ai-content-dev-kv-{suffix}`
- **Staging**: `ai-content-staging-kv-{suffix}`
- **Production**: `ai-content-prod-kv-{suffix}`

## 🔍 Monitoring & Validation

### Post-Deployment Verification

#### Function App Health Check
```bash
# Test HTTP-triggered function
curl -X POST "https://your-function-app.azurewebsites.net/api/GetHotTopics" \
  -H "Content-Type: application/json" \
  -d '{"test": true}'
```

#### Key Vault Access Validation
```bash
# Verify function can access secrets
az functionapp config appsettings list \
  --name "your-function-app" \
  --resource-group "your-resource-group"

# Check Key Vault audit logs
az monitor activity-log list \
  --resource-group "your-resource-group" \
  --start-time "2025-08-05T00:00:00Z"
```

#### Security Monitoring
```bash
# Generate security report
make security-scan

# Check Key Vault diagnostic logs
az monitor diagnostic-settings list \
  --resource "/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.KeyVault/vaults/{kv}"
```

### Performance Monitoring
- **Application Insights**: Function execution metrics
- **Azure Monitor**: Resource utilization and alerts
- **Key Vault Diagnostics**: Secret access patterns and performance

## 🚨 Troubleshooting

### Common Deployment Issues

#### Key Vault Access Denied
```bash
# Check access policies
az keyvault show --name "your-keyvault" --query "properties.accessPolicies"

# Verify managed identity
az functionapp identity show --name "your-function-app" --resource-group "your-rg"

# Fix access policy
az keyvault set-policy --name "your-keyvault" \
  --object-id "function-app-identity-id" \
  --secret-permissions get list
```

#### Function Deployment Failure
```bash
# Check function app logs
az functionapp log tail --name "your-function-app" --resource-group "your-rg"

# Verify function app settings
az functionapp config appsettings list --name "your-function-app" --resource-group "your-rg"

# Redeploy with verbose logging
func azure functionapp publish your-function-app --verbose
```

#### Terraform State Issues
```bash
# Refresh state
terraform refresh -var-file="environment.tfvars"

# Import existing resources if needed
terraform import azurerm_resource_group.main /subscriptions/{sub}/resourceGroups/{rg}

# Force unlock if state is locked
terraform force-unlock {lock-id}
```

### Security Issue Resolution

#### Failed Security Scans
```bash
# Run specific security check
checkov -d infra --check CKV_AZURE_XXX

# Review and fix specific issues
# Update infrastructure code
# Re-run security validation
make security-scan
```

#### Secret Rotation Issues
```bash
# Update expired secrets
az keyvault secret set --vault-name "your-keyvault" \
  --name "secret-name" \
  --value "new-value" \
  --expires "2026-08-05T00:00:00Z"

# Restart function app to pick up new secrets
az functionapp restart --name "your-function-app" --resource-group "your-rg"
```

## 📊 Cost Management

### Deployment Cost Analysis
```bash
# Estimate infrastructure costs
make cost-estimate

# Review Infracost output
cat infra/infracost-report.json
```

### Cost Optimization
- **Function App**: Consumption plan for pay-per-execution
- **Storage**: Lifecycle policies for automatic tiering
- **Key Vault**: Standard tier for most workloads
- **Monitoring**: Configure appropriate retention policies

## 🔄 Rollback Procedures

### Quick Rollback (Production)
```bash
# Revert to previous Git commit
git revert HEAD
git push origin main

# Or rollback to specific commit
git reset --hard {previous-commit-hash}
git push --force origin main
```

### Infrastructure Rollback
```bash
# Revert Terraform changes
git checkout {previous-infrastructure-commit}
cd infra
terraform plan -var-file="production.tfvars"
terraform apply -var-file="production.tfvars"
```

### Function-Only Rollback
```bash
# Deploy previous function version
git checkout {previous-function-commit}
cd functions
func azure functionapp publish your-function-app
```

## 📋 Deployment Checklist

### Pre-Deployment
- [ ] Code changes tested locally
- [ ] Security scan passing (make security-scan)
- [ ] Environment variables configured
- [ ] Key Vault secrets updated if needed
- [ ] Terraform plan reviewed
- [ ] Cost impact assessed

### During Deployment
- [ ] Monitor deployment logs
- [ ] Verify Key Vault access
- [ ] Test function endpoints
- [ ] Check Application Insights
- [ ] Validate security monitoring

### Post-Deployment
- [ ] End-to-end functional testing
- [ ] Performance monitoring review
- [ ] Security audit log verification
- [ ] Documentation updates
- [ ] Stakeholder notification

This deployment guide ensures secure, reliable deployments with comprehensive monitoring and quick recovery procedures.
