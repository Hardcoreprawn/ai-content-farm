/**
 * Performance Optimization Module
 * Handles performance monitoring, lazy loading, and optimization features
 */

window.PerformanceOptimizer = (function () {
    'use strict';

    let performanceMetrics = {
        loadTime: 0,
        renderTime: 0,
        totalSize: 0
    };

    function init() {
        measurePerformance();
        initializeServiceWorker();
        optimizeImages();
        enablePrefetching();
        monitorVitals();
        setupOfflineIndicator();
    }

    function measurePerformance() {
        if ('performance' in window) {
            window.addEventListener('load', function () {
                setTimeout(() => {
                    const perfData = performance.getEntriesByType('navigation')[0];

                    if (perfData) {
                        performanceMetrics.loadTime = perfData.loadEventEnd - perfData.loadEventStart;
                        performanceMetrics.renderTime = perfData.domComplete - perfData.domLoading;

                        logPerformanceMetrics();
                    }
                }, 0);
            });
        }
    }

    function logPerformanceMetrics() {
        if (window.console && console.group) {
            console.group('🚀 Performance Metrics');
            console.log('Load Time:', performanceMetrics.loadTime + 'ms');
            console.log('Render Time:', performanceMetrics.renderTime + 'ms');
            console.log('Total Resources:', performance.getEntriesByType('resource').length);
            console.groupEnd();
        }
    }

    function initializeServiceWorker() {
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js')
                .then(function (registration) {
                    console.log('SW registered:', registration);
                })
                .catch(function (error) {
                    console.log('SW registration failed:', error);
                });
        }
    }

    function optimizeImages() {
        // Lazy loading for images
        const images = document.querySelectorAll('img[data-src]');

        if ('IntersectionObserver' in window && images.length > 0) {
            const imageObserver = new IntersectionObserver(function (entries) {
                entries.forEach(function (entry) {
                    if (entry.isIntersecting) {
                        loadImage(entry.target);
                        imageObserver.unobserve(entry.target);
                    }
                });
            }, {
                rootMargin: '50px'
            });

            images.forEach(function (img) {
                imageObserver.observe(img);
            });
        }

        // Fallback for browsers without IntersectionObserver
        else if (images.length > 0) {
            images.forEach(loadImage);
        }
    }

    function loadImage(img) {
        const src = img.dataset.src;
        if (!src) return;

        img.src = src;
        img.classList.remove('lazy');
        img.classList.add('loaded');

        img.onload = function () {
            img.style.opacity = '1';
        };
    }

    function enablePrefetching() {
        // Prefetch critical resources
        const criticalLinks = document.querySelectorAll('link[rel="prefetch"]');

        // Auto-prefetch article links on hover
        const articleLinks = document.querySelectorAll('.article-card a');

        articleLinks.forEach(function (link) {
            let prefetched = false;

            link.addEventListener('mouseenter', function () {
                if (!prefetched && 'requestIdleCallback' in window) {
                    requestIdleCallback(() => {
                        prefetchLink(this.href);
                        prefetched = true;
                    });
                }
            });
        });
    }

    function prefetchLink(url) {
        const link = document.createElement('link');
        link.rel = 'prefetch';
        link.href = url;
        document.head.appendChild(link);
    }

    function monitorVitals() {
        // Monitor Core Web Vitals if available
        if ('web-vitals' in window) {
            // This would require the web-vitals library
            // For now, we'll implement basic monitoring
            monitorLCP();
            monitorFID();
            monitorCLS();
        }
    }

    function monitorLCP() {
        // Largest Contentful Paint monitoring
        if ('PerformanceObserver' in window) {
            try {
                const observer = new PerformanceObserver(function (list) {
                    const entries = list.getEntries();
                    const lastEntry = entries[entries.length - 1];

                    if (lastEntry && lastEntry.startTime) {
                        console.log('LCP:', lastEntry.startTime);
                    }
                });

                observer.observe({ entryTypes: ['largest-contentful-paint'] });
            } catch (e) {
                // Observer not supported for this type
            }
        }
    }

    function monitorFID() {
        // First Input Delay monitoring
        if ('PerformanceObserver' in window) {
            try {
                const observer = new PerformanceObserver(function (list) {
                    const entries = list.getEntries();

                    entries.forEach(function (entry) {
                        if (entry.processingStart && entry.startTime) {
                            const fid = entry.processingStart - entry.startTime;
                            console.log('FID:', fid);
                        }
                    });
                });

                observer.observe({ entryTypes: ['first-input'] });
            } catch (e) {
                // Observer not supported for this type
            }
        }
    }

    function monitorCLS() {
        // Cumulative Layout Shift monitoring
        if ('PerformanceObserver' in window) {
            try {
                let clsScore = 0;

                const observer = new PerformanceObserver(function (list) {
                    const entries = list.getEntries();

                    entries.forEach(function (entry) {
                        if (!entry.hadRecentInput && entry.value) {
                            clsScore += entry.value;
                        }
                    });

                    console.log('CLS:', clsScore);
                });

                observer.observe({ entryTypes: ['layout-shift'] });
            } catch (e) {
                // Observer not supported for this type
            }
        }
    }

    function setupOfflineIndicator() {
        window.addEventListener('online', function () {
            showConnectionStatus('online');
        });

        window.addEventListener('offline', function () {
            showConnectionStatus('offline');
        });
    }

    function showConnectionStatus(status) {
        // Remove existing indicators
        const existingIndicator = document.querySelector('.connection-indicator');
        if (existingIndicator) {
            existingIndicator.remove();
        }

        // Create new indicator
        const indicator = document.createElement('div');
        indicator.className = `connection-indicator connection-${status}`;
        indicator.textContent = status === 'online' ? 'Back online' : 'You\'re offline';

        document.body.appendChild(indicator);

        // Auto-hide online indicator
        if (status === 'online') {
            setTimeout(() => {
                if (indicator.parentNode) {
                    indicator.remove();
                }
            }, 3000);
        }
    }

    function getMetrics() {
        return performanceMetrics;
    }

    function reportPerformance() {
        // This could send data to analytics service
        console.log('Performance Report:', performanceMetrics);
    }

    return {
        init,
        getMetrics,
        reportPerformance
    };
})();
