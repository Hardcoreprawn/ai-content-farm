/**
 * Theme Management Module
 * Handles dark/light mode switching and system preference detection
 */

window.ThemeManager = (function () {
    'use strict';

    let currentTheme = localStorage.getItem('theme') || 'auto';

    function init() {
        const themeToggle = document.querySelector('.theme-toggle');
        const htmlElement = document.documentElement;

        // Apply saved theme or detect system preference
        applyTheme(currentTheme);

        if (themeToggle) {
            themeToggle.addEventListener('click', function () {
                currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
                applyTheme(currentTheme);
                localStorage.setItem('theme', currentTheme);

                // Add animation feedback
                this.style.transform = 'scale(0.95)';
                setTimeout(() => {
                    this.style.transform = '';
                }, 150);
            });
        }

        // Listen for system theme changes
        if (window.matchMedia) {
            const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
            mediaQuery.addEventListener('change', function () {
                if (currentTheme === 'auto') {
                    applyTheme('auto');
                }
            });
        }
    }

    function applyTheme(theme) {
        const htmlElement = document.documentElement;

        if (theme === 'dark') {
            htmlElement.setAttribute('data-theme', 'dark');
        } else if (theme === 'light') {
            htmlElement.setAttribute('data-theme', 'light');
        } else {
            // Auto mode - use system preference
            htmlElement.removeAttribute('data-theme');
            if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
                htmlElement.setAttribute('data-theme', 'dark');
            }
        }

        // Dispatch theme change event
        const themeEvent = new CustomEvent('themeChanged', {
            detail: { theme: theme }
        });
        document.dispatchEvent(themeEvent);
    }

    function getCurrentTheme() {
        return currentTheme;
    }

    function setTheme(theme) {
        if (['light', 'dark', 'auto'].includes(theme)) {
            currentTheme = theme;
            applyTheme(theme);
            localStorage.setItem('theme', theme);
        }
    }

    return {
        init,
        getCurrentTheme,
        setTheme,
        applyTheme
    };
})();
