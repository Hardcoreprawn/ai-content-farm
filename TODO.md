# TODO - Clean Restart

**Status**: 🔥 **Fresh Start - Simplify Everything**  
**Goal**: Cost-effective, maintainable system with standardized APIs

## 🎯 Current Situation
- ✅ **8 containers deployed** in Azure and running
- ⚠️ **Collector has Key Vault auth issues** - `reddit_available: false`
- ⚠️ **Inconsistent APIs** - some use `/api/container-name/endpoint`, should be `/api/endpoint`
- 💰 **Over-engineered and expensive** - 8 containers when we need 3-4

## 📋 Phase 1: Fix Current Issues (This Week)

### 1. Fix Collector Key Vault Access
- [ ] **Debug Reddit API access** - collector can't get secrets from Key Vault
- [ ] **Verify Managed Identity** permissions for Key Vault
- [ ] **Test Reddit collection** with proper auth

### 2. Standardize API Patterns  
- [ ] **Fix API paths** - change from `/api/container-name/endpoint` to `/api/endpoint`
- [ ] **Consistent response format** - all containers use StandardResponse
- [ ] **Standard endpoints** - all containers have `/health`, `/status`, `/docs`

## 📋 Phase 2: Consolidate Containers (Next 2 Weeks)

### Target Architecture (4 containers):
1. **Collector** - Reddit → topics (merge collector + scheduler)
2. **Processor** - Topics → articles (merge ranker + enricher + generator)  
3. **Publisher** - Articles → website (merge markdown + site generator)
4. **Scheduler** - Orchestration and timers

### Expected Savings:
- **Current**: 8 containers × 0.5 CPU = ~$77-110/month
- **Target**: 4 containers with right-sized resources = ~$40-62/month
- **Savings**: 40-50% cost reduction

## 🚀 Immediate Actions

1. **Fix the collector auth issue** - get Reddit working
2. **Standardize API paths** - remove container names from URLs
3. **Test end-to-end pipeline** - collector → processor → publisher
4. **Document what works** - update README with current state

---

**Priority**: Fix collector auth first, then standardize APIs, then consolidate containers.
