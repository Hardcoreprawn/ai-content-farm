# Architecture Pivot: Single-Topic Processing

**Date**: October 8, 2025  
**Status**: IN PROGRESS  
**Impact**: Critical - Changes entire content-processor design

---

## Problem Identified

**Current Architecture (Sequential Batching)**:
```
content-collector → collection.json (100 topics) → 1 queue message
                                                      ↓
content-processor → load collection → process 100 topics sequentially
Time: 100 * 20s = 33 minutes (even with KEDA, only 1 message!)
```

**Scaling Problem**: 
- KEDA can scale to 10 processors, but only 1 queue message exists
- All 10 processors sit idle while 1 processes 100 topics sequentially
- No true parallelization despite horizontal scaling capability

---

## New Architecture (Parallel Single-Topic)

**Improved Flow**:
```
content-collector:
  → Collects 100 topics
  → Saves collection.json (audit trail)
  → Sends 100 individual queue messages (1 per topic)

Queue: 100 messages
  ↓↓↓ (KEDA scales to 10 processors)

content-processor (10 instances):
  → Each receives 1 message with 1 topic
  → Process immediately (no collection loading)
  → Generate article (20s)
  → Save and trigger markdown-generator

Time: 20s (90% faster!)
```

---

## Queue Message Format Change

**Old Format** (collection-based):
```json
{
  "operation": "process",
  "payload": {
    "blob_path": "collections/2025/10/08/file.json",
    "collection_id": "reddit_123"
  }
}
```

**New Format** (topic-based):
```json
{
  "operation": "process_topic",
  "payload": {
    "topic_id": "reddit_abc123",
    "title": "AI Breakthrough in 2025",
    "source": "reddit",
    "subreddit": "technology",
    "url": "https://reddit.com/r/technology/comments/abc123",
    "upvotes": 150,
    "comments": 75,
    "collected_at": "2025-10-08T12:00:00Z",
    "priority_score": 0.85,
    "collection_id": "reddit_123",
    "collection_blob": "collections/2025/10/08/file.json"
  }
}
```

---

## Content-Processor Changes

### Files to DELETE
- ❌ `collection_operations.py` (351 lines) - No longer need to load collections
- ❌ `test_collection_operations.py` (462 lines) - Tests for deleted module
- ❌ `topic_conversion.py` (389 lines) - Collector does conversion now
- ❌ `test_topic_conversion.py` (650+ lines) - Tests for deleted module
- ❌ `services/topic_conversion.py` (111 lines) - Old service class
- ❌ `services/topic_discovery.py` - Already removed

**Net Deletion**: ~2000 lines of unnecessary code

### Files to SIMPLIFY
- ✅ `processor.py` - Remove `process_collection_file()`, add `process_single_topic()`
- ✅ `endpoints/storage_queue_router.py` - Handle `process_topic` operation
- ✅ `models.py` - Add `TopicProcessingRequest` model

### New Processing Flow

**processor.py**:
```python
async def process_single_topic(
    self,
    topic: TopicMetadata,
    collection_id: Optional[str] = None,
) -> TopicProcessingResult:
    """
    Process a single topic from queue message.
    
    Flow:
    1. Acquire lease (prevent duplicate processing)
    2. Generate article (OpenAI)
    3. Save to processed-content
    4. Trigger markdown-generator
    5. Release lease
    6. Return result
    """
    # Much simpler - no collection loading, no iteration
    # Just process this one topic
```

---

## Benefits

### Performance
- **90% faster**: 20s instead of 33 minutes for 100 topics
- **True parallelization**: 100 topics = 100 messages = 10 processors @ 10 each
- **Better KEDA scaling**: Queue length directly reflects work items

### Code Quality
- **~2000 lines deleted**: Simpler codebase
- **No collection parsing**: Remove entire complexity layer
- **Clearer responsibilities**: 
  - Collector: Gather topics, deduplicate, queue individual items
  - Processor: Process one topic (article generation)

### Operational
- **Better observability**: Each queue message = 1 topic = 1 trace
- **Easier debugging**: Failed topics isolated in queue
- **Cost efficiency**: Processors scale up/down based on actual work
- **No blocking**: One slow topic doesn't block 99 others

---

## Migration Strategy

### Phase 1: Content-Processor (This Session)
1. ✅ Create architecture pivot document (this file)
2. Delete obsolete modules (collection_operations, topic_conversion)
3. Update `models.py` with new queue message format
4. Simplify `processor.py` for single-topic processing
5. Update `endpoints/storage_queue_router.py`
6. Update tests for new flow
7. Verify 413 baseline tests still pass (may drop to ~300 after deletions)

### Phase 2: Content-Collector (Next Session)
1. Add topic fanout after collection save
2. Send individual queue messages per topic
3. Keep collection.json save for audit trail
4. Update tests for new behavior

### Phase 3: Integration Testing
1. End-to-end test: collector → 100 messages → processor → articles
2. KEDA scaling test: Verify processors scale with queue length
3. Performance baseline: Measure actual improvement

---

## Backward Compatibility

**Question**: Should we support old collection-based messages?

**Answer**: YES, during transition period

```python
# In storage_queue_router.py
if message.operation == "process":
    # OLD FORMAT: collection blob path
    blob_path = message.payload.get("blob_path")
    if blob_path:
        # Legacy: load collection and process (slow)
        await processor.process_collection_file(blob_path)
        
elif message.operation == "process_topic":
    # NEW FORMAT: single topic data
    topic = TopicMetadata(**message.payload)
    await processor.process_single_topic(topic)
```

This allows gradual rollout without breaking existing queued messages.

---

## Risks & Mitigations

### Risk 1: Queue Message Size
- **Risk**: 100 topics = 100 messages = larger queue storage
- **Mitigation**: Azure Queue message limit is 64KB per message, our topics ~1-2KB
- **Cost**: Minimal (<$0.01/month difference)

### Risk 2: Duplicate Processing
- **Risk**: Same topic queued multiple times
- **Mitigation**: Lease mechanism already handles this (check lease before processing)
- **Additional**: Add `topic_id` to lease blob name for deduplication

### Risk 3: Ordering
- **Risk**: Topics processed out of order
- **Mitigation**: Not a concern - topics are independent, no ordering requirement

### Risk 4: Collector Complexity
- **Risk**: Collector needs to send 100 messages instead of 1
- **Mitigation**: Simple loop, already has queue client, minimal code
- **Benefit**: Collector remains responsible for deduplication (right place)

---

## Success Metrics

### Before (Current)
- Time to process 100 topics: 33 minutes
- KEDA utilization: 10% (1 processor active, 9 idle)
- Code complexity: ~2000 lines collection handling
- Failed topic isolation: None (entire batch fails)

### After (Target)
- Time to process 100 topics: **20 seconds**
- KEDA utilization: **90%+** (all processors active)
- Code complexity: **~500 lines simpler**
- Failed topic isolation: **Individual retry per topic**

---

## Next Steps

1. ✅ Document architecture pivot (this file)
2. Delete obsolete collection/topic_conversion modules
3. Update processor.py with `process_single_topic()`
4. Update queue message handling
5. Update tests
6. Verify baseline tests pass
7. Update REFACTORING_CHECKLIST.md with new plan

---

**Status**: Ready to execute Phase 1
