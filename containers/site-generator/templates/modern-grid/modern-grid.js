/**
 * Modern Grid Theme JavaScript - Main Entry Point
 * Coordinates initialization of all theme modules
 */

document.addEventListener('DOMContentLoaded', function () {
    'use strict';

    // Initialize all modules
    if (typeof window.ThemeManager !== 'undefined') {
        window.ThemeManager.init();
    }

    if (typeof window.NavigationManager !== 'undefined') {
        window.NavigationManager.init();
    }

    if (typeof window.ArticleManager !== 'undefined') {
        window.ArticleManager.init();
    }

    if (typeof window.PerformanceOptimizer !== 'undefined') {
        window.PerformanceOptimizer.init();
    }

    if (typeof window.AccessibilityManager !== 'undefined') {
        window.AccessibilityManager.init();
    }

    console.log('🎨 Modern Grid theme initialized with modular architecture');
});
