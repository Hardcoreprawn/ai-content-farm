# Blob Container Cleanup Analysis

## Current State (October 4, 2025)

### Container Usage Analysis

| Container | Status | Blob Count | Last Modified | Purpose | Action |
|-----------|--------|------------|---------------|---------|--------|
| `$web` | ✅ ACTIVE | Many | 2025-09-22 | Static website hosting | **KEEP** |
| `collected-content` | ✅ ACTIVE | Many | 2025-09-17 | Collection output | **KEEP** |
| `collection-templates` | ✅ ACTIVE | Many | 2025-09-25 | Collection configs | **KEEP** |
| `markdown-content` | ✅ ACTIVE | Many | 2025-09-17 | Generated markdown | **KEEP** |
| `processed-content` | ✅ ACTIVE | Many | 2025-09-17 | Processor output | **KEEP** |
| `prompts` | ✅ ACTIVE | Many | 2025-09-17 | AI prompts storage | **KEEP** |
| `pipeline-logs` | ✅ ACTIVE | Many | 2025-09-17 | Pipeline logging | **KEEP** |
| `static-sites` | ⚠️ DEPRECATED | 21 | 2025-10-04 | Old site archives | **REMOVE** |
| `content-topics` | ❌ UNUSED | 0 | 2025-09-17 | Never used | **REMOVE** |
| `enriched-content` | ❌ UNUSED | 0 | 2025-09-17 | Never used | **REMOVE** |
| `ranked-content` | ❌ UNUSED | 0 | 2025-09-17 | Never used | **REMOVE** |
| `pricing-cache` | ❌ UNUSED | 0 | 2025-09-17 | Referenced but unused | **REMOVE** |

---

## Containers to Remove

### 1. `pricing-cache` (Empty, Referenced but Unused)
- **Purpose**: Originally for caching Azure pricing API responses
- **Current State**: 0 blobs, never populated
- **References**: 
  - `libs/app_config.py` - Defined but not used
  - `infra/main.tf` - Terraform resource
- **Reason to Remove**: Pricing data not being cached anywhere

### 2. `content-topics` (Empty, Never Used)
- **Purpose**: Unknown/unclear original purpose
- **Current State**: 0 blobs
- **References**: 
  - `infra/main.tf` - Terraform resource
- **Reason to Remove**: No code references, never used

### 3. `enriched-content` (Empty, Never Used)
- **Purpose**: Was planned for content enrichment pipeline stage
- **Current State**: 0 blobs
- **References**: 
  - `libs/app_config.py` - Defined constant
  - `infra/main.tf` - Terraform resource
- **Reason to Remove**: Enrichment feature never implemented

### 4. `ranked-content` (Empty, Referenced but Unused)
- **Purpose**: Was planned for content ranking pipeline stage
- **Current State**: 0 blobs
- **References**: 
  - `container-config/content-processor-containers.json` - staging_container
  - `docker-compose.yml` - Environment variable
  - `libs/app_config.py`, `libs/config_base.py` - Configuration
  - `tests/test_system_integration.py` - Test mocks
- **Reason to Remove**: Content ranking happens in-memory, not stored

### 5. `static-sites` (Deprecated Archives)
- **Purpose**: Stored `.tar.gz` archives of generated sites
- **Current State**: 21 old archives from September 2025
- **References**: 
  - `libs/app_config.py`, `libs/startup_config.py` - Configuration
  - `infra/main.tf` - Terraform resource
- **Reason to Remove**: 
  - Sites now deployed directly to `$web` container
  - Archives not used for rollback or history
  - Just taking up space

---

## Code References to Clean Up

### Python Configuration Files
```python
# libs/app_config.py - Remove these lines:
ENRICHED_CONTENT = "enriched-content"
RANKED_CONTENT = "ranked-content"
STATIC_SITES = "static-sites"
# PRICING_CACHE is not actually referenced anywhere despite being defined

# libs/config_base.py - Remove:
default="ranked-content", description="Container for ranked content"

# libs/startup_config.py - Remove:
"static_sites_container": "static-sites",
```

### Container Configuration Files
```json
// container-config/content-processor-containers.json - Remove:
"staging_container": "ranked-content",
```

### Docker Compose
```yaml
# docker-compose.yml - Remove environment variables:
- RANKED_CONTENT_CONTAINER=ranked-content
```

### Test Files
```python
# tests/test_system_integration.py - Update mocks to remove:
"ranked-content": "ranked-content",
# And all test references to ranked-content container
```

---

## Terraform Changes Required

### Remove Container Resources
```terraform
# infra/main.tf - Remove these resources:
resource "azurerm_storage_container" "topics" { ... }
resource "azurerm_storage_container" "enriched_content" { ... }
resource "azurerm_storage_container" "ranked_content" { ... }
resource "azurerm_storage_container" "static_sites" { ... }
resource "azurerm_storage_container" "pricing_cache" { ... }
```

---

## Cost Impact

### Current Monthly Costs (Estimated)
- Empty containers: $0.00 (metadata only, negligible)
- `static-sites` with 21 small blobs: ~$0.01/month
- **Total Savings**: Negligible (~$0.01/month)

### Primary Benefits
1. **Reduced Complexity**: Fewer resources to manage
2. **Clear Architecture**: Only active containers remain
3. **Prevent Future Confusion**: Developers won't wonder what these are for
4. **Cleaner Terraform State**: Fewer resources to track

---

## Migration Plan

### Phase 1: Backup static-sites (If Needed)
```bash
# Only if you want to preserve old site archives
az storage blob download-batch \
  --account-name aicontentprodstkwakpx \
  --auth-mode login \
  --source static-sites \
  --destination ./backup/static-sites/
```

### Phase 2: Remove Terraform Resources
```bash
cd infra/
terraform plan  # Review what will be deleted
terraform apply # Remove containers
```

### Phase 3: Clean Up Code References
1. Remove config constants from `libs/app_config.py`
2. Remove environment variables from `docker-compose.yml`
3. Remove test mocks from `tests/test_system_integration.py`
4. Remove config from `container-config/*.json`

### Phase 4: Verification
```bash
# Verify containers are gone
az storage container list \
  --account-name aicontentprodstkwakpx \
  --auth-mode login \
  --output table

# Verify application still works
make test
```

---

## Risk Assessment

### Low Risk Containers (Safe to Remove)
- ✅ `pricing-cache` - Never used, 0 blobs
- ✅ `content-topics` - Never used, 0 blobs, no code references
- ✅ `enriched-content` - Never used, 0 blobs

### Medium Risk Containers (Review Code First)
- ⚠️ `ranked-content` - Has code references but 0 blobs
  - **Action**: Remove after confirming tests don't depend on it
- ⚠️ `static-sites` - Has old data but deprecated pattern
  - **Action**: Backup first if paranoid, then remove

### Recommended Order
1. **Remove pricing-cache, content-topics, enriched-content** (no risk)
2. **Test thoroughly** with remaining containers
3. **Remove ranked-content** after updating tests
4. **Remove static-sites** after backing up (if desired)

---

## Final Container List (After Cleanup)

### Production Containers (KEEP)
```
$web                    # Static website hosting (critical)
collected-content       # Collection pipeline output
collection-templates    # Collection configuration files
markdown-content        # Generated markdown articles
processed-content       # Processed content output
prompts                 # AI prompt templates
pipeline-logs           # Pipeline execution logs
```

### Total: 7 containers (down from 12)

---

## Conclusion

**Recommendation**: Remove all 5 unused containers to simplify architecture.

- **Cost Impact**: Negligible (~$0.01/month savings)
- **Risk**: Very low (all containers are empty or deprecated)
- **Benefit**: Cleaner codebase, reduced complexity, clear architecture
- **Effort**: ~30 minutes (Terraform changes + code cleanup)

**Next Steps**: 
1. Review and approve this plan
2. Update Terraform to remove containers
3. Clean up code references
4. Test thoroughly
5. Document final architecture
