# Security Alert Cleanup Plan - 29 Issues to Resolve

## 📊 **Current State**
- **Total Open Alerts**: 29
- **Critical (Error)**: 13 🔴
- **Medium (Warning)**: 15 🟡  
- **Low (Note)**: 1 🟢

## 🎯 **Priority Fix Strategy**

### **Phase 1: Quick Wins (Low Effort, High Impact)**

#### **A. Information Exposure (3 CodeQL errors)**
**Issue**: Exception details exposed in error responses
**Files**: 
- `containers/site-generator/storage_queue_router.py:203`
- `containers/content-collector/endpoints/storage_queue_router.py:134`  
- `containers/content-processor/endpoints/storage_queue_router.py:160`

**Fix**: Replace detailed exception messages with generic error responses
**Effort**: 15 minutes
**Impact**: Fixes 3 critical security vulnerabilities

#### **B. Shell Injection (1 Semgrep error)**
**Issue**: Potential shell injection in GitHub Actions
**File**: `.github/actions/sync-container-versions/action.yml:26`

**Fix**: Quote shell variables and use safer bash practices
**Effort**: 5 minutes  
**Impact**: Fixes CI/CD security vulnerability

### **Phase 2: Infrastructure Hardening (Medium Effort)**

#### **C. Key Vault Network ACL (1 Trivy error)**
**Issue**: Key vault lacks network access restrictions
**File**: `infra/main.tf:39`

**Fix**: Add network ACL block to key vault Terraform configuration
**Effort**: 10 minutes
**Impact**: Hardens infrastructure security

#### **D. Secret Expiration (Semgrep + checkov)**
**Issue**: Secrets without expiration dates
**Fix**: Add expiration policies to Azure Key Vault secrets
**Effort**: 20 minutes
**Impact**: Reduces long-term credential exposure risk

### **Phase 3: Comprehensive Cleanup (Remaining Issues)**

#### **E. Storage & Cognitive Services (checkov warnings)**
**Issues**: 
- Missing blob logging
- Public network access enabled
- Various Azure service hardening

**Fix**: Update Terraform configurations for Azure services
**Effort**: 30-45 minutes
**Impact**: Full infrastructure compliance

## 🚀 **Immediate Action Plan**

### **Step 1: Fix Critical Exceptions (15 min)**
Update all 3 storage queue routers to use generic error responses instead of exposing exception details.

### **Step 2: Fix Shell Injection (5 min)**  
Quote variables in GitHub Actions workflow to prevent injection.

### **Step 3: Harden Key Vault (10 min)**
Add network ACL to Key Vault Terraform configuration.

**Total Time for Critical Issues**: ~30 minutes
**Impact**: Fixes 5 of 13 critical errors

## 📋 **Implementation Order**
1. ✅ **Information Exposure** (3 files) - Immediate security risk
2. ✅ **Shell Injection** (1 file) - CI/CD security  
3. ✅ **Key Vault ACL** (1 file) - Infrastructure hardening
4. 🔄 **Secret Expiration** (multiple files) - Policy enforcement
5. 🔄 **Remaining Warnings** (11 issues) - Full compliance

## 💡 **Long-term Prevention**
- **Pre-commit hooks**: Block new security issues
- **Baseline exceptions**: Accept acceptable risks  
- **Regular reviews**: Monthly security alert cleanup

---
**Goal**: Reduce from 29 → 15 → 5 → 0 alerts over 3 focused sessions
**Priority**: Fix the 13 critical errors first, warnings can wait
