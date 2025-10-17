# Quick Reference: Performance Monitoring

## Browser Console (No Setup Required)

### View All Metrics
```javascript
siteMetrics.all()
```

### Get Performance Score (0-100)
```javascript
siteMetrics.performance()
// Returns score with interpretation:
// 90-100: Excellent
// 75-89: Good  
// 50-74: Needs improvement
// 0-49: Poor
```

### Core Web Vitals
```javascript
siteMetrics.vitals()
// Returns:
// {
//   lcp: 1500,     // Largest Contentful Paint (ms)
//   fcp: 800,      // First Contentful Paint (ms)
//   cls: 0.05,     // Cumulative Layout Shift
//   ttfb: 200,     // Time to First Byte (ms)
//   fid: 50        // First Input Delay (ms)
// }
```

### Page Load Performance
```javascript
siteMetrics.navigation()
// Returns:
// {
//   dns: 50,        // DNS lookup time
//   tcp: 100,       // TCP connection time
//   ttfb: 200,      // Time to first byte
//   download: 300,  // Content download
//   domParsing: 150,// DOM parsing
//   domReady: 800,  // DOM complete
//   pageLoad: 2000  // Full page load
// }
```

### Resource Loading Summary
```javascript
siteMetrics.resources()
// Returns summary grouped by resource type:
// {
//   "script": {count: 5, totalSize: 250000, totalTime: 1500, avgTime: 300},
//   "stylesheet": {count: 2, totalSize: 50000, totalTime: 800, avgTime: 400},
//   ...
// }
```

### Slowest Resources
```javascript
siteMetrics.slowest()
// Returns top 10 slowest resources:
// [
//   {name: "...", type: "script", size: 150000, duration: 850, cached: false},
//   ...
// ]
```

### Design Structure Analysis
```javascript
siteMetrics.design()
// Returns complete site structure analysis:
// {
//   totalElements: 2500,
//   headings: {h1: 1, h2: 12, h3: 45, ...},
//   images: 25,
//   links: 150,
//   textContent: {totalLength: 50000, wordCount: 8000, paragraphs: 100},
//   layoutComplexity: {gridElements: 5, flexElements: 20, ...},
//   colors: [...]
// }
```

### Full Report
```javascript
siteMetrics.report()
// Returns complete report with all metrics combined
```

## Azure Application Insights Portal

### View Performance Events
1. Open Azure Portal
2. Navigate to your Application Insights resource
3. Go to **Logs** tab
4. Run query:
```kusto
customEvents
| where name == "PagePerformance"
| project timestamp, url=customDimensions.url, score=customDimensions.performanceScore
| order by timestamp desc
```

### View Core Web Vitals Trends
```kusto
customMetrics
| where name in ("LargestContentfulPaint", "CumulativeLayoutShift", "TimeToFirstByte")
| summarize avg(value) by name, bin(timestamp, 1h)
| render timechart
```

### View User Interactions
```kusto
customEvents
| where name startswith "UserAction"
| summarize count() by name
```

### View Resource Performance
```kusto
customEvents
| where name startswith "ResourceLoading"
| project timestamp, resourceType=name, data=customDimensions
```

## Tracking Custom Actions

### Track Page View
```javascript
// Automatically tracked - no action needed
```

### Track User Action
```javascript
window.trackAction('MyAction', {
    property1: 'value',
    property2: 'another value'
}, {
    metric1: 100,
    metric2: 250
});

// Example: Track custom feature use
window.trackAction('ToggleDarkMode', {
    enabled: true
}, {
    timingMs: 45
});
```

### Track Errors
```javascript
try {
    riskyOperation();
} catch (error) {
    window.trackError(error, 'error');  // 'error', 'warning', or 'info'
}
```

## Environment Configuration

### Enable Monitoring
```bash
export APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=xxx;IngestionEndpoint=https://xxx.in.applicationinsights.azure.com/"
export APPINSIGHTS_INSTRUMENTATION_KEY="xxx-xxx-xxx-xxx"
```

### Disable Monitoring (for local dev)
```bash
export DISABLE_APPLICATION_INSIGHTS=true
```

## Common Troubleshooting

### Metrics Not Appearing
```javascript
// Check if monitoring is available
typeof window.siteMetrics  // Should be 'object'

// Check for errors
window.siteMetrics.all()   // Check for errors in response

// Check Application Insights
typeof window.appInsights  // Should be 'object'
```

### AppInsights SDK Not Loading
- Check browser console for network errors
- Verify CDN is accessible
- Verify credentials are correct
- Check Application Insights resource exists

### Performance Score is 0
- Indicates Web Vitals not yet collected
- Wait for page to fully load
- Core Web Vitals require user interaction or specific page state
- Run after 3-5 seconds

## Performance Interpretation

### LCP (Largest Contentful Paint)
- **Good**: < 2.5 seconds
- **Needs Work**: 2.5 - 4 seconds
- **Poor**: > 4 seconds

### FCP (First Contentful Paint)
- **Good**: < 1.8 seconds
- **Needs Work**: 1.8 - 3 seconds
- **Poor**: > 3 seconds

### CLS (Cumulative Layout Shift)
- **Good**: < 0.1
- **Needs Work**: 0.1 - 0.25
- **Poor**: > 0.25

### TTFB (Time to First Byte)
- **Good**: < 600 ms
- **Needs Work**: 600 - 1800 ms
- **Poor**: > 1800 ms

## Sample Dashboard Queries

### Pages with Poor Performance
```kusto
customEvents
| where name == "PagePerformance"
| where todouble(customDimensions.performanceScore) < 50
| project timestamp, url, score=customDimensions.performanceScore
| order by timestamp desc
```

### Resource Type Distribution
```kusto
customEvents
| where name startswith "ResourceLoading"
| extend resourceType = extract("ResourceLoading_(.+)", 1, name)
| summarize TotalCount=sum(todouble(customDimensions.count)),
            AvgTime=avg(todouble(customDimensions.avgTime))
            by resourceType
```

### User Scroll Engagement
```kusto
customEvents
| where name == "UserAction_ScrollDepth"
| summarize count() by tostring(customDimensions.percentage)
| order by customDimensions_percentage asc
```

## Export Data

### Export to CSV
```kusto
customEvents
| where name == "PagePerformance"
| project timestamp, url, score
| order by timestamp desc
// Click "Export" button to save as CSV
```

### Create Alert
1. Query your metrics
2. Click "New alert rule"
3. Set threshold (e.g., score < 50)
4. Configure notification (email, webhook, etc.)

---

**For detailed documentation, see `/docs/PERFORMANCE_MONITORING_GUIDE.md`**
