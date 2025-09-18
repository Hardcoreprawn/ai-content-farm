/**
 * JabLab Tech News - Interactive Features
 * Minimal JavaScript for enhanced user experience
 */

(function () {
    'use strict';

    // Initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', function () {
        initializeTheme();
        initializeNavigation();
        initializeReadingTime();
        initializeSearchIfNeeded();
        initializeLazyLoading();
    });

    /**
     * Theme Management
     */
    function initializeTheme() {
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)');

        // Listen for system theme changes
        prefersDark.addEventListener('change', (e) => {
            updateTheme(e.matches ? 'dark' : 'light');
        });

        // Apply initial theme
        updateTheme(prefersDark.matches ? 'dark' : 'light');
    }

    function updateTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);

        // Update meta theme-color for mobile browsers
        const metaThemeColor = document.querySelector('meta[name="theme-color"]');
        if (metaThemeColor) {
            metaThemeColor.setAttribute('content',
                theme === 'dark' ? '#0f172a' : '#ffffff'
            );
        }
    }

    /**
     * Navigation Enhancement
     */
    function initializeNavigation() {
        // Add active state to navigation
        const currentPath = window.location.pathname;
        const navLinks = document.querySelectorAll('.nav-link');

        navLinks.forEach(link => {
            if (link.getAttribute('href') === currentPath) {
                link.classList.add('active');
            }
        });

        // Smooth scroll for anchor links
        document.addEventListener('click', function (e) {
            const target = e.target.closest('a[href^="#"]');
            if (target) {
                e.preventDefault();
                const targetElement = document.querySelector(target.getAttribute('href'));
                if (targetElement) {
                    targetElement.scrollIntoView({ behavior: 'smooth' });
                }
            }
        });
    }

    /**
     * Reading Time Calculation
     */
    function initializeReadingTime() {
        const articleContent = document.querySelector('.article-content');
        if (!articleContent) return;

        const text = articleContent.textContent;
        const wordCount = text.split(/\s+/).length;
        const wordsPerMinute = 200;
        const readingTime = Math.ceil(wordCount / wordsPerMinute);

        // Add reading time indicator
        const metaContainer = document.querySelector('.article-meta-full');
        if (metaContainer) {
            const readingTimeElement = document.createElement('div');
            readingTimeElement.className = 'meta-row';

            // Create elements safely to prevent XSS
            const labelSpan = document.createElement('span');
            labelSpan.className = 'meta-label';
            labelSpan.textContent = 'Reading Time:';

            const valueSpan = document.createElement('span');
            valueSpan.className = 'meta-value';
            valueSpan.textContent = `${readingTime} min read`;

            readingTimeElement.appendChild(labelSpan);
            readingTimeElement.appendChild(valueSpan);
            metaContainer.appendChild(readingTimeElement);
        }
    }

    /**
     * Simple Search (Future Enhancement)
     */
    function initializeSearchIfNeeded() {
        const searchInput = document.querySelector('#search-input');
        if (!searchInput) return;

        let searchTimeout;
        searchInput.addEventListener('input', function (e) {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                performSearch(e.target.value);
            }, 300);
        });
    }

    function performSearch(query) {
        // Future: Implement client-side search
        console.log('Search query:', query);
    }

    /**
     * Lazy Loading for Images
     */
    function initializeLazyLoading() {
        const images = document.querySelectorAll('img[data-src]');

        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        img.src = img.dataset.src;
                        img.classList.remove('lazy');
                        imageObserver.unobserve(img);
                    }
                });
            });

            images.forEach(img => imageObserver.observe(img));
        } else {
            // Fallback for older browsers
            images.forEach(img => {
                img.src = img.dataset.src;
                img.classList.remove('lazy');
            });
        }
    }

    /**
     * Analytics (Privacy-Friendly)
     */
    function trackPageView() {
        // Future: Add privacy-friendly analytics
        // Could use self-hosted analytics like Plausible
        console.log('Page view:', window.location.pathname);
    }

    /**
     * Performance Monitoring
     */
    function initializePerformanceTracking() {
        // Monitor Core Web Vitals
        if ('web-vital' in window) {
            // Future: Implement CLS, FID, LCP tracking
        }
    }

    /**
     * Progressive Web App Features
     */
    function initializePWA() {
        // Service worker registration
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js')
                .then(registration => {
                    console.log('SW registered:', registration);
                })
                .catch(registrationError => {
                    console.log('SW registration failed:', registrationError);
                });
        }

        // Install prompt handling
        let deferredPrompt;
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            deferredPrompt = e;
            showInstallButton();
        });

        function showInstallButton() {
            // Future: Show install button in UI
            console.log('App can be installed');
        }
    }

    /**
     * Error Handling
     */
    window.addEventListener('error', function (e) {
        console.error('JavaScript error:', e.error);
        // Future: Report errors to monitoring service
    });

    /**
     * Utility Functions
     */
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    function throttle(func, limit) {
        let inThrottle;
        return function () {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    /**
     * Expose utility functions globally if needed
     */
    window.JabLab = {
        utils: {
            debounce,
            throttle
        }
    };

})();
