# Reprocess Flow Analysis - End-to-End Pipeline Review

**Date**: October 6, 2025  
**Status**: Pre-deployment validation  
**Objective**: Ensure clean rebuild with proper ASCII filenames and working URLs

## 🔍 Complete Flow Analysis

### Phase 1: Collection Reprocessing (Collector)

**Endpoint**: `POST /reprocess`  
**Location**: `containers/content-collector/endpoints/reprocess.py`

**Flow**:
1. Lists all blobs in `collected-content` container with prefix `collections/`
2. For each collection JSON file:
   - Reads collection metadata
   - Creates queue message with payload:
     ```json
     {
       "operation": "process",
       "service_name": "content-collector",
       "payload": {
         "blob_path": "collections/YYYY-MM-DD-HHMMSS.json",
         "collection_id": "reddit_1234567890",
         "reprocess": true
       },
       "correlation_id": "reprocess_timestamp_count"
     }
     ```
   - Sends to `content-processing-requests` queue
3. Returns: `{"collections_queued": 585, "estimated_cost": "$0.94", "estimated_time": "~58 min"}`

**Issues Identified**: ✅ None - Working correctly

---

### Phase 2: Content Processing (Processor)

**Trigger**: KEDA scales processor based on queue depth  
**Location**: `containers/content-processor/`

**KEDA Scaling Configuration**:
```terraform
min_replicas = 0
max_replicas = 3
queueLength = "1"  # Scale immediately
pollingInterval = 30  # Check every 30s
```

**Message Processing**:
1. **Background Poller** (`StorageQueuePoller`):
   - Polls `content-processing-requests` queue every 5s
   - Processes up to 10 messages per batch
   - Calls `message_handler` for each message

2. **Message Handler** (`storage_queue_router.py`):
   - Receives `operation: "process"` message
   - Calls `processor.process_available_work()` (❌ **THIS IS THE PROBLEM**)
   - Does NOT use the `blob_path` from queue message!
   - Instead, scans blob storage for unprocessed items (discovery mode)

3. **Article Generation**:
   - Generates article content via OpenAI
   - Calls `MetadataGenerator.generate_metadata()`:
     - Translates non-English titles to English
     - Generates URL-safe slug (kebab-case)
     - Creates filename: `articles/YYYY-MM-DD-slug.html`
     - Generates SEO-optimized description
   - Saves to `processed-content` container as JSON with metadata:
     ```json
     {
       "filename": "articles/2025-10-06-pentagon-vulcan-rocket-costs.html",
       "slug": "pentagon-vulcan-rocket-costs",
       "url": "/articles/2025-10-06-pentagon-vulcan-rocket-costs.html",
       "title": "Pentagon Contract Figures Show ULA's Vulcan Rocket Is Getting More Expensive",
       "content": "Full article HTML...",
       "cost_usd": 0.0013,  // Now optional (fixed)
       "tokens_used": 1125
     }
     ```

**Critical Issues**:
- ❌ **Queue message payload ignored!** Processor uses discovery mode instead of processing specific blob_path
- ❌ **No targeted processing** - Processes whatever it finds, not what was queued
- ⚠️ **Scaling inefficiency** - KEDA sees 585 messages but processor may only handle 10 at startup

**Why it didn't scale last time**:
1. Processor consumed messages quickly (acknowledged them)
2. But didn't actually process them - used discovery mode instead
3. KEDA saw empty queue → scaled down
4. Actual processing happened async via discovery scanning
5. No backpressure signal for KEDA to scale up

---

### Phase 3: Site Generation (Site-Generator)

**Trigger**: Processor sends message to `site-generation-requests` queue  
**Location**: `containers/site-generator/`

**KEDA Scaling**: Similar to processor (min=0, max=2)

**Flow**:
1. **Queue Message** (from processor):
   ```json
   {
     "operation": "wake_up",
     "service_name": "content-processor", 
     "payload": {
       "content_type": "processed",
       "articles_generated": 10,
       "correlation_id": "processor_run_id"
     }
   }
   ```

2. **Processing** (`storage_queue_router.py` → `_process_queue_request()`):
   - If `content_type == "processed"`:
     - Calls `generate_markdown_batch()` (JSON → Markdown)
     - Then calls `generate_static_site()` (Markdown → HTML)
   - If `content_type == "markdown"`:
     - Only calls `generate_static_site()`

3. **Markdown Generation** (`generate_markdown_batch`):
   - Reads from `processed-content` container
   - For each JSON article:
     - Extracts content, title, metadata
     - Creates markdown file with frontmatter
     - Saves to `markdown-content` container
   - **Uses processor-provided filename**: ✅ Proper ASCII names!

4. **HTML Generation** (`generate_static_site`):
   - Reads from `markdown-content` container
   - For each markdown file:
     - Extracts frontmatter (YAML metadata)
     - Converts markdown body to HTML (Jinja2 template)
     - **Uses processor-provided fields**:
       ```python
       filename = article.get("filename")  # articles/YYYY-MM-DD-slug.html
       slug = article.get("slug")          # kebab-case slug
       url = article.get("url")            # /articles/YYYY-MM-DD-slug.html
       ```
     - Renders article template with proper URLs
     - Uploads to `$web` container (static site)

5. **Index Page Generation**:
   - Lists all articles
   - Sorts by date (newest first)
   - Generates `index.html` with article links
   - All links use processor-provided URLs ✅

**Issues Identified**:
- ✅ **Filename handling**: Uses processor metadata (proper ASCII)
- ✅ **URL generation**: Uses processor-provided URLs (working links)
- ✅ **Fallback logic**: Has legacy filename support for old articles
- ⚠️ **Duplicate prevention**: Relies on filename uniqueness (handled by processor)

---

## 🚨 Critical Problem: Queue Message Ignoring

### Root Cause

The processor's `storage_queue_router.py` receives messages with `operation: "process"` but calls:

```python
result = await processor.process_available_work(
    batch_size=batch_size,
    priority_threshold=priority_threshold,
    options=payload.get("processing_options", {}),
)
```

This function **does NOT use the `blob_path` from the queue message**! It scans blob storage for unprocessed items instead.

### Why This Breaks Scaling

1. ✅ 585 messages queued
2. ✅ KEDA sees queue depth → scales to max replicas  
3. ❌ Processor acknowledges messages quickly (deletes from queue)
4. ❌ But processes via discovery scanning (ignores queue payload)
5. ❌ KEDA sees empty queue → scales down
6. ❌ Processing continues slowly via scanning, not queue-driven

### Expected Behavior

The processor should:
1. Read `blob_path` from queue message
2. Load that specific collection file
3. Process ONLY that collection
4. Move to next message
5. This creates proper backpressure for KEDA scaling

---

## 📋 Recommendations

### Option 1: Fix Queue Message Handling (Recommended)

**Change**: Make processor respect `blob_path` in queue payload

**Benefits**:
- ✅ True event-driven processing
- ✅ KEDA scales correctly with actual load
- ✅ No duplicate processing
- ✅ Predictable throughput

**Changes Required**:
- Modify `storage_queue_router.py` to use `payload.blob_path`
- Update `process_available_work()` to accept specific collection file
- Add tests for targeted processing

**Effort**: ~2 hours

---

### Option 2: Accept Current Behavior (Quick Fix)

**Change**: None - use discovery mode as-is

**Implications**:
- ⚠️ Queue messages are just "wake-up" signals
- ⚠️ Actual processing via background scanning
- ⚠️ KEDA scaling won't match actual work
- ⚠️ May process same items multiple times
- ✅ Simpler code (already working)
- ✅ Eventually consistent

**Changes Required**:
- Update reprocess endpoint documentation
- Set realistic expectations for throughput
- Accept that scaling is approximate

**Effort**: None (document only)

---

## 🎯 Site Generation Validation

### URL Structure (Processor-Generated)
```
Filename:  articles/2025-10-06-pentagon-vulcan-rocket-costs.html
Slug:      pentagon-vulcan-rocket-costs
URL:       /articles/2025-10-06-pentagon-vulcan-rocket-costs.html
```

### HTML Output
- ✅ Uses processor filename (ASCII-safe)
- ✅ Uses processor URL (proper links)
- ✅ All internal links work
- ✅ Index page has correct article links
- ✅ No Vietnamese characters in filenames
- ✅ Proper date prefixes for sorting

### What We'll Get
1. **Clean filenames**: `articles/YYYY-MM-DD-slug.html`
2. **Working URLs**: `/articles/YYYY-MM-DD-slug.html`
3. **Proper index**: Sorted by date, newest first
4. **No duplicates**: Filename uniqueness ensures no overwrites
5. **SEO-friendly**: Kebab-case slugs, descriptive URLs

---

## 🔄 Recommended Test Flow

### Before Reprocess
```bash
# Verify clean state
az storage blob list --container-name processed-content  # Should be 0
az storage blob list --container-name '$web'             # Should be 0
az storage queue peek --queue-name content-processing-requests  # Should be 0
```

### Trigger Reprocess
```bash
curl -X POST https://...-collector.../reprocess \
  -H "Content-Type: application/json" \
  -d '{"dry_run": false, "max_items": 50}'  # Start with 50 for testing
```

### Monitor
```bash
# Watch queue depth (should spike then drop)
watch -n 5 'az storage queue peek --queue-name content-processing-requests | wc -l'

# Watch processor replicas (should scale 0 → 3)
watch -n 5 'az containerapp replica list --name processor | wc -l'

# Watch processed items (should grow steadily)
watch -n 10 'az storage blob list --container-name processed-content | wc -l'

# Watch site files (should appear after ~2-3 min)
watch -n 15 'az storage blob list --container-name $web | wc -l'
```

### Validate Results
```bash
# Check a few generated files
az storage blob list --container-name '$web' --prefix articles/ | head -10

# Verify ASCII-only filenames
az storage blob list --container-name '$web' --prefix articles/ | \
  grep -P '[^\x00-\x7F]'  # Should be empty

# Check index.html exists
az storage blob show --container-name '$web' --name index.html
```

---

## ✅ Decision Needed

**Choose before triggering reprocess**:

1. **Fix queue handling** (2 hours work, proper scaling)
2. **Accept discovery mode** (works now, imperfect scaling)

**My recommendation**: Option 2 for now (accept current behavior), fix properly in next iteration.

**Why**: 
- Site generation IS correct (uses processor metadata)
- Scaling is suboptimal but functional
- Testing with 50-100 items will reveal any issues
- Can fix queue handling after validating end-to-end flow

---

**Status**: Ready for reprocess test with Option 2 approach
