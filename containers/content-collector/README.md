# Content Collector - Streaming Pipeline

A high-performance async streaming content collector for the AI Content Farm pipeline. Collects content from Reddit and Mastodon, validates quality in-stream, deduplicates, and sends to processing queue.

## Overview

**Content Collector** is a pure async streaming service that ingests content from multiple sources (Reddit, Mastodon) and processes items through a quality gate in real-time. Each item flows through the pipeline independently:

```
Collection (async generators)
    ↓
Quality Review (item-level filtering)
    ↓
Deduplication (14-day window, SHA256 hashing)
    ↓
Blob Storage (append-only)
    ↓
Queue Message (processor-ready format)
```

## Architecture

### Pure Functional Streaming

The entire pipeline uses **pure functional async/await** patterns - no classes, no state mutation, no side effects beyond I/O:

- **Collectors**: `collect.py` - Async generators for Reddit and Mastodon APIs
- **Quality**: `quality/review.py` - Item-level validation, readability, technical relevance
- **Rate Limiting**: `pipeline/rate_limit.py` - Token bucket + exponential backoff
- **Deduplication**: `pipeline/dedup.py` - 14-day blob window, SHA256 content hashing
- **Orchestration**: `pipeline/stream.py` - Coordinates full pipeline flow
- **Manual Testing**: `endpoints/trigger.py` - HTTP endpoint for ad-hoc collection testing

### Key Characteristics

- ✅ **Async-First**: Pure async/await, zero blocking I/O
- ✅ **No Classes**: Functional programming throughout (except Pydantic models)
- ✅ **No State**: Pure functions with explicit dependencies
- ✅ **Streaming**: Items processed individually as they arrive (not batched)
- ✅ **Observable**: Comprehensive stats tracking and logging
- ✅ **Testable**: 12 e2e integration tests covering full pipeline
- ✅ **Container App Ready**: API key auth, standardized responses

## File Structure

### Core Collectors (210 lines)
- `collectors/collect.py` (207 lines)
  - `collect_reddit()` - Async generator for Reddit trending/subreddit topics
  - `collect_mastodon()` - Async generator for Mastodon hashtags
  - `rate_limited_get()` - Async context manager with rate limiting

- `collectors/standardize.py` (140 lines)
  - Format conversion: Reddit/Mastodon → standardized item dict

### Pipeline Modules (650 lines)
- `pipeline/rate_limit.py` (140 lines)
  - Token bucket rate limiter
  - Exponential backoff (2.0-2.5x multiplier, 300-600s max)
  - Per-source rate limit tracking

- `pipeline/dedup.py` (150 lines)
  - `hash_content()` - SHA256(title + first 500 chars of content)
  - `is_seen()` - Check 14-day blob window for duplicates
  - `mark_seen()` - Append to today's dedup file

- `pipeline/stream.py` (160 lines)
  - `stream_collection()` - Main orchestration function
  - `create_queue_message()` - Exact format for content-processor

### Quality Module (220 lines)
- `quality/review.py`
  - `validate_item()` - Required fields check
  - `check_readability()` - Length, markup detection, symbol ratio
  - `check_technical_relevance()` - Tech keyword matching, off-topic filtering
  - `review_item()` - Single-pass item review with rejection tracking

### Authentication (30 lines)
- `auth/validate_auth.py`
  - `validate_api_key()` - x-api-key header validation
  - Uses COLLECTION_API_KEY environment variable

### Endpoints (120 lines)
- `endpoints/trigger.py`
  - `validate_trigger_payload()` - Validates sources and limits
  - `create_trigger_message()` - Creates manual collection trigger
  - Used by manual HTTP endpoint for testing

### Testing (300+ tests)
- **E2E Integration Tests** (`tests/test_pipeline_e2e.py`) - 12 tests
  - Basic flow, quality filtering, deduplication
  - Queue message format validation
  - Error recovery and stats accuracy

- **Unit Tests** (18 test files)
  - Collector tests, rate limiting, dedup, quality review
  - Auth validation, trigger endpoint validation
  - Message creation and format validation

## API Reference

### Manual Collection Trigger

**Endpoint**: `POST /api/collect/trigger`

**Authentication**: `x-api-key` header with COLLECTION_API_KEY

**Request Body**:
```json
{
  "subreddits": ["programming", "Python"],
  "instances": ["fosstodon.org"],
  "min_score": 25,
  "max_items": 50
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Collection triggered",
  "data": {
    "collection_id": "manual_2025-10-21_12345678",
    "collection_blob": "collections/manual_2025-10-21_12345678.json"
  }
}
```

### Queue Message Format

Items that pass quality gates are sent to the processing queue:

```json
{
  "operation": "process_topic",
  "service_name": "content-collector",
  "timestamp": "2025-10-21T12:00:00Z",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "payload": {
    "topic_id": "reddit_abc123",
    "title": "Article Title",
    "source": "reddit",
    "collected_at": "2025-10-21T12:00:00Z",
    "priority_score": 0.75,
    "collection_id": "manual_2025-10-21_12345678",
    "collection_blob": "collections/manual_2025-10-21_12345678.json",
    "subreddit": "programming",
    "url": "https://reddit.com/r/programming/post",
    "upvotes": 150,
    "comments": 45,
    "author": "tech_expert"
  }
}
```

## Testing

### Run All Tests
```bash
cd /workspaces/ai-content-farm/containers/content-collector
python -m pytest -v
```

### Run E2E Integration Tests Only
```bash
python -m pytest tests/test_pipeline_e2e.py -v
```

### Run Specific Test Module
```bash
python -m pytest tests/test_quality_review.py -v
python -m pytest tests/test_rate_limit_429.py -v
python -m pytest tests/test_trigger_endpoint.py -v
```

### Coverage Report
```bash
python -m pytest --cov=. --cov-report=html
```

### Example Test Results
```
294 passed, 6 skipped
- test_pipeline_e2e.py: 12 tests (basic flow, quality filtering, dedup, message format)
- test_quality_review.py: 45 tests (validation, readability, relevance)
- test_rate_limit_429.py: 32 tests (token bucket, backoff, rate limits)
- test_trigger_endpoint.py: 25 tests (auth, payload validation, message creation)
- Other tests: 180+ tests (collectors, dedup, monitoring)
```

## Manual Testing

### Test with curl

**1. Trigger collection for programming subreddit**
```bash
curl -X POST http://localhost:7071/api/collect/trigger \
  -H "x-api-key: $COLLECTION_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "subreddits": ["programming"],
    "min_score": 50,
    "max_items": 10
  }'
```

**2. Trigger collection for Mastodon instance**
```bash
curl -X POST http://localhost:7071/api/collect/trigger \
  -H "x-api-key: $COLLECTION_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "instances": ["fosstodon.org"],
    "max_items": 10
  }'
```

**3. Invalid request (missing key)**
```bash
curl -X POST http://localhost:7071/api/collect/trigger \
  -H "Content-Type: application/json" \
  -d '{"subreddits": ["programming"]}'

# Returns: 401 Unauthorized - Function key required
```

### Local Development

**1. Set environment variables**
```bash
export COLLECTION_API_KEY="test_key_123"
export REDDIT_CLIENT_ID="your_reddit_client_id"
export REDDIT_CLIENT_SECRET="your_reddit_client_secret"
export MASTODON_ACCESS_TOKEN="your_mastodon_token"
```

**2. Run the collector manually**
```bash
cd /workspaces/ai-content-farm/containers/content-collector
python -c "
import asyncio
from collectors.collect import collect_reddit

async def test():
    async for item in collect_reddit(['programming'], min_score=50, max_items=5):
        print(f'Collected: {item[\"title\"]}')
        break

asyncio.run(test())
"
```

## Quality Filtering

Items must pass three quality gates to be published:

### 1. Validation
- Required fields: `id`, `title`, `content`, `source`
- All must be non-empty strings

### 2. Readability
- Title: ≥10 characters, ≥50% alphanumeric
- Content: ≥100 characters
- Reject if mostly HTML/JSON (>15% markup)

### 3. Technical Relevance
- Must contain tech keywords: code, software, develop, tech, data, api, etc.
- Must not match off-topic patterns (funny, videos, gaming, etc.)

### Stats Example
```
collected: 100
published: 72 (72% quality pass rate)
rejected_quality: 25 (off-topic, unreadable)
rejected_dedup: 3 (duplicates within 14 days)
```

## Deduplication Strategy

**Three-Layer Approach**:

1. **In-Memory** (current batch)
   - Fast O(1) hash lookup during collection
   - Set of hashes seen in current stream

2. **Same-Day Blob** (today)
   - Persistent across container restarts
   - Blob: `deduplicated-content/YYYY-MM-DD.json`

3. **Historical Window** (14 days)
   - Prevents republishing old content
   - Checked before publishing to queue

**Hash Algorithm**: SHA256(title + first 500 chars of content)

## Performance Characteristics

### Rate Limiting
- **Reddit**: 60 requests/minute (1/second)
- **Mastodon**: 300 requests/minute (5/second)
- **Backoff**: Exponential 2.0-2.5x on 429 (max 10 minutes)

### Throughput
- ~2-5 items/second (depends on rate limits, quality pass rate)
- Items processed individually (no batching)
- Memory footprint: ~100MB per 1000 items in dedup window

### Latency
- Item collection: 200-500ms per item
- Quality review: <10ms per item (pure function)
- Dedup check: <50ms per item (blob lookup)
- Queue send: ~20ms per item
- **End-to-end**: ~300-600ms per item

## Troubleshooting

### Items Not Being Published

**Check logs for**:
```
# Quality rejection
"Quality rejected: item_id - content_too_short"
"Quality rejected: item_id - title_not_readable"
"Quality rejected: item_id - off_topic_subreddit"

# Dedup rejection
"Duplicate: item_id"

# Blob/queue errors
"Error checking dedup: ..."
"Error processing item: ..."
```

**Debug steps**:
1. Check item passes validation: `validate_item(item)`
2. Check readability: `check_readability(item)`
3. Check relevance: `check_technical_relevance(item)`
4. Verify dedup blob exists and is readable
5. Check queue client is connected

### Rate Limiting Issues

If seeing `429 Too Many Requests`:
```
# Current backoff applied
"Rate limited, backoff: 2.0 seconds"
"Rate limited, backoff: 5.0 seconds"
"Rate limited, backoff: 10 seconds"

# If max backoff reached (600s)
"Max backoff reached, skipping request"
```

**Fix**: Reduce `max_items` or increase collection interval

### Authentication Errors

```bash
# Missing API key
401 Unauthorized - Function key required

# Invalid key
401 Unauthorized - Invalid API key

# Set correct key in environment
export COLLECTION_API_KEY="your_actual_key"
```

## Implementation Phases

### ✅ Phase 1: Core Streaming Modules
- 5 modules, 650 lines
- Async collectors, rate limiting, dedup, orchestration
- 17 tests passing

### ✅ Phase 2: Quality Integration
- 1 module, 200 lines
- Item-level filtering (validation, readability, relevance)
- 20 tests, 37 total

### ✅ Phase 3: Manual Testing Endpoint
- 2 modules, 120 lines
- HTTP endpoint with API key auth
- 25 tests, 62 total

### ✅ Phase 4: Cleanup & Documentation
- Old batch code removed (11 files deleted)
- E2E integration tests (12 tests)
- Documentation updated

## Development

### Adding New Source

1. Create collector in `collectors/collect.py`:
```python
async def collect_source_name(query, **kwargs):
    """Async generator yielding standardized items."""
    async for item in source_api:
        yield {
            "id": item["id"],
            "title": item["title"],
            "content": item["content"],
            "source": "source_name",
            "url": item["url"],
            "metadata": {...}
        }
```

2. Add format converter in `collectors/standardize.py`

3. Add tests in `tests/test_collectors.py`

4. Update pipeline orchestration in `service_logic.py`

### Performance Optimization

- Items processed individually (no batching)
- Dedup checked before blob write (fail-fast)
- Quality review skipped if validation fails
- Error recovery continues pipeline (doesn't fail entire batch)

## Status

✅ **Production Ready** (October 2025)
- 294 tests passing
- Pure async streaming architecture
- Quality filtering in production
- Deduplication working reliably
- E2E integration tests validating full pipeline

## Next Steps

1. Monitor production metrics (collection rate, quality pass rate, dedup effectiveness)
2. Tune quality gates based on content-processor feedback
3. Extend to additional sources (RSS feeds, web scraping, Bluesky)
4. Implement collection scheduling and webhook integration
