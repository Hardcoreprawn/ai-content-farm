# Pipeline Verification Quick Reference

## 🚀 Quick Start

```bash
# Interactive verification tool
./scripts/verify-pipeline.sh

# Or check status immediately
az containerapp list \
  --resource-group ai-content-prod-rg \
  --query "[].{Name:name, Status:properties.runningStatus, Replicas:properties.template.scale.minReplicas}" \
  --output table
```

## 📋 Common Commands

### Check KEDA Scaling
```bash
# Watch processor scaling in real-time
watch -n 5 "az containerapp replica list \
  --name ai-content-prod-processor \
  --resource-group ai-content-prod-rg \
  --output table"
```

### Stream Logs (Most Important)
```bash
# Site-generator (REFACTORED - watch for errors!)
az containerapp logs show \
  --name ai-content-prod-site-generator \
  --resource-group ai-content-prod-rg \
  --follow --tail 100

# Processor
az containerapp logs show \
  --name ai-content-prod-processor \
  --resource-group ai-content-prod-rg \
  --follow --tail 100

# Collector
az containerapp logs show \
  --name ai-content-prod-collector \
  --resource-group ai-content-prod-rg \
  --follow --tail 100
```

### Check Queue Depths
```bash
# Process topic queue (after collection)
az storage queue show \
  --name process-topic \
  --account-name aicontentprodstorage \
  --auth-mode login \
  --query "approximateMessageCount"

# Markdown generation queue
az storage queue show \
  --name generate-markdown \
  --account-name aicontentprodstorage \
  --auth-mode login \
  --query "approximateMessageCount"

# Site publish queue
az storage queue show \
  --name publish-site \
  --account-name aicontentprodstorage \
  --auth-mode login \
  --query "approximateMessageCount"
```

### Inspect Blob Storage
```bash
# Today's collections
az storage blob list \
  --account-name aicontentprodstorage \
  --container-name collected-content \
  --prefix "collections/$(date +%Y/%m/%d)/" \
  --auth-mode login \
  --output table

# Today's processed content
az storage blob list \
  --account-name aicontentprodstorage \
  --container-name processed-content \
  --prefix "$(date +%Y/%m/%d)/" \
  --auth-mode login \
  --output table

# Today's markdown
az storage blob list \
  --account-name aicontentprodstorage \
  --container-name markdown-content \
  --prefix "articles/$(date +%Y/%m/%d)/" \
  --auth-mode login \
  --output table
```

### Check for Errors (Post-Refactor)
```bash
# Site-generator errors
az containerapp logs show \
  --name ai-content-prod-site-generator \
  --resource-group ai-content-prod-rg \
  --tail 500 \
  | grep -E "ERROR|Exception|Traceback|AttributeError|TypeError" -A 10

# Application Insights exceptions
az monitor app-insights query \
  --app ai-content-prod-insights \
  --resource-group ai-content-prod-rg \
  --analytics-query "
    exceptions
    | where timestamp > ago(1h)
    | where cloud_RoleName == 'ai-content-prod-site-generator'
    | project timestamp, type, outerMessage
    | order by timestamp desc
  " \
  --output table
```

## 🎯 Verification Workflow

### 1. Check Initial State
```bash
./scripts/verify-pipeline.sh
# Select option 1: Show pipeline status overview
```

### 2. Trigger Collection (Optional)
```bash
# Get collector URL
COLLECTOR_URL=$(az containerapp show \
  --name ai-content-prod-collector \
  --resource-group ai-content-prod-rg \
  --query "properties.configuration.ingress.fqdn" \
  --output tsv)

# Trigger collection
curl -X POST "https://${COLLECTOR_URL}/collect" \
  -H "Content-Type: application/json" \
  -d '{"template": "tech-news", "max_topics": 5}'
```

### 3. Monitor Collection
```bash
# Stream collector logs
./scripts/verify-pipeline.sh
# Select option 4: Stream collector logs

# Look for:
# ✅ "Collected X topics"
# ✅ "Saved collection to blob"
# ✅ "Enqueued X messages to process-topic"
```

### 4. Watch KEDA Scale Processor
```bash
./scripts/verify-pipeline.sh
# Select option 3: Watch KEDA scaling in real-time

# Expected: Processor replicas increase from 0 to N
```

### 5. Monitor Processing
```bash
# Stream processor logs
./scripts/verify-pipeline.sh
# Select option 5: Stream processor logs

# Look for:
# ✅ "Processing topic: {id}"
# ✅ "Saved processed content"
# ✅ "Enqueued to generate-markdown"
```

### 6. Monitor Markdown Generation
```bash
./scripts/verify-pipeline.sh
# Select option 6: Stream markdown-gen logs

# Look for:
# ✅ "Rendering template"
# ✅ "Saved markdown to blob"
# ✅ "Enqueued to publish-site"
```

### 7. Verify Site Generation (CRITICAL - Refactored)
```bash
./scripts/verify-pipeline.sh
# Select option 8: Check site-generator for refactor errors

# Then select option 7: Stream site-generator logs

# Watch for OOP → Functional refactor issues:
# ❌ AttributeError (class methods on functions)
# ❌ TypeError (parameter mismatches)
# ❌ ImportError (module reorganization)
```

### 8. Verify Scale-Down
```bash
# After 5-10 minutes, check all containers scaled to 0
az containerapp replica list \
  --name ai-content-prod-processor \
  --resource-group ai-content-prod-rg

# Should return empty list
```

## 🚨 What to Look For

### Success Indicators ✅
- Collections saved to blob storage
- Queue messages created (count matches topics)
- KEDA scales containers from 0→N→0
- Processed content has enrichment data
- Markdown files have proper frontmatter
- Static site generated successfully
- No exceptions in logs

### Failure Indicators ❌
- AttributeError or TypeError in site-generator
- Containers stuck at 0 replicas (KEDA not scaling)
- Messages stuck in queues
- Missing blob artifacts
- Exceptions in Application Insights
- Containers don't scale back to 0

## 📊 One-Line Status Check

```bash
# Quick pipeline health check
echo "Collector: $(az containerapp replica list --name ai-content-prod-collector --resource-group ai-content-prod-rg --query 'length(@)' -o tsv) replicas | Processor: $(az containerapp replica list --name ai-content-prod-processor --resource-group ai-content-prod-rg --query 'length(@)' -o tsv) replicas | Queue: $(az storage queue show --name process-topic --account-name aicontentprodstorage --auth-mode login --query 'approximateMessageCount' -o tsv) messages"
```

## 🔧 Troubleshooting

### KEDA Not Scaling
```bash
# Check scaler configuration
az containerapp show \
  --name ai-content-prod-processor \
  --resource-group ai-content-prod-rg \
  --query "properties.template.scale.rules" \
  --output json
```

### Site-Generator Errors (Post-Refactor)
```bash
# Get full error context
az containerapp logs show \
  --name ai-content-prod-site-generator \
  --resource-group ai-content-prod-rg \
  --tail 1000 > /tmp/site-gen-errors.log

# Search for specific error patterns
grep -E "AttributeError|TypeError|ImportError" /tmp/site-gen-errors.log -B 5 -A 10
```

### Messages Not Processing
```bash
# Check dead-letter queues
az storage queue list \
  --account-name aicontentprodstorage \
  --auth-mode login \
  --query "[?contains(name, 'poison')]"
```

## 📝 Documentation

- **Full Plan**: `PIPELINE_VERIFICATION_PLAN.md`
- **Interactive Tool**: `./scripts/verify-pipeline.sh`
- **This Guide**: `docs/VERIFICATION_QUICK_REFERENCE.md`
