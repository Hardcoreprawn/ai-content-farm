# Content Processor Logging Issues & Improvements

**Date**: 2025-10-12  
**Priority**: High (Production Debugging & Cost Monitoring)  
**Status**: Observed during successful KEDA scaling test

## Issues Found in Production Logs

### 1. ⚠️ CRITICAL: Azure OpenAI Rate Limiting (429 Errors)

**Observed:**
```
16:51:57 - httpx - INFO - HTTP Request: POST https://aicontentprodopenai.openai.azure.com/openai/deployments/gpt-35-turbo/chat/completions?api-version=2024-07-01-preview "HTTP/1.1 429 Too Many Requests"
16:51:57 - openai._base_client - INFO - Retrying request to /chat/completions in 2.000000 seconds
```

**Problem:**
- Multiple replicas (5 concurrent) hitting Azure OpenAI simultaneously
- Each replica processing messages in parallel
- Exceeding Azure OpenAI rate limits (TPM - Tokens Per Minute or RPM - Requests Per Minute)
- Causing delays and retries

**Impact:**
- Slower processing (waiting 2+ seconds per retry)
- Wasted API calls
- Potential cascade failures if retries exhaust
- Higher costs from retry overhead

**Solution Options:**

1. **Immediate: Reduce KEDA maxReplicas** (Quick fix)
   ```hcl
   # In infra/container_app_processor.tf
   min_replicas = 0
   max_replicas = 2  # Reduce from 3 to 2
   ```

2. **Better: Increase Azure OpenAI TPM/RPM Quota**
   - Current quota: Unknown (need to check)
   - Recommended: Check quota and request increase if needed
   - Use Azure Portal → OpenAI → Quotas to view/adjust

3. **Best: Implement Rate Limiting in Code**
   ```python
   # Add to libs/openai_client.py
   import asyncio
   from asyncio import Semaphore
   
   # Global semaphore to limit concurrent OpenAI calls across replicas
   # Would need Redis/Storage-based distributed semaphore for multi-replica
   OPENAI_SEMAPHORE = Semaphore(3)  # Max 3 concurrent OpenAI calls
   
   async def generate_article(...):
       async with OPENAI_SEMAPHORE:
           # Make OpenAI call
           response = await client.chat.completions.create(...)
   ```

4. **Alternative: Use Azure OpenAI Provisioned Throughput**
   - Switch from Pay-As-You-Go to Provisioned Throughput Units (PTUs)
   - More expensive but guaranteed capacity
   - Only worth it for high-volume production

**Recommended Action:**
1. Check current Azure OpenAI quota in Azure Portal
2. If quota is low, request increase
3. If quota is adequate, reduce maxReplicas to 2 temporarily
4. Monitor 429 errors - if they persist, implement distributed rate limiting

---

### 2. 🚨 Excessive Azure SDK Debug Logging

**Observed:**
```
16:51:57 - azure.core.pipeline.policies.http_logging_policy - INFO - Request URL: 'https://aicontentprodstkwakpx.queue.core.windows.net/...'
method: 'DELETE'
headers:
'x-ms-version': 'REDACTED'
'Accept': 'application/xml'
'User-Agent': 'azsdk-python-storage-queue/12.13.0 Python/3.11.14 (Linux-6.6.96.2-2.azl3-x86_64-with-glibc2.41)'
...
16:51:57 - azure.core.pipeline.policies.http_logging_policy - INFO - Response status: 204
```

**Problem:**
- Azure SDK logging every HTTP request/response with full headers
- Polluting logs with 10-15 lines per queue operation
- Makes it impossible to find actual application logs
- Increases log storage costs
- Contains sensitive data (even though REDACTED, it's noise)

**Solution:**

```python
# In containers/content-processor/main.py (or shared config)
import logging

# Suppress Azure SDK debug logging
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)
logging.getLogger("azure.core.pipeline.policies").setLevel(logging.WARNING)
logging.getLogger("azure").setLevel(logging.WARNING)

# Keep only errors from Azure SDK
logging.getLogger("azure.core").setLevel(logging.ERROR)
```

**Where to Add:**
- Add to all container `main.py` or `app.py` files
- Add to `libs/__init__.py` for global effect
- Consider environment variable to enable for debugging: `AZURE_SDK_LOG_LEVEL`

---

### 3. 📊 Missing Performance Metrics

**Current Logs:**
```
16:51:57 - services.article_generation - INFO - Processing topic: 16 Best Laptops (2025), WIRED-Tested and Approved
16:51:57 - openai_client - INFO - 🤖 OPENAI: Generating article for topic: '16 Best Laptops (2025), WIRED-Tested and Approved'
16:51:57 - openai_client - INFO - 🤖 OPENAI: Using model: gpt-35-turbo, endpoint: https://aicontentprodopenai.openai.azure.com/
16:51:57 - openai_client - INFO - 🤖 OPENAI: Target word count: 3000
16:51:57 - openai_client - INFO - 📝 PROMPT: Built prompt with 1427 characters
16:51:57 - openai_client - INFO - 🚀 OPENAI: Sending request to Azure OpenAI...
```

**Missing Information:**
- ❌ How long did the OpenAI call take?
- ❌ How many tokens were used? (directly impacts cost)
- ❌ What was the actual article length generated?
- ❌ Did the article meet the 3000 word target?
- ❌ What was the total processing time for this topic?

**Recommended Additions:**

```python
# In libs/openai_client.py

async def generate_article(topic: str, target_words: int = 3000) -> str:
    start_time = time.time()
    
    logger.info(f"🤖 OPENAI: Generating article for topic: '{topic}'")
    logger.info(f"🤖 OPENAI: Using model: {model}, endpoint: {endpoint}")
    logger.info(f"🤖 OPENAI: Target word count: {target_words}")
    
    # Build prompt
    prompt = build_prompt(topic, target_words)
    prompt_length = len(prompt)
    logger.info(f"📝 PROMPT: Built prompt with {prompt_length} characters")
    
    # Send request
    logger.info("🚀 OPENAI: Sending request to Azure OpenAI...")
    response = await client.chat.completions.create(...)
    
    # ADD: Response metrics
    completion_time = time.time() - start_time
    content = response.choices[0].message.content
    word_count = len(content.split())
    
    # ADD: Token usage metrics (critical for cost tracking)
    tokens_used = response.usage.total_tokens if response.usage else 0
    prompt_tokens = response.usage.prompt_tokens if response.usage else 0
    completion_tokens = response.usage.completion_tokens if response.usage else 0
    
    # ADD: Cost calculation (approximate)
    # GPT-3.5-turbo pricing: ~$0.0015 per 1K prompt tokens, ~$0.002 per 1K completion tokens
    estimated_cost = (prompt_tokens * 0.0015 / 1000) + (completion_tokens * 0.002 / 1000)
    
    logger.info(
        f"✅ OPENAI: Article generated in {completion_time:.2f}s | "
        f"Words: {word_count}/{target_words} ({word_count/target_words*100:.1f}% of target) | "
        f"Tokens: {tokens_used} (prompt: {prompt_tokens}, completion: {completion_tokens}) | "
        f"Est. cost: ${estimated_cost:.4f}"
    )
    
    # ADD: Warning if significantly over/under target
    if word_count < target_words * 0.7:
        logger.warning(f"⚠️ Article is only {word_count/target_words*100:.1f}% of target word count")
    elif word_count > target_words * 1.3:
        logger.warning(f"⚠️ Article is {word_count/target_words*100:.1f}% over target word count")
    
    return content
```

**Expected Improved Output:**
```
16:51:57 - openai_client - INFO - 🚀 OPENAI: Sending request to Azure OpenAI...
16:52:03 - openai_client - INFO - ✅ OPENAI: Article generated in 6.23s | Words: 2847/3000 (94.9% of target) | Tokens: 4231 (prompt: 356, completion: 3875) | Est. cost: $0.0082
```

---

### 4. 📦 Missing Batch Processing Summary

**Current State:**
- Individual message logs: "✅ Successfully processed message 403438b6-9498-4e17-9e8a-c49c510b917e"
- No aggregation of metrics across batch

**Missing Information:**
- Total messages processed in current batch
- Average processing time per message
- Total OpenAI tokens used in batch (cost tracking)
- Success/failure ratio
- Queue depth remaining

**Recommended Addition:**

```python
# In containers/content-processor/main.py

async def startup_queue_processor(...):
    total_processed = 0
    total_tokens = 0
    total_cost = 0.0
    total_failures = 0
    batch_start_time = time.time()
    
    while True:
        batch_iteration_start = time.time()
        
        # Track metrics per batch
        batch_tokens = 0
        batch_cost = 0.0
        batch_failures = 0
        
        messages_processed = await process_queue_messages(
            queue_name=queue_name,
            message_handler=message_handler,
            max_messages=max_batch_size,
        )
        
        # Aggregate metrics (would need to return from message_handler)
        total_processed += messages_processed
        total_tokens += batch_tokens
        total_cost += batch_cost
        
        if messages_processed == 0:
            total_duration = time.time() - batch_start_time
            logger.info(
                f"✅ Processing complete: {total_processed} messages in {total_duration:.2f}s "
                f"({total_processed/total_duration:.2f} msgs/sec) | "
                f"Total tokens: {total_tokens:,} | Total cost: ${total_cost:.2f} | "
                f"Failures: {total_failures}"
            )
            break
        
        batch_duration = time.time() - batch_iteration_start
        logger.info(
            f"📦 Batch {total_processed//max_batch_size + 1}: "
            f"Processed {messages_processed} messages in {batch_duration:.2f}s "
            f"({messages_processed/batch_duration:.2f} msgs/sec) | "
            f"Tokens: {batch_tokens:,} | Cost: ${batch_cost:.4f} | "
            f"Total progress: {total_processed} messages, ${total_cost:.2f}"
        )
```

---

### 5. 🔍 Poor Error Context

**Current State:**
- Generic success messages without context
- No indication of what happens on failures
- Missing correlation IDs for tracing

**Improvement Needed:**

```python
logger.info(
    f"✅ PROCESSED: {topic_id} | "
    f"Title: {title[:50]}... | "
    f"Source: {source} | "
    f"Priority: {priority_score} | "
    f"Processing time: {duration:.2f}s | "
    f"Output: {output_blob_path} | "
    f"Correlation: {correlation_id}"
)
```

---

## Priority Implementation Order

1. **IMMEDIATE**: Suppress Azure SDK debug logging (takes 5 minutes, huge log improvement)
2. **HIGH**: Add OpenAI token/cost tracking (critical for cost monitoring)
3. **HIGH**: Investigate and fix Azure OpenAI 429 errors (affecting performance)
4. **MEDIUM**: Add batch processing summaries (helps with monitoring)
5. **MEDIUM**: Add processing time metrics (helps identify slow topics)
6. **LOW**: Improve error context (nice to have)

---

## Testing Checklist

- [ ] Verify Azure SDK logs are suppressed (should see 90% fewer log lines)
- [ ] Confirm OpenAI token usage is logged
- [ ] Validate cost calculations are accurate
- [ ] Check 429 errors decrease after maxReplicas reduction
- [ ] Ensure batch summaries provide useful metrics
- [ ] Test that AZURE_SDK_LOG_LEVEL=DEBUG re-enables debugging when needed

---

**Created**: 2025-10-12 during production KEDA scaling observation  
**Files Affected**:
- `/workspaces/ai-content-farm/containers/content-processor/main.py`
- `/workspaces/ai-content-farm/libs/openai_client.py`
- `/workspaces/ai-content-farm/libs/queue_client.py`
- `/workspaces/ai-content-farm/infra/container_app_processor.tf` (for maxReplicas)

**Status**: Documented - Ready for implementation
