# Collector Architecture Refactor - Status & Design

## Current Status

**Branch**: `feature/quality-gate-streaming-foundation` (Combined PR #649 + #651)

### Merged Components
- ✅ Quality Gate: 5 modules (config, dedup, detectors, scoring, gate) - 171 tests
- ✅ Cleanup: Removed 12+ deprecated adaptive strategy files
- ✅ Security: URL domain validation (CodeQL fix)
- ✅ Queue Fix: Visibility timeout 600s → 60s
- ✅ Rate Limiter: Async-compatible utility

### Current Limitations
- ❌ Reddit disabled (due to blocking 2 weeks ago)
- ❌ OOP factory patterns remain in some paths
- ❌ No integrated collect/review/message flow
- ❌ Dedupe & quality gate not in pipeline yet
- ❌ Batch processing only (no item-level granularity)

---

## Proposed Refactor

### Architecture: Pure Functional Pipeline

```python
# Three pure functions replacing OOP collectors
def collect(source: dict) -> AsyncGenerator[dict, None]:
    """Collect items from source. Yields standardized items."""
    # source: {"type": "rss", "urls": [...]} or {"type": "mastodon", "instance": "..."}
    # Yields: {"id", "title", "content", "source", "collected_at", "url", ...}

def review(item: dict) -> dict:
    """Apply quality gate filters. Returns item with quality metadata."""
    # Input: collected item
    # Output: item with {"quality_score", "quality_passed", "reason", "detections": {...}}

def message(item: dict, collection_id: str) -> dict:
    """Create queue message for item. Returns message dict."""
    # Input: reviewed item + collection context
    # Output: {"operation": "process", "payload": item, "topic_id": ...}
```

### Processing Flow
```
collect_batch(sources)
  └─> collect_from_source(source) for each source
       └─> AsyncGenerator yields items
            └─> review(item)                    # Apply quality gate
                 └─> if quality_passed
                      └─> message(item) → queue
                      └─> dedupe.mark_seen(item)
```

### Contracts to Test
1. **Collect Contract**
   - Input: Valid source config
   - Output: AsyncGenerator of standardized dicts
   - Required fields: id, title, content, source, collected_at, url
   - No duplicates in single batch

2. **Review Contract**
   - Input: Collected item dict
   - Output: Same dict + quality fields
   - Added fields: quality_score (0-1), quality_passed (bool), reason, detections
   - Deterministic: Same input → Same output

3. **Message Contract**
   - Input: Reviewed item + collection_id
   - Output: Azure queue message structure
   - Required: operation, payload, topic_id, correlation_id
   - Matches markdown-generator expectations

4. **Blob Interactions**
   - Dedup reads from: `deduplicated-content/{date}.json`
   - Dedup writes to: `deduplicated-content/{date}.json` (append)
   - Quality gate reads from: config constants (no blob I/O)
   - Config blocker lists stored in: `quality_config.py` (code, not blobs)

5. **Queue Interactions**
   - Connection string: `QUEUE_CONNECTION_STRING` env var
   - Queue name: `content-to-process` (from config)
   - Message format: JSON with operation, payload, metadata
   - Visibility timeout: 60s (recent fix)

### Implementation Strategy
1. Convert `simple_*.py` collectors to pure `collect()` functions
2. Create `pipeline.py`: orchestrates collect → review → message → queue/dedup
3. Update `content_processing_simple.py` to use pipeline functions
4. Add contract tests (no mocks, use real structures)
5. Re-enable Reddit in `collect()` with safe rate limiting

### Files to Modify
- `containers/content-collector/collectors/simple_reddit.py` → `collect_reddit(config)`
- `containers/content-collector/collectors/simple_mastodon.py` → `collect_mastodon(config)`
- `containers/content-collector/collectors/simple_web.py` → `collect_web(config)`
- **NEW**: `containers/content-collector/pipeline.py` (orchestration)
- `containers/content-collector/content_processing_simple.py` (use pipeline)

### Risk Areas
- Rate limiting on Reddit (need exponential backoff)
- Dedup blob I/O timing (need to validate write patterns)
- Message format compatibility (markdown-generator expectations)
- Mastodon instance rate limits (less documented)

---

## Recommendation

**Use Sonnet for:**
- Detailed analysis of current contracts (blobs, queues, dedup patterns)
- Design of rate limiting strategy for Reddit
- Integration testing between components
- Large-scale refactoring across multiple files

**Use Haiku for:**
- Quick tactical fixes
- Specific function implementations (once design finalized)
- Test writing

---

## Decision Points

1. **Redis vs. Blob for dedup?** Currently using blobs (`deduplicated-content/{date}.json`)
2. **Rate limit strategy?** Exponential backoff or token bucket?
3. **Keep batch API?** Or pure item-level processing?
4. **Streaming vs. batch?** Current: batch with `collect_content_batch()`, proposed: streaming with AsyncGenerator

