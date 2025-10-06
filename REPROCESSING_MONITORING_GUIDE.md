# Reprocessing Performance Monitoring Guide

## Current Scaling Configuration

### Content Processor
- **Current**: min=0, max=3 replicas
- **KEDA Rule**: Scales based on queue depth (queueLength=1, immediate scaling)
- **Suggestion**: Increase to max=10 for better throughput during bulk reprocessing

### Site Generator
- **Current**: min=0, max=2 replicas
- **KEDA Rule**: Scales based on site-generation-requests queue
- **Consideration**: May become bottleneck after processing completes

### Collector
- **Current**: min=0, max=2 replicas
- **KEDA Rule**: Cron-based scaling (not queue-based)

## Monitoring Tools

### 1. Custom Monitoring Script (NEW)
**Location**: `scripts/monitor-reprocessing.sh`

**Single Snapshot**:
```bash
./scripts/monitor-reprocessing.sh
```

Shows:
- Current queue depth
- Container replica counts for all services
- Content statistics (collected/processed counts)
- Estimated completion time

**Continuous Monitoring**:
```bash
./scripts/monitor-reprocessing.sh --continuous 10
```

Live table showing every 10 seconds:
- Time | Queue | Processor Replicas | Site Gen Replicas | Processed Count | Rate (items/min)

Perfect for watching:
- How quickly queue drains
- How fast KEDA scales up/down
- Actual processing throughput
- System bottlenecks

### 2. Reprocess Status Endpoint
**Endpoint**: `GET /reprocess/status`

```bash
curl https://ai-content-prod-collector.../reprocess/status | jq
```

Returns:
```json
{
  "status": "success",
  "data": {
    "queue_depth": 577,
    "collected_items": 577,
    "processed_items": 3348,
    "queue_name": "content-processing-requests"
  }
}
```

### 3. Azure Portal Metrics

**Container Apps Metrics**:
- Navigate to: Portal → Resource Groups → ai-content-prod-rg → content-processor
- Metrics to watch:
  - **Replica Count**: See how many instances are running
  - **CPU Usage**: Check if CPU-bound
  - **Memory Usage**: Check for memory issues
  - **HTTP Request Rate**: Requests per second
  - **Response Time**: Processing latency

**Storage Queue Metrics**:
- Navigate to: Portal → Storage Account → aicontentprodstkwakpx → Queues → content-processing-requests
- Metrics:
  - **Message Count**: Current queue depth
  - **Ingress**: Messages added per second
  - **Egress**: Messages processed per second
  - **Queue Capacity**: Storage usage

### 4. Azure CLI Commands

**Get Queue Depth**:
```bash
az storage queue stats \
  --account-name aicontentprodstkwakpx \
  --name content-processing-requests \
  --auth-mode login
```

**Get Replica Count**:
```bash
az containerapp replica list \
  --name ai-content-prod-processor \
  --resource-group ai-content-prod-rg \
  --query "length([])" -o tsv
```

**Live Container Logs**:
```bash
az containerapp logs show \
  --name ai-content-prod-processor \
  --resource-group ai-content-prod-rg \
  --tail 50 \
  --follow
```

**Get Recent Revisions**:
```bash
az containerapp revision list \
  --name ai-content-prod-processor \
  --resource-group ai-content-prod-rg \
  --query "[].{Name:name,Active:properties.active,Replicas:properties.replicas,Created:properties.createdTime}" \
  --output table
```

## Performance Expectations

### Current Configuration (max=3)
- **Parallel Processing**: Up to 3 items simultaneously
- **Processing Rate**: ~30 items/min (assuming 6s per item)
- **577 items**: ~19 minutes to complete
- **Cost**: $0.92 for processing

### Proposed Configuration (max=10)
- **Parallel Processing**: Up to 10 items simultaneously
- **Processing Rate**: ~100 items/min (assuming 6s per item)
- **577 items**: ~6 minutes to complete
- **Cost**: Same $0.92 (Azure OpenAI cost, not compute)
- **Additional Compute Cost**: Minimal (~$0.05 for 6 min vs 19 min)

### Bottleneck Analysis

**Processor → Site Generator Queue**:
- Each processed item triggers site generation
- If processor max=10, could queue 10 items/min
- Site generator max=2 may struggle to keep up
- **Recommendation**: Consider site-gen max=5

## Increasing Processor Capacity

### Option 1: Terraform Change (Recommended)
**File**: `infra/container_app_processor.tf`

```terraform
# Current
max_replicas = 3

# Proposed for bulk reprocessing
max_replicas = 10
```

**Deploy**:
```bash
cd infra
terraform plan
terraform apply
```

**Pros**: 
- Infrastructure as code
- Permanent change
- Tracked in git

**Cons**: 
- Requires terraform apply
- ~2-3 minutes to deploy

### Option 2: Azure CLI (Quick Test)
```bash
az containerapp update \
  --name ai-content-prod-processor \
  --resource-group ai-content-prod-rg \
  --max-replicas 10
```

**Pros**: 
- Immediate effect
- Good for testing

**Cons**: 
- Temporary (next terraform apply will revert)
- Not tracked in code

## Key Metrics to Watch

### 1. Queue Drain Rate
**Formula**: (Messages processed) / (Time elapsed)
**Target**: 100+ items/min with max=10
**Monitoring**: `./scripts/monitor-reprocessing.sh --continuous 10`

### 2. Replica Count Scaling
**Question**: How fast does KEDA scale up?
**Expected**: Should hit max replicas within 30-60 seconds
**Monitoring**: Azure Portal → Metrics → Replica Count

### 3. Processing Time per Item
**Formula**: Total time / Total items
**Target**: ~6 seconds per item
**Monitoring**: Container logs or Application Insights

### 4. Site Generator Queue Growth
**Question**: Does site-gen keep up with processor output?
**Concern**: If processor max=10 but site-gen max=2, queue builds up
**Monitoring**: Check `site-generation-requests` queue depth

### 5. Cost per Item
**Formula**: Total Azure OpenAI cost / Items processed
**Expected**: ~$0.0016 per item
**Monitoring**: Azure Cost Management (24h delay)

### 6. Error Rate
**Formula**: Failed items / Total items
**Target**: <1% errors
**Monitoring**: Container logs, Application Insights

## Monitoring During Reprocessing

### Phase 1: Queue Building (First 30 seconds)
Watch for:
- Queue depth ramping up to 577
- Collector response time
- Any queue client errors

### Phase 2: Processor Scaling (30-90 seconds)
Watch for:
- Replica count increasing to max
- CPU/memory usage per replica
- First processed items appearing

### Phase 3: Steady State (5-20 minutes)
Watch for:
- Consistent processing rate
- Queue depth steadily decreasing
- No replica restarts or errors
- Site-gen queue building up?

### Phase 4: Tail-off (Last few minutes)
Watch for:
- Replicas scaling down
- Final items completing
- Queue reaching zero
- Site generator catching up

## Recommended Monitoring Setup

**Before Starting Reprocessing**:
1. Open Azure Portal → Processor → Metrics (Replica Count chart)
2. Open terminal with: `./scripts/monitor-reprocessing.sh --continuous 10`
3. Open another terminal: `az containerapp logs show ... --follow`
4. Note start time and initial processed count

**During Reprocessing**:
- Watch continuous monitor for rate and scaling
- Check logs occasionally for errors
- Monitor Azure metrics for CPU/memory issues

**After Completion**:
- Calculate actual throughput (items/min)
- Check total time vs estimate
- Review any errors in logs
- Verify site generation completed
- Calculate actual cost vs estimate

## Azure Application Insights (Advanced)

If you want deep metrics:

**Custom Metrics to Add**:
```python
# In processor code
from opencensus.ext.azure import metrics_exporter
from opencensus.stats import aggregation as aggregation_module
from opencensus.stats import measure as measure_module
from opencensus.stats import stats as stats_module
from opencensus.stats import view as view_module

# Track processing time
processing_time_measure = measure_module.MeasureFloat(
    "processing_time",
    "Time to process one item",
    "seconds"
)

# Track success/failure
processing_success_measure = measure_module.MeasureInt(
    "processing_success",
    "Processing result",
    "count"
)
```

## Summary: What You Have Now

✅ **GET /reprocess/status** - Quick snapshot of queue and counts
✅ **Custom monitoring script** - Continuous live monitoring with rates
✅ **Azure Portal metrics** - Historical charts and alerting
✅ **Azure CLI commands** - Scriptable monitoring
✅ **Container logs** - Detailed error tracking

**Recommended Next Step**:
1. Increase processor max_replicas to 10 for better throughput
2. Consider site-gen max=5 to prevent bottleneck
3. Use continuous monitoring script during reprocessing
4. Analyze results to optimize for future runs

---

**Status**: Monitoring tools ready
**Script**: `./scripts/monitor-reprocessing.sh`
**Scaling**: Currently max=3, recommend max=10 for bulk operations
