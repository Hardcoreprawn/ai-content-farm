# Azure Dashboard Setup & Usage Guide

## Overview

The dashboard infrastructure provides comprehensive monitoring for both site performance and content pipeline processing through Azure Log Analytics saved queries. This guide explains how to set up, access, and use these dashboards.

## What's Included

### Performance Queries Pack
Monitors site performance metrics:
- **Performance Score Trends** - Average performance scores over time
- **Core Web Vitals Overview** - LCP, CLS, TTFB, FCP metrics summary
- **Resource Loading Performance** - Resource loading times by type
- **User Interactions Summary** - User action tracking over time
- **Performance Score Distribution** - Breakdown of excellent/good/needs-improvement scores

### Pipeline Queries Pack
Monitors content processing pipeline:
- **Container App Errors** - Exception tracking by container
- **Processing Success Rate** - Pipeline processing success over time
- **Storage Queue Depth** - Message queue depth monitoring
- **KEDA Scaling Activity** - Container replica scaling patterns

## Deployment

### Prerequisites
- Terraform backend configured (`infra/bootstrap/` completed)
- Azure CLI authenticated (`az login`)
- Application Insights resource already provisioned

### Deploy Queries

```bash
# Plan infrastructure changes
cd /workspaces/ai-content-farm/infra
terraform plan -target=azurerm_log_analytics_query_pack.performance_queries

# Apply query pack creation
terraform apply -target=azurerm_log_analytics_query_pack.performance_queries
terraform apply -target=azurerm_log_analytics_query_pack.pipeline_queries

# Apply all saved queries
terraform apply -target=azurerm_log_analytics_query_pack_query

# Get dashboard URLs
terraform output appinsights_analytics_url
terraform output appinsights_dashboards_url
```

## Accessing Dashboards

### Method 1: Azure Portal (Recommended)

1. **Navigate to Analytics**
   ```
   https://portal.azure.com → Log Analytics Workspaces → ai-content-prod-la
   ```

2. **Open Log Analytics**
   - Click on "Logs" in the left sidebar
   - This opens the Kusto Query Language (KQL) editor

3. **View Saved Queries**
   - Click "Queries" button on the left
   - Scroll to "Performance Queries" or "Pipeline Queries" sections
   - Double-click any query to run it

4. **Pin to Dashboard**
   - After running a query, click "📌 Pin to dashboard"
   - Select existing dashboard or create new one
   - Arrange tiles in desired layout

### Method 2: Using Terraform Outputs

```bash
# Get Application Insights analytics URL
cd /workspaces/ai-content-farm/infra
terraform output -raw appinsights_analytics_url
# Click the link to open in browser
```

### Method 3: Direct Search in Azure Portal

```
Search bar → "Log Analytics Workspaces" → Select "ai-content-prod-la" → Logs
```

## Available Queries

### Performance Monitoring

#### Performance Score Trends
**Purpose:** Track average site performance scores over time

**Query:**
```kusto
customEvents
| where name == 'PagePerformance'
| extend score = todouble(customDimensions.performanceScore)
| summarize AvgScore = avg(score) by bin(timestamp, 1h)
| render timechart
```

**Interpretation:**
- Scores 0-100 (higher is better)
- Scores 90+ = Excellent performance
- Scores 75-89 = Good performance
- Scores 50-74 = Needs improvement
- Scores <50 = Poor performance

**What to Look For:**
- Downward trends → Site degradation
- Sudden drops → Possible deployment issues or traffic spikes
- Consistent high scores → Good optimization

#### Core Web Vitals Overview
**Purpose:** Snapshot of critical performance metrics

**Query:**
```kusto
customMetrics
| where name in ('LargestContentfulPaint', 'CumulativeLayoutShift', 'TimeToFirstByte', 'FirstContentfulPaint')
| summarize Avg = avg(value) by name
| render table
```

**Metrics Explained:**
- **LCP (Largest Contentful Paint)** ← Target: <2.5s
  - Time until largest content element renders
  - Measures perceived load speed
  
- **CLS (Cumulative Layout Shift)** ← Target: <0.1
  - Score of unexpected layout changes
  - Lower is better (0 = no shifts)
  
- **TTFB (Time to First Byte)** ← Target: <600ms
  - Time from request to first response byte
  - Reflects server response speed
  
- **FCP (First Contentful Paint)** ← Target: <1.8s
  - Time until first content element renders
  - Marks when page starts loading

**Using These Metrics:**
- Compare against Google's Core Web Vitals thresholds
- Watch for degradation after deployments
- Identify performance bottlenecks for optimization

#### Resource Loading Performance
**Purpose:** Identify slow resource types (scripts, images, styles)

**Query:**
```kusto
customEvents
| where name startswith 'ResourceLoading'
| extend resourceType = extract('ResourceLoading_(.+)', 1, name)
| summarize Count = sum(todouble(customDimensions.count)), 
           AvgTime = avg(todouble(customDimensions.avgTime)), 
           TotalSize = sum(todouble(customDimensions.totalSize))
           by resourceType
| order by AvgTime desc
```

**Interpretation:**
- **Count:** How many resources of this type loaded
- **AvgTime:** Average load time in milliseconds
- **TotalSize:** Total bytes transferred

**What to Look For:**
- Images taking longer than scripts (CDN issue?)
- Specific resource types with high load times
- Total size trends (increasing = more content to load)

**Optimization Ideas:**
- Images: Use CDN, compression, lazy loading
- Scripts: Defer non-critical, minify, bundle
- Styles: Critical CSS inlining, async fonts

#### User Interactions Summary
**Purpose:** Track how users interact with the site

**Query:**
```kusto
customEvents
| where name startswith 'UserAction'
| summarize count() by name, bin(timestamp, 1h)
| render timechart
```

**Tracked Interactions:**
- Pagination clicks
- Article link clicks
- Scroll depth tracking
- Page view events

**What to Look For:**
- Peak interaction times → Traffic patterns
- Which actions are most common → UX preferences
- Drops in interaction → Technical issues

#### Performance Score Distribution
**Purpose:** See percentage of pages in each performance category

**Query:**
```kusto
customEvents
| where name == 'PagePerformance'
| extend score = todouble(customDimensions.performanceScore)
| extend category = case(
    score >= 90, 'Excellent',
    score >= 75, 'Good',
    score >= 50, 'Needs Improvement',
    'Poor')
| summarize count() by category
```

**Interpretation:**
- Shows proportion of pages in each performance tier
- Goal: Maximize "Excellent" percentage
- Target: 90%+ of pages in Excellent/Good categories

### Pipeline Monitoring

#### Container App Errors
**Purpose:** Track exceptions by container in pipeline

**Query:**
```kusto
exceptions
| summarize count() by cloud_RoleName, exceptionType
| order by count_ desc
```

**Containers to Monitor:**
- `content-collector` - Reddit content harvesting
- `content-processor` - Topic ranking and enrichment
- `markdown-generator` - Article generation
- `site-publisher` - Static site publishing

**What to Look For:**
- New exception types
- Exceptions from specific container
- Error rate increases
- Exception frequency patterns

#### Processing Success Rate
**Purpose:** Track percentage of successful pipeline runs

**Query:**
```kusto
customEvents
| where name contains 'process'
| extend success = name contains 'Success' or name contains 'Complete'
| summarize Total = count(), Successful = sum(success) by bin(timestamp, 1h)
| extend SuccessRate = todouble(Successful) / Total * 100
| render timechart
```

**Interpretation:**
- Shows success/failure ratio over time
- 100% = All processing completed successfully
- <100% = Some jobs failed or are still processing

**Target:** 99%+ success rate (occasional failures acceptable)

**When Success Rate Drops:**
1. Check Container App Errors query for exception types
2. Review container logs in Azure Portal
3. Check storage queue status
4. Review input data for quality issues

#### Storage Queue Depth
**Purpose:** Monitor how many items are waiting to be processed

**Query:**
```kusto
AzureMetrics
| where ResourceProvider == 'MICROSOFT.STORAGE'
| where MetricName == 'ApproximateMessageCount'
| summarize AvgDepth = avg(Total), MaxDepth = max(Total) by bin(TimeGenerated, 15m), Resource
| render timechart
```

**Interpretation:**
- **Rising queue depth** = Items arriving faster than processing
- **Stable depth** = Balanced input/processing speed
- **Depth = 0** = No pending items

**What to Look For:**
- Queue growing → Scaling issue or processing bottleneck
- Queue stable → System in equilibrium
- KEDA should increase replicas when depth rises

#### KEDA Scaling Activity
**Purpose:** Monitor how container app scales based on queue depth

**Query:**
```kusto
AzureMetrics
| where ResourceProvider == 'MICROSOFT.APP'
| where MetricName == 'ReplcaCount'
| summarize AvgReplicas = avg(Total) by bin(TimeGenerated, 1h), Resource
| render timechart
```

**Interpretation:**
- Shows number of running container instances over time
- Should scale UP when queue depth increases
- Should scale DOWN when queue empties

**What to Look For:**
- Scaling delays (queue depth up but replicas not)
- Overshooting (too many replicas for queue depth)
- Aggressive scaling (frequent up/down changes)

**KEDA Configuration:**
- Located in `infra/applications.tf`
- Look for `azure_queue_length` scaler rules
- Target queue depth threshold (typically 30)
- Min/max replicas (typically 1-10)

## Creating Custom Dashboards

### Step 1: Run a Query

1. Go to Log Analytics Workspace → Logs
2. Paste a query (see above)
3. Click "Run"
4. Visualize results (table, chart, etc.)

### Step 2: Pin to Dashboard

1. Click "📌 Pin to dashboard" button
2. Select dashboard:
   - "Create new" for new dashboard
   - Existing dashboard to add tile
3. Name the tile (appears as label)
4. Click "Pin"

### Step 3: Arrange Dashboard

1. Go to Dashboard home
2. Click "Edit"
3. Resize/move tiles
4. Click "Done editing"

### Example: Create "Site Health" Dashboard

```bash
# Go to Log Analytics Workspace
# Run each query and pin to new "Site Health" dashboard:

# Tile 1: Performance Score (current hour)
customEvents
| where name == 'PagePerformance'
| summarize Avg = avg(todouble(customDimensions.performanceScore))
| render indicator
# Pin as "Current Performance Score"

# Tile 2: Web Vitals (current hour)
customMetrics
| where name == 'LargestContentfulPaint'
| summarize Avg = avg(value)
| render indicator
# Pin as "LCP (ms)"

# Tile 3: Success Rate (current hour)
customEvents
| where name contains 'process'
| extend success = name contains 'Success'
| summarize SuccessRate = sum(success) / count() * 100
| render indicator
# Pin as "Processing Success Rate %"
```

## Monitoring Best Practices

### Daily Review Checklist
- [ ] Check performance score trends (any significant drops?)
- [ ] Review Core Web Vitals (all within thresholds?)
- [ ] Check container errors (any new exception types?)
- [ ] Verify queue depth (stable or growing?)
- [ ] Check KEDA scaling (responding to load?)

### Alert Setup (Future Enhancement)
While not yet configured, you can manually create alerts:

1. In Log Analytics, run a query
2. Click "New alert rule"
3. Set condition (e.g., AvgScore < 75)
4. Set action group (email, webhook, etc.)
5. Save alert

### Performance Optimization Workflow

**When Performance Score Drops:**
1. Run "Performance Score Trends" query
2. Check "Resource Loading Performance" for bottlenecks
3. Review "User Interactions" for traffic surge
4. Check "Core Web Vitals" for specific metric degradation

**When Processing Slows Down:**
1. Check "Storage Queue Depth" (items piling up?)
2. Check "KEDA Scaling Activity" (replicas insufficient?)
3. Check "Container App Errors" (exceptions occurring?)
4. Review container logs for specific errors

## Command Reference

### Query Execution
```bash
# Run query from Azure CLI (KQL query saved to file)
az monitor log-analytics query \
  --workspace {workspace_id} \
  --analytics-query "customEvents | where name == 'PagePerformance' | count"
```

### Get Resource IDs
```bash
# Get Log Analytics Workspace ID
az monitor log-analytics workspace show \
  --resource-group ai-content-prod-rg \
  --workspace-name ai-content-prod-la \
  --query id -o tsv

# Get Application Insights ID
az monitor app-insights component show \
  --resource-group ai-content-prod-rg \
  --app ai-content-prod-ai \
  --query id -o tsv
```

## Troubleshooting

### Queries Show No Data

**Cause:** Application Insights not receiving telemetry

**Solution:**
1. Verify `APPINSIGHTS_INSTRUMENTATION_KEY` is set on all containers
2. Check if site has page views: 
   ```kusto
   pageViews | count
   ```
3. Check Application Insights status in Azure Portal
4. Verify containers are running:
   ```bash
   az containerapp list -o table
   ```

### Dashboard Not Loading

**Cause:** Azure Portal authentication issue

**Solution:**
1. Sign out of Azure Portal (`Ctrl+Shift+Del`)
2. Clear browser cache
3. Log back in
4. Try accessing dashboard URL again

### Query Syntax Error

**Cause:** KQL syntax issues

**Solution:**
1. Check KQL syntax at [learn.microsoft.com/en-us/azure/data-explorer/kusto/query/](https://learn.microsoft.com/en-us/azure/data-explorer/kusto/query/)
2. Validate column names exist in your data
3. Use "Schema" panel on left to explore available fields

## Next Steps

1. **Deploy Dashboards:** Run `terraform apply` to create query packs
2. **Review Queries:** Open each query in Log Analytics and understand the data
3. **Create Dashboard:** Pin 3-4 key queries to a new dashboard
4. **Set Up Alerts:** Create alerts for critical thresholds (optional)
5. **Daily Monitoring:** Add dashboard review to operational checklist

## Additional Resources

- [Azure Log Analytics Documentation](https://learn.microsoft.com/en-us/azure/azure-monitor/logs/log-analytics-overview)
- [Kusto Query Language Reference](https://learn.microsoft.com/en-us/azure/data-explorer/kusto/query/)
- [Application Insights Overview](https://learn.microsoft.com/en-us/azure/azure-monitor/app/app-insights-overview)
- [Creating Azure Dashboards](https://learn.microsoft.com/en-us/azure/azure-portal/azure-portal-dashboards)
