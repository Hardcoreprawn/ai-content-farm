# Pipeline Verification Plan - Post Site-Generator Refactor
**Date**: October 9, 2025  
**Context**: After major refactor from OOP to functional programming  
**Objective**: Verify full pipeline functionality in Azure production environment  

## 🎯 Verification Approach

Per project philosophy: **"Direct Azure Development: Work in live Azure environment, not local development"**

We will verify the entire pipeline in the production Azure environment (`ai-content-prod-rg`) by:
1. Monitoring Azure Container Apps logs in real-time
2. Inspecting blob storage for content artifacts
3. Checking queue messages and processing
4. Observing KEDA scaling behavior

## 📋 Pre-Verification Checklist

### 1. Verify Deployment Status
```bash
# Check all container apps are running
az containerapp list \
  --resource-group ai-content-prod-rg \
  --query "[].{Name:name, Status:properties.runningStatus, Replicas:properties.template.scale.minReplicas}" \
  --output table

# Expected:
# - ai-content-prod-collector (Running, min replicas: 0)
# - ai-content-prod-processor (Running, min replicas: 0)
# - ai-content-prod-markdown-gen (Running, min replicas: 0)
# - ai-content-prod-site-generator (Running, min replicas: 0)
```

### 2. Check Recent Deployments
```bash
# Verify latest revision dates
az containerapp revision list \
  --name ai-content-prod-site-generator \
  --resource-group ai-content-prod-rg \
  --query "[0].{Name:name, Created:properties.createdTime, Active:properties.active}" \
  --output table
```

### 3. Verify Queue Infrastructure
```bash
# List all queues
az storage queue list \
  --account-name aicontentprodstorage \
  --auth-mode login \
  --query "[].name" \
  --output table

# Expected queues:
# - process-topic (fanout pattern)
# - generate-markdown
# - publish-site
```

## 🔍 Stage 1: Collection Verification

### Objective
Verify that content-collector:
- Runs on KEDA cron schedule (8-hour intervals)
- Collects topics from configured sources
- Saves collection JSON to blob storage
- Enqueues fanout messages to `process-topic` queue

### Verification Steps

#### 1.1 Trigger Collection Manually (Optional)
```bash
# Get collector endpoint
COLLECTOR_URL=$(az containerapp show \
  --name ai-content-prod-collector \
  --resource-group ai-content-prod-rg \
  --query "properties.configuration.ingress.fqdn" \
  --output tsv)

# Trigger collection via API
curl -X POST "https://${COLLECTOR_URL}/collect" \
  -H "Content-Type: application/json" \
  -d '{
    "template": "tech-news",
    "max_topics": 10
  }'
```

#### 1.2 Monitor Collection Logs
```bash
# Stream collector logs in real-time
az containerapp logs show \
  --name ai-content-prod-collector \
  --resource-group ai-content-prod-rg \
  --follow \
  --tail 50

# Look for:
# ✅ "Starting collection with template: tech-news"
# ✅ "Collected X topics from Y sources"
# ✅ "Saved collection to blob: collections/2025/10/09/collection_TIMESTAMP.json"
# ✅ "Enqueued X messages to process-topic queue"
# ❌ Any ERROR or EXCEPTION messages
```

#### 1.3 Verify Blob Storage
```bash
# List recent collections
az storage blob list \
  --account-name aicontentprodstorage \
  --container-name collected-content \
  --prefix "collections/2025/10/09/" \
  --auth-mode login \
  --query "[].{Name:name, Created:properties.creationTime, Size:properties.contentLength}" \
  --output table

# Download and inspect latest collection
LATEST_COLLECTION=$(az storage blob list \
  --account-name aicontentprodstorage \
  --container-name collected-content \
  --prefix "collections/2025/10/09/" \
  --auth-mode login \
  --query "[-1].name" \
  --output tsv)

az storage blob download \
  --account-name aicontentprodstorage \
  --container-name collected-content \
  --name "$LATEST_COLLECTION" \
  --file /tmp/latest-collection.json \
  --auth-mode login

# Inspect structure
jq '.metadata | {total_topics, sources, timestamp}' /tmp/latest-collection.json
jq '.topics[0] | {title, source, url}' /tmp/latest-collection.json
```

#### 1.4 Verify Queue Messages
```bash
# Check process-topic queue depth
az storage queue show \
  --name process-topic \
  --account-name aicontentprodstorage \
  --auth-mode login \
  --query "approximateMessageCount" \
  --output tsv

# Peek at messages (without dequeuing)
az storage message peek \
  --queue-name process-topic \
  --account-name aicontentprodstorage \
  --auth-mode login \
  --num-messages 5

# Expected message structure:
# {
#   "topic_id": "uuid",
#   "collection_id": "uuid",
#   "source": "reddit|rss|mastodon",
#   "blob_path": "collections/2025/10/09/collection_xxx.json"
# }
```

### Success Criteria - Stage 1
- [ ] Collection completes without errors
- [ ] Collection JSON saved to blob storage with correct structure
- [ ] Queue messages created (1 message per topic)
- [ ] Message count matches topic count in collection
- [ ] Logs show successful fanout operation

---

## 🔍 Stage 2: Processing Verification

### Objective
Verify that content-processor:
- KEDA scales up when messages appear in `process-topic` queue
- Processes each topic message individually
- Saves processed content to blob storage
- Enqueues message to `generate-markdown` queue

### Verification Steps

#### 2.1 Monitor KEDA Scaling
```bash
# Watch replica count in real-time
watch -n 5 "az containerapp replica list \
  --name ai-content-prod-processor \
  --resource-group ai-content-prod-rg \
  --query '[].name' \
  --output table | wc -l"

# Expected behavior:
# - Starts at 0 replicas (idle)
# - Scales to N replicas based on queue depth
# - Processes messages
# - Scales back to 0 when queue empty
```

#### 2.2 Monitor Processing Logs
```bash
# Stream processor logs
az containerapp logs show \
  --name ai-content-prod-processor \
  --resource-group ai-content-prod-rg \
  --follow \
  --tail 100

# Look for:
# ✅ "Scaled up from 0 to N replicas"
# ✅ "Processing topic: {topic_id}"
# ✅ "Enriched content with AI analysis"
# ✅ "Saved processed content to blob: processed-content/..."
# ✅ "Enqueued message to generate-markdown queue"
# ❌ Any processing failures or retries
```

#### 2.3 Verify Processed Blob Storage
```bash
# List processed content
az storage blob list \
  --account-name aicontentprodstorage \
  --container-name processed-content \
  --prefix "2025/10/09/" \
  --auth-mode login \
  --query "[].{Name:name, Created:properties.creationTime}" \
  --output table

# Download and inspect processed content
az storage blob download \
  --account-name aicontentprodstorage \
  --container-name processed-content \
  --name "2025/10/09/topic_xxx.json" \
  --file /tmp/processed-topic.json \
  --auth-mode login

# Verify processor added enrichment data
jq '. | {
  title, 
  filename,
  enrichment: .enrichment | keys,
  quality_score,
  processing_metadata
}' /tmp/processed-topic.json
```

#### 2.4 Verify Generate-Markdown Queue
```bash
# Check queue depth
az storage queue show \
  --name generate-markdown \
  --account-name aicontentprodstorage \
  --auth-mode login \
  --query "approximateMessageCount"

# Peek at messages
az storage message peek \
  --queue-name generate-markdown \
  --account-name aicontentprodstorage \
  --auth-mode login \
  --num-messages 5
```

#### 2.5 Monitor KEDA Scale-Down
```bash
# Verify processor scales back to 0
az containerapp replica list \
  --name ai-content-prod-processor \
  --resource-group ai-content-prod-rg \
  --output table

# Expected: Empty list after all messages processed
```

### Success Criteria - Stage 2
- [ ] KEDA scales up processor replicas when queue has messages
- [ ] Each topic processed individually (fanout pattern working)
- [ ] Processed content saved to blob with enrichment data
- [ ] Generate-markdown queue receives messages
- [ ] KEDA scales processor back to 0 when queue empty
- [ ] No processing errors or message dead-lettering

---

## 🔍 Stage 3: Markdown Generation Verification

### Objective
Verify that markdown-generator:
- KEDA scales up when messages appear in `generate-markdown` queue
- Generates markdown articles from processed content
- Saves markdown to blob storage
- Enqueues message to `publish-site` queue

### Verification Steps

#### 3.1 Monitor KEDA Scaling
```bash
# Watch markdown-generator replicas
watch -n 5 "az containerapp replica list \
  --name ai-content-prod-markdown-gen \
  --resource-group ai-content-prod-rg \
  --output table | wc -l"
```

#### 3.2 Monitor Generation Logs
```bash
# Stream markdown-generator logs
az containerapp logs show \
  --name ai-content-prod-markdown-gen \
  --resource-group ai-content-prod-rg \
  --follow \
  --tail 100

# Look for:
# ✅ "Processing markdown generation request"
# ✅ "Loaded processed content from blob"
# ✅ "Rendering template: blog|tldr|deepdive"
# ✅ "Saved markdown to blob: markdown-content/..."
# ✅ "Enqueued publish message"
```

#### 3.3 Verify Markdown Blob Storage
```bash
# List generated markdown
az storage blob list \
  --account-name aicontentprodstorage \
  --container-name markdown-content \
  --prefix "articles/2025/10/09/" \
  --auth-mode login \
  --query "[].{Name:name, Size:properties.contentLength}" \
  --output table

# Download and inspect markdown
az storage blob download \
  --account-name aicontentprodstorage \
  --container-name markdown-content \
  --name "articles/2025/10/09/topic-slug.md" \
  --file /tmp/article.md \
  --auth-mode login

# Verify frontmatter and content
head -30 /tmp/article.md
```

#### 3.4 Verify Publish Queue
```bash
# Check publish-site queue
az storage queue show \
  --name publish-site \
  --account-name aicontentprodstorage \
  --auth-mode login \
  --query "approximateMessageCount"
```

### Success Criteria - Stage 3
- [ ] KEDA scales up markdown-generator replicas
- [ ] Markdown files generated with proper frontmatter
- [ ] Markdown saved to blob storage
- [ ] Publish-site queue receives messages
- [ ] KEDA scales back to 0 after processing

---

## 🔍 Stage 4: Site Generation Verification (Refactored Container)

### Objective
Verify that site-generator (newly refactored to functional programming):
- KEDA scales up when messages appear in `publish-site` queue
- Reads markdown from blob storage
- Generates static site successfully
- Handles errors gracefully with new functional architecture

### Verification Steps

#### 4.1 Monitor KEDA Scaling
```bash
# Watch site-generator replicas
watch -n 5 "az containerapp replica list \
  --name ai-content-prod-site-generator \
  --resource-group ai-content-prod-rg \
  --output table | wc -l"

# This is the critical test - did refactor break scaling?
```

#### 4.2 Monitor Site Generation Logs (CRITICAL)
```bash
# Stream site-generator logs - WATCH FOR REFACTOR ISSUES
az containerapp logs show \
  --name ai-content-prod-site-generator \
  --resource-group ai-content-prod-rg \
  --follow \
  --tail 200

# Look for SUCCESS indicators:
# ✅ "Processing site generation request"
# ✅ "Loaded markdown from blob: markdown-content/..."
# ✅ "Generated static site successfully"
# ✅ "Site generation completed in X seconds"

# Look for FAILURE indicators (from OOP → Functional refactor):
# ❌ AttributeError (likely from class → function conversion)
# ❌ TypeError (parameter mismatches)
# ❌ "NoneType has no attribute..." (missing function return values)
# ❌ Import errors (module reorganization issues)
# ❌ Configuration loading failures (changed initialization pattern)
```

#### 4.3 Test Functional Architecture Directly
```bash
# Get site-generator endpoint
SITE_GEN_URL=$(az containerapp show \
  --name ai-content-prod-site-generator \
  --resource-group ai-content-prod-rg \
  --query "properties.configuration.ingress.fqdn" \
  --output tsv)

# Test health endpoint (should work with functional refactor)
curl "https://${SITE_GEN_URL}/health"

# Test status endpoint
curl "https://${SITE_GEN_URL}/status"

# Manually trigger site generation
curl -X POST "https://${SITE_GEN_URL}/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "markdown-content/articles/",
    "force_rebuild": false
  }'
```

#### 4.4 Verify Static Site Output
```bash
# Check for generated site artifacts
az storage blob list \
  --account-name aicontentprodstorage \
  --container-name site-output \
  --auth-mode login \
  --query "[].{Name:name, Modified:properties.lastModified}" \
  --output table

# Look for:
# - index.html
# - article pages
# - _site/ directory structure
# - Recent modification times (indicates successful generation)
```

#### 4.5 Check Application Insights for Errors
```bash
# Query Application Insights for exceptions
az monitor app-insights query \
  --app ai-content-prod-insights \
  --resource-group ai-content-prod-rg \
  --analytics-query "
    exceptions
    | where timestamp > ago(1h)
    | where cloud_RoleName == 'ai-content-prod-site-generator'
    | project timestamp, type, outerMessage, innermostMessage
    | order by timestamp desc
  " \
  --output table
```

### Success Criteria - Stage 4 (REFACTOR VALIDATION)
- [ ] KEDA scales up site-generator replicas
- [ ] No AttributeError or TypeError from OOP → Functional refactor
- [ ] Configuration loading works with new functional pattern
- [ ] Static site generated successfully
- [ ] Site artifacts saved to blob storage
- [ ] KEDA scales back to 0 after processing
- [ ] No exceptions in Application Insights

---

## 📊 End-to-End Pipeline Metrics

### Overall Success Indicators
```bash
# Check full pipeline timing
# Expected flow: Collection → Processing → Generation → Site (< 30 minutes)

# Count artifacts at each stage
echo "=== Pipeline Artifact Count ==="
echo "Collections:"
az storage blob list --account-name aicontentprodstorage --container-name collected-content --prefix "collections/2025/10/09/" --auth-mode login --query "length(@)"

echo "Processed:"
az storage blob list --account-name aicontentprodstorage --container-name processed-content --prefix "2025/10/09/" --auth-mode login --query "length(@)"

echo "Markdown:"
az storage blob list --account-name aicontentprodstorage --container-name markdown-content --prefix "articles/2025/10/09/" --auth-mode login --query "length(@)"

echo "Site artifacts:"
az storage blob list --account-name aicontentprodstorage --container-name site-output --auth-mode login --query "length(@)"
```

### KEDA Scaling Analysis
```bash
# Review KEDA scaling events across all containers
for container in collector processor markdown-gen site-generator; do
  echo "=== $container KEDA Events ==="
  az monitor activity-log list \
    --resource-group ai-content-prod-rg \
    --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
    --query "[?contains(resourceId, '$container')].{Time:eventTimestamp, Status:status.value, Operation:operationName.localizedValue}" \
    --output table
done
```

### Cost Verification (Zero-Replica Scaling)
```bash
# Verify containers scale to 0 when idle
echo "=== Current Replica Counts (Should be 0 when idle) ==="
for container in collector processor markdown-gen site-generator; do
  COUNT=$(az containerapp replica list \
    --name "ai-content-prod-$container" \
    --resource-group ai-content-prod-rg \
    --query "length(@)" \
    --output tsv)
  echo "$container: $COUNT replicas"
done
```

---

## 🚨 Troubleshooting Guide

### Issue: KEDA Not Scaling Up
```bash
# Check KEDA scaler configuration
az containerapp show \
  --name ai-content-prod-processor \
  --resource-group ai-content-prod-rg \
  --query "properties.template.scale.rules" \
  --output json

# Verify managed identity has queue permissions
az role assignment list \
  --assignee $(az containerapp show --name ai-content-prod-processor --resource-group ai-content-prod-rg --query "identity.principalId" -o tsv) \
  --scope /subscriptions/$(az account show --query id -o tsv)/resourceGroups/ai-content-prod-rg
```

### Issue: Site-Generator Errors (Post-Refactor)
```bash
# Get detailed error logs
az containerapp logs show \
  --name ai-content-prod-site-generator \
  --resource-group ai-content-prod-rg \
  --tail 500 \
  | grep -E "ERROR|Exception|Traceback" -A 10

# Check for common refactor issues:
# - AttributeError → class method called on function
# - TypeError → parameter mismatches
# - ImportError → module reorganization issues
```

### Issue: Messages Stuck in Queue
```bash
# Check dead-letter queue (if configured)
az storage queue show \
  --name process-topic-poison \
  --account-name aicontentprodstorage \
  --auth-mode login

# Check message age
az storage message peek \
  --queue-name process-topic \
  --account-name aicontentprodstorage \
  --auth-mode login \
  --num-messages 1
```

---

## ✅ Final Validation Checklist

### Pipeline Functionality
- [ ] Content collected from sources
- [ ] Collection saved to blob storage
- [ ] Fanout messages created (1 per topic)
- [ ] Processor scaled up automatically
- [ ] Topics processed individually
- [ ] Processed content saved to blob
- [ ] Markdown generated from processed content
- [ ] Site generated from markdown
- [ ] All containers scaled back to 0

### KEDA Scaling Behavior
- [ ] Collector runs on cron schedule (8 hours)
- [ ] Processor scales 0→N based on process-topic queue
- [ ] Markdown-gen scales 0→N based on generate-markdown queue
- [ ] Site-generator scales 0→N based on publish-site queue
- [ ] All containers scale back to 0 when idle

### Refactor Validation (Site-Generator)
- [ ] No OOP-related errors (AttributeError, TypeError)
- [ ] Functional architecture handles requests correctly
- [ ] Configuration loading works
- [ ] Error handling graceful
- [ ] Performance acceptable

### Observability
- [ ] Logs streaming successfully
- [ ] Application Insights capturing telemetry
- [ ] No critical errors or exceptions
- [ ] Metrics show expected behavior

---

## 📝 Verification Session Log

**Start Time**: _____________  
**Operator**: _____________  

### Stage 1: Collection
- [ ] Triggered at: _____________
- [ ] Completed at: _____________
- [ ] Topics collected: _____________
- [ ] Issues: _____________

### Stage 2: Processing
- [ ] Started at: _____________
- [ ] KEDA scaled to: _____________ replicas
- [ ] Completed at: _____________
- [ ] Issues: _____________

### Stage 3: Markdown Generation
- [ ] Started at: _____________
- [ ] Articles generated: _____________
- [ ] Completed at: _____________
- [ ] Issues: _____________

### Stage 4: Site Generation (REFACTORED)
- [ ] Started at: _____________
- [ ] KEDA scaled to: _____________ replicas
- [ ] Completed at: _____________
- [ ] **Refactor issues**: _____________
- [ ] **Functional architecture working**: YES / NO

### Overall Results
- **Total pipeline time**: _____________
- **Success rate**: _____________
- **Critical issues**: _____________
- **Next steps**: _____________

---

## 🎯 Next Actions Based on Results

### If All Green ✅
- Document successful verification
- Update STATUS.md with confirmed working state
- Close related GitHub issues
- Plan next feature implementation

### If Issues Found ❌
- Capture detailed error logs
- Create targeted GitHub issues
- Rollback if critical (if needed)
- Fix and re-verify

---

**End of Verification Plan**
