# Site Generator Architecture Review - Queue Processing Flow

**Date:** October 2, 2025  
**Reviewer:** GitHub Copilot  
**Focus:** JSON → Markdown → HTML processing via single queue

---

## 🎯 Current Architecture Summary

### Components Reviewed
1. **storage_queue_router.py** - Queue message processing logic
2. **content_processing_functions.py** - Markdown and HTML generation
3. **queue_processor.py** - Queue message handling (recently fixed)
4. **Infrastructure** - KEDA scaling configuration
5. **functional_config.py** - Queue configuration

---

## ✅ What's Working Correctly

### 1. **KEDA Scaling Configuration**
```terraform
custom_scale_rule {
  name             = "storage-queue-scaler"
  custom_rule_type = "azure-queue"
  metadata = {
    queueName   = "site-generation-requests"
    queueLength = "1"  # Immediate processing
  }
}
```
✅ Container scales from 0 → 1 when message arrives  
✅ Single queue: `site-generation-requests`  
✅ Min replicas: 0, Max replicas: 2

### 2. **Content Type Routing** (Lines 44-154 in storage_queue_router.py)
The router correctly handles three paths:

**Path A: JSON Only** (`content_type: "json"`)
```python
if content_type == "json":
    # Generate markdown from JSON
    mr = await generate_markdown_batch(...)
    markdown_files = mr.files_generated
    # ❌ STOPS HERE - No HTML generation
```

**Path B: Markdown Only** (`content_type: "markdown"`)
```python
elif content_type == "markdown":
    # Generate HTML from existing markdown
    site_result = await generate_static_site(...)
    # ✅ Complete
```

**Path C: Auto/Legacy** (no content_type specified)
```python
else:
    # Markdown first
    mr = await generate_markdown_batch(...)
    # Then HTML (if markdown was created)
    if markdown_files > 0:
        site_result = await generate_static_site(...)
```

### 3. **Queue Message Handling**
✅ Uses standardized `QueueMessageModel` from libs  
✅ Properly processes `wake_up` and `generate_site` operations  
✅ Returns detailed processing results

---

## ❌ Critical Gap Identified

### **Missing: JSON → Markdown → HTML Chain**

**THE PROBLEM:**
When `content_type: "json"` is processed:
1. ✅ JSON is converted to Markdown
2. ✅ Markdown files are saved to blob storage
3. ❌ **NO follow-up queue message is sent**
4. ❌ HTML generation never happens automatically
5. ❌ Site remains outdated until manual trigger

**Current Behavior:**
```
content-processor → queue message → site-generator
                    (content_type: json)
                                     ↓
                              Generate Markdown
                                     ↓
                                  STOPS ❌
```

**Expected Behavior:**
```
content-processor → queue message → site-generator
                    (content_type: json)
                                     ↓
                              Generate Markdown
                                     ↓
                          Send queue message ✅
                    (content_type: markdown)
                                     ↓
                              Generate HTML
                                     ↓
                                 Complete ✅
```

---

## 🤔 Architectural Decision Required

### Option 1: Two-Stage Queue (Recommended ✅)

**Implementation:**
```python
# In generate_markdown_batch() after successful generation:
if markdown_files > 0:
    from libs.queue_client import get_queue_client, QueueMessageModel
    
    queue_client = get_queue_client("site-generation-requests")
    message = QueueMessageModel(
        service_name="site-generator",
        operation="wake_up",
        payload={
            "content_type": "markdown",
            "markdown_files": markdown_files,
            "trigger": "markdown_completion",
            "correlation_id": generator_id
        }
    )
    await queue_client.send_message(message)
```

**Pros:**
- ✅ Clear separation of concerns (JSON→MD is one task, MD→HTML is another)
- ✅ Can scale markdown and HTML generation independently
- ✅ Failed HTML generation doesn't require re-generating markdown
- ✅ Aligns with event-driven architecture
- ✅ Easy to monitor and debug (each stage has distinct logs)
- ✅ Supports batch processing (accumulate markdown, generate HTML once)

**Cons:**
- ⚠️ Slightly more complex (two queue messages instead of one)
- ⚠️ Tiny cost increase (~$0.0001 per message for Storage Queue)
- ⚠️ Need to handle queue message delivery failures

### Option 2: Single-Stage Processing

**Implementation:**
```python
# In storage_queue_router.py _process_queue_request():
if content_type == "json":
    # Generate markdown
    mr = await generate_markdown_batch(...)
    markdown_files = mr.files_generated
    
    # Immediately generate HTML if markdown was created
    if markdown_files > 0:
        site_result = await generate_static_site(...)
```

**Pros:**
- ✅ Simpler - everything happens in one wake-up
- ✅ No queue message sending needed
- ✅ Guaranteed completion (no intermediate failures)

**Cons:**
- ❌ Long processing time (JSON→MD→HTML all at once)
- ❌ KEDA timeout issues if processing takes too long
- ❌ Container must stay warm for entire pipeline
- ❌ Can't scale stages independently
- ❌ Failed HTML generation requires reprocessing JSON→MD
- ❌ Creates dependency between unrelated operations

---

## 💡 Recommended Solution: Two-Stage Queue

### Why This is Better Architecture

1. **Resilience:** If HTML generation fails, markdown is already saved - just retry HTML
2. **Scalability:** KEDA can spawn multiple instances for HTML generation if many markdown files accumulate
3. **Cost Efficiency:** Container can shut down between stages (markdown complete → scale to zero → wake for HTML)
4. **Monitoring:** Clear metrics for each stage (markdown generation time vs HTML generation time)
5. **Future-Proof:** Easy to add more stages (e.g., markdown → optimize images → generate HTML)

### Implementation Changes Required

#### 1. **Add Queue Message Sending to `generate_markdown_batch()`**

```python
# In content_processing_functions.py after line 177
async def generate_markdown_batch(
    source: str,
    blob_client: SimplifiedBlobClient,
    config: Dict[str, Any],
    batch_size: int = 10,
    force_regenerate: bool = False,
    generator_id: str = "",
    send_html_trigger: bool = True,  # NEW parameter
) -> GenerationResponse:
    # ... existing code ...
    
    # After successful markdown generation (after line 177):
    if generated_files and send_html_trigger:
        await _trigger_html_generation(
            markdown_files=generated_files,
            queue_name=config.get("QUEUE_NAME", "site-generation-requests"),
            generator_id=generator_id
        )
    
    return GenerationResponse(...)
```

#### 2. **Add Helper Function for Queue Triggering**

```python
# New function in content_processing_functions.py
async def _trigger_html_generation(
    markdown_files: List[str],
    queue_name: str,
    generator_id: str
) -> None:
    """Send queue message to trigger HTML generation from markdown."""
    try:
        from libs.queue_client import get_queue_client, QueueMessageModel
        
        message = QueueMessageModel(
            service_name="site-generator",
            operation="wake_up",
            payload={
                "content_type": "markdown",
                "markdown_files_count": len(markdown_files),
                "trigger": "markdown_completion",
                "correlation_id": generator_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
        async with get_queue_client(queue_name) as queue_client:
            result = await queue_client.send_message(message)
            logger.info(
                f"Triggered HTML generation: {len(markdown_files)} markdown files ready "
                f"(message_id: {result.get('message_id')})"
            )
    except Exception as e:
        logger.error(f"Failed to trigger HTML generation: {e}")
        # Don't fail the markdown generation if queue message fails
        # Operator can manually trigger HTML generation if needed
```

#### 3. **Update Router to Prevent Double-Triggering**

```python
# In storage_queue_router.py line 78-90
if content_type == "json":
    # Only create markdown - HTML will be triggered via queue
    mr = await generate_markdown_batch(
        source="storage-queue-trigger",
        batch_size=articles_generated or 10,
        force_regenerate=payload.get("force_regenerate", False),
        blob_client=context["blob_client"],
        config=context["config_dict"],
        generator_id=payload.get("correlation_id") or context["generator_id"],
        send_html_trigger=True,  # Let it send the follow-up message
    )
```

---

## 🔒 Dependency Analysis

### Is This Creating a Dependency?

**Short Answer:** No - it's creating proper **event-driven decoupling**.

**Long Answer:**
- Markdown generation **completes successfully** before sending queue message
- If queue message fails, markdown is still saved (operator can manually trigger HTML)
- HTML generation is **independent** - it only reads markdown, doesn't touch JSON
- Container can scale to zero between stages
- No circular dependencies (one-way: JSON → MD → HTML)

### Circular Dependency Check ✅
```
site-generator → queue → site-generator (different content_type)
       ↓                        ↓
   JSON→MD                   MD→HTML
```
This is **NOT circular** because:
- Different operations (markdown vs HTML)
- One-way flow (JSON never depends on HTML)
- Self-contained stages (each can run independently)

---

## 📊 Performance Impact

### Current (Broken) Flow
```
content-processor sends message → site-generator wakes
  → generates markdown (30s)
  → shuts down
  → HTML never generated ❌
```

### Proposed (Fixed) Flow
```
content-processor sends message → site-generator wakes
  → generates markdown (30s)
  → sends queue message
  → shuts down
  → KEDA detects new message
  → site-generator wakes again
  → generates HTML (60s)
  → shuts down
```

**Total Container Runtime:** ~90 seconds (spread across 2 wake-ups)  
**Total Wall Time:** ~95 seconds (5s between stages)  
**Extra Cost:** ~$0.0001 per queue message  
**Benefit:** Complete automation ✅

---

## 🎯 Recommendation

### ✅ **Implement Two-Stage Queue Processing**

**Reasons:**
1. Aligns with event-driven architecture principles
2. Provides resilience and independent scaling
3. Minimal cost increase (<$1/month even at high volume)
4. Future-proof for pipeline extensions
5. Better monitoring and debugging
6. No circular dependencies created
7. **Required to make the system actually work end-to-end**

### 🚫 **Avoid Single-Stage Processing**

**Reasons:**
1. Creates tight coupling between unrelated operations
2. Long processing times risk KEDA timeouts
3. Failed HTML generation requires full reprocessing
4. Can't scale stages independently
5. Container must stay warm for entire pipeline (higher cost)

---

## 📝 Action Items

### Immediate (Required for System to Work)
- [ ] Add `_trigger_html_generation()` helper function
- [ ] Update `generate_markdown_batch()` to send queue message
- [ ] Add `send_html_trigger` parameter with default `True`
- [ ] Update tests to cover queue message sending
- [ ] Update documentation with two-stage flow

### Future Enhancements
- [ ] Add queue message retry logic with exponential backoff
- [ ] Add dead-letter queue for failed messages
- [ ] Add metrics for stage transitions
- [ ] Consider batch accumulation (wait for N markdown files before triggering HTML)

---

## 📚 References

- **Queue Client Implementation:** `libs/queue_client.py`
- **Storage Queue Router:** `containers/site-generator/storage_queue_router.py`
- **Content Processing:** `containers/site-generator/content_processing_functions.py`
- **KEDA Configuration:** `infra/container_apps.tf` (lines 545-560)
- **Queue Processor Fix:** Just completed (lines 117-120 and 150-153)

---

## ✨ Conclusion

**Current State:** System only completes JSON → Markdown, leaving HTML generation as manual step  
**Root Cause:** Missing queue message to trigger HTML generation after markdown completion  
**Solution:** Add queue message sending after successful markdown generation  
**Impact:** Completes the automation pipeline without creating problematic dependencies  
**Cost:** Negligible (~$0.0001 per message)  
**Complexity:** Low - leverages existing queue infrastructure  

**Verdict:** ✅ Two-stage queue processing is the correct architectural choice.
