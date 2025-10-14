# Markdown Generator Site-Publisher Signaling Fix

**Date**: October 14, 2025  
**Issue**: Markdown-generator not signaling site-publisher for subsequent batches  
**Solution**: Stable empty queue pattern with configurable wait period

## Problem Analysis

### Original Behavior (Broken)
```python
signaled_site_publisher = False  # One-time flag

if total_processed > 0 and not signaled_site_publisher:
    await signal_site_publisher(...)
    signaled_site_publisher = True  # Never resets!
```

**Issue**: Flag never reset after first signal, causing silent failures for subsequent batches.

### Traffic Pattern
- **content-processor**: Bursty output, scales up to 8 instances
- **markdown-generator**: Very fast (35+ articles/sec), single instance  
- **site-publisher**: Full Hugo site rebuild (~few seconds)

### Why Simple Solutions Don't Work

1. **Signal per batch**: Would trigger 6-30+ rebuilds/minute during bursts → wasteful
2. **Fixed cooldown timer**: Arbitrary delays, may miss content or rebuild too often
3. **Original one-shot flag**: Only works for first batch (current bug)

## Solution: Stable Empty Queue Pattern

Signal site-publisher when:
1. ✅ Queue is empty after processing messages
2. ✅ Queue has been **stable/empty for 30+ seconds**
3. ✅ New content was processed since last signal

### Configuration
```bash
STABLE_EMPTY_DURATION_SECONDS=30  # Default: 30s
```

**30 seconds chosen because:**
- Content-processors take ~10s per article
- With 8 processors, burst creates messages rapidly  
- 30s stable = processors likely finished their batch
- Balances freshness vs rebuild frequency

## Implementation Details

### State Tracking
```python
# OLD (broken):
signaled_site_publisher = False  # One-time flag

# NEW (fixed):
queue_empty_since = None            # Track when queue first became empty
total_processed_since_signal = 0   # Count messages since last signal
```

### Logic Flow

#### When Messages Arrive:
```python
if messages_processed > 0:
    queue_empty_since = None  # Reset: queue active again
    total_processed_since_signal += messages_processed
    # Keep processing...
```

#### When Queue Empty:
```python
if messages_processed == 0:
    if queue_empty_since is None:
        queue_empty_since = current_time  # Start tracking stability
    
    stable_seconds = (current_time - queue_empty_since).total_seconds()
    
    # Signal if stable AND new content exists
    if stable_seconds >= STABLE_EMPTY_DURATION and total_processed_since_signal > 0:
        await signal_site_publisher(total_processed_since_signal, output_container)
        total_processed_since_signal = 0  # Reset for next batch
```

## Example Scenarios

### Scenario 1: Single Batch
```
00:00 - Container starts, queue empty
00:10 - 50 messages arrive from processors
00:12 - Processed 50 messages (2 seconds)
00:12 - Queue empty, start stability timer
00:42 - Queue stable for 30s → signal site-publisher ✅
```

### Scenario 2: Multiple Bursts
```
00:00 - Container starts
00:10 - Process 30 messages
00:12 - Queue empty, start timer
00:20 - 20 more messages arrive (processors still working)
00:22 - Queue empty again, RESET timer
00:52 - Queue stable for 30s → signal site-publisher ✅
01:00 - 15 more messages arrive
01:02 - Queue empty, start timer  
01:32 - Queue stable for 30s → signal site-publisher AGAIN ✅
```

### Scenario 3: Continuous Stream
```
00:00 - Process messages continuously
00:00 - 10 messages
00:02 - 15 messages
00:04 - 8 messages
... (queue never stable for 30s)
... (NO site rebuild during active processing) ✅
05:00 - Queue finally stable for 30s → single rebuild for all content ✅
```

## Benefits

✅ **Batches updates naturally**: No arbitrary timers or fixed intervals  
✅ **Handles bursts gracefully**: Waits for processor batch to complete  
✅ **Prevents rebuild spam**: Single rebuild per burst cycle  
✅ **Respects traffic patterns**: Adapts to actual processing behavior  
✅ **Multiple batches work**: Signal resets properly for subsequent cycles  
✅ **Configurable**: Adjust `STABLE_EMPTY_DURATION_SECONDS` per environment  

## Monitoring & Logs

### Log Messages
```
📭 Queue empty after processing 50 new messages. Waiting 30s to ensure processor burst complete...
✅ Queue stable for 30s after processing 50 new messages - signaling site-publisher
✅ Site-publisher signaled. Continuing to poll. KEDA will scale to 0 after cooldown period.
📦 Processed 20 messages (batch total: 20, lifetime: 70). Checking for more...
```

### Key Metrics to Monitor
- `total_processed_since_signal`: Messages in current batch
- `stable_empty_seconds`: How long queue has been empty
- `total_processed`: Lifetime message count

## Testing Checklist

- [ ] First batch signals correctly
- [ ] Second batch signals correctly (flag resets)
- [ ] Third+ batches signal correctly
- [ ] No signal during continuous processing
- [ ] No signal if queue empty on startup (no new content)
- [ ] Signal respects 30s stability period
- [ ] Multiple rapid bursts batch into single signal

## Deployment

### Files Changed
- `containers/markdown-generator/queue_processor.py` - Core logic fix
- `infra/container_app_markdown_generator.tf` - Add `STABLE_EMPTY_DURATION_SECONDS` env var

### Configuration
```terraform
env {
  name  = "STABLE_EMPTY_DURATION_SECONDS"
  value = "30"  # Wait 30s after queue empty before signaling
}
```

### Rollout
1. Deploy updated markdown-generator container
2. Monitor logs for "Queue stable for Xs" messages
3. Verify site-publisher triggered after processor bursts
4. Adjust `STABLE_EMPTY_DURATION_SECONDS` if needed

## Tuning Guidelines

**If site updates are too slow:**
- Decrease `STABLE_EMPTY_DURATION_SECONDS` (try 20s or 15s)

**If too many rebuilds:**
- Increase `STABLE_EMPTY_DURATION_SECONDS` (try 45s or 60s)

**Current default (30s) works well for:**
- 8 content-processors @ ~10s per article
- Markdown-generator processing @ 35+ articles/sec
- Site-publisher rebuild @ ~few seconds

## Related Files
- `containers/markdown-generator/queue_processor.py` - Implementation
- `containers/markdown-generator/main.py` - Container entry point
- `containers/site-publisher/app.py` - Message receiver
- `infra/container_app_markdown_generator.tf` - Infrastructure config
- `infra/storage.tf` - Queue definitions
