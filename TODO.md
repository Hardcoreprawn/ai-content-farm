# TODO - Clean Restart Approach

**Status**: 🔄 Updating Tests for Standardized APIs  
**Goal**: Simple, cost-effective content pipeline that works

## 🎯 Current Status

### ✅ What's Working
- **8 containers deployed** in Azure Container Apps (all running)
- **CI/CD pipeline** with Terraform deployment working
- **Authentication** via OIDC and managed identity set up

### 🚀 Current Fix: Update Tests for Modern APIs
- **✅ Collector Key Vault issue**: Fixed environment variables and credential access
- **✅ Clean API design**: Modern FastAPI with proper models (SourceConfig, DiscoveryRequest)
- **🔄 Test compatibility**: Updating tests to match standardized API patterns instead of legacy formats

### 🎯 Smart Approach
Instead of making our clean API backward compatible with old tests, we're updating the tests to match our standardized API design. This gives us:
- Clean, modern FastAPI patterns
- Consistent models across all containers  
- Standard `/api/collector/*` endpoints
- Proper request/response validation

### 📋 Clean Architecture Target (2-3 weeks)

**4 Simple Containers**:
1. **Collector** - Reddit API → topics (merge scheduler + collector)
2. **Processor** - Topics → articles (merge ranker + enricher + generator)  
3. **Publisher** - Articles → website (merge markdown + site generator)
4. **Scheduler** - Timer orchestration

**Benefits**:
- 50% cost reduction (~$40/month vs $80/month)
- Simpler to understand and maintain
- Standard FastAPI patterns throughout
