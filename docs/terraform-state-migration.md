# Terraform State Migration Guide

**Created:** August 7, 2025  
**Status:** CRITICAL - Needs Implementation

## Current State Management Issues

### ❌ **Bootstrap Infrastructure**
- **Current**: Using local state (`terraform.tfstate` in bootstrap directory)
- **Problem**: If local state is lost, can't manage the storage account that holds all other state
- **Risk**: Single point of failure for entire infrastructure

### ⚠️ **Application Infrastructure** 
- **Current**: Has empty backend configuration, likely using local state
- **Problem**: Not using the remote state storage account that bootstrap created
- **Risk**: State not shared, can't deploy from different machines/CI

## Required Migration Steps

### **Phase 1: Fix Bootstrap State (HIGH PRIORITY)**

#### **Step 1: Verify Current Bootstrap State**
```bash
cd infra/bootstrap
terraform state list
# Should show all bootstrap resources including storage account
```

#### **Step 2: Get Storage Account Name**
```bash
# Get the actual storage account name from current state
terraform output storage_account_name
# Update backend.hcl with the actual name
```

#### **Step 3: Migrate Bootstrap to Remote State**
```bash
# Initialize with backend configuration
terraform init -backend-config=backend.hcl

# This will prompt to migrate existing state to remote backend
# Answer "yes" when prompted
```

#### **Step 4: Verify Migration**
```bash
# Verify state is now remote
terraform state list
# Should work and show same resources

# Verify local state is gone
ls terraform.tfstate*
# Should show backup files only
```

### **Phase 2: Fix Application State**

#### **Step 1: Update Backend Config**
```bash
cd infra/application

# Update backend-staging.hcl with correct storage account name
# (Get from bootstrap output)
```

#### **Step 2: Initialize with Remote Backend**
```bash
# For staging
terraform init -backend-config=backend-staging.hcl

# For production  
terraform init -backend-config=backend-production.hcl
```

## Updated Deployment Process

### **Bootstrap Deployment (One-time)**
```bash
cd infra/bootstrap

# 1. Initial deployment with local state
terraform init
terraform apply

# 2. Get storage account name
STORAGE_ACCOUNT=$(terraform output -raw storage_account_name)

# 3. Update backend.hcl with actual storage account name
sed -i "s/aicontentfarm76ko2h/$STORAGE_ACCOUNT/g" backend.hcl

# 4. Migrate to remote state
terraform init -backend-config=backend.hcl
# Answer "yes" to migrate state

# 5. Verify remote state works
terraform state list
```

### **Application Deployment (Per Environment)**
```bash
cd infra/application

# 1. Get storage account name from bootstrap
STORAGE_ACCOUNT=$(cd ../bootstrap && terraform output -raw storage_account_name)

# 2. Update backend config for environment
sed -i "s/aicontentfarm76ko2h/$STORAGE_ACCOUNT/g" backend-staging.hcl

# 3. Initialize with remote backend
terraform init -backend-config=backend-staging.hcl

# 4. Deploy
terraform apply -var-file=staging.tfvars
```

## Benefits After Migration

### 🔒 **Improved Reliability**
- No single point of failure
- State is backed up in Azure Storage (with versioning)
- Can recover from any machine with proper credentials

### 👥 **Team Collaboration** 
- Multiple developers can work on same infrastructure
- CI/CD can deploy from clean environments
- No state conflicts or overwrites

### 🔄 **Proper State Locking**
- Azure Storage provides state locking
- Prevents concurrent modifications
- Safer terraform operations

## Validation Checklist

After migration, verify:

- [ ] Bootstrap state is in Azure Storage (`bootstrap.tfstate`)
- [ ] Application state is in Azure Storage (`staging.tfstate`, `production.tfstate`)  
- [ ] No local `terraform.tfstate` files in directories
- [ ] `terraform state list` works from any clean checkout
- [ ] CI/CD can deploy without existing local state

## Risk Mitigation

### **Before Migration**
```bash
# Backup current state files
cp infra/bootstrap/terraform.tfstate infra/bootstrap/terraform.tfstate.backup.$(date +%Y%m%d)
cp infra/application/terraform.tfstate infra/application/terraform.tfstate.backup.$(date +%Y%m%d)
```

### **Emergency Recovery**
If migration fails, restore from backup:
```bash
cp terraform.tfstate.backup.YYYYMMDD terraform.tfstate
terraform init -backend=false
```

---

**⚠️ This migration should be done BEFORE making the key vault separation changes in production!**
