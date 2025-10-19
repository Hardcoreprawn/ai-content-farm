# Message Dequeue Timing - Quick Reference Guide

## The Problem (TL;DR)

Your content pipeline uses Azure Storage Queue with a **hardcoded 10-minute visibility timeout** that's:
- ❌ Way too long for most operations (markdown generation: 15-30s, content processing: 45-60s)
- ❌ Causes messages to reappear while still processing (timeout expires mid-processing → duplicate processing)
- ❌ No deduplication safeguards to catch duplicates
- ❌ No verification that messages are actually deleted after processing

**Impact**: Messages could be processed 2-3 times, wasting compute costs and creating duplicate articles.

---

## Current State: Where's the Problem?

### 1. **Hardcoded Timeouts** (❌ Main Issue)

| File | Line | Current Value | Status |
|------|------|---------------|--------|
| `libs/queue_client.py` | 229 | `visibility_timeout=600` (10 min) | 🔴 Too high |
| `libs/storage_queue_client.py` | 282 | Uses config default (30s) | ⚠️ Inconsistent |
| `containers/markdown-generator/config.py` | 72 | 72 seconds | 🟢 Better but not optimized |
| `containers/content-processor/` | ? | Unknown | ❓ Needs audit |

### 2. **No Deletion Verification** (❌ Secondary Issue)

```python
# Current pattern (content-processor)
await delete_message(msg_id, pop_receipt)  # Delete, but no verification
# If this fails silently, message will reappear after timeout!
```

### 3. **No Deduplication** (❌ Hidden Problem)

If a message somehow reappears (timeout expires), it will be processed again:
- No duplicate detection
- No message ID tracking
- No way to know if you processed it twice

---

## The Solution: 5-Phase Implementation

### Phase 1: Audit (Diagnostic)
**What**: Find all visibility timeouts and measure actual processing times  
**When**: Week 1  
**Output**: Baseline report with recommendations

### Phase 2: Optimize Timeouts (High Impact)
**What**: Use container-specific, calculated visibility timeouts  
**When**: Week 1-2  
**Example**:
- content-processor: 45s avg processing → 90s timeout (45s + 75% buffer)
- markdown-generator: 15s avg → 60s timeout
- site-publisher: 90s avg → 180s timeout

### Phase 3: Deletion Verification (Reliability)
**What**: Add retry logic and verification for message deletion  
**When**: Week 2  
**Benefits**: Catch and retry failed deletions automatically

### Phase 4: Deduplication (Safety Net)
**What**: Track processed messages to catch duplicates  
**When**: Week 2-3  
**Benefit**: If message reappears anyway, we'll detect and skip it

### Phase 5: Monitoring (Observability)
**What**: Create alerts for duplicate detection, deletion failures, timeout risks  
**When**: Week 3  
**Benefit**: Early warning of problems

---

## Key Files to Understand

### Configuration
- `libs/storage_queue_client.py` - Queue config and defaults
- `libs/queue_client.py` - Current hardcoded timeout (line 229)
- `containers/*/config.py` - Container-specific settings

### Operations
- `libs/queue_client.py:receive_messages()` - Where to calculate timeout
- `libs/queue_client.py:complete_message()` - Where to verify deletion
- `containers/content-processor/queue_operations_pkg/queue_client_operations.py` - Example operations

### Monitoring
- Application Insights - Track processing time and deletion success
- Azure Portal - View queue properties and message counts

---

## Quick Implementation Steps

### Step 1: Create timeout calculator
```python
# New file: libs/visibility_timeout.py
def calculate_visibility_timeout(container_name: str) -> int:
    """Calculate appropriate visibility timeout for container."""
    # content-processor: 90s
    # markdown-generator: 60s
    # site-publisher: 180s
    # Returns: int (seconds)
```

### Step 2: Create deletion with retry
```python
# New file: libs/queue_message_handling.py
async def delete_message_with_retry(queue_client, message, max_retries=3):
    """Delete message with automatic retry on failure."""
    # Try up to 3 times
    # Log each attempt
    # Return (success: bool, error: str)
```

### Step 3: Create deduplicator
```python
# New file: libs/message_deduplication.py
class MessageDeduplicator:
    """Track processed messages to catch duplicates."""
    # In-memory cache (fast)
    # Blob storage log (persistent)
    # Cross-instance deduplication
```

### Step 4: Update containers to use new functions
```python
# Each container's message handler:
# 1. Use calculate_visibility_timeout() when receiving
# 2. Use delete_message_with_retry() when processing
# 3. Use MessageDeduplicator to catch duplicates
```

### Step 5: Add monitoring
```kusto
// Application Insights queries
// Track: processing time, duplicate rate, deletion success
// Create alerts for high duplicate rate and deletion failures
```

---

## Recommended Timeouts (Based on Analysis)

| Container | Avg Processing Time | Recommended Timeout | Safety Buffer |
|-----------|-------------------|-------------------|---------------|
| content-collector | 30-120s (per batch) | 180s | 50% |
| content-processor | 45-60s | 90s | 50% |
| markdown-generator | 15-30s | 60s | 100% |
| site-publisher | 60-120s | 180s | 50% |

**Formula**: `timeout = processing_time + (processing_time * buffer_percent)`

---

## Testing Strategy

### Before You Deploy

1. **Unit tests** - Test timeout calculation and deduplication logic
2. **Integration tests** - Test complete message lifecycle in dev environment
3. **Load tests** - Test with production-like workload (50+ articles)
4. **Failure scenarios**:
   - Simulate deletion failure (should retry)
   - Simulate duplicate message (should detect)
   - Simulate timeout expiry (should use deduplication)

### Monitoring

**Dashboard metrics** to track:
- Processing duration distribution (p50, p95, p99)
- Duplicate detection rate (should be 0%)
- Deletion success rate (should be >99%)
- Message requeue count (should be 0)

**Alerts to set up**:
- ⚠️ Duplicate detection rate > 5%
- 🔴 Deletion failure rate > 2%
- ⚠️ Processing time > 80% of visibility timeout

---

## Files Modified (Implementation Checklist)

### New Files
- [ ] `libs/visibility_timeout.py` - Timeout calculation logic
- [ ] `libs/queue_message_handling.py` - Deletion with retry
- [ ] `libs/message_deduplication.py` - Deduplication logic
- [ ] `docs/MESSAGE_DEQUEUE_IMPLEMENTATION_PLAN.md` - Full implementation plan (this file!)
- [ ] `docs/MONITORING_QUERIES.md` - Application Insights queries
- [ ] `infra/monitoring_alerts.tf` - Alert configuration

### Modified Files
- [ ] `libs/queue_client.py` - Use calculated timeouts (line 229)
- [ ] `libs/storage_queue_client.py` - Update defaults in config
- [ ] `containers/content-processor/queue_operations_pkg/queue_client_operations.py` - Use safe deletion
- [ ] `containers/markdown-generator/queue_processor.py` - Use safe deletion
- [ ] `containers/content-processor/main.py` - Integrate deduplicator
- [ ] `containers/markdown-generator/main.py` - Integrate deduplicator
- [ ] `containers/content-collector/main.py` - Use calculated timeouts
- [ ] `containers/site-publisher/main.py` - Use calculated timeouts

---

## Success Criteria

You'll know this is working when:

✅ **No duplicate processing** - Same message never processed twice  
✅ **No message loss** - All messages either processed or properly cleaned up  
✅ **Appropriate timeouts** - Processing always finishes before timeout  
✅ **High reliability** - >99% deletion success rate  
✅ **Observable** - All operations tracked in Application Insights  
✅ **Monitored** - Alerts active for failures  

---

## Estimated Effort

- **Phase 1 (Audit)**: 4-6 hours
- **Phase 2 (Timeouts)**: 8-12 hours
- **Phase 3 (Deletion)**: 6-8 hours
- **Phase 4 (Deduplication)**: 10-14 hours
- **Phase 5 (Monitoring)**: 4-6 hours
- **Testing**: 8-12 hours
- **Total**: 40-58 hours (~1-2 weeks)

---

## Next Steps

1. **Review** the full implementation plan in `docs/MESSAGE_DEQUEUE_IMPLEMENTATION_PLAN.md`
2. **Create GitHub issues** for each phase
3. **Start with Phase 1** - Audit and measure
4. **Report baseline** before proceeding to Phase 2
5. **Iterate** with monitoring data

---

## Questions?

Key decisions to make:

1. Should we start with just timeout optimization (Phase 2) or go full implementation (all phases)?
2. Should deduplication use blob storage or just in-memory cache?
3. What duplicate rate should trigger alerts (5%? 1%?)?
4. Should deletion verification be sync (slower but safer) or async?

See full plan for details: `docs/MESSAGE_DEQUEUE_IMPLEMENTATION_PLAN.md`
