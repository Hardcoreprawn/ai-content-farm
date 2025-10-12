# Site-Publisher Testing Plan - Fresh Run

**Date**: 2025-10-12  
**Status**: Ready to test with clean slate

---

## Changes Made

1. ✅ **Pinned site-publisher to maxReplicas=1** (correct for Hugo builds)
2. ✅ **Turned off automatic new revisions** (reduces log fragmentation)
3. ✅ **Restarted all containers** (fresh state)

---

## What to Monitor

### 1. Collector → Processor Flow
```bash
# Watch collector generate messages
az containerapp logs show --name ai-content-prod-collector --resource-group ai-content-prod-rg --tail 50 --follow true

# Expected: "Collected X topics, sent to processing queue"
```

### 2. Processor → Markdown-Generator Flow
```bash
# Watch processor consume and generate markdown requests
az containerapp logs show --name ai-content-prod-processor --resource-group ai-content-prod-rg --tail 50 --follow true

# Expected: 
# - "Processing topic: ..."
# - "Sent to markdown-generation queue"
# - Watch for 429 errors (OpenAI rate limiting)
```

### 3. Markdown-Generator → Site-Publisher Flow
```bash
# Watch markdown-gen process and send site-publish trigger
az containerapp logs show --name ai-content-prod-markdown-gen --resource-group ai-content-prod-rg --tail 50 --follow true

# Expected:
# - "Successfully processed article: ... (Xms)"
# - "Queue empty after processing X messages"
# - "Sent publish request to site-publisher"
# - Watch for: Multiple replicas sending duplicate triggers
```

### 4. Site-Publisher (CRITICAL - Need Visibility)
```bash
# Watch site-publisher receive message and build site
az containerapp logs show --name ai-content-prod-site-publisher --resource-group ai-content-prod-rg --tail 100 --follow true

# NEED TO SEE:
# - "Processing queue message <id>"
# - "Starting build and deploy pipeline"
# - Hugo build output
# - "Deployed X files to blob storage"
# - OR: Error messages explaining what failed
```

---

## Key Questions to Answer

### Question 1: Do messages reach site-publisher queue?
```bash
# Check queue depth
az storage message peek --queue-name site-publishing-requests --account-name aicontentprodstkwakpx --auth-mode login --num-messages 5 2>&1 | jq '.'
```

### Question 2: Does site-publisher scale up automatically?
```bash
# Check replicas
az containerapp replica list --name ai-content-prod-site-publisher --resource-group ai-content-prod-rg --query "[].{name:name,status:properties.runningState}" -o table
```

### Question 3: Are static files being generated?
```bash
# Check $web container (static website hosting)
az storage blob list --container-name '$web' --account-name aicontentprodstkwakpx --auth-mode login --query "[].name" -o table | head -20

# Check web-output container (if different)
az storage blob list --container-name 'web-output' --account-name aicontentprodstkwakpx --auth-mode login --query "[].name" -o table | head -20
```

### Question 4: What about processed markdown files?
```bash
# Check markdown-content container for generated .md files
az storage blob list --container-name 'markdown-content' --account-name aicontentprodstkwakpx --auth-mode login --prefix "processed/" --query "[].name" -o table | head -20
```

---

## Known Issues to Watch For

### Issue 1: Duplicate Site-Publish Messages
**Symptom**: 3 markdown-gen replicas all send site-publish trigger  
**Evidence**: We saw 2-3 messages with same batch_id but different markdown_count  
**Impact**: Site might build multiple times for same batch  
**Look for**: Multiple "Sent publish request" logs at same timestamp

### Issue 2: Site-Publisher Silent Failures
**Symptom**: Messages disappear from queue but no logs, no static site  
**Evidence**: Earlier we saw 3 messages vanish without processing logs  
**Impact**: Site never gets built  
**Look for**: "Received 0 messages" when queue should have messages

### Issue 3: Hugo Build Failures
**Symptom**: Site-publisher processes message but build fails  
**Evidence**: Need to see - no logs available from previous runs  
**Impact**: No static site generated  
**Look for**: Exception logs, Hugo error messages, file I/O errors

### Issue 4: Missing Blob Container Configuration
**Symptom**: Hugo builds but can't find output destination  
**Evidence**: $web container is empty, web-output might not exist  
**Look for**: "Container not found", "Permission denied", "No such container"

---

## Expected Timeline (Approximate)

```
T+0:00  - Collector starts, scrapes Reddit/Mastodon/RSS
T+0:30  - Collector sends messages to processing queue
T+0:31  - Processor scales up (3-5 replicas)
T+0:31  - Processor hits OpenAI API (watch for 429 errors!)
T+2:00  - Processor completes, sends to markdown-gen queue
T+2:01  - Markdown-gen scales up (3 replicas - too many!)
T+2:03  - Markdown-gen completes (80 msgs in 2-3 seconds)
T+2:03  - Markdown-gen sends site-publish trigger (watch for duplicates!)
T+2:04  - Site-publisher scales up (1 replica)
T+2:04  - Site-publisher receives message (CRITICAL - need to see this!)
T+2:05  - Hugo build starts (NEED LOGS!)
T+2:10  - Hugo build completes, uploads to blob storage (NEED LOGS!)
T+2:10  - Site-publisher signals completion
T+7:10  - All containers scale to 0 (5-minute cooldown)
```

---

## Commands to Run

### Start Collection
```bash
# Manually start collector (or wait for CRON at 00:00, 08:00, 16:00 UTC)
# Since collector is CRON-based, easiest to just restart it
az containerapp replica list --name ai-content-prod-collector --resource-group ai-content-prod-rg
# If no replicas, wait for next CRON window or trigger manually via Azure Portal
```

### Monitor All Containers (Multi-terminal)
```bash
# Terminal 1 - Collector
watch -n 5 'az containerapp replica list --name ai-content-prod-collector --resource-group ai-content-prod-rg --query "[].properties.runningState" -o tsv'

# Terminal 2 - Processor  
watch -n 5 'az containerapp replica list --name ai-content-prod-processor --resource-group ai-content-prod-rg --query "[].properties.runningState" -o tsv | wc -l'

# Terminal 3 - Markdown-gen
watch -n 5 'az containerapp replica list --name ai-content-prod-markdown-gen --resource-group ai-content-prod-rg --query "[].properties.runningState" -o tsv | wc -l'

# Terminal 4 - Site-publisher (CRITICAL)
watch -n 5 'az containerapp replica list --name ai-content-prod-site-publisher --resource-group ai-content-prod-rg --query "[].properties.runningState" -o tsv'
```

### Check Queue Depths in Real-Time
```bash
# Run this in a loop to see messages flowing
while true; do
  echo "=== $(date) ==="
  echo -n "Processing queue: "
  az storage message peek --queue-name content-processing-requests --account-name aicontentprodstkwakpx --auth-mode login --num-messages 1 2>/dev/null | jq 'length'
  echo -n "Markdown queue: "
  az storage message peek --queue-name markdown-generation-requests --account-name aicontentprodstkwakpx --auth-mode login --num-messages 1 2>/dev/null | jq 'length'
  echo -n "Site-publish queue: "
  az storage message peek --queue-name site-publishing-requests --account-name aicontentprodstkwakpx --auth-mode login --num-messages 1 2>/dev/null | jq 'length'
  echo ""
  sleep 10
done
```

---

## Success Criteria

1. ✅ Collector generates messages (confirmed working)
2. ✅ Processor scales and processes (confirmed working, watch for 429s)
3. ✅ Markdown-gen scales and processes (confirmed working at 21-36ms/article)
4. ❓ **Markdown-gen sends site-publish trigger (need to verify only ONE replica sends)**
5. ❓ **Site-publisher scales up when message arrives (KEDA issue?)**
6. ❓ **Site-publisher receives and processes message (need logs!)**
7. ❓ **Hugo build executes successfully (need logs!)**
8. ❓ **Static files appear in blob storage (need to verify!)**
9. ✅ All containers scale to 0 after cooldown (5 minutes)

---

## Next Steps After This Run

1. **If site-publisher still shows no logs**:
   - Check KEDA authentication for site-publisher specifically
   - Check if queue messages have correct format
   - Add debug logging to message_handler

2. **If site-publisher processes but fails**:
   - Analyze error messages
   - Check Hugo configuration
   - Check blob storage permissions
   - Check container resource limits

3. **If site-publisher succeeds**:
   - Add comprehensive logging (as documented)
   - Fix duplicate message issue
   - Optimize KEDA settings
   - Add monitoring/alerts

---

**Ready to trigger collection and monitor!**
