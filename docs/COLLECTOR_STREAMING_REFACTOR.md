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

## Phase 2: Quality Integration ✅ COMPLETE

### Quality Module Created (200 lines, 20 tests)

**quality/review.py**
- `validate_item(item)` - Check required fields: id, title, content, source
- `check_readability(item)` - Filters: min title/content length, readable text
- `check_technical_relevance(item)` - Filters: tech keywords, off-topic sources
- `review_item(item, check_relevance=True)` - Complete review pipeline
  - Returns: (passes: bool, reason: Optional[str])
  - Pure sync function (no I/O)

**Integration into stream.py**
- Call `review_item()` after collect, before dedup
- Track rejected_quality stat
- Log rejection reason for debugging

### Tests Created (20 tests, all passing)

**tests/test_quality_review.py**
- 5 validation tests (required fields, types, structure)
- 5 readability tests (length, content quality, markup detection)
- 4 technical relevance tests (keywords, off-topic sources)
- 5 integration tests (full pipeline, mixed items)

**Result**: All 37 Phase 1+2 tests passing

---

## Phase 3: HTTP Endpoint for Manual Testing & Debugging

### Purpose
Manual collection trigger for:
- Testing new subreddit/instance sources before adding to templates
- Debugging quality filters on specific sources
- Ad-hoc collection runs (one-off verification)
- NOT used in production (templates use KEDA timer instead)

### Design: Simple Sync HTTP Endpoint

Container App serves HTTP endpoint directly:
- Accept parameters (subreddits, instances, filters)
- Run collection immediately in request context
- Return results with stats
- Fast enough for manual testing

```
HTTP POST /collect
  ↓
Validate auth header
  ↓
Validate payload
  ↓
Run streaming pipeline (collect → review → dedupe → queue)
  ↓
Return: 200 OK with stats
{
  "status": "complete",
  "stats": {
    "collected": 42,
    "published": 38,
    "rejected_quality": 3,
    "rejected_dedup": 1
  },
  "collection_id": "manual_abc123"
}
```

### File Structure

```
containers/content-collector/
├── endpoints/
│   ├── __init__.py
│   └── collect.py         # POST /collect handler
│
├── auth/
│   ├── __init__.py
│   └── validate_auth.py   # API key validation
```

### Authentication

**Simple API Key** (via environment variable):
- Request header: `x-api-key: <COLLECTION_API_KEY>`
- Key stored in Key Vault, injected as env var to container
- Used only for manual testing (not production-critical)
- Can be rotated by updating container env var

```python
# Example validation
def validate_api_key(headers: Dict[str, str]) -> bool:
    provided_key = headers.get("x-api-key", "").strip()
    expected_key = os.getenv("COLLECTION_API_KEY")
    return provided_key == expected_key if expected_key else False
```

### Endpoint: POST /collect

**Purpose**: Manual collection trigger with immediate results

```python
async def collect_handler(request):
    """
    HTTP endpoint for manual collection testing.
    
    Request:
    POST /collect
    Headers: x-api-key: <key>
    Body:
    {
        "subreddits": ["programming"],
        "min_score": 25,
        "max_items": 50
    }
    
    Response:
    {
        "status": "complete",
        "collection_id": "manual_abc123",
        "stats": {
            "collected": 42,
            "published": 38,
            "rejected_quality": 3,
            "rejected_dedup": 1
        }
    }
    """
    # 1. Validate auth
    if not validate_api_key(request.headers):
        return 401 {"error": "Invalid API key"}
    
    # 2. Parse and validate payload
    try:
        payload = request.get_json()
    except:
        return 400 {"error": "Invalid JSON"}
    
    is_valid, error = validate_trigger_payload(payload)
    if not is_valid:
        return 400 {"error": error}
    
    # 3. Create collector
    collection_id = f"manual_{uuid4().hex[:8]}"
    
    if payload.get("subreddits"):
        collector = collect_reddit(
            subreddits=payload["subreddits"],
            min_score=payload.get("min_score", 25),
            max_items=payload.get("max_items", 50)
        )
    elif payload.get("instances"):
        collector = collect_mastodon(
            instance=payload["instances"][0],
            max_items=payload.get("max_items", 50)
        )
    else:
        return 400 {"error": "No sources provided"}
    
    # 4. Run streaming pipeline (blocks during request)
    stats = await stream_collection(
        collector_fn=collector,
        collection_id=collection_id,
        collection_blob=f"manual-tests/{datetime.now(timezone.utc).isoformat()}.json",
        blob_client=blob_client,
        queue_client=queue_client
    )
    
    # 5. Return results
    return 200 {
        "status": "complete",
        "collection_id": collection_id,
        "stats": stats
    }
```

### Example Usage

```bash
# Test new subreddit before adding to templates
curl -X POST http://localhost:8000/collect \
  -H "x-api-key: $COLLECTION_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "subreddits": ["newsubreddit"],
    "min_score": 25,
    "max_items": 10
  }'

# Response
{
  "status": "complete",
  "stats": {
    "collected": 8,
    "published": 7,
    "rejected_quality": 1,
    "rejected_dedup": 0
  },
  "collection_id": "manual_abc12345"
}

# Verify results in blob storage
az storage blob list \
  --account-name aicontentprodsa \
  --container-name manual-tests \
  --output table
```

### Testing Strategy

1. **Unit tests**: Payload validation, auth, message creation (25 tests ✅)
2. **Integration tests**: HTTP endpoint flow (validate → collect → queue)
3. **Manual tests**: Curl against local/staging endpoint
4. **Debugging**: Use collection_id to find blob results, verify quality filtering

### Container App Setup

- Add endpoint route in app.py or FastAPI handler
- Inject COLLECTION_API_KEY env var from Key Vault
- No special infrastructure needed (runs in existing container)
- Request timeout: 30-60 seconds (manual testing is not time-critical)

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
