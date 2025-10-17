/**
 * Site Performance Monitoring & Design Visibility with Azure Application Insights
 *
 * Provides real-time visibility into:
 * - Page load performance (Core Web Vitals)
 * - Resource loading times
 * - Design structure and layout metrics
 * - Memory and performance usage
 * - Custom business metrics
 * - Integrated telemetry to Azure Application Insights
 */

class PerformanceMonitor {
    constructor(appInsightsConfig = null) {
        this.metrics = {};
        this.resourceTimings = [];
        this.navigationTiming = null;
        this.appInsights = null;
        this.appInsightsConfig = appInsightsConfig;
        this.vitals = {
            lcp: null,  // Largest Contentful Paint
            fid: null,  // First Input Delay
            cls: null,  // Cumulative Layout Shift
            fcp: null,  // First Contentful Paint
            ttfb: null, // Time to First Byte
        };
        this.init();
    }

    init() {
        if (!window.performance) {
            console.warn('Performance API not available');
            return;
        }

        // Initialize Application Insights if config provided
        this.initializeAppInsights();

        // Collect navigation timing
        window.addEventListener('load', () => this.collectNavigationTiming());

        // Collect Core Web Vitals
        this.collectWebVitals();

        // Collect resource timings
        this.collectResourceTimings();

        // Monitor design structure
        this.monitorDesignStructure();

        // Setup console API
        this.setupConsoleAPI();

        // Send telemetry on page unload
        window.addEventListener('beforeunload', () => this.sendTelemetry());
    }

    initializeAppInsights() {
        // Check for Application Insights config from meta tags or global config
        const configElement = document.querySelector('meta[name="appinsights-config"]');
        const config = configElement ? JSON.parse(configElement.content) : this.appInsightsConfig;

        if (!config || !config.instrumentationKey) {
            console.debug('Application Insights not configured');
            return;
        }

        try {
            // Load Application Insights SDK
            const sdkLink = 'https://cdn.jsdelivr.net/npm/@microsoft/applicationinsights-web@3.0.0/dist/applicationinsights-web.min.js';
            const script = document.createElement('script');
            script.src = sdkLink;
            script.async = true;
            script.onload = () => {
                if (window.appInsights) {
                    const appInsights = new window.appInsights.ApplicationInsights({
                        config: {
                            instrumentationKey: config.instrumentationKey,
                            connectionString: config.connectionString,
                            enableAutoRouteTracking: true,
                            enableRequestHeaderTracking: true,
                            enableResponseHeaderTracking: true,
                            enableAjaxErrorStatusText: true,
                            enableAjaxPerfTracking: true,
                            maxAjaxCallsPerView: 500,
                            enableDebug: false,
                            samplingPercentage: 100,
                        }
                    });

                    appInsights.loadAppInsights();
                    this.appInsights = appInsights;
                    console.log('Application Insights initialized');

                    // Track page view
                    appInsights.trackPageView();
                }
            };
            document.head.appendChild(script);
        } catch (e) {
            console.debug('Failed to load Application Insights:', e);
        }
    }

    collectNavigationTiming() {
        const perfData = window.performance.timing;
        this.navigationTiming = {
            dns: perfData.domainLookupEnd - perfData.domainLookupStart,
            tcp: perfData.connectEnd - perfData.connectStart,
            ttfb: perfData.responseStart - perfData.fetchStart,
            download: perfData.responseEnd - perfData.responseStart,
            domParsing: perfData.domInteractive - perfData.domLoading,
            domReady: perfData.domContentLoadedEventEnd - perfData.fetchStart,
            pageLoad: perfData.loadEventEnd - perfData.fetchStart,
        };

        this.metrics.navigationTiming = this.navigationTiming;
    }

    collectWebVitals() {
        // Largest Contentful Paint
        if ('PerformanceObserver' in window) {
            try {
                const lcpObserver = new PerformanceObserver((list) => {
                    const entries = list.getEntries();
                    const lastEntry = entries[entries.length - 1];
                    this.vitals.lcp = lastEntry.renderTime || lastEntry.loadTime;
                });
                lcpObserver.observe({ type: 'largest-contentful-paint', buffered: true });
            } catch (e) {
                console.debug('LCP observer not supported');
            }

            // Cumulative Layout Shift
            try {
                const clsObserver = new PerformanceObserver((list) => {
                    let cls = 0;
                    for (const entry of list.getEntries()) {
                        if (!entry.hadRecentInput) {
                            cls += entry.value;
                        }
                    }
                    this.vitals.cls = cls;
                });
                clsObserver.observe({ type: 'layout-shift', buffered: true });
            } catch (e) {
                console.debug('CLS observer not supported');
            }

            // First Input Delay / Interaction to Next Paint
            try {
                const fidObserver = new PerformanceObserver((list) => {
                    const entries = list.getEntries();
                    if (entries.length > 0) {
                        this.vitals.fid = entries[0].processingDuration;
                    }
                });
                fidObserver.observe({ type: 'first-input', buffered: true });
            } catch (e) {
                console.debug('FID observer not supported');
            }

            // First Contentful Paint
            try {
                const fcpObserver = new PerformanceObserver((list) => {
                    const entries = list.getEntries();
                    for (const entry of entries) {
                        if (entry.name === 'first-contentful-paint') {
                            this.vitals.fcp = entry.startTime;
                        }
                    }
                });
                fcpObserver.observe({ type: 'paint', buffered: true });
            } catch (e) {
                console.debug('FCP observer not supported');
            }
        }

        // Time to First Byte
        if (window.performance.timing) {
            this.vitals.ttfb = window.performance.timing.responseStart - window.performance.timing.fetchStart;
        }

        this.metrics.webVitals = this.vitals;
    }

    collectResourceTimings() {
        if (!window.performance.getEntriesByType) return;

        const resources = window.performance.getEntriesByType('resource');
        this.resourceTimings = resources.map(r => ({
            name: r.name,
            type: r.initiatorType,
            size: r.transferSize || 0,
            duration: r.duration,
            cached: r.transferSize === 0 && r.decodedBodySize > 0,
        }));

        // Categorize by type
        const byType = {};
        this.resourceTimings.forEach(r => {
            if (!byType[r.type]) byType[r.type] = [];
            byType[r.type].push(r);
        });

        this.metrics.resourcesByType = Object.entries(byType).reduce((acc, [type, resources]) => {
            acc[type] = {
                count: resources.length,
                totalSize: resources.reduce((sum, r) => sum + r.size, 0),
                totalTime: resources.reduce((sum, r) => sum + r.duration, 0),
                avgTime: resources.reduce((sum, r) => sum + r.duration, 0) / resources.length,
            };
            return acc;
        }, {});

        this.metrics.slowestResources = this.resourceTimings
            .sort((a, b) => b.duration - a.duration)
            .slice(0, 10);
    }

    monitorDesignStructure() {
        const structure = {
            totalElements: document.querySelectorAll('*').length,
            headings: {
                h1: document.querySelectorAll('h1').length,
                h2: document.querySelectorAll('h2').length,
                h3: document.querySelectorAll('h3').length,
                h4: document.querySelectorAll('h4').length,
                h5: document.querySelectorAll('h5').length,
                h6: document.querySelectorAll('h6').length,
            },
            images: document.querySelectorAll('img').length,
            links: document.querySelectorAll('a').length,
            forms: document.querySelectorAll('form').length,
            buttons: document.querySelectorAll('button').length,
            tables: document.querySelectorAll('table').length,
            textContent: {
                totalLength: document.body.innerText.length,
                wordCount: document.body.innerText.split(/\s+/).length,
                paragraphs: document.querySelectorAll('p').length,
            },
            layout: {
                width: window.innerWidth,
                height: window.innerHeight,
                aspectRatio: (window.innerWidth / window.innerHeight).toFixed(2),
                devicePixelRatio: window.devicePixelRatio,
            },
            colors: this.extractColorPalette(),
        };

        // Analyze layout complexity
        structure.layoutComplexity = this.analyzeLayoutComplexity();

        this.metrics.designStructure = structure;
    }

    analyzeLayoutComplexity() {
        const elements = document.querySelectorAll('*');
        const layout = {
            gridElements: document.querySelectorAll('[style*="grid"], .grid').length,
            flexElements: document.querySelectorAll('[style*="flex"], .flex').length,
            absoluteElements: 0,
            fixedElements: 0,
            layeredElements: 0,
        };

        elements.forEach(el => {
            const computed = window.getComputedStyle(el);
            if (computed.position === 'absolute') layout.absoluteElements++;
            if (computed.position === 'fixed') layout.fixedElements++;
            if (computed.zIndex && computed.zIndex !== 'auto') layout.layeredElements++;
        });

        return layout;
    }

    extractColorPalette() {
        const colors = new Map();
        const elements = document.querySelectorAll('*');

        elements.forEach(el => {
            const computed = window.getComputedStyle(el);
            const bg = computed.backgroundColor;
            const fg = computed.color;

            if (bg && bg !== 'rgba(0, 0, 0, 0)') {
                colors.set(`bg:${bg}`, (colors.get(`bg:${bg}`) || 0) + 1);
            }
            if (fg) {
                colors.set(`fg:${fg}`, (colors.get(`fg:${fg}`) || 0) + 1);
            }
        });

        // Return top 10 colors
        return Array.from(colors.entries())
            .sort((a, b) => b[1] - a[1])
            .slice(0, 10)
            .map(([color, count]) => ({ color, count }));
    }

    setupConsoleAPI() {
        window.siteMetrics = {
            all: () => this.getAllMetrics(),
            vitals: () => this.vitals,
            navigation: () => this.navigationTiming,
            resources: () => this.metrics.resourcesByType,
            slowest: () => this.metrics.slowestResources,
            design: () => this.metrics.designStructure,
            performance: () => this.getPerformanceScore(),
            report: () => this.generateReport(),
        };

        console.log('%c📊 Site Metrics Available', 'color: #4f46e5; font-size: 14px; font-weight: bold;');
        console.log('Use window.siteMetrics to access performance data:');
        console.log('  • siteMetrics.all()      - Complete metrics');
        console.log('  • siteMetrics.vitals()   - Core Web Vitals');
        console.log('  • siteMetrics.navigation() - Navigation timing');
        console.log('  • siteMetrics.resources() - Resource summary');
        console.log('  • siteMetrics.slowest()  - Slowest resources');
        console.log('  • siteMetrics.design()   - Design structure');
        console.log('  • siteMetrics.performance() - Performance score');
        console.log('  • siteMetrics.report()   - Full report');
    }

    getAllMetrics() {
        return this.metrics;
    }

    getPerformanceScore() {
        // Simple performance scoring (0-100)
        let score = 100;

        // LCP (target: < 2.5s)
        if (this.vitals.lcp) {
            score -= Math.min(50, (this.vitals.lcp / 2500) * 50);
        }

        // CLS (target: < 0.1)
        if (this.vitals.cls) {
            score -= Math.min(20, (this.vitals.cls / 0.1) * 20);
        }

        // TTFB (target: < 600ms)
        if (this.vitals.ttfb) {
            score -= Math.min(20, (this.vitals.ttfb / 600) * 20);
        }

        // FCP (target: < 1.8s)
        if (this.vitals.fcp) {
            score -= Math.min(10, (this.vitals.fcp / 1800) * 10);
        }

        return Math.max(0, Math.round(score));
    }

    generateReport() {
        const report = {
            timestamp: new Date().toISOString(),
            url: window.location.href,
            performanceScore: this.getPerformanceScore(),
            webVitals: this.vitals,
            navigationTiming: this.navigationTiming,
            resourceSummary: this.metrics.resourcesByType,
            designMetrics: this.metrics.designStructure,
            userAgent: navigator.userAgent,
        };

        return report;
    }

    sendTelemetry() {
        if (!this.appInsights) {
            console.debug('Application Insights not available - skipping telemetry');
            return;
        }

        try {
            const report = this.generateReport();

            // Send custom event with performance metrics
            this.appInsights.trackEvent({
                name: 'PagePerformance',
                properties: {
                    url: report.url,
                    performanceScore: report.performanceScore,
                    pageLoadTime: report.navigationTiming?.pageLoad || 0,
                    resourceCount: this.resourceTimings.length,
                    designComplexity: report.designMetrics?.layoutComplexity || {},
                },
                measurements: {
                    lcp: report.webVitals.lcp || 0,
                    fcp: report.webVitals.fcp || 0,
                    cls: report.webVitals.cls || 0,
                    ttfb: report.webVitals.ttfb || 0,
                    fid: report.webVitals.fid || 0,
                    pageLoadTime: report.navigationTiming?.pageLoad || 0,
                    resourceLoadTime: (report.navigationTiming?.download || 0),
                    domParsing: report.navigationTiming?.domParsing || 0,
                    elementsCount: report.designMetrics?.totalElements || 0,
                    imagesCount: report.designMetrics?.images || 0,
                    linksCount: report.designMetrics?.links || 0,
                }
            });

            // Send individual Web Vitals as custom metrics
            if (report.webVitals.lcp) {
                this.appInsights.trackMetric({
                    name: 'LargestContentfulPaint',
                    average: report.webVitals.lcp
                });
            }

            if (report.webVitals.cls !== null) {
                this.appInsights.trackMetric({
                    name: 'CumulativeLayoutShift',
                    average: report.webVitals.cls
                });
            }

            if (report.webVitals.fcp) {
                this.appInsights.trackMetric({
                    name: 'FirstContentfulPaint',
                    average: report.webVitals.fcp
                });
            }

            if (report.webVitals.ttfb) {
                this.appInsights.trackMetric({
                    name: 'TimeToFirstByte',
                    average: report.webVitals.ttfb
                });
            }

            // Send resource summary
            if (this.metrics.resourcesByType) {
                Object.entries(this.metrics.resourcesByType).forEach(([type, data]) => {
                    this.appInsights.trackEvent({
                        name: `ResourceLoading_${type}`,
                        measurements: {
                            count: data.count,
                            totalSize: data.totalSize,
                            totalTime: data.totalTime,
                            avgTime: data.avgTime,
                        }
                    });
                });
            }

            // Send design metrics as trace
            this.appInsights.trackTrace({
                message: 'Design Structure Analysis',
                properties: {
                    totalElements: String(report.designMetrics?.totalElements || 0),
                    headingsCount: String(report.designMetrics?.headings ?
                        Object.values(report.designMetrics.headings).reduce((a, b) => a + b, 0) : 0),
                    imagesCount: String(report.designMetrics?.images || 0),
                    linksCount: String(report.designMetrics?.links || 0),
                    wordCount: String(report.designMetrics?.textContent?.wordCount || 0),
                }
            });

            console.log('Telemetry sent to Application Insights');
        } catch (e) {
            console.debug('Error sending telemetry:', e);
        }
    }

    // Track custom user actions to Application Insights
    trackUserAction(actionName, properties = {}, measurements = {}) {
        if (!this.appInsights) return;

        try {
            this.appInsights.trackEvent({
                name: `UserAction_${actionName}`,
                properties,
                measurements
            });
        } catch (e) {
            console.debug('Error tracking user action:', e);
        }
    }

    // Track errors to Application Insights
    trackError(error, severity = 'error') {
        if (!this.appInsights) return;

        try {
            this.appInsights.trackException({
                exception: error,
                severityLevel: severity === 'error' ? 2 : severity === 'warning' ? 1 : 0,
            });
        } catch (e) {
            console.debug('Error tracking exception:', e);
        }
    }
}

// Initialize on load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        new PerformanceMonitor();
    });
} else {
    new PerformanceMonitor();
}
