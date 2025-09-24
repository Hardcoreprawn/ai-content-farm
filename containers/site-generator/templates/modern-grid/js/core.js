/**
 * Modern Grid Theme - Core JavaScript
 * Main initialization and coordination module
 */

(function () {
    'use strict';

    // Initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', function () {
        // Initialize core modules
        if (window.ThemeManager) window.ThemeManager.init();
        if (window.NavigationManager) window.NavigationManager.init();
        if (window.ArticleManager) window.ArticleManager.init();
        if (window.PerformanceManager) window.PerformanceManager.init();
        if (window.AccessibilityManager) window.AccessibilityManager.init();
    });

})();
