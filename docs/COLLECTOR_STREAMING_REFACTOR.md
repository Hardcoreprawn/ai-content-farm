# Content-Collector Streaming Refactor - Implementation Plan

**Status**: Planning Complete - Ready for Implementation  
**Branch**: `feature/quality-gate-streaming-foundation`  
**Target**: Pure functional streaming architecture  
**Timeline**: 2-3 weeks

---

## Goals

1. ✅ Stream items one-by-one (not batch)
2. ✅ Quality gate integrated into collection flow
3. ✅ Pure functions, no OOP state mutation
4. ✅ Social sources only (Reddit, Mastodon)
5. ✅ Defensive rate limiting (prevent IP blocks)
6. ✅ **CRITICAL**: Honor existing message format for content-processor

---

## Critical: Message Format Compatibility

**MUST MAINTAIN** existing queue message structure for content-processor:

```python
# Required format (from topic_fanout.py)
{
    "operation": "process_topic",
    "service_name": "content-collector",
    "timestamp": "2025-10-21T12:00:00Z",
    "correlation_id": "uuid",
    "payload": {
        "topic_id": "reddit_abc123",
        "title": "Article Title",
        "source": "reddit",
        "collected_at": "2025-10-21T12:00:00Z",
        "priority_score": 0.75,
        "collection_id": "col_xyz",
        "collection_blob": "collections/2025-10-21/col_xyz.json",
        # Optional Reddit fields:
        "subreddit": "programming",
        "url": "https://reddit.com/...",
        "upvotes": 150,
        "comments": 42
    }
}
```

**DO NOT CHANGE** this format. Content-processor depends on these exact fields.

---

## Architecture

### Current (Batch)
```
collect_all() → [100 items] → dedupe → save blob → flood queue (5 min)
```

### Target (Streaming)
```
async for item in collect():
  → review(item)
  → if pass: dedupe → save blob → send message (10 sec per item)
```

---

## Configuration (Tuned)

```python
# Collection frequency: Every 8 hours (KEDA cron - already configured)
# Quality thresholds:
REDDIT_MIN_SCORE = 25          # UP from 10 (better quality)
REDDIT_MAX_PER_SUBREDDIT = 25  # DOWN from 50 (less noise)
MASTODON_MIN_BOOSTS = 5        # UP from 3
DEDUP_WINDOW_DAYS = 14         # UP from 1 (Reddit resurrects old posts)

# Rate limiting:
REDDIT_DELAY_SECONDS = 2.0
REDDIT_MAX_BACKOFF = 300.0     # 5 min max
MASTODON_DELAY_SECONDS = 1.0   # Gentler on instances
```

---

## File Structure (New)

```
containers/content-collector/
├── collectors/
│   ├── collect.py           # NEW: Pure async generators (~350 lines)
│   └── standardize.py       # NEW: Format converters (~200 lines)
│
├── pipeline/
│   ├── stream.py            # NEW: Streaming orchestration (~350 lines)
│   ├── rate_limit.py        # NEW: Token bucket + backoff (~200 lines)
│   └── dedup.py             # MOVE from quality_dedup.py (~250 lines)
│
├── quality/                 # REORGANIZE existing quality_* files
│   ├── config.py            # KEEP as-is
│   ├── review.py            # RENAME quality_gate.py
│   ├── detectors.py         # KEEP as-is
│   └── scoring.py           # KEEP as-is
│
├── storage/
│   ├── blob_ops.py          # NEW: Append-only operations (~150 lines)
│   └── queue_ops.py         # NEW: Message sending (~100 lines)
│
├── endpoints/
│   ├── collect.py           # NEW: Streaming collection API
│   └── status.py            # NEW: Monitoring endpoint
│
└── [DELETE]
    ├── content_processing_simple.py
    ├── collectors/simple_*.py
    └── (old OOP collectors)
```

---

## Implementation Checklist

### Phase 1: Core Functions (Week 1)
- [x] Tests created (50+ test cases across 3 files)
- [ ] `collectors/collect.py` - Pure Reddit/Mastodon generators
- [ ] `collectors/standardize.py` - Item format conversion
- [ ] `pipeline/rate_limit.py` - Token bucket + exponential backoff

### Phase 2: Pipeline Integration (Week 1-2)
- [ ] `pipeline/stream.py` - Orchestrate collect → review → save → queue
- [ ] `pipeline/dedup.py` - Move from quality_dedup.py, add 14-day window
- [ ] `storage/blob_ops.py` - Append-only blob writes
- [ ] `storage/queue_ops.py` - Message sending with **exact format preservation**
- [ ] Integration tests with ephemeral Azure containers

### Phase 3: Quality Integration (Week 2)
- [ ] Reorganize quality_* into quality/ directory
- [ ] Update quality/review.py for streaming (item-level, not batch)
- [ ] Integrate review into pipeline/stream.py
- [ ] Verify quality gate scoring matches existing behavior

### Phase 4: API & Cleanup (Week 2-3)
- [ ] `endpoints/collect.py` - New streaming collection endpoint
- [ ] Update service_logic.py to use pipeline/stream.py
- [ ] **Validate message format** with content-processor integration test
- [ ] Delete old collectors (simple_*.py, content_processing_simple.py)
- [ ] Update all tests for new architecture

### Phase 5: Bluesky (Future)
- [ ] Deferred - current sources working well

---

## Critical Tests

### Message Format Test (Required)
```python
async def test_message_format_compatibility():
    """Verify messages match content-processor expectations."""
    item = {
        "id": "reddit_test",
        "title": "Test Post",
        "source": "reddit",
        "metadata": {"subreddit": "test", "score": 50}
    }
    
    message = create_topic_message(item, "col_123", "blob_path")
    
    # MUST have these exact fields
    assert message["operation"] == "process_topic"
    assert message["service_name"] == "content-collector"
    assert "timestamp" in message
    assert "correlation_id" in message
    
    payload = message["payload"]
    assert payload["topic_id"] == "reddit_test"
    assert payload["title"] == "Test Post"
    assert payload["source"] == "reddit"
    assert payload["collection_id"] == "col_123"
    assert payload["collection_blob"] == "blob_path"
    # Optional fields present when available
    assert payload.get("subreddit") == "test"
```

### Streaming Integration Test
```python
async def test_full_streaming_pipeline():
    """End-to-end: collect → review → dedupe → save → queue."""
    # Use ephemeral Azure containers for real integration
    stats = await stream_collection(
        collector_fn=collect_reddit(["test"], max_items=5),
        collection_id="test_col",
        blob_client=test_blob,
        queue_client=test_queue
    )
    
    assert stats.collected > 0
    assert stats.published > 0
    assert stats.rejected_quality >= 0
    assert stats.rejected_dedup >= 0
```

---

## Key Constraints

1. **No breaking changes** to message format (content-processor dependency)
2. **Pure functions only** (no class state mutation)
3. **File size limit**: Max 400 lines per file
4. **DRY principle**: No code duplication
5. **Defensive coding**: Handle rate limits, network errors gracefully
6. **Social sources only**: No RSS/web scraping

---

## Quality Thresholds (Updated)

```python
# Reddit
MIN_SCORE = 25              # Up from 10
MAX_PER_SUBREDDIT = 25      # Down from 50
MIN_COMMENT_RATIO = 0.05    # Comments/upvotes

# Mastodon
MIN_BOOSTS = 5              # Up from 3
MIN_FAVOURITES = 10         # Up from 5
MAX_PER_INSTANCE = 30       # Down from 40

# Deduplication
DEDUP_WINDOW_DAYS = 14      # Up from 1
```

---

## Progress Tracking

**Week 1 Goals**:
- [x] Pure collection functions tests complete (test_collectors_stream.py)
- [x] Rate limiter tests complete (test_rate_limit.py)
- [x] Streaming pipeline tests complete (test_streaming_pipeline.py)
- [ ] Implement all Phase 1 modules (5 files)

**Week 2 Goals**:
- [ ] Streaming pipeline orchestration complete
- [ ] Integration tests passing
- [ ] Message format validated with processor

**Week 3 Goals**:
- [ ] Old code deleted
- [ ] All tests updated
- [ ] PR ready for review

---

## Rollback Plan

If streaming causes issues:
1. Revert to `simple_reddit.py` collectors
2. Keep quality gate improvements
3. Add streaming in v2 after processor optimizations

---

## Success Metrics

- ✅ First item processed in <30 seconds (vs 5 minutes)
- ✅ Queue messages smooth (vs flood)
- ✅ Quality rejection rate 30-50% (filtering works)
- ✅ No rate limit blocks from Reddit/Mastodon
- ✅ All tests passing (unit + integration)
- ✅ Message format unchanged (processor compatibility)

---

**Last Updated**: 2025-10-21  
**Owner**: Content-Collector Refactor Team  
**Next Review**: After Phase 1 completion

---

## Test Files Created
- ✅ `tests/test_collectors_stream.py` (350+ lines, 15+ test cases)
- ✅ `tests/test_rate_limit.py` (250+ lines, 15+ test cases) 
- ✅ `tests/test_streaming_pipeline.py` (400+ lines, 20+ test cases)
- ✅ `tests/PHASE1_TESTS.md` (roadmap and implementation guide)
