# Pipeline Monitoring and KEDA Scaling Guide

This guide provides comprehensive tools and strategies for monitoring your four-container pipeline and optimizing KEDA scaling settings.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Monitoring Tools](#monitoring-tools)
3. [Understanding Your Pipeline](#understanding-your-pipeline)
4. [KEDA Scaling Analysis](#keda-scaling-analysis)
5. [Common Scenarios](#common-scenarios)
6. [Troubleshooting](#troubleshooting)

## Quick Start

### 1. Real-Time Monitoring Dashboard

Monitor queue depths and container scaling in real-time:

```bash
# Basic monitoring (updates every 10 seconds)
./scripts/monitor-pipeline-performance.sh

# Custom interval
./scripts/monitor-pipeline-performance.sh --interval 5

# Export metrics to CSV for analysis
./scripts/monitor-pipeline-performance.sh --export metrics.csv --duration 30

# Monitor specific resource group
./scripts/monitor-pipeline-performance.sh --resource-group ai-content-prod-rg
```

**What you'll see:**
- Queue depths for all 4 stages (collection, processing, markdown, publishing)
- Current replica counts vs. max replicas
- Real-time bottleneck detection
- Scaling recommendations

### 2. KEDA Scaling Analysis

After collecting metrics, analyze KEDA scaling behavior:

```bash
# Analyze collected metrics
python scripts/analyze-keda-scaling.py --csv metrics.csv

# Save detailed report
python scripts/analyze-keda-scaling.py --csv metrics.csv --output report.json
```

**What you'll get:**
- Optimal `queueLength` recommendations
- `activationQueueLength` tuning suggestions
- `min_replicas` and `max_replicas` recommendations
- Terraform configuration snippets
- Scaling latency analysis

### 3. Pipeline Flow-Through Analysis

Measure end-to-end processing times:

```bash
# Analyze last 60 minutes of pipeline activity
python scripts/analyze-pipeline-flow.py --duration 60

# Custom duration
python scripts/analyze-pipeline-flow.py --duration 120
```

**What you'll get:**
- Average processing time per stage
- Bottleneck identification
- Throughput metrics (items/hour)
- P50, P95, P99 latency percentiles

## Monitoring Tools

### Tool 1: `monitor-pipeline-performance.sh`

**Purpose:** Real-time dashboard for queue depths and replica counts

**Key Features:**
- Live updates with configurable refresh interval
- Color-coded health indicators
- Automatic bottleneck detection
- CSV export for historical analysis

**Output Example:**
```
╔══════════════════════════════════════════════════════════════════════════╗
║          AI Content Farm - Pipeline Performance Monitor                  ║
╚══════════════════════════════════════════════════════════════════════════╝

  Timestamp: 2025-10-14 14:30:00
  Resource Group: ai-content-prod-rg
  Update Interval: 10s

┌─────────────────────────────────────────────────────────────────────────┐
│ Queue Depths                                                            │
├─────────────────────────────────────────────────────────────────────────┤
│   Collection Queue:            0 messages                               │
│   Processing Queue:           45 messages                               │
│   Markdown Queue:              3 messages                               │
│   Publishing Queue:            0 messages                               │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ Container Replicas                                                      │
├─────────────────────────────────────────────────────────────────────────┤
│   Collector:               0 / 1 replicas (KEDA: manual)                │
│   Processor:               3 / 6 replicas (KEDA: queueLength=8)         │
│   Markdown Generator:      1 / 1 replicas (KEDA: queueLength=1)         │
│   Site Publisher:          0 / 1 replicas (KEDA: queueLength=1)         │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ Pipeline Flow Analysis                                                  │
├─────────────────────────────────────────────────────────────────────────┤
│   ✓ Pipeline healthy - steady processing rate                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Tool 2: `analyze-keda-scaling.py`

**Purpose:** Analyze scaling patterns and generate optimization recommendations

**Key Features:**
- Statistical analysis of queue depths and replica counts
- Scale-up/down event tracking
- Scaling latency measurement
- Automatic Terraform config generation

**Analysis Metrics:**
- Average queue depth over monitoring period
- Peak queue depth
- Average replica utilization
- Scaling frequency (up/down events)
- Time to scale up from trigger

**Recommendations Include:**
- `queueLength` optimization (messages per replica)
- `activationQueueLength` tuning (0→1 transition threshold)
- `max_replicas` capacity planning
- Cooldown period adjustments
- Pre-warming strategies

### Tool 3: `analyze-pipeline-flow.py`

**Purpose:** Measure end-to-end processing times and identify bottlenecks

**Key Features:**
- Tracks individual items through all pipeline stages
- Measures stage-by-stage processing times
- Calculates throughput (items/hour)
- Identifies slowest pipeline stage

**Metrics Tracked:**
- Collection duration (Reddit API → collected-content blob)
- Processing duration (lease → research → quality check)
- Markdown generation duration (JSON → markdown)
- Publishing duration (markdown → Hugo site build)
- Total end-to-end duration

## Understanding Your Pipeline

### Pipeline Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Content   │    │   Content   │    │  Markdown   │    │    Site     │
│  Collector  │───▶│  Processor  │───▶│  Generator  │───▶│  Publisher  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │                   │
       ▼                   ▼                   ▼                   ▼
  collection-q      processing-q       markdown-q         publish-q
  (manual)          (0-6 replicas)     (0-1 replica)      (0-1 replica)
```

### Current KEDA Configuration

| Stage | Queue | Min/Max Replicas | queueLength | activationLength | Notes |
|-------|-------|------------------|-------------|------------------|-------|
| **Collector** | content-collection-requests | 0/1 | N/A | N/A | Manual trigger only |
| **Processor** | content-processing-requests | 0/6 | 8 | 1 | AI processing, can scale up |
| **Markdown** | markdown-generation-requests | 0/1 | 1 | 1 | Fast processing, single replica |
| **Publisher** | site-publishing-requests | 0/1 | 1 | 1 | Hugo builds must be sequential |

### KEDA Scaling Parameters Explained

**`min_replicas`**: Minimum number of replicas (typically 0 to save costs when idle)

**`max_replicas`**: Maximum number of replicas (capacity limit)

**`queueLength`**: Target messages per replica
- Lower = more responsive but more frequent scaling
- Higher = less scaling overhead but slower response to load
- Formula: `desired_replicas = ceil(queue_depth / queueLength)`

**`activationQueueLength`**: Minimum queue depth to activate first replica (0→1 transition)
- Lower = faster startup but may scale unnecessarily for tiny bursts
- Higher = saves costs but increases latency for small workloads

**Cooldown Period**: Time to wait before scaling down (default: 300s)
- Prevents thrashing (rapid scale up/down cycles)
- Configure via Azure CLI (not in Terraform provider yet)

## KEDA Scaling Analysis

### Typical Workflow

1. **Collect Baseline Metrics** (30-60 minutes during normal operation)
   ```bash
   ./scripts/monitor-pipeline-performance.sh --export baseline.csv --duration 60
   ```

2. **Analyze Scaling Behavior**
   ```bash
   python scripts/analyze-keda-scaling.py --csv baseline.csv --output baseline-report.json
   ```

3. **Review Recommendations**
   - Check suggested queueLength values
   - Review max_replicas capacity warnings
   - Note any scaling thrashing issues

4. **Load Test** (optional but recommended)
   ```bash
   # Trigger large collection job
   ./scripts/start-event-driven-pipeline.sh
   
   # Monitor during load test
   ./scripts/monitor-pipeline-performance.sh --export loadtest.csv --duration 30
   ```

5. **Analyze Load Test Results**
   ```bash
   python scripts/analyze-keda-scaling.py --csv loadtest.csv --output loadtest-report.json
   ```

6. **Apply Changes**
   - Update Terraform configurations with recommended values
   - Deploy via CI/CD pipeline (never manual deployment)
   - Monitor for 24-48 hours to validate

### Interpreting Analysis Results

#### Good Scaling Behavior ✅
- Queue depth stays relatively stable
- Replicas scale up/down smoothly (not frequent thrashing)
- Average replica count < 80% of max_replicas
- Scale-up latency < 60 seconds

#### Problematic Patterns ⚠️

**Pattern 1: Queue Buildup Despite Available Capacity**
```
Avg Queue Depth: 150 messages
Max Replicas: 6
Avg Replicas: 2.1
```
**Issue:** queueLength too high, not scaling aggressively enough  
**Fix:** Decrease queueLength from 8 to 4 or lower

**Pattern 2: Frequent Scaling Thrashing**
```
Scale-up Events: 45
Scale-down Events: 42
```
**Issue:** queueLength too low or cooldown too short  
**Fix:** Increase queueLength or extend cooldown period

**Pattern 3: Max Replicas Saturated**
```
Avg Replicas: 5.8 / 6
Max Queue Depth: 250
```
**Issue:** Not enough capacity for workload  
**Fix:** Increase max_replicas (but check costs and rate limits)

**Pattern 4: Slow Scale-Up**
```
Avg Scale-up Latency: 180s
```
**Issue:** Container startup time or KEDA polling interval  
**Fix:** Consider min_replicas=1 during peak hours for pre-warming

## Common Scenarios

### Scenario 1: Processing Queue Backing Up

**Symptoms:**
- Processing queue > 100 messages
- Processor replicas < max_replicas
- Items taking > 10 minutes end-to-end

**Investigation:**
```bash
# Monitor in real-time
./scripts/monitor-pipeline-performance.sh

# Check if hitting rate limits
az monitor log-analytics query \
  -w <workspace-id> \
  --analytics-query "ContainerAppConsoleLogs_CL | where ContainerAppName_s contains 'processor' | where Log_s contains 'rate limit'" \
  --timespan PT1H
```

**Likely Causes:**
1. queueLength too high (currently 8)
2. OpenAI rate limits (hitting 500k TPM)
3. Container startup time too slow

**Solutions:**
```terraform
# Option A: More aggressive scaling
custom_scale_rule {
  metadata = {
    queueLength           = "4"  # Changed from 8
    activationQueueLength = "1"
  }
}

# Option B: Higher capacity
template {
  max_replicas = 10  # Changed from 6, but check costs
}

# Option C: Pre-warming (costs more)
template {
  min_replicas = 1  # Changed from 0
  max_replicas = 6
}
```

### Scenario 2: Cost Optimization for Low-Traffic Periods

**Goal:** Reduce costs when pipeline is mostly idle

**Current Behavior:**
- All containers scale to zero when idle ✅
- But may scale up unnecessarily for small bursts

**Optimization:**
```terraform
# Increase activation threshold for processor
custom_scale_rule {
  metadata = {
    queueLength           = "8"
    activationQueueLength = "5"  # Changed from 1
  }
}
```

**Trade-off:** First 5 items in queue won't trigger scaling (adds latency)

**When to use:** During nights/weekends if you can tolerate 5-10 minute delays

### Scenario 3: Load Testing for Capacity Planning

**Goal:** Understand maximum throughput and scaling limits

**Test Plan:**
```bash
# 1. Start monitoring
./scripts/monitor-pipeline-performance.sh --export loadtest.csv --duration 60 &

# 2. Generate large workload (e.g., 500 Reddit posts)
# Use your collection trigger mechanism

# 3. Wait for completion (monitor dashboard)

# 4. Analyze results
python scripts/analyze-keda-scaling.py --csv loadtest.csv
python scripts/analyze-pipeline-flow.py --duration 60
```

**Key Metrics to Capture:**
- Peak queue depths at each stage
- Maximum concurrent replicas
- Throughput (items/hour) at various load levels
- End-to-end P95/P99 latency
- Any error rates or rate limiting

**Capacity Planning:**
```
If P99 latency > SLA target:
  → Increase max_replicas or decrease queueLength

If hitting rate limits:
  → Implement rate limiting in application
  → Consider multiple OpenAI accounts
  → Add retry with exponential backoff

If costs too high:
  → Increase queueLength (less frequent scaling)
  → Decrease max_replicas (accept higher latency)
  → Batch processing instead of individual items
```

### Scenario 4: Debugging Scaling Issues

**Problem:** KEDA not scaling despite queue having messages

**Diagnostic Steps:**

1. **Check KEDA Authentication**
   ```bash
   # Verify managed identity has Storage Queue Data Reader role
   az role assignment list \
     --assignee <container-identity-principal-id> \
     --scope /subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.Storage/storageAccounts/<storage>
   ```

2. **Check KEDA Scaler Configuration**
   ```bash
   # Get current KEDA config
   az containerapp show \
     --name ai-content-prod-processor \
     --resource-group ai-content-prod-rg \
     --query "properties.template.scale" -o json
   ```

3. **Check Container App Logs**
   ```bash
   # Look for KEDA scaler errors
   az monitor log-analytics query \
     -w <workspace-id> \
     --analytics-query "ContainerAppSystemLogs_CL | where Log_s contains 'keda' | order by TimeGenerated desc" \
     --timespan PT1H
   ```

4. **Manual Scaling Test**
   ```bash
   # Force manual scale to verify container works
   az containerapp update \
     --name ai-content-prod-processor \
     --resource-group ai-content-prod-rg \
     --min-replicas 1
   
   # Check if it processes messages
   # Then reset to 0 for auto-scaling
   ```

## Troubleshooting

### Issue: Monitor Script Shows All Zeros

**Cause:** Azure CLI not authenticated or wrong resource group

**Fix:**
```bash
# Re-authenticate
az login

# Verify resource group
az group list --query "[].name" -o table

# Run with explicit resource group
./scripts/monitor-pipeline-performance.sh --resource-group <your-rg-name>
```

### Issue: Python Analysis Scripts Fail

**Cause:** Missing dependencies

**Fix:**
```bash
# Install required packages
pip install numpy

# Or use dev container which has everything pre-installed
```

### Issue: Can't Query Log Analytics

**Cause:** Need Log Analytics Reader role

**Fix:**
```bash
# Grant yourself access
az role assignment create \
  --assignee <your-email> \
  --role "Log Analytics Reader" \
  --scope /subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.OperationalInsights/workspaces/<workspace>
```

### Issue: Scaling Recommendations Seem Wrong

**Cause:** Not enough data collected (< 30 minutes) or atypical workload

**Fix:**
1. Collect metrics during normal operation (not just idle time)
2. Run for at least 30-60 minutes
3. Include both peak and off-peak periods
4. Run multiple analyses and compare trends

## Best Practices

### Monitoring Cadence

- **Daily:** Quick health check with `monitor-pipeline-performance.sh` (5 minutes)
- **Weekly:** Full analysis with 60-minute metric collection
- **After Changes:** 24-48 hour monitoring period to validate
- **During Incidents:** Real-time monitoring with 5-second interval

### Metric Collection

- **Store CSV exports:** Keep historical data for trend analysis
- **Label clearly:** Include date, workload type, configuration in filename
- **Before/after comparisons:** Collect metrics before and after KEDA changes

### Scaling Changes

- **One change at a time:** Don't modify multiple parameters simultaneously
- **Document reasoning:** Note why you made each change
- **Gradual adjustments:** Change queueLength by 2x max, not 10x
- **CI/CD only:** Never manual infrastructure changes

### Cost vs. Performance Trade-offs

| Priority | Configuration Strategy |
|----------|------------------------|
| **Cost** | max_replicas=3, queueLength=16, activationLength=8, min_replicas=0 |
| **Balanced** | max_replicas=6, queueLength=8, activationLength=1, min_replicas=0 |
| **Performance** | max_replicas=10, queueLength=2, activationLength=1, min_replicas=1 |

## Additional Resources

- [KEDA Azure Storage Queue Scaler Docs](https://keda.sh/docs/latest/scalers/azure-storage-queue/)
- [Azure Container Apps Scaling Docs](https://learn.microsoft.com/en-us/azure/container-apps/scale-app)
- [Project Architecture Decision Records](../docs/ARCHITECTURE_DECISION_DEPENDENCY_INJECTION.md)

## Quick Reference

### Key Commands

```bash
# Real-time monitoring
./scripts/monitor-pipeline-performance.sh

# Collect 30-min baseline
./scripts/monitor-pipeline-performance.sh --export baseline.csv --duration 30

# Analyze scaling
python scripts/analyze-keda-scaling.py --csv baseline.csv

# Measure flow-through
python scripts/analyze-pipeline-flow.py --duration 60

# Check queue depths manually
az storage queue stats --name content-processing-requests --account-name <storage> --auth-mode login

# Check current replicas
az containerapp replica list --name <app-name> --resource-group <rg>
```

### Current Configuration Summary

```
Collector:    0-1 replicas, manual trigger
Processor:    0-6 replicas, queueLength=8, activation=1
Markdown:     0-1 replicas, queueLength=1, activation=1
Publisher:    0-1 replicas, queueLength=1, activation=1
```

---

**Last Updated:** October 14, 2025  
**Maintainer:** AI Content Farm Team
