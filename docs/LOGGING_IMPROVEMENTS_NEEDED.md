# Logging Improvements Needed

**Date**: 2025-10-12  
**Priority**: Medium (Observability Enhancement)  
**Impact**: Better performance monitoring and troubleshooting

## Issue: Missing Duration Metrics in Batch Processing Logs

### Current State
The queue processing logs show progress but don't include timing information:

```
16:46:55 - queue_processor - INFO - 📦 Processed 10 messages (total: 80). Checking for more...
```

**Problems:**
- No visibility into batch processing time
- Can't measure throughput (messages/second)
- Can't detect performance degradation
- Can't correlate processing time with batch size

### Affected Files
All three queue-processing containers have this issue:

1. `/workspaces/ai-content-farm/containers/content-processor/main.py:170`
2. `/workspaces/ai-content-farm/containers/markdown-generator/queue_processor.py:167`
3. `/workspaces/ai-content-farm/containers/site-publisher/app.py:158`

### Recommended Solution

Add timing metrics to the `startup_queue_processor` function:

```python
async def startup_queue_processor(
    queue_name: str,
    message_handler: Callable,
    max_batch_size: int,
    output_container: str,
) -> None:
    """Process queue messages until empty, then signal site-publisher and scale down."""
    logger.info(f"🔍 Checking queue: {queue_name}")

    total_processed = 0
    processing_start_time = time.time()  # ADD: Overall start time
    
    while True:
        batch_start_time = time.time()  # ADD: Batch start time
        
        messages_processed = await process_queue_messages(
            queue_name=queue_name,
            message_handler=message_handler,
            max_messages=max_batch_size,
        )

        if messages_processed == 0:
            if total_processed > 0:
                total_duration = time.time() - processing_start_time  # ADD: Calculate total time
                throughput = total_processed / total_duration if total_duration > 0 else 0  # ADD: Calculate throughput
                
                logger.info(
                    f"✅ Markdown queue empty after processing {total_processed} messages "
                    f"in {total_duration:.2f}s ({throughput:.2f} msgs/sec) - "  # ADD: Duration and throughput
                    "signaling site-publisher to build static site"
                )
                # ... rest of completion logic
            else:
                logger.info(
                    "✅ Queue empty on startup. "
                    "Container will remain alive. KEDA will scale to 0 after cooldown period."
                )
            break

        batch_duration = time.time() - batch_start_time  # ADD: Calculate batch time
        total_processed += messages_processed
        
        logger.info(
            f"📦 Processed {messages_processed} messages (total: {total_processed}) "
            f"in {batch_duration:.2f}s ({messages_processed/batch_duration:.2f} msgs/sec). "  # ADD: Batch metrics
            "Checking for more..."
        )

        await asyncio.sleep(2)
```

### Expected Log Output (Improved)

```
16:46:53 - queue_processor - INFO - 📦 Processed 10 messages (total: 10) in 2.34s (4.27 msgs/sec). Checking for more...
16:46:55 - queue_processor - INFO - 📦 Processed 10 messages (total: 20) in 1.98s (5.05 msgs/sec). Checking for more...
...
16:46:57 - queue_processor - INFO - ✅ Markdown queue empty after processing 80 messages in 45.67s (1.75 msgs/sec) - signaling site-publisher to build static site
```

### Benefits

1. **Performance Monitoring**: See if processing is getting slower over time
2. **Capacity Planning**: Understand how many messages can be processed per second
3. **Debugging**: Identify slow batches that might indicate issues
4. **Cost Optimization**: Calculate actual processing time vs KEDA cooldown time
5. **SLA Tracking**: Measure end-to-end pipeline latency

## Related Issue: Unclosed aiohttp Sessions

Also found in markdown-generator logs:

```
16:46:55 - asyncio - ERROR - Unclosed client session
16:46:55 - asyncio - ERROR - Unclosed connector
```

**Root Cause**: Not properly closing aiohttp client sessions in async context managers.

**Files to Check**:
- Any aiohttp ClientSession usage in libs/ or containers/
- Ensure all async with blocks properly close sessions

**Fix Pattern**:
```python
# Ensure session is closed in finally block or use context manager correctly
async with aiohttp.ClientSession() as session:
    # ... use session
    pass  # Session automatically closes here
```

## Priority for Implementation

1. **High Priority**: Add duration metrics (easy win, big observability value)
2. **Medium Priority**: Fix aiohttp cleanup warnings (prevents log noise)

## Testing Checklist

- [ ] Verify duration logs appear for all three containers
- [ ] Confirm throughput calculations are accurate
- [ ] Check logs don't impact performance significantly
- [ ] Ensure aiohttp warnings are eliminated
- [ ] Validate timing works correctly for single-message and large batches

---

**Created**: 2025-10-12 after observing successful KEDA scaling and pipeline operation  
**Status**: Documented - Ready for implementation
