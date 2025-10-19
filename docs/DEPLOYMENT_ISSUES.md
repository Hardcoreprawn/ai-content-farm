# Deployment Issues & Snags - October 11, 2025

## 🚨 Critical Issues

### 1. Markdown-Generator: Health Check Using Wrong Permissions Test
**Status**: � **FALSE NEGATIVE - CONTAINER FUNCTIONAL**  
**Container**: `ai-content-prod-markdown-gen`  
**Error**: Health endpoint returns `"status":"unhealthy"`, but **container is working**  
**Root Cause**: Health check calls `get_account_information()` which requires control plane permissions, but managed identity only has data plane permissions (Storage Blob Data Contributor, Storage Queue Data Contributor)  
**Impact**: Health endpoint misleading, but **actual functionality works** (137 messages processed successfully)  

**Evidence Container IS Working**:
```
12:23:33 - main - INFO - ✅ Queue empty after processing 137 messages.
12:23:29 - markdown_processor - INFO - Successfully processed article: ...20251011_122325_rss_549674.md
```

**Health Check Issue**:
```python
# Current health check (line 203):
app.state.blob_service_client.get_account_information()  # ❌ Requires control-plane permissions

# Should use simpler check like other containers:
return {"status": "healthy" if client_exists else "not_connected"}
```

**Fix Applied**:
- ✅ Added `MARKDOWN_QUEUE_NAME=markdown-generation-requests` to Terraform
- ✅ Added `MARKDOWN_QUEUE_NAME=markdown-generation-requests` manually via Azure CLI
- ✅ Container restarted with new revision (0000026)
- ⚠️ Health check still reports unhealthy (but container processes messages successfully)

**Recommendation**: Update health check to use simpler connection test (follow-up deployment)

**Comparison** (other containers have their queue names):
- ✅ collector: `STORAGE_QUEUE_NAME=content-collection-requests`
- ✅ processor: `STORAGE_QUEUE_NAME=content-processing-requests` + `MARKDOWN_QUEUE_NAME=markdown-generation-requests`
- ✅ markdown-gen: `MARKDOWN_QUEUE_NAME=markdown-generation-requests` (NOW FIXED)
- ✅ site-publisher: `QUEUE_NAME=site-publishing-requests`

---

## ⚠️ Inconsistencies & Improvements

### 2. Inconsistent Queue Environment Variable Names
**Status**: ⚠️ **INCONSISTENT**  
**Impact**: Confusing, error-prone configuration

**Current State**:
- `collector`: Uses `STORAGE_QUEUE_NAME`
- `processor`: Uses `STORAGE_QUEUE_NAME` + `MARKDOWN_QUEUE_NAME`
- `markdown-gen`: **Missing** (should be `MARKDOWN_QUEUE_NAME`)
- `site-publisher`: Uses `QUEUE_NAME`

**Recommendation**: Standardize to container-specific names:
- collector → `COLLECTION_QUEUE_NAME`
- processor → `PROCESSING_QUEUE_NAME` + `MARKDOWN_QUEUE_NAME`
- markdown-gen → `MARKDOWN_QUEUE_NAME` + `PUBLISHING_QUEUE_NAME`
- site-publisher → `PUBLISHING_QUEUE_NAME`

**Priority**: Medium (works but inconsistent)

---

### 3. Missing AZURE_TENANT_ID on Collector
**Status**: ⚠️ **INCONSISTENT**  
**Container**: `ai-content-prod-collector`  
**Impact**: May cause authentication issues in some scenarios

**Current State**:
- ❌ collector: Missing `AZURE_TENANT_ID`
- ✅ processor: Has `AZURE_TENANT_ID=d1790d70-c02c-4e8e-94ee-e3ccbdb19d19`
- ✅ markdown-gen: Has `AZURE_TENANT_ID`
- ✅ site-publisher: Has `AZURE_TENANT_ID`

**Fix Required**:
```terraform
# In infra/container_app_collector.tf
env {
  name  = "AZURE_TENANT_ID"
  value = data.azurerm_client_config.current.tenant_id
}
```

---

### 4. Missing /metrics Endpoint on Collector and Processor
**Status**: ⚠️ **FEATURE GAP**  
**Containers**: `collector`, `processor`  
**Impact**: Inconsistent monitoring capabilities

**Current State**:
- ❌ collector: Returns 404 for `/metrics` (suggests `/status` instead)
- ❌ processor: Returns 404 for `/metrics` (suggests `/status` instead)
- ❌ markdown-gen: Returns 404 for `/metrics`
- ✅ site-publisher: `/metrics` works correctly

**Available Endpoints**:
- collector: `/status` (not `/metrics`)
- processor: `/status` (not `/metrics`)
- markdown-gen: No metrics endpoint found
- site-publisher: `/metrics` ✅

**Recommendation**: 
- Either standardize all to `/metrics`
- Or update site-publisher to use `/status` like others
- Document which endpoint to use for monitoring

---

### 5. KEDA Scaling Verification Needed
**Status**: ⏳ **PENDING VERIFICATION**  
**Impact**: Cost efficiency depends on this working

**Current Observation**:
```
collector:       0 replicas (ScaledToZero) ✅
processor:       1 replica (Running) ⚠️ - Should scale to 0
markdown-gen:    1 replica (Running) ⚠️ - Should scale to 0
site-publisher:  1 replica (Running) ⚠️ - Should scale to 0
```

**Expected After Poll-Until-Empty Fix**:
- All containers should scale to 0 when queues are empty
- Wait 5-10 minutes to observe auto-scaling
- Verify cooldown period working

**Test Plan**:
1. Wait 10 minutes and check replica counts
2. Send test message to queue
3. Verify KEDA scales 0→1
4. After processing, verify scales 1→0

---

## ✅ Working Correctly

### Health Endpoint Status
- ✅ **collector**: 200 OK, healthy (after 56s cold start from 0 replicas)
- ✅ **processor**: 200 OK, healthy (274s uptime)
- ❌ **markdown-gen**: 200 OK, but **unhealthy** (connection failures)
- ✅ **site-publisher**: 200 OK, healthy (1053s uptime)

### Infrastructure Resources
- ✅ All 4 container apps deployed
- ✅ All storage queues exist
- ✅ KEDA scalers configured
- ✅ Managed identity authentication working (except markdown-gen config issue)
- ✅ RBAC roles assigned

---

## 📋 Action Plan (Priority Order)

### Immediate (Fix Critical Issues)
1. **Add MARKDOWN_QUEUE_NAME to markdown-generator** (5 min)
   - Update `infra/container_app_markdown_generator.tf`
   - Deploy via CI/CD
   - Verify health endpoint shows healthy

### Short-term (Improve Consistency)
2. **Add AZURE_TENANT_ID to collector** (2 min)
3. **Standardize metrics/status endpoints** (1 hour)
4. **Verify KEDA scaling behavior** (15 min wait time)

### Medium-term (Testing & Validation)
5. **Test end-to-end pipeline**:
   - Trigger collection
   - Verify queue message flow
   - Check each container processes correctly
   - Manually trigger site-publisher
   - Verify static site deployment

### Long-term (Phase 6)
6. **Add queue completion signaling** to markdown-generator
   - Automate site-publisher trigger
   - Complete end-to-end automation

---

## � Pipeline Test Results (October 11, 2025 12:20-12:56 UTC)

### ✅ Successful Components
- **Collector**: ✅ Processed startup collection, scaled to 0 replicas (KEDA working!)
- **Processor**: ✅ Processed 267 messages successfully
- **Markdown-Gen**: ✅ Processed 137 messages successfully, generated proper markdown
- **Content Quality**: ✅ Only 1 "best of" article (legitimate WIRED review), no garbage listicles
- **Markdown Format**: ✅ Proper markdown with YAML frontmatter, correct `contentType: "text/markdown"`
- **Storage**: ✅ 4212 markdown files ready for publishing

### ⚠️ Issues Discovered

**Issue #6: KEDA Scaling Not Aggressive Enough - Processor Bottleneck**
- **Status**: ⚠️ **PERFORMANCE PRIORITY** - Impacts pipeline elasticity
- **Container**: `processor` (and potentially markdown-gen, site-publisher)
- **Observed**: Processor stayed at 1 replica for entire 267-message workload
- **Current Config**:
  ```terraform
  max_replicas = 3
  min_replicas = 0
  pollingInterval = 30  # KEDA checks queue every 30s
  cooldownPeriod = 300  # 5 minutes before scale down
  
  custom_scale_rule {
    metadata = {
      queueLength = "1"  # Scale up for every 1 message
    }
  }
  ```
- **Root Cause Analysis**:
  - KEDA polling interval (30s) too slow vs message processing speed
  - Container processes messages faster than KEDA can detect queue depth
  - By the time KEDA polls, queue has already been drained by single replica
  - Result: No scale-up trigger despite large batch
  
- **Impact**:
  - ✅ **Cost**: Single replica = cost-efficient (~$0.10/hour vs ~$0.30/hour for 3 replicas)
  - ❌ **Speed**: 267 messages took ~13 minutes (slower than desired)
  - ❌ **Elasticity**: Not demonstrating horizontal scaling capability
  - ❌ **Future Concerns**: Different AI models will have varying processing times
    - GPT-4 calls: 2-5s per message
    - Claude calls: 1-3s per message  
    - Future multi-modal: 10-30s per message
    - Need elastic scaling to handle mixed workloads efficiently

- **Proposed Solutions** (in order of preference):

  **Option A: Aggressive Scaling (Recommended for Development)**
  ```terraform
  max_replicas = 10
  pollingInterval = 15  # Check every 15s instead of 30s
  
  custom_scale_rule {
    metadata = {
      queueLength = "5"  # Scale up for every 5 messages (1 replica per 5 messages)
      activationQueueLength = "1"  # Wake up from 0 at 1 message
    }
  }
  ```
  - **Pros**: Demonstrates scaling, faster processing, handles varying model speeds
  - **Cons**: Higher cost during peak (~$1/hour for 10 replicas), more complex
  
  **Option B: Balanced Scaling**
  ```terraform
  max_replicas = 5
  pollingInterval = 20
  
  custom_scale_rule {
    metadata = {
      queueLength = "10"  # Scale up for every 10 messages
      activationQueueLength = "1"
    }
  }
  ```
  - **Pros**: Balance between cost and speed
  - **Cons**: Still might not scale aggressively for burst workloads
  
  **Option C: Keep Current (Production Cost-Efficient)**
  - No changes, accept slower processing
  - Best for stable, low-volume production workloads
  - Not suitable for development/demo or variable model performance

- **Recommendation**: Implement **Option A** for processor and markdown-gen
  - Needed to demonstrate platform capability
  - Essential for handling different AI model performance characteristics
  - Can tune back to Option B/C after validating scaling works
  
- **Testing Plan**:
  1. Apply Option A config to processor
  2. Trigger collection with ~100 messages
  3. Monitor KEDA metrics: `kubectl get hpa` equivalent for Container Apps
  4. Verify multiple replicas spin up (expect 2-5 replicas for 100 messages)
  5. Verify scale-down to 0 after queue empty
  6. Measure processing time improvement (expect 50-70% faster)

- **Priority**: **Medium-High** - Not blocking but important for:
  - Platform capability demonstration
  - Handling variable AI model performance
  - Future-proofing for multi-modal content

**Issue #7: Site-Publisher - Double HTTPS in baseURL**
- **Status**: 🔴 **CRITICAL - BLOCKING SITE DEPLOYMENT**
- **Container**: `site-publisher`
- **Error**: Hugo build fails with `--baseURL https://https://aicontentprodstkwakpx.z33.web.core.windows.net/`
- **Root Cause**: Terraform uses `"https://${azurerm_storage_account.main.primary_web_endpoint}"` but `primary_web_endpoint` already includes `https://`
- **Impact**: Cannot publish site, Hugo build fails immediately
- **Fix Applied**:
  - ✅ Updated Terraform to use `azurerm_storage_account.main.primary_web_endpoint` directly (removed duplicate `https://`)
  - ✅ Applied manually via `az containerapp update --set-env-vars`
- **Status**: Fixed in Terraform, needs deployment

**Issue #8: Hugo Build Failing - Missing PaperMod Theme**
- **Status**: 🔴 **CRITICAL - BLOCKING SITE DEPLOYMENT - ROOT CAUSE IDENTIFIED**
- **Container**: `site-publisher`
- **Error**: Hugo exits with code 1, stderr empty (silent failure)
- **Logs**: `"Hugo build failed: "` (no error details captured)
- **Root Cause**: **Hugo theme "PaperMod" not installed in Docker image**
  - `hugo-config/config.toml` specifies `theme = "PaperMod"`
  - Dockerfile builds Hugo v0.151.0 but doesn't install any themes
  - Hugo silently fails when theme directory doesn't exist
  - Theme should be at `/app/themes/PaperMod/` but directory doesn't exist

- **Evidence**:
  ```toml
  # hugo-config/config.toml line 6
  theme = "PaperMod"  # ❌ Theme not present in container
  ```
  
  ```dockerfile
  # Dockerfile - No theme installation!
  COPY --from=hugo-builder /go/bin/hugo /usr/local/bin/hugo
  # Missing: Theme installation step
  ```

- **Impact**: 
  - Cannot build static site (Hugo fails immediately)
  - 4212 markdown files ready but cannot be published
  - Blocks end-to-end pipeline completion

- **Proposed Solutions**:

  **Option A: Install PaperMod Theme from Git (Recommended)**
  ```dockerfile
  # After line 40 in Dockerfile (after hugo version check)
  RUN apk add --no-cache git && \
      mkdir -p /app/themes && \
      git clone --depth 1 https://github.com/adityatelange/hugo-PaperMod.git /app/themes/PaperMod && \
      apk del git
  ```
  - **Pros**: Official theme, maintained, feature-rich
  - **Cons**: Adds ~10MB to image, requires git in build

  **Option B: Use Hugo Built-in Theme**
  ```toml
  # Change config.toml
  theme = ""  # Remove theme requirement
  # Or use: theme = "blank"
  ```
  - **Pros**: No external dependency, smaller image
  - **Cons**: Minimal styling, would need custom CSS

  **Option C: Bundle Pre-downloaded Theme**
  ```dockerfile
  # In Dockerfile
  COPY themes/PaperMod /app/themes/PaperMod
  ```
  - **Pros**: No runtime download, faster builds
  - **Cons**: Need to manually update theme, larger repo

- **Recommendation**: **Option A** - Install PaperMod from Git
  - Clean, maintainable solution
  - Official theme with good SEO optimization
  - Small image size increase acceptable for functionality
  - Can pin to specific commit/tag for reproducibility

- **Implementation Plan**:
  1. Update `containers/site-publisher/Dockerfile` to install PaperMod
  2. Test locally: `docker build` and verify theme exists
  3. Test Hugo build with theme: `hugo --source /tmp/test`
  4. Commit and push to trigger CI/CD
  5. Manual test after deployment: POST to `/publish` endpoint
  6. Verify static site deployed to `$web` container
  7. Check site URL: `https://aicontentprodstkwakpx.z33.web.core.windows.net/`

- **Priority**: **CRITICAL** - Blocking Phase 8 completion

**Issue #9: No Automatic Site-Publisher Trigger**
- **Status**: ⚠️ **EXPECTED - PHASE 6 ENHANCEMENT**
- **Impact**: Must manually trigger site-publisher after markdown-gen completes
- **Root Cause**: Markdown-generator doesn't send completion message to `site-publishing-requests` queue
- **Workaround**: Manual curl to `/publish` endpoint
- **Recommendation**: Implement in Phase 6 (queue completion signaling)
- **Priority**: Medium (planned enhancement)

---

## �🔍 Monitoring Commands

```bash
# Check container status
az containerapp list --resource-group ai-content-prod-rg \
  --query '[].{Name:name, Status:properties.runningStatus, Replicas:properties.runningStatus}' -o table

# Check replica counts (KEDA scaling)
for app in collector processor markdown-gen site-publisher; do
  az containerapp revision list --name "ai-content-prod-$app" --resource-group ai-content-prod-rg \
    --query '[0].{Name:name, State:properties.runningState, Replicas:properties.replicas}' -o table
done

# Check queue depths
az storage queue list --account-name aicontentprodstkwakpx \
  --auth-mode login --query '[].{Name:name}' -o table

# Test health endpoints
for app in collector processor markdown-gen site-publisher; do
  curl -s "https://ai-content-prod-$app.whitecliff-6844954b.uksouth.azurecontainerapps.io/health" | jq .
done
```

---

**Created**: October 11, 2025 12:15 UTC  
**Last Updated**: October 11, 2025 12:57 UTC (Added pipeline test results + new issues #6-9)
