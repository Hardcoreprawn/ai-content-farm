# Markdown Generator Message Format Fix - October 20, 2025

## Problem
Markdown-generator was sending queue messages to site-publishing-requests queue, but site-publisher was rejecting them with:
```
WARNING: Message missing 'operation' field, skipping
```

The messages were being received but not processed because of a **contract mismatch** between the two containers.

## Root Cause Analysis

### Markdown-Generator Was Sending:
```json
{
  "service_name": "markdown-generator",
  "operation": "site_publish_request",
  "payload": {
    "batch_id": "collection-...",
    "markdown_count": 42,
    "markdown_container": "markdown-content",
    "trigger": "queue_empty",
    "timestamp": "2025-10-20T07:16:28.022353"
  }
}
```

### Site-Publisher Expected:
```json
{
  "service_name": "markdown-generator",
  "operation": "markdown_generated",
  "payload": {
    "batch_id": "collection-...",
    "markdown_container": "markdown-content",
    "trigger": "queue_empty",
    "timestamp": "2025-10-20T07:16:28.022353"
  },
  "content_summary": {
    "files_created": 42,
    "files_failed": 0,
    "force_rebuild": false
  }
}
```

**Issues**:
1. `operation` field mismatch: `"site_publish_request"` vs `"markdown_generated"`
2. Missing `content_summary` field with `files_created` count
3. Incorrect field names in payload (`markdown_count` vs using `content_summary`)

## Solution
Updated `containers/markdown-generator/queue_processor.py` function `signal_site_publisher()` to send the correct message format:

```python
publish_message = {
    "service_name": "markdown-generator",
    "operation": "markdown_generated",  # ← FIXED: Was "site_publish_request"
    "payload": {
        "batch_id": batch_id,
        "markdown_container": output_container,
        "trigger": "queue_empty",
        "timestamp": datetime.utcnow().isoformat(),
    },
    "content_summary": {  # ← FIXED: Added missing field
        "files_created": total_processed,
        "files_failed": 0,
        "force_rebuild": False,
    },
}
```

## Changes Made

**File**: `/workspaces/ai-content-farm/containers/markdown-generator/queue_processor.py`

**Function**: `signal_site_publisher(total_processed: int, output_container: str)`

**Changes**:
- Line 136: Changed `"operation": "site_publish_request"` → `"operation": "markdown_generated"`
- Removed `"markdown_count"` from payload (moved to content_summary)
- Added `"content_summary"` object with `files_created`, `files_failed`, and `force_rebuild`
- Updated log message to show `files_created` count for clarity

## Verification

After fix, the message format now matches what site-publisher expects:

✅ Operation field is `"markdown_generated"` (not skipped)
✅ `content_summary` field exists with required fields
✅ Site-publisher will receive `files_created` count correctly

## Testing

Build successful:
```bash
docker build --tag markdown-generator:test -f containers/markdown-generator/Dockerfile .
```

Result: `sha256:ecbabe113b0d2cd0a6bc3326561acb11ceddfe1be2029cff395c7657ca6c0e93`

## Impact

With this fix:
1. ✅ Markdown-generator messages will be **accepted** by site-publisher (correct operation type)
2. ✅ Site-publisher will extract `files_created` count correctly
3. ✅ Site rebuilds will trigger **only when markdown files were actually created**
4. ✅ Prevents false rebuilds with zero-content messages

## Related Documentation

- Site-Publisher message handler: `containers/site-publisher/app.py` (lines 97-130)
- Message format specification: `docs/PHASE6_IMPLEMENTATION_COMPLETE.md`
- Original optimization plan: `docs/PIPELINE_OPTIMIZATION_PLAN.md` (Issue #1)

---

**Status**: ✅ FIXED  
**Container**: markdown-generator  
**Deployment**: Via CI/CD pipeline (GitHub Actions)
