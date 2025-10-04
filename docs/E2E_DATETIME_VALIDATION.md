# End-to-End Datetime Serialization Validation

## What Changed

### Commit ad41461: Functional Datetime Serialization
- **Library**: `libs/simplified_blob_client.py` 
- **Change**: `upload_json()` now uses `serialize_datetime()` to recursively convert all datetime objects to ISO format strings
- **Impact**: All three containers (collector, processor, generator) use this shared library
- **Status**: ✅ Deployed and verified in production

### Commit 0e6dbd7: Fix Resource Leaks  
- **Container**: `containers/content-processor/main.py`
- **Change**: Added API client cleanup to FastAPI lifespan shutdown handler
- **Fix**: Prevents "Unclosed client session" and "Unclosed connector" errors
- **Status**: ✅ Deployed and verified (issue #571 closed)

## Verification Results (2025-10-03 13:35 UTC)

### ✅ Datetime Serialization - WORKING
**Test**: Downloaded most recent collection blob  
**File**: `collections/2025/10/03/collection_20251003_132831.json`  
**Result**: All datetime fields correctly serialized to ISO format strings

```json
{
  "created_at": "2025-10-03T13:29:01.914223",  // ✅ ISO string
  "metadata": {
    "timestamp": "2025-10-03T13:29:01.914207Z",  // ✅ ISO string with Z
    ...
  }
}
```

**Verification**:
- ✅ No JSON serialization errors in collector logs
- ✅ Collections being saved successfully every ~6 minutes
- ✅ 10 recent collections found in blob storage (13:29, 13:23, 13:17, etc.)
- ✅ All datetime objects automatically converted by `serialize_datetime()` pure function

### ✅ Resource Leaks - FIXED
**Test**: Checked processor logs after deployment  
**Result**: No more "Unclosed client session" or "Unclosed connector" errors

**Verification**:
- ✅ API client cleanup code added to FastAPI lifespan shutdown
- ✅ Processor revision 0000067 deployed successfully
- ✅ No resource leak warnings in recent logs

## Validation Checklist

### 1. Collector → Blob Storage
**Test**: Collector saves collection data with timestamps
```bash
# Monitor collector logs for successful upload
az containerapp logs show \
  --name ai-content-prod-collector \
  --resource-group ai-content-prod-rg \
  --follow --tail 50
```
**Expected**: 
- ✅ "Uploaded JSON to..." log messages (no serialization errors)
- ✅ Collection files in blob storage with ISO timestamp strings

**Validate blob content**:
```bash
# Download a recent collection and check datetime format
az storage blob download \
  --account-name aicontentprodstorage \
  --container-name collections \
  --name "2025/10/03/*/reddit-*.json" \
  --file /tmp/test-collection.json
cat /tmp/test-collection.json | jq '.collected_at, .articles[0].published_at'
# Should show ISO strings like "2025-10-03T12:34:56"
```

### 2. Processor → Blob Storage
**Test**: Processor reads collection, processes articles, saves results with enriched metadata
```bash
# Monitor processor logs
az containerapp logs show \
  --name ai-content-prod-processor \
  --resource-group ai-content-prod-rg \
  --follow --tail 50
```
**Expected**:
- ✅ Successfully reads collection JSON (datetime strings parse correctly)
- ✅ Saves processed articles (no serialization errors on article metadata)
- ✅ Processing result files contain ISO timestamp strings

**Validate blob content**:
```bash
# Check processed article has proper datetime serialization
az storage blob download \
  --account-name aicontentprodstorage \
  --container-name processed \
  --name "2025/10/03/*/processed-*.json" \
  --file /tmp/test-processed.json
cat /tmp/test-processed.json | jq '.metadata.processed_at, .articles[0].published'
# Should show ISO strings
```

### 3. Generator → Site Files
**Test**: Generator reads processed data, generates site with publication dates
```bash
# Monitor generator logs
az containerapp logs show \
  --name ai-content-prod-generator \
  --resource-group ai-content-prod-rg \
  --follow --tail 50
```
**Expected**:
- ✅ Successfully reads processed JSON
- ✅ Generates articles with frontmatter dates
- ✅ Site builds successfully with proper dates

**Validate generated content**:
```bash
# Check generated article frontmatter
az storage blob download \
  --account-name aicontentprodstorage \
  --container-name generated \
  --name "articles/*.md" \
  --file /tmp/test-article.md
head -20 /tmp/test-article.md
# Should show YAML frontmatter with date: "2025-10-03" or similar
```

## Contract Validation

### Input Contract (Containers → Library)
```python
# All containers call upload_json() the same way (unchanged)
await blob_client.upload_json(
    container="collections",
    blob_name="path/to/file.json",
    data={"collected_at": datetime.now(), ...},  # Can still pass datetime objects
    overwrite=True
)
```
**Status**: ✅ No changes required in container code

### Output Contract (Library → Blob Storage)
**Before**: Datetime objects caused JSON serialization errors
**After**: All datetime objects automatically converted to ISO strings
```json
{
  "collected_at": "2025-10-03T12:34:56",  // Was: datetime object (failed)
  "metadata": {
    "created": "2025-10-03T12:00:00"      // Now: ISO string (works)
  }
}
```
**Status**: ✅ More predictable output format

### Reading Contract (Blob Storage → Containers)
**Question**: Do containers expect datetime objects or strings when reading?
**Answer**: They read JSON, which always returns strings. If they need datetime objects, they must parse ISO strings:
```python
data = await blob_client.download_json(container, blob_name)
# data["collected_at"] is now a string "2025-10-03T12:34:56"
# If datetime object needed:
from datetime import datetime
dt = datetime.fromisoformat(data["collected_at"])
```
**Status**: ⚠️ Check if any container code expects datetime objects from JSON reads

## Quick Smoke Test

Run one full cycle and verify no errors:
```bash
# 1. Trigger collector (or wait for scheduled run)
# 2. Check all three container logs for errors
# 3. Verify files in blob storage at each stage
# 4. Check final generated site has proper dates

# One-liner to check all container health
for app in collector processor generator; do
  echo "=== $app ==="
  az containerapp show \
    --name ai-content-prod-$app \
    --resource-group ai-content-prod-rg \
    --query 'properties.runningStatus' -o tsv
done
```

## Rollback Plan

If datetime serialization causes issues:
```bash
# Revert to previous commit
git revert ad41461
git push origin main
# CI/CD will redeploy previous version
```

## Success Criteria

- ✅ No JSON serialization errors in any container logs
- ✅ All blob storage files have ISO format datetime strings
- ✅ Generated site displays proper dates
- ✅ Full collector → processor → generator cycle completes
- ✅ No regressions in existing functionality
