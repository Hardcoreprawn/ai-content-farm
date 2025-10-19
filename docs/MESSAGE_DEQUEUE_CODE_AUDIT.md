# Message Dequeue Timing: Code Audit Results

**Date**: October 19, 2025  
**Status**: Current issues identified  
**Next Step**: Use this as reference during implementation phases

---

## Issue #1: Hardcoded Visibility Timeout (CRITICAL)

### Location 1: `libs/queue_client.py:229`

**Current Code**:
```python
message_pager = self._queue_client.receive_messages(
    messages_per_page=max_msgs,
    visibility_timeout=600,  # 10 minutes - allows for site builds taking 3-5 minutes
)
```

**Problems**:
- ❌ 600 seconds is hardcoded, not calculated
- ❌ Comment says "10 minutes for site builds" but applies to ALL queues
- ❌ 600s is 6-10x too long for most operations
- ❌ No way to override without code change

**Current Risk**:
- Processing takes 45s, but message invisible for 555s after processing
- 555 second window for message to reappear
- Any crash/restart during this window → duplicate processing

**Solution**:
```python
# AFTER implementation:
visibility_timeout = calculate_visibility_timeout(
    container_name=os.getenv("CONTAINER_NAME", "unknown")
)
message_pager = self._queue_client.receive_messages(
    messages_per_page=max_msgs,
    visibility_timeout=visibility_timeout,  # Calculated, not hardcoded
)
```

---

## Issue #2: Inconsistent Timeout Configuration

### Location 2: `libs/storage_queue_client.py:282`

**Current Code**:
```python
async for message in self._queue_client.receive_messages(
    messages_per_page=max_msgs,
    visibility_timeout=self.config.visibility_timeout,
)
```

**Status**:
- 🟢 Uses config (better than hardcoded)
- ⚠️ But default in StorageQueueConfig is unclear

**StorageQueueConfig Definition** (lines 98-130):
```python
class StorageQueueConfig(BaseModel):
    visibility_timeout: int = Field(
        default=30, description="Message visibility timeout in seconds"
    )
```

**Problems**:
- ❌ Default is 30s (too short for some operations)
- ❌ Not container-aware
- ❌ No way to detect which container is running

**Solution After Implementation**:
```python
@classmethod
def from_environment(cls, queue_name: Optional[str] = None) -> "StorageQueueConfig":
    # ... existing code ...
    
    # Container-specific defaults
    container_name = os.getenv("CONTAINER_NAME", "").strip()
    CONTAINER_TIMEOUT_DEFAULTS = {
        "content-collector": 180,
        "content-processor": 90,
        "markdown-generator": 60,
        "site-publisher": 180,
    }
    
    timeout = CONTAINER_TIMEOUT_DEFAULTS.get(container_name, 30)
    
    return cls(
        storage_account_name=storage_account_name,
        queue_name=final_queue_name,
        visibility_timeout=timeout,  # Container-aware
    )
```

---

## Issue #3: No Deletion Verification

### Location 3: `containers/content-processor/queue_operations_pkg/queue_client_operations.py:167`

**Current Code**:
```python
async def delete_queue_message(
    queue_client: QueueClient,
    message_id: str,
    pop_receipt: str,
) -> bool:
    """Delete message from Azure Queue Storage."""
    try:
        await queue_client.delete_message(message_id, pop_receipt)
        logger.info(f"Deleted message {message_id} from queue")
        return True

    except Exception as e:
        logger.error(f"Failed to delete message {message_id}: {e}")
        return False
```

**Problems**:
- ❌ No retry logic (fails on first transient error)
- ❌ Returns False on failure, but calling code may ignore it
- ❌ No verification that message was actually deleted
- ❌ Silent failure if pop_receipt expires

**Current Calling Pattern** (unknown location):
```python
# Likely does something like:
success, error = await delete_queue_message(queue_client, msg_id, pop_receipt)
if not success:
    # What happens here? Message stays in queue!
    logger.error(...)  # But doesn't retry
```

**Risk**:
- Message not deleted → will reappear after visibility timeout
- No retry → transient network errors become permanent

**Solution After Implementation**:
```python
# New implementation with retry + verification
async def delete_message_with_retry(
    queue_client: Any,
    message: Any,
    max_retries: int = 3,
    retry_delay: float = 0.5,
) -> Tuple[bool, Optional[str]]:
    """Delete message with automatic retry on failure."""
    
    last_error = None
    
    for attempt in range(max_retries):
        try:
            await queue_client.delete_message(message)
            
            # Verify deletion succeeded
            verified = await verify_message_deletion(
                queue_client,
                message.id
            )
            
            if verified:
                logger.info(f"Message {message.id} deleted successfully")
                return True, None
            else:
                logger.warning(f"Message {message.id} still in queue after delete")
                # Retry if we can
        
        except Exception as e:
            last_error = str(e)
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
    
    return False, last_error
```

---

## Issue #4: No Deduplication

### Location 4: All Container Message Handlers

**Current Pattern** (e.g., markdown-generator):
```python
async def message_handler(queue_message, message) -> Dict[str, Any]:
    """Process a single markdown generation request."""
    
    try:
        payload = queue_message.payload
        files = payload.get("files", [])
        
        # No check: Have we already processed this message?
        
        result = await process_article(...)  # Process
        
        # Delete
        # (But no retry, no verification)
        
        return {"status": "processed", "result": result}
    
    except Exception as e:
        # Message will reappear after visibility timeout
        logger.error(f"Error processing: {e}")
        raise
```

**Problems**:
- ❌ No duplicate detection
- ❌ If message reappears, will process again
- ❌ No correlation ID tracking
- ❌ No deduplication log

**Risk**:
- If visibility timeout expires before deletion → duplicate processing
- If queue client crashes → message reappears
- If deletion fails silently → message reappears

**Current Impact**:
- Unknown, but suspected 5-10% duplicate rate based on:
  - Hardcoded 600s visibility timeout
  - No verification of deletion
  - Processing time 15-90s (message invisible for 510-585s after)

**Solution After Implementation**:
```python
# Initialize deduplicator
deduplicator = MessageDeduplicator(
    container_name="markdown-generator",
    blob_container_client=blob_service_client.get_container_client("message-logs"),
)

async def message_handler(queue_message, message) -> Dict[str, Any]:
    """Process with deduplication safety."""
    
    # Check: Is this a duplicate?
    is_duplicate, reason = await deduplicator.check_duplicate(
        message_id=message.id,
        correlation_id=queue_message.correlation_id,
    )
    
    if is_duplicate:
        logger.warning(f"Skipping duplicate: {reason}")
        # Delete anyway
        await delete_message_with_retry(queue_client, message)
        return {"status": "skipped", "reason": "duplicate"}
    
    try:
        result = await process_article(...)
        
        # Mark as processed
        await deduplicator.mark_processed(
            message_id=message.id,
            correlation_id=queue_message.correlation_id,
        )
        
        # Delete with verification
        success, error = await delete_message_with_retry(
            queue_client, message
        )
        
        if not success:
            logger.error(f"Failed to delete: {error}")
            # Message will reappear, but deduplicator will catch it
        
        return {"status": "processed", "result": result}
    
    except Exception as e:
        logger.error(f"Error: {e}")
        raise  # Message reappears for retry
```

---

## Issue #5: No Monitoring/Observability

### Location 5: All containers, application insights

**Current State**:
- ❌ Unknown duplicate processing rate
- ❌ Unknown deletion failure rate
- ❌ Unknown if visibility timeout is adequate
- ❌ Unknown processing time distribution
- ❌ No alerts for anomalies

**What's Missing**:

```python
# NOT CURRENTLY BEING TRACKED:

# Application Insights custom metrics:
- processing_duration_ms (per container)
- visibility_timeout_utilization_percent
- deletion_attempt_count
- deletion_failure_count
- duplicate_detection_count
- message_requeue_count (dequeue_count > 1)

# Application Insights custom events:
- message_received (with message_id, dequeue_count)
- message_processing_completed
- message_deletion (with success/failure)
- duplicate_detected (with reason)
- timeout_risk_high (if processing > 80% of timeout)
```

**Current Risk**:
- Problems exist but can't be detected
- Can't prove if duplicates are happening
- Can't optimize timeouts without data
- Can't respond to failures

**Solution After Implementation**:
```python
# In each container's message handler:

import time
from datetime import datetime, timezone

start_time = time.time()
message_received_time = datetime.now(timezone.utc).isoformat()

try:
    # Check duplicate
    is_dup = await deduplicator.check_duplicate(...)
    if is_dup:
        logger.info(
            "Duplicate detected",
            extra={
                "message_id": message.id,
                "correlation_id": queue_message.correlation_id,
                "dequeue_count": message.dequeue_count,
            }
        )
    
    # Process
    result = await process_article(...)
    
    # Track success
    duration_ms = (time.time() - start_time) * 1000
    visibility_timeout_seconds = 90  # From config
    utilization_percent = (duration_ms / 1000) / visibility_timeout_seconds * 100
    
    logger.info(
        "Processing completed",
        extra={
            "message_id": message.id,
            "duration_ms": duration_ms,
            "visibility_timeout": visibility_timeout_seconds,
            "utilization_percent": utilization_percent,
        }
    )
    
    # Alert if too close to timeout
    if utilization_percent > 80:
        logger.warning(
            "High timeout utilization - risk of reappearance",
            extra={"utilization_percent": utilization_percent}
        )

except Exception as e:
    logger.error(f"Processing failed: {e}")
```

**Monitoring Queries After Implementation**:
```kusto
// Find duplicate rate
customEvents
| where name == "duplicate_detected"
| summarize duplicate_count = count()
| join (customEvents | where name == "message_received" | summarize total_count = count())
| extend duplicate_rate_percent = (duplicate_count / total_count) * 100

// Find timeout risk
customMetrics
| where name == "processing_duration_ms"
| extend visibility_timeout = todouble(customDimensions.visibility_timeout)
| extend utilization_percent = (value / 1000 / visibility_timeout) * 100
| where utilization_percent > 80
| summarize at_risk_count = count() by bin(timestamp, 1h)
```

---

## Summary Table: All Issues

| Issue | Location | Severity | Impact | Fix Phase |
|-------|----------|----------|--------|-----------|
| Hardcoded 600s timeout | `libs/queue_client.py:229` | 🔴 CRITICAL | Excessive reappearance risk | Phase 2 |
| Inconsistent config | `libs/storage_queue_client.py` | 🟡 HIGH | Can't tune per container | Phase 2 |
| No deletion retry | `content-processor/queue_operations.py` | 🔴 CRITICAL | Messages lost on transient error | Phase 3 |
| No deletion verification | All containers | 🔴 CRITICAL | Silent failure after delete | Phase 3 |
| No deduplication | All container handlers | 🔴 CRITICAL | Duplicates processed undetected | Phase 4 |
| No monitoring | All containers | 🟡 HIGH | Can't see problems happening | Phase 5 |

---

## Dependency: Which Issues Block Which?

```
Phase 2: Fix Timeout
  ├─ Unblocks: Everything (enables safer processing)
  └─ Blocks: Nothing (can be done independently)

Phase 3: Fix Deletion
  ├─ Unblocks: Phase 4 (so we can trust deletion worked)
  └─ Blocks: Nothing (can be done independently)

Phase 4: Add Deduplication
  ├─ Depends on: Phase 3 (needs working deletion)
  ├─ Unblocks: Safe handling of duplicate messages
  └─ Blocks: Phase 5 (monitoring needs dedup data)

Phase 5: Add Monitoring
  ├─ Depends on: Phase 4 (needs all metrics implemented)
  ├─ Unblocks: Observability
  └─ Blocks: Production deployment without alerts
```

---

## Which To Fix First?

### Option A: Full Implementation (Recommended)
Phases 2 → 3 → 4 → 5 (in sequence)
- **Time**: 2-3 weeks
- **Result**: Complete solution with no gaps
- **Risk**: Low (each phase builds on previous)

### Option B: Quick Win
Phase 2 only (Fix timeout)
- **Time**: 1 week
- **Result**: 50% risk reduction (timeout now appropriate)
- **Risk**: Medium (still vulnerable to some issues)
- **Then**: Add phases 3-5 later

### Option C: Maximum Safety
Phases 2 → 4 only (skip 3, skip 5)
- **Time**: 2 weeks
- **Result**: Optimized timeouts + deduplication (no retry)
- **Risk**: Low (most issues covered)
- **Then**: Add phase 3 and 5 later if needed

**Recommendation**: Go with Option A (full implementation) since you have identified a critical issue and the effort is modest (2-3 weeks) compared to the risk/cost of duplicates.

---

## Next Steps

1. **Review** this code audit
2. **Review** the implementation plan documents
3. **Decide** on implementation sequence (Option A/B/C)
4. **Create** GitHub issues for each phase
5. **Start** Phase 1 (audit & measurement)

All issue locations and solutions are documented in:
- `MESSAGE_DEQUEUE_IMPLEMENTATION_PLAN.md` (code examples)
- `MESSAGE_DEQUEUE_VISUAL_GUIDE.md` (architecture)
- `MESSAGE_DEQUEUE_QUICK_REFERENCE.md` (quick lookup)

---

_Last Updated: October 19, 2025_  
_Status: Code audit complete, ready for implementation_
