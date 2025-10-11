# Site Publisher Gap Analysis

**Date**: October 11, 2025 13:25 UTC  
**Status**: 🚨 **BLOCKING ISSUE IDENTIFIED**

## Executive Summary

The site-publisher infrastructure is deployed and functional, but the **automated end-to-end pipeline is broken** because the markdown-generator does not signal the site-publisher when it finishes processing.

**Impact**: Site will never auto-publish after content collection unless manually triggered.

---

## Current State Verification (October 11, 2025 13:20-13:25 UTC)

### ✅ What's Working

1. **All containers deployed and running**:
   - `ai-content-prod-collector`: Running (KEDA 0→1→0 working!)
   - `ai-content-prod-processor`: Running (processed 267 messages)
   - `ai-content-prod-markdown-gen`: Running (processed 137 messages)
   - `ai-content-prod-site-publisher`: Running (waiting for trigger)

2. **Content pipeline successful**:
   - Collection: Complete
   - Processing: 267 articles processed
   - Markdown generation: **4212 markdown files created** in `markdown-content` container
   - Quality: Only 1 "best of" article (legitimate)

3. **Infrastructure complete**:
   - Queue: `site-publishing-requests` created
   - Container: `web-backup` created
   - KEDA: Workload identity configured
   - Hugo: PaperMod theme deployed (v7.0)

### ❌ What's Broken

**CRITICAL**: Markdown-generator does not send completion signal to site-publisher.

**Evidence**:
```bash
# Markdown files created
$ az storage blob list --container markdown-content --query "length([?contains(name, '.md')])"
4212

# Site-publisher queue (should have 1 message)
$ az storage message peek --queue-name site-publishing-requests
[]  # EMPTY!

# Site-publisher logs
"Received 0 messages from queue 'site-publishing-requests'"
"Queue empty after processing 0 messages"
```

**Root Cause**: Phase 6 from checklist was never implemented.

---

## The Missing Code (Phase 6)

### Current Code (markdown-generator/main.py:142-147)
```python
if messages_processed == 0:
    # Queue is empty - stop polling and let KEDA scale down
    logger.info(
        f"✅ Queue empty after processing {total_processed} messages. "
        "Container will stay alive for HTTP requests. "
        "KEDA will scale to 0 when queue remains empty."
    )
    break  # ❌ JUST BREAKS - DOESN'T SIGNAL SITE-PUBLISHER
```

### Required Code (from SITE_PUBLISHER_CHECKLIST.md Phase 6)
```python
if messages_processed == 0:
    # Queue is empty - signal site-publisher to build site
    logger.info(
        f"✅ Markdown queue empty after processing {total_processed} messages - "
        "signaling site-publisher"
    )
    
    # Send completion signal to site-publisher queue
    from libs.queue_client import send_queue_message
    from libs.models import QueueMessageModel
    
    publish_message = QueueMessageModel(
        service_name="markdown-generator",
        operation="site_publish_request",
        payload={
            "batch_id": f"collection-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
            "markdown_count": total_processed,
            "trigger": "queue_empty",
            "markdown_container": settings.markdown_container,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )
    
    await send_queue_message(
        queue_name="site-publishing-requests",
        message=publish_message
    )
    
    logger.info(
        f"📤 Sent publish request to site-publisher "
        f"(batch_id={publish_message.payload['batch_id']})"
    )
    
    break  # Now let KEDA scale down
```

---

## Impact Analysis

### Without Fix (Current State)
- ❌ Site never auto-publishes after content collection
- ❌ 4212 markdown files sitting unused in blob storage
- ❌ Manual intervention required to trigger publish
- ❌ End-to-end automation broken

### With Fix (After Implementation)
- ✅ Collection → Processing → Markdown → **Signal** → Publish (fully automated)
- ✅ KEDA scales site-publisher 0→1 when message arrives
- ✅ Hugo builds 4212 articles into static site
- ✅ Site deployed to $web container
- ✅ KEDA scales back to 0 (cost efficient)

---

## Implementation Plan

### Step 1: Add completion signal to markdown-generator
**File**: `/workspaces/ai-content-farm/containers/markdown-generator/main.py`

**Changes**:
1. Import queue client functions at top of `startup_queue_processor()`
2. Replace the `break` statement with signal-sending code (see above)
3. Add error handling for queue send failures

**Estimated time**: 30 minutes

### Step 2: Test locally
```bash
# Build container
cd containers/markdown-generator
docker build -t markdown-generator:test .

# Run with queue access
docker run --env-file .env markdown-generator:test
```

**Estimated time**: 15 minutes

### Step 3: Deploy via CI/CD
```bash
git checkout -b feature/markdown-gen-completion-signal
# Make changes
git commit -m "Add site-publisher completion signal to markdown-generator"
git push origin feature/markdown-gen-completion-signal
# Create PR → CI/CD → Deploy
```

**Estimated time**: 45 minutes (including pipeline wait)

### Step 4: Verify end-to-end
1. Trigger collection (or wait for scheduled run)
2. Watch pipeline: collection → processing → markdown
3. Verify message appears in `site-publishing-requests` queue
4. Verify site-publisher scales 0→1
5. Check Hugo build logs
6. Verify site deployed to $web
7. Access static website URL

**Estimated time**: 1-2 hours (depending on collection schedule)

---

## Workaround (Manual Trigger)

Until Phase 6 is implemented, you can manually trigger the site-publisher:

```bash
# Get the site-publisher FQDN
FQDN="ai-content-prod-site-publisher.whitecliff-6844954b.uksouth.azurecontainerapps.io"

# Trigger manual publish
curl -X POST "https://${FQDN}/publish" \
  -H "Content-Type: application/json" \
  -d '{
    "batch_id": "manual-trigger-20251011",
    "markdown_container": "markdown-content",
    "output_container": "$web"
  }'
```

---

## Success Criteria

- [ ] Markdown-generator sends message to `site-publishing-requests` queue when done
- [ ] Site-publisher receives message and scales 0→1
- [ ] Hugo builds site from 4212 markdown files
- [ ] Static site deployed to $web container
- [ ] Site accessible at Azure static URL
- [ ] End-to-end automation confirmed working

---

## Next Actions

**Priority**: 🚨 **HIGH** (blocks automated publishing)

1. **Immediate**: Update SITE_PUBLISHER_CHECKLIST.md to reflect current status (DONE)
2. **Next**: Implement Phase 6 completion signal in markdown-generator
3. **Then**: Deploy and test end-to-end pipeline
4. **Finally**: Update documentation with lessons learned

---

**Generated**: October 11, 2025 13:25 UTC  
**Last Updated**: October 11, 2025 13:25 UTC
