# Markdown-Generator Scaling Issue Analysis

**Date**: 2025-10-12  
**Priority**: MEDIUM (Performance optimization - causes unnecessary scaling churn)  
**Status**: Identified during testing

---

## Problem: Premature Scale-Down During Active Processing

### Observed Behavior

```
Timeline of markdown-generator scaling:
T+0:00  - Processor sends 10 messages to markdown-gen queue
T+0:01  - KEDA polls, sees 10 messages, scales markdown-gen to 1 replica
T+0:02  - Markdown-gen starts, processes 10 messages in 0.3 seconds
T+0:02  - Queue empty, markdown-gen exits processing loop
T+0:02  - **Cooldown starts (5 minutes)**
T+0:30  - Processor sends 10 MORE messages to queue
T+0:30  - **Markdown-gen is in cooldown, NOT polling queue!**
T+0:30  - Messages sit in queue waiting
T+0:60  - KEDA next poll (30s interval), sees 10 messages
T+0:60  - KEDA tries to scale up, but replica is still in cooldown
T+5:02  - Cooldown ends, replica terminates
T+5:32  - KEDA polls again, sees 10 messages, scales UP from 0→1
T+5:33  - New replica starts, processes 10 messages in 0.3 seconds
T+5:33  - **Cycle repeats!**
```

### Root Cause

The markdown-generator uses a **poll-until-empty** pattern:

```python
while True:
    messages_processed = await process_queue_messages(...)
    
    if messages_processed == 0:
        # Queue empty - exit and let KEDA scale to 0
        break
    
    await asyncio.sleep(2)
```

**Problem**: The container exits the polling loop immediately when the queue is empty, assuming work is done. But the **processor is still running** and generating more messages!

**Impact**:
- Container enters cooldown while processor is still working
- New messages arrive during cooldown but container isn't polling
- Must wait for cooldown to end (5 min) OR for KEDA to detect messages (30s)
- Causes scaling churn: scale down → wait → scale up → repeat

---

## Why This Happens

### Processor Speed vs Markdown-Generator Speed

**Processor**:
- Calls OpenAI API for each topic
- Takes 2-6 seconds per topic
- Processes 10 topics = 20-60 seconds
- Sends messages gradually as each topic completes

**Markdown-Generator**:
- Simple Jinja2 template rendering
- Takes 21-36ms per article
- Processes 10 articles = 0.3 seconds
- **Much faster than processor!**

### The Race Condition

```
Processor timeline:
T+0:00 - Start processing 10 topics
T+0:03 - Topic 1 done → send to markdown queue
T+0:05 - Topic 2 done → send to markdown queue
...
T+0:30 - Topic 10 done → send to markdown queue

Markdown-gen timeline:
T+0:03 - KEDA scales up (sees 1 message)
T+0:04 - Process 1 message in 0.03s
T+0:04 - Queue empty! Exit polling loop
T+0:04 - **Enter 5-minute cooldown**
T+0:05 - Processor sends topic 2 (markdown-gen not polling!)
T+0:07 - Processor sends topic 3 (markdown-gen not polling!)
...
```

**Result**: Markdown-generator scales down BEFORE processor finishes sending all messages.

---

## Solutions

### Solution 1: Intelligent Waiting (Recommended)

Keep polling for a grace period even after queue is empty:

```python
async def startup_queue_processor(...):
    """
    Process queue messages until empty, with intelligent waiting
    to handle gradual message arrival from upstream.
    """
    total_processed = 0
    empty_poll_count = 0
    max_empty_polls = 3  # Wait for 3 empty polls before exiting
    
    while True:
        messages_processed = await process_queue_messages(
            queue_name=queue_name,
            message_handler=message_handler,
            max_messages=max_batch_size,
        )
        
        if messages_processed == 0:
            empty_poll_count += 1
            
            if empty_poll_count >= max_empty_polls:
                # Queue has been empty for multiple polls - truly done
                if total_processed > 0:
                    logger.info(
                        f"✅ Queue empty for {empty_poll_count} polls after processing "
                        f"{total_processed} messages. Exiting."
                    )
                else:
                    logger.info("✅ Queue empty on startup. Exiting.")
                break
            else:
                # Queue empty but might get more messages soon
                logger.info(
                    f"📭 Queue empty (poll {empty_poll_count}/{max_empty_polls}). "
                    f"Waiting {5 * empty_poll_count}s for more messages..."
                )
                await asyncio.sleep(5 * empty_poll_count)  # Backoff: 5s, 10s, 15s
                continue
        
        # Reset counter when we process messages
        empty_poll_count = 0
        total_processed += messages_processed
        
        logger.info(f"📦 Processed {messages_processed} messages (total: {total_processed})")
        await asyncio.sleep(2)
```

**Behavior**:
- First empty poll: Wait 5 seconds and check again
- Second empty poll: Wait 10 seconds and check again  
- Third empty poll: Wait 15 seconds and check again
- After 3 empty polls (30s total wait): Exit

**Benefits**:
- Catches late-arriving messages from slow processor
- Prevents premature scale-down
- Minimal cost (30s extra runtime vs 5-minute cooldown)
- Self-adjusting based on message arrival pattern

### Solution 2: Estimated Completion Time

Calculate expected batch completion time:

```python
async def startup_queue_processor(...):
    """Wait for upstream batch to complete based on expected timing."""
    
    # Get initial queue depth to estimate batch size
    initial_depth = await get_queue_depth(queue_name)
    
    if initial_depth == 0:
        logger.info("Queue empty on startup")
        return
    
    # Estimate upstream completion time
    # Processor: ~3s per topic, sends messages gradually
    # So wait for (initial_depth * 3) seconds for batch to complete
    estimated_batch_time = initial_depth * 3
    max_wait_time = min(estimated_batch_time, 120)  # Cap at 2 minutes
    
    logger.info(
        f"📊 Initial queue depth: {initial_depth}. "
        f"Will poll for up to {max_wait_time}s for batch completion."
    )
    
    start_time = time.time()
    total_processed = 0
    last_message_time = time.time()
    
    while True:
        elapsed = time.time() - start_time
        idle_time = time.time() - last_message_time
        
        # Exit if we've waited long enough AND no messages for 10s
        if elapsed > max_wait_time and idle_time > 10:
            logger.info(
                f"✅ Batch completion timeout ({max_wait_time}s) reached. "
                f"Processed {total_processed} messages. Exiting."
            )
            break
        
        messages_processed = await process_queue_messages(...)
        
        if messages_processed > 0:
            last_message_time = time.time()
            total_processed += messages_processed
            logger.info(
                f"📦 Processed {messages_processed} (total: {total_processed}). "
                f"Elapsed: {elapsed:.0f}s/{max_wait_time}s"
            )
        else:
            logger.info(
                f"📭 Queue empty. Waiting... "
                f"(elapsed: {elapsed:.0f}s, idle: {idle_time:.0f}s)"
            )
        
        await asyncio.sleep(5)
```

**Benefits**:
- Waits for expected batch completion time
- Adapts to batch size
- More predictable behavior

**Drawbacks**:
- Hardcoded timing assumptions
- May wait too long for small batches
- May exit too early for large batches with 429 errors

### Solution 3: Reduce Cooldown Period (Quick Fix)

Just reduce cooldown from 300s to 30-60s:

```hcl
scale {
  min_replicas    = 0
  max_replicas    = 1
  cooldown_period = 30  # Reduced from 300
}
```

**Benefits**:
- Simple change
- Reduces wasted wait time
- Container can scale back up faster

**Drawbacks**:
- Doesn't fix root cause
- Still has scaling churn
- More scaling events = more cold starts

### Solution 4: Keep Min Replicas = 1 During Collection Hours

Since collection happens every 8 hours on CRON:

```hcl
# Option: Keep 1 replica warm during expected processing windows
# But this requires time-based configuration (not supported in KEDA currently)

# Alternative: Accept the scaling pattern as-is, optimize cooldown
scale {
  min_replicas    = 0
  max_replicas    = 1
  cooldown_period = 60  # Faster scale-down
}
```

---

## Recommended Approach

**Implement Solution 1 (Intelligent Waiting) + Solution 3 (Reduced Cooldown)**

```python
# In markdown-generator/queue_processor.py
async def startup_queue_processor(...):
    total_processed = 0
    empty_poll_count = 0
    max_empty_polls = 3  # ~30s total wait
    
    while True:
        messages_processed = await process_queue_messages(...)
        
        if messages_processed == 0:
            empty_poll_count += 1
            if empty_poll_count >= max_empty_polls:
                break
            await asyncio.sleep(10)  # Wait 10s between empty polls
            continue
        
        empty_poll_count = 0  # Reset on new messages
        total_processed += messages_processed
        await asyncio.sleep(2)
```

```hcl
# In infra/container_app_markdown_generator.tf
scale {
  min_replicas    = 0
  max_replicas    = 1
  cooldown_period = 60  # Reduced from 300
}
```

**Benefits**:
- Catches late-arriving messages (solves race condition)
- Faster recovery if we do scale down (60s vs 300s)
- Minimal extra cost (30s extra runtime)
- Simple to implement and test

---

## Testing This Run

### What to Watch For

1. **Markdown-gen scaling pattern**:
   ```bash
   # Monitor replica count over time
   watch -n 5 'az containerapp replica list --name ai-content-prod-markdown-gen --resource-group ai-content-prod-rg --query "[].properties.runningState" -o tsv | wc -l'
   ```

2. **Queue depth during processing**:
   ```bash
   # Watch for messages arriving while replica is alive
   while true; do
     echo "$(date): $(az storage message peek --queue-name markdown-generation-requests --account-name aicontentprodstkwakpx --auth-mode login --num-messages 1 2>/dev/null | jq 'length') messages"
     sleep 5
   done
   ```

3. **Markdown-gen logs**:
   ```bash
   az containerapp logs show --name ai-content-prod-markdown-gen --resource-group ai-content-prod-rg --tail 50 --follow true
   
   # Look for:
   # - "Processed X messages (total: Y)"
   # - "Queue empty after processing..."
   # - Time between last message and exit
   ```

4. **Site-publisher trigger timing**:
   ```bash
   # Check when site-publish message arrives
   az storage message peek --queue-name site-publishing-requests --account-name aicontentprodstkwakpx --auth-mode login --num-messages 1 2>&1 | jq '.[] | .insertionTime'
   ```

### Expected Timeline (With Current Config)

```
T+0:00  - Collector starts
T+0:30  - Collector sends ~80 topics to processor queue
T+0:31  - Processor scales up, starts processing
T+0:34  - Processor completes first topic → markdown-gen queue
T+0:35  - Markdown-gen scales up (KEDA sees 1 message)
T+0:35  - Markdown-gen processes 1 message in 0.03s
T+0:35  - **Queue empty, markdown-gen exits** ← PROBLEM!
T+0:35  - **Markdown-gen enters 5-min cooldown**
T+0:36  - Processor sends topic 2 (markdown-gen not polling!)
T+0:38  - Processor sends topic 3 (markdown-gen not polling!)
...
T+2:00  - Processor completes all 80 topics
T+2:00  - Markdown queue has ~79 messages waiting
T+2:05  - KEDA next poll (30s interval), sees 79 messages
T+2:05  - KEDA scales markdown-gen up (still in cooldown)
T+2:35  - Cooldown ends, old replica terminates
T+2:35  - New replica starts, processes all 79 messages in 2-3 seconds
T+2:38  - Site-publisher receives trigger
```

**Problem**: 2-minute delay between first message and batch processing!

### With Proposed Fix (Intelligent Waiting)

```
T+0:00  - Collector starts
T+0:30  - Collector sends ~80 topics to processor queue
T+0:31  - Processor scales up, starts processing
T+0:34  - Processor completes first topic → markdown-gen queue
T+0:35  - Markdown-gen scales up
T+0:35  - Markdown-gen processes 1 message in 0.03s
T+0:35  - **Queue empty, but markdown-gen waits 10s** ← FIX!
T+0:36  - Processor sends topic 2
T+0:37  - Markdown-gen polls again, finds 1-2 messages
T+0:37  - Processes messages, resets empty counter
T+0:38  - Processor sends topic 3-5
T+0:39  - Markdown-gen polls, finds 3-5 messages
... (continues polling while processor works)
T+2:00  - Processor completes all 80 topics
T+2:01  - Markdown-gen polls, finds last few messages
T+2:02  - Markdown-gen processes last batch
T+2:02  - Queue empty, wait 10s
T+2:12  - Still empty, wait 10s  
T+2:22  - Still empty, wait 10s
T+2:32  - **3 empty polls, exit and send site-publish trigger**
T+2:33  - Site-publisher receives trigger
```

**Result**: No scaling churn, continuous processing, 30s extra runtime vs 2-minute delay!

---

## Current Test Focus

**For this run, just observe and document**:
1. ✅ How long between first and last markdown message?
2. ✅ Does markdown-gen scale down prematurely?
3. ✅ How long until site-publisher gets triggered?
4. ✅ **CRITICAL**: Does site-publisher actually process the message?

**After observing behavior, implement fixes in next iteration.**

---

**Status**: Documented issue, solution designed, ready to observe in current test run
