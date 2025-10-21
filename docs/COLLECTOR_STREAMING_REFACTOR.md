# Content-Collector Streaming Refactor - Implementation Plan

**Status**: Phase 1 Complete ✅ → Phase 2 In Progress  
**Branch**: `feature/quality-gate-streaming-foundation`  
**Target**: Pure functional streaming architecture  
**Timeline**: 2-3 weeks

---

## Phase 1: Core Streaming Modules ✅ COMPLETE

### Modules Created (650 lines, all passing tests)

1. ✅ **collectors/collect.py** (207 lines)
   - `collect_reddit()` - Pure async generator with quality filtering
   - `collect_mastodon()` - Pure async generator for social timeline
   - `rate_limited_get()` - Async context manager for HTTP requests
   - Uses aiohttp (async, no blocking)

2. ✅ **collectors/standardize.py** (140 lines)
   - `standardize_reddit_item()` - Convert Reddit JSON to standard format
   - `standardize_mastodon_item()` - Convert Mastodon JSON to standard format
   - `validate_item()` - Check required fields present

3. ✅ **pipeline/rate_limit.py** (140 lines)
   - `RateLimiter` class - Token bucket with exponential backoff
   - `handle_429()` - Exponential backoff on rate limit errors
   - `create_reddit_limiter()` - 30 rpm, 2.5x multiplier, 600s max
   - `create_mastodon_limiter()` - 60 rpm, 2.0x multiplier, 300s max

4. ✅ **pipeline/stream.py** (160 lines)
   - `stream_collection()` - Orchestration: collect → review → dedupe → queue
   - `create_queue_message()` - **CRITICAL**: Exact message format for content-processor
   - Returns stats: collected, published, rejected_quality, rejected_dedup

5. ✅ **pipeline/dedup.py** (150 lines)
   - `hash_content()` - SHA256 of title + content
   - `is_seen()` - Check 14-day blob window
   - `mark_seen()` - Mark content as seen
   - Defensive: fails open if blob unreachable

### Tests Created (17 tests, all passing)

1. ✅ **tests/test_rate_limit_429.py** (7 tests)
   - 429 triggers exponential backoff (1x → 2x → 4x → 8x)
   - Max backoff respected (doesn't exceed cap)
   - Retry-After header honored
   - Backoff resets after success
   - Token acquisition includes delay
   - Reddit/Mastodon limiter configs correct

2. ✅ **tests/test_async_patterns.py** (10 tests)
   - collect_reddit is async generator
   - collect_mastodon is async generator
   - rate_limited_get returns async context manager
   - stream_collection is async function
   - Dedup functions are async (I/O operations)
   - Standardize functions are pure sync (no I/O)
   - RateLimiter.acquire is async
   - No blocking I/O in async generators
   - aiohttp used (not blocking requests)

**Result**: 17 tests passing, all code quality checks passing

---

## Phase 2: Quality Integration 🚧 IN PROGRESS

### Goals

1. Move existing quality_gate.py logic → quality/review.py
2. Refactor for item-level (not batch-level) operation
3. Integrate into stream.py pipeline
4. Keep all existing quality logic intact

### File Structure

```
containers/content-collector/
├── quality/
│   ├── __init__.py
│   ├── review.py          # MOVE from quality_gate.py (item-level)
│   ├── readability.py     # Keep existing
│   ├── technical_relevance.py  # Keep existing
│   └── fact_check.py      # Keep existing
```

### Implementation Steps

1. **review.py** - Refactor review_item() for single items
   - Input: standardized item dict
   - Checks: readability, technical relevance, fact-check
   - Output: reviewed_item (with review metadata) or None (rejected)
   - No async yet (keep existing logic)

2. **Integrate into stream.py**
   - Already has placeholder: `from quality.review import review_item`
   - Call after collect, before dedup
   - Track rejected_quality stat

3. **Test integration**
   - Create test_quality_integration.py
   - Verify review_item filters correctly
   - Verify stats tracked

---

## Phase 3: API Endpoints

### Goals

1. Create HTTP endpoint for manual collection trigger
2. Support parameters: subreddits, instances, min_score, max_items
3. Return immediate response + async processing

### File Structure

```
containers/content-collector/
├── endpoints/
│   ├── __init__.py
│   └── collect.py         # HTTP POST /collect
```

### Endpoint Design

```python
# POST /collect
{
    "subreddits": ["programming", "learnprogramming"],
    "instances": ["fosstodon.org"],
    "min_score": 25,
    "max_items": 50
}

# Response (immediate)
{
    "status": "processing",
    "collection_id": "col_abc123",
    "expected_items": 50
}

# Check status: GET /collect/col_abc123
{
    "status": "processing|complete",
    "stats": {
        "collected": 42,
        "published": 38,
        "rejected_quality": 3,
        "rejected_dedup": 1
    }
}
```

---

## Phase 4: Cleanup

### Remove Old Code

- ❌ simple_reddit_collector.py
- ❌ simple_mastodon_collector.py
- ❌ content_processing_simple.py
- ❌ Old batch collection logic

### Migrate Configuration

- ✅ Collection frequency (KEDA cron already configured)
- Update collection templates to use new API

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

**TESTED**: test_message_format_compatibility validates exact fields  
**VERIFIED**: stream.py create_queue_message produces correct format

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
```

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
