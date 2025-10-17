# Performance Monitoring & Azure Application Insights Integration

**Document Status**: Complete Implementation Guide  
**Date**: October 17, 2025  
**Components**: Client-side telemetry, Application Insights integration, Hugo configuration

## Overview

The site-publisher now integrates comprehensive performance monitoring with Azure Application Insights, providing complete visibility into:

- **Core Web Vitals**: LCP, FCP, CLS, TTFB, FID
- **Page Load Performance**: Navigation timing, resource loading
- **Design Structure**: Layout complexity, element counts, typography
- **User Interactions**: Pagination clicks, article views, scroll depth
- **Resource Analysis**: By type, size, and load time

## Architecture

### Client-Side Components

```
Performance Monitor (JavaScript)
├── Web Vitals Collection (PerformanceObserver)
├── Navigation Timing (Performance API)
├── Resource Analysis (getEntriesByType)
├── Design Structure Analysis (DOM inspection)
└── Application Insights Integration (SDK)
    ├── Custom Events
    ├── Metrics
    ├── Traces
    └── Exception Tracking
```

### Backend Integration

```
Hugo Build Process
├── Configure Telemetry (configure_telemetry.py)
│   ├── Read Azure credentials from env vars
│   └── Inject into config.toml
├── Build Site (Hugo)
│   ├── Inject JavaScript libraries
│   ├── Inject telemetry partial
│   └── Include performance-monitor.js
└── Deploy (Azure Static Web Apps)
    └── Serve with telemetry enabled
```

## Features

### 1. Core Web Vitals Tracking

**Largest Contentful Paint (LCP)**
- Tracks when main content becomes visible
- Target: < 2.5 seconds
- Automatically measured and sent to Application Insights

**First Contentful Paint (FCP)**
- Tracks when any content first appears
- Target: < 1.8 seconds
- Used for performance scoring

**Cumulative Layout Shift (CLS)**
- Measures visual instability
- Target: < 0.1
- Helps identify layout rendering issues

**Time to First Byte (TTFB)**
- Tracks server response time
- Target: < 600 ms
- Indicates backend performance

**First Input Delay (FID)**
- Measures responsiveness to user input
- Target: < 100 ms
- Tracks interaction readiness

### 2. Page Performance Metrics

**Navigation Timing**
- DNS lookup time
- TCP connection time
- Server response time
- Content download time
- DOM parsing time
- DOM ready time
- Complete page load time

**Resource Analysis**
- Grouped by type (script, stylesheet, image, font, etc.)
- Metrics per type:
  - Count of resources
  - Total size in bytes
  - Total load time
  - Average load time
  - Cached resources

**Slowest Resources**
- Top 10 slowest-loading resources
- Helps identify performance bottlenecks

### 3. Design Structure Analysis

**Layout Metrics**
- Total element count
- Heading hierarchy (H1-H6)
- Image count
- Link count
- Form count
- Button count
- Table count

**Layout Complexity**
- Grid elements count
- Flex elements count
- Absolute positioning count
- Fixed positioning count
- Z-index layering analysis

**Content Analysis**
- Total text length
- Word count
- Paragraph count
- Viewport dimensions
- Device pixel ratio
- Aspect ratio

**Color Palette Extraction**
- Top 10 most-used colors
- Both background and foreground colors
- Helps analyze design consistency

### 4. User Interaction Tracking

**Pagination Navigation**
- Tracked on click
- Properties: URL, text content
- Helps understand content discovery patterns

**Article Clicks**
- Tracked when users click article links
- Properties: URL, article title
- Measures content engagement

**Scroll Depth**
- Tracked at 25%, 50%, 75%, 100%
- Helps understand user engagement depth
- Identifies content sections of interest

### 5. Performance Scoring

**Algorithm**
```
Base Score: 100
- Reduce by (LCP / 2500) * 50 points (max 50)
- Reduce by (CLS / 0.1) * 20 points (max 20)
- Reduce by (TTFB / 600) * 20 points (max 20)
- Reduce by (FCP / 1800) * 10 points (max 10)

Result: 0-100 score
```

**Score Interpretation**
- 90-100: Excellent
- 75-89: Good
- 50-74: Needs improvement
- 0-49: Poor

## Usage

### Accessing Metrics in Browser Console

```javascript
// Get complete performance report
siteMetrics.all()

// Get Core Web Vitals
siteMetrics.vitals()

// Get navigation timing
siteMetrics.navigation()

// Get resource summary by type
siteMetrics.resources()

// Get slowest resources
siteMetrics.slowest()

// Get design structure analysis
siteMetrics.design()

// Get performance score (0-100)
siteMetrics.performance()

// Get full report object
siteMetrics.report()
```

### Tracking Custom User Actions

```javascript
// Track a custom action
window.trackAction('MyAction', {
    property1: 'value1',
    property2: 'value2'
}, {
    metric1: 100,
    metric2: 250
})

// Track an error
window.trackError(error, 'error')  // or 'warning', 'info'
```

### Application Insights Portal

**View Metrics**:
1. Navigate to Azure Portal
2. Open Application Insights resource
3. View under:
   - **Performance** → Custom events
   - **Logs** → customEvents, customMetrics, traces
   - **Live Metrics** → Real-time events

**Query Examples** (KQL):
```kusto
// Get page performance events
customEvents
| where name == "PagePerformance"
| project timestamp, url=tostring(customDimensions.url), 
          score=toint(customDimensions.performanceScore)
| order by timestamp desc

// Get Web Vitals over time
customMetrics
| where name in ("LargestContentfulPaint", "CumulativeLayoutShift")
| summarize avg(value) by name, bin(timestamp, 1h)

// Get user actions
customEvents
| where name startswith "UserAction"
| summarize count() by name
```

## Configuration

### Environment Variables

**Required** (for Application Insights integration):
```bash
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=...;IngestionEndpoint=...
APPINSIGHTS_INSTRUMENTATION_KEY=xxx-xxx-xxx-xxx
```

**Optional**:
```bash
DISABLE_APPLICATION_INSIGHTS=true  # Disable monitoring (default: false)
```

### Hugo Configuration

**File**: `hugo-config/config.toml`

```toml
[params]
  # Enable/disable analytics
  analyticsEnabled = true

  [params.appInsights]
    instrumentationKey = ""  # Populated from env var
    connectionString = ""    # Populated from env var
```

### Deployment Configuration

**Dockerfile**:
- Copies `performance-monitor.js` to static files
- Copies telemetry partials to layouts

**Site Builder** (`site_builder.py`):
- Calls `configure_telemetry.py` before Hugo build
- Injects credentials into config.toml
- Hugo renders with telemetry enabled

## Performance Impact

### JavaScript Bundle Size
- `performance-monitor.js`: ~12 KB
- Application Insights SDK (CDN): ~170 KB (cached)
- **Total additional**: ~12 KB to initial load + lazy-loaded SDK

### Monitoring Overhead
- Collection: ~2-5 ms (non-blocking)
- Telemetry send: ~50-100 ms (async, after page load)
- Impact on Core Web Vitals: Negligible (<1%)

### Network Impact
- Telemetry payload: ~2-5 KB per pageview
- Sent asynchronously after page load
- Doesn't affect perceived performance

## Security & Privacy

### Data Collection
- No personally identifiable information (PII)
- No sensitive headers or credentials
- User agent and URL only

### GDPR Compliance
- All data collection is optional (can be disabled)
- Users can opt-out via `analyticsEnabled = false`
- Analytics can be disabled server-side

### Network Security
- HTTPS only (Application Insights enforces)
- No credentials transmitted
- Same-origin policy enforcement

## Troubleshooting

### Telemetry Not Appearing in Application Insights

**Check**:
1. Connection string configured: `echo $APPLICATIONINSIGHTS_CONNECTION_STRING`
2. Hugo config updated: Check `hugo-config/config.toml`
3. JavaScript errors: Check browser console
4. Network tab: Verify telemetry requests sent to Application Insights

**Solutions**:
- Verify credentials are correct
- Check Application Insights resource exists in Azure Portal
- Verify CDN availability (performance-monitor.js loads)
- Clear browser cache and reload

### High Performance Score but Slow Page

**Investigate**:
1. Check `siteMetrics.slowest()` for resource bottlenecks
2. Review `siteMetrics.resources()` for type distribution
3. Check server response time: `siteMetrics.navigation().ttfb`
4. Verify cached resources vs fresh resources

### Missing Metrics

**Check**:
- Browser supports Performance API (all modern browsers)
- JavaScript console for errors: `window.siteMetrics` should be available
- Application Insights SDK loaded successfully
- Network requests to Application Insights endpoint

## Examples

### Analyzing Performance Issues

```javascript
// Check where time is spent
const perf = siteMetrics.navigation();
console.log('DNS Lookup:', perf.dns + 'ms');
console.log('TCP Connection:', perf.tcp + 'ms');
console.log('Server Response:', perf.ttfb + 'ms');
console.log('Content Download:', perf.download + 'ms');
console.log('DOM Parsing:', perf.domParsing + 'ms');

// Identify slowest resources
const slowest = siteMetrics.slowest();
slowest.forEach(r => {
    console.log(`${r.type}: ${r.name} (${r.duration.toFixed(2)}ms)`);
});
```

### Understanding Design Complexity

```javascript
// Analyze layout
const design = siteMetrics.design();
console.log('Total Elements:', design.totalElements);
console.log('Layout Complexity:', design.layoutComplexity);
console.log('Text Content:', design.textContent.wordCount, 'words');
console.log('Media:', design.images, 'images,', design.links, 'links');
```

### Tracking Feature Usage

```javascript
// Track when user interacts with pagination
document.addEventListener('click', (e) => {
    if (e.target.closest('.pagination-item a')) {
        window.trackAction('PaginationClick', {
            page: e.target.textContent
        });
    }
});

// Track article reading
document.addEventListener('scroll', () => {
    if (window.scrollY > document.body.scrollHeight * 0.5) {
        window.trackAction('ReadArticleHalfway');
    }
});
```

## Next Steps

### Phase 1: Monitor & Baseline (Current)
- ✅ Collect performance metrics
- ✅ Send to Application Insights
- ✅ Manual analysis via console

### Phase 2: Dashboards (Recommended)
- Create Application Insights workbooks
- Real-time performance dashboard
- Historical trend analysis

### Phase 3: Alerting (Future)
- Alert on performance degradation
- Alert on high error rates
- Alert on resource bottlenecks

### Phase 4: Optimization (Future)
- Automated performance recommendations
- Resource optimization suggestions
- Layout complexity analysis

## References

- [Web Vitals](https://web.dev/vitals/)
- [Performance API](https://developer.mozilla.org/en-US/docs/Web/API/Performance)
- [Application Insights Documentation](https://docs.microsoft.com/azure/azure-monitor/app/app-insights-overview)
- [OpenTelemetry](https://opentelemetry.io/)
