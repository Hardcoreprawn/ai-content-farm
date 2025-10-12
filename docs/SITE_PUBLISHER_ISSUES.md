# Site-Publisher Analysis & Issues

**Date**: 2025-10-12  
**Priority**: HIGH (Broken functionality - messages not being processed)  
**Status**: Critical investigation needed

---

## Executive Summary

**Problem**: Site-publisher had 3 messages in queue (from yesterday and today) but shows "Queue empty on startup" in logs. Messages have mysteriously disappeared without being processed successfully.

**Evidence**:
- Queue check at 16:47 showed 3 messages (IDs from 2025-10-11 20:28:03 and 2025-10-12 16:46:57)
- Site-publisher started at 17:03:05, reported "Received 0 messages from queue"  
- Current queue check shows 0 messages - they've disappeared
- No processing logs, no Hugo build logs, no static site generation

**Potential Causes**:
1. ❌ Messages expired (7-day TTL should not have expired)
2. ❌ Another process deleted them (no other consumers)
3. ❌ Message visibility timeout issue (peek should still show them)
4. ⚠️ Site-publisher processed them silently without logs
5. ⚠️ KEDA authentication issue preventing message visibility
6. ⚠️ Queue client configuration issue with managed identity

---

## Queue Message Evidence

### Messages Observed at ~16:47 UTC

**Message 1** (Yesterday):
```json
{
  "message_id": "aae69362-0a5d-4f1a-92b4-02773e769bce",
  "service_name": "markdown-generator",
  "operation": "site_publish_request",
  "timestamp": "2025-10-11T20:28:03.857946Z",
  "payload": {
    "batch_id": "collection-20251011-202803",
    "markdown_count": 82,
    "markdown_container": "markdown-content",
    "trigger": "queue_empty"
  },
  "dequeueCount": 0,
  "insertionTime": "2025-10-11T20:28:03+00:00"
}
```

**Message 2** (Today - first):
```json
{
  "message_id": "866252c1-bd1b-4050-8398-d1a2b6a3559c",
  "timestamp": "2025-10-12T16:46:57.589818Z",
  "payload": {
    "batch_id": "collection-20251012-164657",
    "markdown_count": 20,
    "markdown_container": "markdown-content"
  },
  "insertionTime": "2025-10-12T16:46:57+00:00"
}
```

**Message 3** (Today - second):
```json
{
  "message_id": "8f71176e-82a9-42c6-9bf3-4da2f01c0a99",
  "timestamp": "2025-10-12T16:46:57.933572Z",
  "payload": {
    "batch_id": "collection-20251012-164657",
    "markdown_count": 80,
    "markdown_container": "markdown-content"
  },
  "insertionTime": "2025-10-12T16:46:57+00:00"
}
```

**Analysis**:
- All had `dequeueCount: 0` (never processed)
- Messages 2 and 3 sent ~0.3 seconds apart by different markdown-generator replicas (race condition!)
- Message 1 is 21 hours old
- All within 7-day TTL

---

## Site-Publisher Logs Analysis

### Observed Behavior (17:03:05 UTC)

```
17:03:05 - Starting site-publisher container
17:03:05 - Initialized with storage account: aicontentprodstkwakpx
17:03:05 - 🔍 Checking queue: site-publishing-requests
17:03:05 - StorageQueueClient initialized for queue: site-publishing-requests
17:03:05 - Application startup complete
17:03:05 - Uvicorn running on http://0.0.0.0:8000
17:03:09 - Queue 'site-publishing-requests' already exists
17:03:09 - Connected to Storage Queue: site-publishing-requests
17:03:09 - Received 0 messages from queue 'site-publishing-requests'
17:03:09 - Storage Queue connection closed: site-publishing-requests
17:03:09 - ✅ Queue empty on startup. Container will remain alive. KEDA will scale to 0 after cooldown period.
```

**Key Observations**:
- ❌ No errors logged
- ❌ No processing activity
- ❌ No Hugo build logs
- ❌ No static site generation
- ❌ "Received 0 messages" despite 3 messages known to exist
- ✅ Queue client connected successfully
- ⏱️ 4-second delay between startup and queue check (17:03:05 → 17:03:09)

---

## Site-Publisher Configuration

### KEDA Scaling Config

```json
{
  "queueLength": "1",
  "activationQueueLength": "1",
  "queueLengthStrategy": "all",
  "maxReplicas": 2,
  "minReplicas": 0,
  "cooldownPeriod": 300,
  "pollingInterval": 30
}
```

**Analysis**:
- `queueLength=1` and `maxReplicas=2` means it will scale to 2 replicas for any 2+ messages
- `queueLengthStrategy=all` is problematic (same issue as other containers)
- Should use `perReplica` strategy
- Site builds should almost always use 1 replica (resource-intensive)

### Queue Processing Config

From `/workspaces/ai-content-farm/containers/site-publisher/app.py:141`:

```python
messages_processed = await process_queue_messages(
    queue_name=settings.queue_name,
    message_handler=message_handler,
    max_messages=1,  # One at a time (Hugo builds are resource-intensive)
)
```

**Analysis**:
- ✅ Correct: Processes 1 message at a time (Hugo builds are CPU/memory intensive)
- ✅ Correct: Expects single replica to handle all builds sequentially
- ❌ Problem: No visibility into what's being processed
- ❌ Problem: No timing metrics
- ❌ Problem: No Hugo build output

---

## Critical Issues Found

### Issue 1: Duplicate Message Problem

**Evidence**: Two messages sent 0.3 seconds apart for same batch:
- Message 2: `markdown_count: 20` at 16:46:57.589818Z
- Message 3: `markdown_count: 80` at 16:46:57.933572Z

**Root Cause**: Multiple markdown-generator replicas (3 replicas) each detected "queue empty" and ALL sent site-publishing requests!

**Impact**:
- Site could be built 3 times for same batch
- Wasted resources
- Potential race conditions in Hugo build

**Fix Needed**: Only ONE markdown-generator replica should send the site-publish trigger.

**Recommended Solution**:
```python
# In markdown-generator queue_processor.py
# Use atomic flag or distributed lock before sending trigger

async def signal_site_publisher(...):
    # Check if trigger already sent for this batch_id
    # Use blob storage "lease" as distributed lock
    lock_blob = f"locks/site-publish-{batch_id}.lock"
    
    try:
        # Try to create lock blob (fails if exists)
        await blob_client.upload_blob(
            lock_blob,
            data={"replica_id": os.environ.get('CONTAINER_APP_REPLICA_NAME')},
            overwrite=False  # Fails if already exists
        )
        
        # We got the lock - send the trigger
        await queue_client.send_message(publish_message)
        logger.info("📤 Sent publish request (this replica won the lock)")
        
    except ResourceExistsError:
        logger.info("📤 Publish request already sent by another replica - skipping")
```

---

### Issue 2: Missing Message Visibility

**Symptoms**:
- 3 messages visible at 16:47
- 0 messages visible at 17:03 (container startup)
- No processing logs
- No errors

**Possible Causes**:

1. **Message Visibility Timeout**:
   - If another process grabbed messages with long visibility timeout
   - Default is 30 seconds, but could be configured longer
   - Peek should still show them though

2. **KEDA Authentication Issue**:
   - If KEDA can't read queue correctly
   - Might explain why container didn't scale up automatically
   - User had to manually start container

3. **Queue Client Configuration**:
   - Using wrong queue name?
   - Using wrong storage account?
   - Missing permissions?

4. **Time-based Race Condition**:
   - Messages expired exactly between 16:47 and 17:03?
   - Seems unlikely (16-minute window, 7-day TTL)

**Debugging Needed**:
```python
# Add to site-publisher startup
logger.info(f"Storage account: {settings.azure_storage_account_name}")
logger.info(f"Queue name: {settings.queue_name}")
logger.info(f"Using credential: {type(credential).__name__}")

# Before receiving messages
props = await queue_client.get_queue_properties()
logger.info(f"Queue properties: approximate_message_count={props.approximate_message_count}")

# Try peek before receive
messages = await queue_client.peek_messages(max_messages=10)
logger.info(f"Peeked {len(messages)} messages from queue")
```

---

### Issue 3: No Hugo Build Logging

**Current State**: Zero visibility into Hugo builds

**Missing Logs**:
- ❌ Hugo command being executed
- ❌ Hugo version
- ❌ Build duration
- ❌ Number of pages generated
- ❌ Output directory size
- ❌ Deployment status
- ❌ Static site URL

**Recommended Logging**:

```python
async def build_and_deploy_site(...) -> Dict[str, Any]:
    """Build static site with Hugo and deploy to blob storage."""
    build_start = time.time()
    
    logger.info("🏗️ STARTING HUGO BUILD")
    logger.info(f"  Markdown container: {markdown_container}")
    logger.info(f"  Output container: {output_container}")
    logger.info(f"  Batch ID: {batch_id}")
    
    # Download markdown files
    download_start = time.time()
    files_downloaded = await download_markdown_files(...)
    download_duration = time.time() - download_start
    logger.info(f"📥 Downloaded {files_downloaded} markdown files in {download_duration:.2f}s")
    
    # Run Hugo build
    hugo_start = time.time()
    logger.info("🚀 Running Hugo build...")
    
    result = subprocess.run(
        ["hugo", "--minify", "--destination", output_dir],
        capture_output=True,
        text=True,
        check=True
    )
    
    hugo_duration = time.time() - hugo_start
    logger.info(f"✅ Hugo build completed in {hugo_duration:.2f}s")
    logger.info(f"   Hugo output:\n{result.stdout}")
    
    # Count generated files
    html_files = len(list(Path(output_dir).rglob("*.html")))
    total_files = len(list(Path(output_dir).rglob("*")))
    total_size = sum(f.stat().st_size for f in Path(output_dir).rglob("*") if f.is_file())
    
    logger.info(f"📊 BUILD STATISTICS:")
    logger.info(f"   HTML pages: {html_files}")
    logger.info(f"   Total files: {total_files}")
    logger.info(f"   Total size: {total_size / 1024 / 1024:.2f} MB")
    
    # Upload to blob storage
    upload_start = time.time()
    files_uploaded = await upload_to_blob(...)
    upload_duration = time.time() - upload_start
    logger.info(f"📤 Uploaded {files_uploaded} files to blob storage in {upload_duration:.2f}s")
    
    total_duration = time.time() - build_start
    logger.info(
        f"🎉 SITE BUILD COMPLETE in {total_duration:.2f}s | "
        f"Download: {download_duration:.2f}s | "
        f"Build: {hugo_duration:.2f}s | "
        f"Upload: {upload_duration:.2f}s | "
        f"Pages: {html_files} | "
        f"Size: {total_size / 1024 / 1024:.2f} MB"
    )
    
    return {
        "status": "success",
        "duration": total_duration,
        "pages_generated": html_files,
        "total_files": total_files,
        "site_size_mb": total_size / 1024 / 1024,
        "timing": {
            "download": download_duration,
            "build": hugo_duration,
            "upload": upload_duration
        }
    }
```

---

## Performance & KEDA Tuning

### Expected Performance

Hugo builds are typically:
- **Fast**: 100-500ms for small sites (<100 pages)
- **Medium**: 1-5s for medium sites (100-1000 pages)
- **Slow**: 10-30s for large sites (1000+ pages)
- **Memory**: 200-500MB for small/medium sites
- **CPU**: Single-core, not well parallelized

### Current KEDA Config Issues

1. **`queueLength=1`**: Too aggressive
   - Site builds should queue up, not scale horizontally
   - Hugo is CPU/memory intensive - multiple builds could crash container
   - Recommended: Keep at 1 or increase to 2-3

2. **`maxReplicas=2`**: Probably fine
   - Allows 2 concurrent builds (one per replica)
   - But need to ensure container has enough resources

3. **`cooldownPeriod=300`**: Too long
   - Site builds complete in seconds
   - 5 minutes of idle time wastes resources
   - Recommended: 60-120 seconds

### Recommended KEDA Config

```hcl
custom_scale_rule {
  name             = "site-publish-queue-scaler"
  custom_rule_type = "azure-queue"
  
  metadata = {
    accountName              = azurerm_storage_account.storage.name
    queueName                = azurerm_storage_queue.site_publishing.name
    queueLength              = "1"  # Keep low - builds are intensive
    activationQueueLength    = "1"  # Activate immediately
    queueLengthStrategy      = "perReplica"  # Changed from "all"
    cloud                    = "AzurePublicCloud"
  }
  
  authentication {
    secret_name           = "workload-identity-client-id"
    trigger_parameter     = "workloadIdentity"
  }
}

scale {
  min_replicas = 0
  max_replicas = 1  # Reduced from 2 - usually only need 1
  
  # Faster cooldown for quick builds
  cooldown_period = 120  # Changed from 300 to 120 seconds
}
```

**Reasoning**:
- Hugo builds are sequential, CPU-intensive
- Rarely need >1 replica (builds complete quickly)
- Scale to 0 faster after build completes
- If burst of builds, they queue and process one at a time

---

## Immediate Action Items

### Priority 1: Find Missing Messages (CRITICAL)

1. **Check blob storage for generated sites**:
   ```bash
   az storage blob list --container-name web-output --account-name aicontentprodstkwakpx --auth-mode login --query "[].name" -o table
   ```
   - If sites exist from those batch_ids, messages WERE processed
   - If not, messages were lost

2. **Check Application Insights logs**:
   - More detailed logs than container logs
   - Might show processing that container logs missed

3. **Check for silent exceptions**:
   - Review error handling in message_handler
   - Exceptions might be swallowed

### Priority 2: Fix Duplicate Message Issue

1. Implement distributed lock in markdown-generator
2. Or: Use idempotency - site-publisher ignores duplicate batch_ids
3. Or: Single-replica markdown-generator (but loses fault tolerance)

### Priority 3: Add Comprehensive Logging

1. Add Hugo build logging (see examples above)
2. Add queue visibility debugging
3. Add message processing tracing
4. Add replica ID to all logs

### Priority 4: Fix KEDA Config

1. Change queueLengthStrategy to "perReplica"
2. Consider reducing maxReplicas to 1
3. Reduce cooldownPeriod to 120s

---

## Testing Plan

1. **Trigger new collection**:
   ```bash
   # Start collector manually
   # Should generate markdown
   # Should send site-publish request
   ```

2. **Monitor site-publisher**:
   ```bash
   # Watch logs for:
   # - Message reception
   # - Hugo build output
   # - Upload completion
   # - Final success message
   ```

3. **Verify static site**:
   ```bash
   # Check blob storage for new site
   # Check if site URL is accessible
   # Verify content matches markdown
   ```

4. **Verify KEDA scaling**:
   ```bash
   # Container should start within 30-60s of message
   # Should process and scale to 0 within 2-3 minutes total
   ```

---

**Status**: Critical investigation required - messages disappeared without processing  
**Files to Modify**:
- `/workspaces/ai-content-farm/containers/site-publisher/app.py` (logging)
- `/workspaces/ai-content-farm/containers/site-publisher/site_builder.py` (Hugo logging)
- `/workspaces/ai-content-farm/containers/markdown-generator/queue_processor.py` (duplicate message fix)
- `/workspaces/ai-content-farm/infra/container_app_site_publisher.tf` (KEDA config)
