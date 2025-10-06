# Data Contract Fix - Queue Message `content_type` Field

**Date**: October 6, 2025  
**Issue**: Mismatch between processor and site-generator queue message format  
**Status**: ✅ FIXED

## Problem Discovered

During verification of the complete reprocessing flow, discovered a data contract mismatch in the queue messages between processor and site-generator.

### Collector → Processor (✅ CORRECT)
```json
{
  "operation": "process",
  "service_name": "content-collector",
  "payload": {
    "blob_path": "collections/2025/10/06/file.json",
    "collection_id": "reprocess_123456",
    "reprocess": true
  }
}
```

**Processor correctly expects**: `payload.blob_path` ✅

### Processor → Site-Generator (❌ WAS INCORRECT)

**What Processor Was Sending**:
```json
{
  "service_name": "content-processor",
  "operation": "wake_up",
  "payload": {
    "content_type": "processed",  // ❌ WRONG VALUE
    "files": ["processed-content/articles/2025/10/06/article.json"],
    "files_count": 1,
    "timestamp": "2025-10-06T14:30:00Z",
    "correlation_id": "proc_123456"
  }
}
```

**What Site-Generator Expected**:
```python
content_type = payload.get("content_type")

if content_type == "json":
    # ✅ Generate markdown from processed JSON articles
    # Calls: generate_markdown_batch() → generate_static_site()
    
elif content_type == "markdown":
    # ⚠️ Skip markdown generation, only regenerate HTML
    # Calls: generate_static_site() only
    
else:
    # ❌ Backward-compatible fallback (old behavior)
    # Calls: generate_markdown_batch() → generate_static_site()
```

### Impact of the Bug

- Processor was sending `content_type: "processed"` 
- Site-generator didn't recognize this value
- Fell through to the `else` clause (backward-compatible mode)
- **Still worked** but used unintended code path
- Not following the explicit contract design

## Solution

Changed `libs/queue_triggers.py::trigger_markdown_generation()` to send correct value:

### File: `libs/queue_triggers.py`

**Before**:
```python
async def trigger_markdown_generation(
    processed_files: List[str],
    queue_name: str = "site-generation-requests",
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Trigger markdown generation after content processing."""
    return await trigger_next_stage(
        queue_name=queue_name,
        service_name="content-processor",
        operation="wake_up",
        content_type="processed",  # ❌ WRONG
        files=processed_files,
        correlation_id=correlation_id,
    )
```

**After**:
```python
async def trigger_markdown_generation(
    processed_files: List[str],
    queue_name: str = "site-generation-requests",
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Trigger markdown generation after content processing.
    
    Args:
        processed_files: List of processed article files (JSON format)
        queue_name: Site generation queue name
        correlation_id: Optional correlation ID
    """
    return await trigger_next_stage(
        queue_name=queue_name,
        service_name="content-processor",
        operation="wake_up",
        content_type="json",  # ✅ CORRECT - site-generator expects "json"
        files=processed_files,
        correlation_id=correlation_id,
    )
```

## Additional Fix: Type Hints

Fixed Pyright lint errors by adding explicit type annotation:

**Before**:
```python
payload = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    # ... Pyright inferred Dict[str, str]
}
```

**After**:
```python
payload: Dict[str, Any] = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    # ... Now accepts any value type
}
```

## Verification

### Expected Behavior Now:
1. **Collector** queues message with `blob_path` → **Processor** ✅
2. **Processor** loads collection, processes articles → saves to `processed-content` ✅
3. **Processor** queues message with `content_type: "json"` → **Site-Generator** ✅
4. **Site-Generator** receives `content_type == "json"`:
   - Calls `generate_markdown_batch()` to convert JSON → Markdown
   - Calls `generate_static_site()` to convert Markdown → HTML
   - Publishes to `$web` container ✅

### Files Modified:
- ✅ `libs/queue_triggers.py` (line 183: `content_type="json"`)
- ✅ `libs/queue_triggers.py` (line 57: added `Dict[str, Any]` type hint)

### Testing Required:
- [ ] Unit tests for `trigger_markdown_generation()` (verify `content_type=="json"`)
- [ ] Integration test: Processor → Site-Generator flow
- [ ] End-to-end test: Full reprocess with 10 items

## Data Contract Documentation

### Queue Message Standards

All queue messages follow `QueueMessageModel` format:

```python
{
  "message_id": str,           # Auto-generated UUID
  "correlation_id": str,       # For tracking requests
  "timestamp": datetime,       # ISO-8601 format
  "service_name": str,         # Sender identification
  "operation": str,            # Action to perform
  "payload": Dict[str, Any],   # Operation-specific data
  "metadata": Dict[str, Any]   # Optional metadata
}
```

### Valid `content_type` Values

| Value | Meaning | Used By | Expected Action |
|-------|---------|---------|----------------|
| `"json"` | Processed articles in JSON format | Processor → Site-Gen | Generate markdown + HTML |
| `"markdown"` | Markdown files ready for HTML | Site-Gen → Site-Gen | Generate HTML only |
| `"processed"` | ❌ **DEPRECATED** - Do not use | N/A | Falls back to legacy behavior |

### Operation-Specific Payloads

**Operation: `"process"` (Collector → Processor)**:
```json
{
  "payload": {
    "blob_path": "collections/YYYY/MM/DD/file.json",  // Required
    "collection_id": "collection_name",               // Required
    "reprocess": true                                 // Optional
  }
}
```

**Operation: `"wake_up"` (Processor → Site-Generator)**:
```json
{
  "payload": {
    "content_type": "json",                          // Required: "json" or "markdown"
    "files": ["processed-content/articles/..."],     // Required: array of blob paths
    "files_count": 1,                                // Optional: count for logging
    "correlation_id": "tracking_id"                  // Optional: request tracking
  }
}
```

## Lessons Learned

1. **Always verify data contracts** when connecting services via queues
2. **Document expected values** for enum-like string fields (`content_type`)
3. **Type hints matter** - explicit `Dict[str, Any]` prevents Pyright confusion
4. **Test integration points** - unit tests alone won't catch contract mismatches
5. **Use constants** instead of magic strings (future improvement)

## Future Improvements

- [ ] Define `ContentType` enum in shared library
- [ ] Add Pydantic models for operation-specific payloads
- [ ] Create schema validation for queue messages
- [ ] Add integration tests that verify complete message flow
- [ ] Generate OpenAPI-style documentation for queue contracts

---

**Status**: ✅ Fixed and ready for testing  
**Next Steps**: Run integration test with 10-item reprocess to verify fix
