# Streaming Collection Architecture Diagram

## Current "Batch" Architecture (Inefficient)

```
┌─────────────────────────────────────────────────────────────┐
│  CONTENT COLLECTOR                                          │
│                                                             │
│  1. Collect ALL items (2-3 minutes)                        │
│     ┌──────┐  ┌──────┐  ┌──────┐                          │
│     │Reddit│  │  RSS │  │Masto │  ... wait for all         │
│     │(50)  │  │(30)  │  │(20)  │                          │
│     └───┬──┘  └───┬──┘  └───┬──┘                          │
│         └─────────┴────────┴──── 100 items total           │
│                                                             │
│  2. Deduplicate in memory (10 seconds)                     │
│     [Compute hashes, check for duplicates]                 │
│     → 85 unique items                                       │
│                                                             │
│  3. Save to blob storage (5 seconds)                       │
│     collected-content/collection-20251018.json             │
│                                                             │
│  4. Send ALL to queue RAPIDLY (burst)                      │
│     ┌─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬──┐             │
│     │1│2│3│4│5│6│7│8│9│...│85│ → processing-queue         │
│     └─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┘             │
│                                                             │
│  ⏱️  Time to first item in queue: 3+ minutes               │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│  CONTENT PROCESSOR                                          │
│                                                             │
│  KEDA sees: queueLength = 85 messages (HUGE SPIKE!)        │
│  Scales up: 0 → 5 instances (takes 30-60 seconds)          │
│                                                             │
│  Problems:                                                  │
│  ❌ First article waits 3+ minutes before processing starts │
│  ❌ Queue spike may overwhelm KEDA scaling                  │
│  ❌ Uneven workload distribution across instances           │
└─────────────────────────────────────────────────────────────┘
```

---

## Proposed "Streaming" Architecture (Efficient)

```
┌─────────────────────────────────────────────────────────────┐
│  CONTENT COLLECTOR                                          │
│                                                             │
│  Parallel Streaming Collection (ASYNC)                     │
│                                                             │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │  Reddit Stream   │  │   RSS Stream     │               │
│  │                  │  │                  │               │
│  │  Item 1 ──────┬──┼──┼──Item 1 ──────┬─┼──┐            │
│  │  Item 2 ──────┼──┼──┼──Item 2 ──────┼─┼──┼──┐         │
│  │  Item 3 ──────┼──┼──┼──Item 3 ──────┼─┼──┼──┼──┐      │
│  │  Item 4 ──────┼──┼──┼──...          │ │  │  │  │      │
│  │  ...          │  │  │                │ │  │  │  │      │
│  └───────────────┼──┘  └────────────────┼─┘  │  │  │      │
│                  ▼                       ▼    ▼  ▼  ▼      │
│          ┌──────────────────────────────────────────────┐  │
│          │  DEDUPLICATION LAYER (streaming)             │  │
│          │  - Check against recent history (24h blob)  │  │
│          │  - Hash comparison in memory                │  │
│          │  - Pass unique items immediately downstream  │  │
│          └──────────────────────────────────────────────┘  │
│                               │                             │
│                               ▼                             │
│          ┌──────────────────────────────────────────────┐  │
│          │  DUAL OUTPUT (parallel)                      │  │
│          │                                              │  │
│          │  1. → Send to processing-queue (immediate)   │  │
│          │  2. → Append to collection blob (history)    │  │
│          └──────────────────────────────────────────────┘  │
│                               │                             │
│  ⏱️  Time to first item in queue: 5-30 SECONDS!            │
└───────────────────────────────┼─────────────────────────────┘
                                │
                                ▼
              Queue receives items GRADUALLY:
              [1] → [2] → [3] → [4] → ... → [85]
              
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│  CONTENT PROCESSOR                                          │
│                                                             │
│  KEDA sees: queueLength gradually increases                │
│  - queueLength=1 → scale to 1 instance (processes item 1)  │
│  - queueLength=8 → scale to 1 instance (within threshold)  │
│  - queueLength=16 → scale to 2 instances                   │
│  - queueLength=32 → scale to 4 instances                   │
│                                                             │
│  Benefits:                                                  │
│  ✅ First article processed within 30 seconds               │
│  ✅ Smooth KEDA scaling (no spike)                          │
│  ✅ Even workload distribution                              │
│  ✅ Better resource utilization                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Comparison: Batch vs Streaming

| Metric | Batch (Current) | Streaming (Proposed) | Improvement |
|--------|----------------|---------------------|-------------|
| **Time to first item** | 3-5 minutes | 5-30 seconds | **10x faster** |
| **Queue load pattern** | Huge spike | Gradual ramp | Smoother |
| **KEDA scaling** | Slow to react | Responsive | Better utilization |
| **Implementation** | Simple | Complex | Trade-off |
| **Deduplication** | In-memory only | Recent history + memory | More robust |
| **Partial failures** | All-or-nothing | Graceful degradation | More resilient |

---

## Implementation Flow

### Phase 1: Recent History Deduplication
```python
# Load recent collections for cross-batch deduplication
async def load_recent_collection_history(hours: int = 24) -> Set[str]:
    """
    Load content hashes from recent collections.
    
    Returns set of content_hash values seen in last N hours.
    Enables deduplication across collection runs.
    """
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
    recent_blobs = storage.list_blobs(
        container="collected-content",
        prefix="collections/",
        modified_since=cutoff_time
    )
    
    seen_hashes = set()
    for blob in recent_blobs:
        collection = await storage.download_json(blob.name)
        for item in collection.get('items', []):
            seen_hashes.add(item.get('content_hash'))
    
    logger.info(f"Loaded {len(seen_hashes)} hashes from last {hours}h")
    return seen_hashes
```

### Phase 2: Streaming Collector
```python
# Modify collector to yield items instead of returning list
async def collect_batch_streaming(self, **kwargs) -> AsyncIterator[Dict]:
    """
    Stream items one-by-one as collected.
    
    Yields:
        Content items immediately after validation
    """
    # Load deduplication history
    recent_hashes = await load_recent_collection_history(hours=24)
    
    # Stream items from source
    async for raw_item in self._fetch_items_async():
        # Validate content criteria
        if not meets_content_criteria(raw_item):
            continue
        
        # Calculate hash for deduplication
        content_hash = calculate_content_hash(raw_item)
        
        # Check against recent history
        if content_hash in recent_hashes:
            logger.debug(f"Skipping duplicate: {raw_item['title'][:50]}")
            continue
        
        # Add to seen set
        recent_hashes.add(content_hash)
        raw_item['content_hash'] = content_hash
        
        # Yield immediately to caller
        yield raw_item
```

### Phase 3: Service Integration
```python
# Modify service to handle streaming
async def collect_and_stream_to_processor(
    self,
    sources_data: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Collect content and stream directly to processor.
    
    Returns collection metadata (items saved to blob + queue).
    """
    collection_id = generate_collection_id()
    items_collected = 0
    items_queued = 0
    
    # Process each source with streaming
    for source_config in sources_data:
        collector = create_streaming_collector(source_config['type'])
        
        async with collector:
            async for item in collector.collect_batch_streaming(**source_config):
                # Parallel operations:
                await asyncio.gather(
                    # 1. Send to processing queue (immediate)
                    self._send_processing_request_single(item),
                    
                    # 2. Append to collection blob (history)
                    self._append_to_collection(collection_id, item)
                )
                
                items_collected += 1
                items_queued += 1
                
                # Log progress every 10 items
                if items_collected % 10 == 0:
                    logger.info(f"Streamed {items_collected} items to processor")
    
    return {
        "collection_id": collection_id,
        "items_collected": items_collected,
        "items_queued": items_queued,
        "status": "streaming_complete"
    }
```

---

## Rollout Strategy

### Option A: Big Bang (Risky)
- Switch all collectors to streaming at once
- Pros: Immediate benefits
- Cons: High risk if bugs exist

### Option B: Phased Rollout (RECOMMENDED)
1. **Week 1**: Implement streaming for Reddit only (highest volume)
2. **Week 2**: Monitor production behavior, tune parameters
3. **Week 3**: Add streaming for RSS if Reddit successful
4. **Week 4**: Add Mastodon, complete rollout

### Option C: A/B Testing (Safest)
- Run batch and streaming in parallel
- Compare performance metrics
- Gradually shift traffic to streaming
- Fallback to batch if issues

---

## Risk Mitigation

### Potential Issues
1. **Deduplication history grows unbounded** → Implement TTL cleanup (7 days)
2. **Streaming state management complex** → Keep implementation simple, test thoroughly
3. **Queue floods if no rate limiting** → Add configurable rate limiting (items/second)
4. **Partial failures harder to debug** → Comprehensive logging and tracing

### Monitoring & Observability
- **Metric**: `time_to_first_item_queued_seconds` (target: <30s)
- **Metric**: `streaming_throughput_items_per_second` (target: 5-10/s)
- **Metric**: `deduplication_hit_rate` (target: 10-20%)
- **Alert**: If time_to_first_item > 60s, investigate bottleneck

---

## Success Criteria

### Must Have
- ✅ Time to first item in queue: <60 seconds (vs 3+ minutes currently)
- ✅ No duplicate processing (verified in logs)
- ✅ Graceful handling of source failures (other sources continue)
- ✅ Backward compatible (can fall back to batch if needed)

### Should Have
- ✅ KEDA scaling more responsive (no huge queue spikes)
- ✅ Even workload distribution across processor instances
- ✅ Collection history deduplication working (24h lookback)

### Nice to Have
- ✅ Configurable streaming rate limits
- ✅ Per-source throughput metrics
- ✅ Real-time progress tracking in logs

---

_Diagram created: October 18, 2025_  
_For: Pipeline Optimization Planning Session_
