# Content Collector Fix: Quality Filtering for Default Sources

## Problem
The content-collector container was collecting 0 items despite successfully connecting to Mastodon instances (fosstodon.org, techhub.social).

### Root Cause
The quality review pipeline was applying **strict technical relevance filtering** to all items, including those from default fallback sources. When collection templates failed to load, the system fell back to default Mastodon public timeline sources, but the items were rejected because:
- Public timeline posts don't always contain technical keywords
- The strict `check_technical_relevance()` was mandatory and required keywords like "code", "software", "API", etc.

## Solution: Permissive vs Strict Quality Modes

### Changes Made

#### 1. **quality/review.py** - Added `strict_mode` parameter
```python
def check_technical_relevance(item, strict_mode=True):
    if not strict_mode:
        # Permissive: Accept anything readable (no keyword check)
        return (True, None)
    # Strict: Require technical keywords
    # ... existing logic
```

**Impact:**
- Permissive mode (strict_mode=False): Only checks readability (title 10+ chars, content 100+ chars)
- Strict mode (strict_mode=True): Also checks for technical keywords

#### 2. **quality/review.py** - Updated `review_item()` function
```python
def review_item(item, check_relevance=True, strict_mode=True):
    # ... validation and readability checks
    if check_relevance:
        passes_relevance, reason = check_technical_relevance(
            item, strict_mode=strict_mode  # Pass through mode
        )
```

#### 3. **pipeline/stream.py** - Added `strict_quality_check` parameter
```python
async def stream_collection(
    collector_fn,
    collection_id,
    collection_blob,
    blob_client,
    queue_client,
    strict_quality_check=True,  # New parameter
):
    # ... later in pipeline
    passes_review, reason = review_item(
        item, strict_mode=strict_quality_check  # Use parameter
    )
```

#### 4. **main.py** - Track template vs default sources
```python
using_template = False  # Track if we're using actual template

# When loading from blob/filesystem
using_template = len(sources) > 0

# When falling back to defaults
if not sources:
    sources = [
        {"instance": "fosstodon.org", "max_items": 25},
        {"instance": "techhub.social", "max_items": 15},
    ]
    using_template = False  # Mark as defaults

# Pass to stream_collection
stats = await stream_collection(
    collector_fn=collect_from_template(),
    collection_id=collection_id,
    collection_blob=collection_blob,
    blob_client=blob_client,
    queue_client=queue_client,
    strict_quality_check=using_template,  # Strict only if using template
)
```

## Behavior After Fix

### When using custom template (e.g., quality-tech.json)
- ✅ Uses **strict mode** (`strict_quality_check=True`)
- ✅ Requires technical keywords in content
- ✅ Filters for relevance to tech topics

### When using default Mastodon sources (fallback)
- ✅ Uses **permissive mode** (`strict_quality_check=False`)
- ✅ Accepts any readable content (title 10+ chars, content 100+ chars)
- ✅ No technical keyword requirement
- ✅ Allows broader content for curation

## Test Results
```
✅ Permissive mode accepts non-technical content that passes readability
✅ Strict mode rejects non-technical content
✅ Strict mode accepts technical content
✅ Basic validation (title/content length) applies in both modes
```

## Log Output Expected

Before (0 items collected):
```
Collecting from fosstodon.org (25 items)...
Collecting from techhub.social (15 items)...
✅ KEDA startup collection complete - Stats: collected=40, published=0, rejected_quality=40
```

After (with items):
```
Collecting from fosstodon.org (25 items)...
Collecting from techhub.social (15 items)...
✅ KEDA startup collection complete - Stats: collected=40, published=X, rejected_quality=Y
```

## Files Modified
1. `containers/content-collector/quality/review.py` - Added strict_mode support
2. `containers/content-collector/pipeline/stream.py` - Added strict_quality_check parameter
3. `containers/content-collector/main.py` - Track template vs defaults, pass strict_quality_check
4. `containers/content-collector/test_quality_modes.py` - NEW: Test quality modes

## Next Steps
1. Rebuild and redeploy content-collector container
2. Monitor logs to verify items are being collected
3. Once items flow through, verify they appear in blob storage collections
4. Test with custom collection templates to ensure strict mode still filters appropriately
