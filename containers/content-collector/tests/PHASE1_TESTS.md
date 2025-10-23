# Phase 1: Core Functions - Test-First Implementation

**Status**: Tests Created - Ready for Implementation  
**Files Created**: 3 test files with 50+ test cases  
**Implementation Order**: Follow this sequence

---

## Test Files Created

### 1. `tests/test_collectors_stream.py` (350+ lines)
**What to test**: Pure async generator collection functions

**Test Classes**:
- `TestCollectRedditGenerator` - Reddit streaming with quality filtering
- `TestCollectMastodonGenerator` - Mastodon streaming
- `TestStandardizeFormat` - Item format conversion
- `TestCollectorIntegration` - Multiple sources, lazy evaluation

**Key Tests**:
- ✅ Items have standardized format (id, title, content, source, metadata, collected_at)
- ✅ Min score filter works (Reddit >= 25)
- ✅ Min boosts filter works (Mastodon >= 5)
- ✅ Max items limit respected
- ✅ Rate limiting delay applied between subreddits
- ✅ Async generator is lazy (doesn't fetch until iterated)
- ✅ Reddit/Mastodon metadata fields preserved

**Required Implementation**:
```
collectors/
├── collect.py
│   ├── collect_reddit(subreddits, sort, min_score, max_items) → AsyncIterator
│   ├── collect_mastodon(instance, timeline, min_boosts, max_items) → AsyncIterator
│   └── rate_limited_get(url) → async context manager
│
└── standardize.py
    ├── standardize_reddit_item(raw) → dict (standardized)
    └── standardize_mastodon_item(raw, instance) → dict (standardized)
```

---

### 2. `tests/test_rate_limit.py` (250+ lines)
**What to test**: Token bucket + exponential backoff rate limiter

**Test Classes**:
- `TestRateLimiter` - Core token bucket logic
- `TestRedditRateLimiter` - Reddit-specific config
- `TestRateLimitContext` - Async context manager
- `TestRateLimiterEdgeCases` - Error handling

**Key Tests**:
- ✅ Token acquisition with rate limiting
- ✅ Exponential backoff on 429 errors (2.0 → 4.0 → 8.0...)
- ✅ Retry-After header respected
- ✅ Backoff resets after success
- ✅ Respects max backoff (300s)
- ✅ Multiple instances independent
- ✅ Concurrent acquires work correctly

**Required Implementation**:
```
pipeline/
└── rate_limit.py
    ├── class RateLimiter
    │   ├── __init__(requests_per_minute, backoff_multiplier, max_backoff)
    │   ├── async acquire() → None
    │   ├── handle_429(retry_after=None) → None
    │   ├── reset_backoff() → None
    │   └── __aenter__/__aexit__ (context manager)
    │
    ├── create_reddit_limiter() → RateLimiter
    └── create_mastodon_limiter() → RateLimiter
```

---

### 3. `tests/test_streaming_pipeline.py` (400+ lines)
**What to test**: Streaming orchestration + message format (CRITICAL)

**Test Classes**:
- `TestMessageFormatCompatibility` - **CRITICAL**: Message format for content-processor
- `TestStreamingPipeline` - Core streaming flow
- `TestStreamingIntegration` - End-to-end behavior

**Key Tests**:
- ✅ **CRITICAL**: Message has exact fields for content-processor
  - operation="process_topic"
  - service_name="content-collector"
  - timestamp, correlation_id
  - payload: topic_id, title, source, collection_id, collection_blob
  - Optional: subreddit, upvotes, comments, url
- ✅ Quality gate integration filters low-quality items
- ✅ Deduplication prevents duplicate publishing
- ✅ Items saved to blob storage
- ✅ Items sent to queue for processor
- ✅ Statistics returned (collected, published, rejected_quality, rejected_dedup)
- ✅ Error handling (continues on individual item errors)
- ✅ Lazy evaluation (generator pattern)

**Required Implementation**:
```
pipeline/
├── stream.py
│   ├── async stream_collection(
│   │       collector_fn,
│   │       collection_id,
│   │       collection_blob,
│   │       blob_client,
│   │       queue_client
│   │   ) → dict (stats)
│   │
│   ├── create_queue_message(item, context) → dict (for processor)
│   ├── review_item(item) → dict (with quality metadata)
│   └── CollectionStats namedtuple
│
└── dedup.py
    ├── async is_seen(item_hash, blob_client) → bool
    ├── async mark_seen(item_hash, blob_client) → bool
    └── hash_content(title, content) → str
```

---

## Implementation Roadmap

### Step 1: Create Module Structure
```bash
mkdir -p containers/content-collector/pipeline
mkdir -p containers/content-collector/collectors
mkdir -p containers/content-collector/storage
mkdir -p containers/content-collector/quality

# Create __init__.py files
touch containers/content-collector/pipeline/__init__.py
touch containers/content-collector/collectors/__init__.py
touch containers/content-collector/storage/__init__.py
touch containers/content-collector/quality/__init__.py
```

### Step 2: Implement Phase 1 Files (in order)
1. **`collectors/collect.py`** (350 lines)
   - `collect_reddit()` - async generator with min_score filter
   - `collect_mastodon()` - async generator with min_boosts filter
   - `rate_limited_get()` - context manager for HTTP requests

2. **`collectors/standardize.py`** (200 lines)
   - `standardize_reddit_item()` - convert raw Reddit to standard format
   - `standardize_mastodon_item()` - convert raw Mastodon to standard format
   - Item validation helper

3. **`pipeline/rate_limit.py`** (200 lines)
   - `RateLimiter` class - token bucket + exponential backoff
   - `create_reddit_limiter()` - Reddit-specific config
   - `create_mastodon_limiter()` - Mastodon-specific config

4. **`pipeline/stream.py`** (350 lines)
   - `stream_collection()` - main orchestration
   - `create_queue_message()` - **preserve exact format**
   - `review_item()` - quality gate integration (use existing quality_gate.py)
   - `CollectionStats` - statistics tracking

5. **`pipeline/dedup.py`** (250 lines)
   - Move existing dedup logic from `quality_dedup.py`
   - `hash_content()` - create item hash
   - `is_seen()` - check blob storage
   - `mark_seen()` - mark item as seen
   - 14-day window implementation

### Step 3: Run Tests
```bash
cd containers/content-collector
PYTHONPATH=/workspaces/ai-content-farm python -m pytest tests/test_collectors_stream.py -v
PYTHONPATH=/workspaces/ai-content-farm python -m pytest tests/test_rate_limit.py -v
PYTHONPATH=/workspaces/ai-content-farm python -m pytest tests/test_streaming_pipeline.py -v
```

### Step 4: Fix Imports
- Update module imports in each file
- Create package __init__.py files
- Configure PYTHONPATH correctly

---

## Key Design Constraints

**From Tests**:
1. ✅ All functions are PURE (no mutation of inputs)
2. ✅ All collection is via ASYNC GENERATORS (not batch)
3. ✅ Message format is EXACT for content-processor compatibility
4. ✅ Quality filtering during collection (not after)
5. ✅ Dedup via blob storage (14-day window)
6. ✅ Rate limiting with exponential backoff

**Configuration** (from tests):
```python
REDDIT_MIN_SCORE = 25
REDDIT_MAX_PER_SUBREDDIT = 25
MASTODON_MIN_BOOSTS = 5
MASTODON_MIN_FAVOURITES = 10
DEDUP_WINDOW_DAYS = 14

REDDIT_DELAY_SECONDS = 2.0
REDDIT_MAX_BACKOFF = 300.0
MASTODON_DELAY_SECONDS = 1.0
```

---

## Success Criteria

**Phase 1 Complete When**:
- [ ] All 3 test files pass (50+ test cases)
- [ ] No import errors (modules exist and import correctly)
- [ ] Message format test passes (critical for processor compatibility)
- [ ] Rate limiter test passes (backoff logic correct)
- [ ] Streaming pipeline test passes (collect → review → dedupe → save → queue)

---

## Next Steps

Once Phase 1 tests pass:
1. Phase 2: Reorganize quality_* files into quality/ directory
2. Phase 3: Create endpoints and integrate with service_logic.py
3. Phase 4: Delete old code (simple_*.py, content_processing_simple.py)
4. Phase 5: Full integration testing

---

**Last Updated**: 2025-10-21  
**Test Count**: 50+ test cases across 3 files  
**Estimated Lines of Code**: 1200+ lines (implementation)
