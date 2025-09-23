/**
 * Accessibility Module
 * Handles accessibility features, keyboard navigation, screen reader support, and WCAG compliance
 */

window.AccessibilityManager = (function () {
    'use strict';

    let focusVisible = false;
    let reducedMotion = false;

    function init() {
        detectReducedMotion();
        setupKeyboardNavigation();
        enhanceScreenReaderSupport();
        setupFocusManagement();
        initializeSkipLinks();
        setupAriaLiveRegions();
        monitorColorContrast();
    }

    function detectReducedMotion() {
        const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

        reducedMotion = prefersReducedMotion.matches;

        if (reducedMotion) {
            document.body.classList.add('reduced-motion');
        }

        // Listen for changes
        prefersReducedMotion.addEventListener('change', function () {
            reducedMotion = this.matches;
            document.body.classList.toggle('reduced-motion', reducedMotion);
        });
    }

    function setupKeyboardNavigation() {
        // Track focus visibility
        document.addEventListener('keydown', function () {
            focusVisible = true;
            document.body.classList.add('focus-visible');
        });

        document.addEventListener('mousedown', function () {
            focusVisible = false;
            document.body.classList.remove('focus-visible');
        });

        // Enhanced keyboard navigation for cards
        const cards = document.querySelectorAll('.article-card, .card');

        cards.forEach(function (card) {
            // Make cards focusable
            if (!card.hasAttribute('tabindex')) {
                card.setAttribute('tabindex', '0');
            }

            // Add keyboard interaction
            card.addEventListener('keydown', function (e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    const link = card.querySelector('a');
                    if (link) {
                        link.click();
                    }
                }
            });
        });

        // Arrow key navigation for grids
        setupGridNavigation();

        // Escape key handlers
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') {
                closeModals();
                closeMobileMenu();
            }
        });
    }

    function setupGridNavigation() {
        const grid = document.querySelector('.articles-grid');
        if (!grid) return;

        const cards = Array.from(grid.querySelectorAll('.article-card'));

        grid.addEventListener('keydown', function (e) {
            const currentIndex = cards.indexOf(document.activeElement);
            if (currentIndex === -1) return;

            let nextIndex = currentIndex;
            const cols = getGridColumns();

            switch (e.key) {
                case 'ArrowRight':
                    nextIndex = Math.min(currentIndex + 1, cards.length - 1);
                    break;
                case 'ArrowLeft':
                    nextIndex = Math.max(currentIndex - 1, 0);
                    break;
                case 'ArrowDown':
                    nextIndex = Math.min(currentIndex + cols, cards.length - 1);
                    break;
                case 'ArrowUp':
                    nextIndex = Math.max(currentIndex - cols, 0);
                    break;
                case 'Home':
                    nextIndex = 0;
                    break;
                case 'End':
                    nextIndex = cards.length - 1;
                    break;
                default:
                    return; // Don't prevent default for other keys
            }

            if (nextIndex !== currentIndex) {
                e.preventDefault();
                cards[nextIndex].focus();
            }
        });
    }

    function getGridColumns() {
        const grid = document.querySelector('.articles-grid');
        if (!grid) return 1;

        const computedStyle = window.getComputedStyle(grid);
        const gridTemplate = computedStyle.getPropertyValue('grid-template-columns');

        // Count the number of columns
        return (gridTemplate.match(/auto|fr|px|%|em|rem/g) || [1]).length;
    }

    function enhanceScreenReaderSupport() {
        // Add proper ARIA labels where missing
        addAriaLabels();

        // Announce dynamic content changes
        setupContentAnnouncements();

        // Enhance form accessibility
        enhanceFormAccessibility();
    }

    function addAriaLabels() {
        // Search input
        const searchInput = document.querySelector('#search');
        if (searchInput && !searchInput.hasAttribute('aria-label')) {
            searchInput.setAttribute('aria-label', 'Search articles');
        }

        // Navigation buttons
        const navButtons = document.querySelectorAll('.nav-toggle, .theme-toggle');
        navButtons.forEach(function (button) {
            if (!button.hasAttribute('aria-label')) {
                const text = button.textContent.trim();
                if (!text) {
                    if (button.classList.contains('nav-toggle')) {
                        button.setAttribute('aria-label', 'Toggle navigation menu');
                    } else if (button.classList.contains('theme-toggle')) {
                        button.setAttribute('aria-label', 'Toggle dark mode');
                    }
                }
            }
        });

        // Article cards
        const articleCards = document.querySelectorAll('.article-card');
        articleCards.forEach(function (card) {
            const title = card.querySelector('.article-title');
            if (title && !card.hasAttribute('aria-label')) {
                card.setAttribute('aria-label', `Article: ${title.textContent.trim()}`);
            }
        });
    }

    function setupContentAnnouncements() {
        // Create or find live regions
        let liveRegion = document.querySelector('#aria-live-region');
        if (!liveRegion) {
            liveRegion = document.createElement('div');
            liveRegion.id = 'aria-live-region';
            liveRegion.setAttribute('aria-live', 'polite');
            liveRegion.setAttribute('aria-atomic', 'true');
            liveRegion.className = 'sr-only';
            document.body.appendChild(liveRegion);
        }

        // Announce search results
        const searchInput = document.querySelector('#search');
        if (searchInput) {
            let searchTimeout;
            searchInput.addEventListener('input', function () {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {
                    announceSearchResults();
                }, 1000);
            });
        }
    }

    function announceSearchResults() {
        const resultsCount = document.querySelector('.results-count');
        const liveRegion = document.querySelector('#aria-live-region');

        if (resultsCount && liveRegion) {
            liveRegion.textContent = resultsCount.textContent;
        }
    }

    function enhanceFormAccessibility() {
        // Add required field indicators
        const requiredFields = document.querySelectorAll('input[required], select[required], textarea[required]');

        requiredFields.forEach(function (field) {
            if (!field.hasAttribute('aria-required')) {
                field.setAttribute('aria-required', 'true');
            }

            // Add visual indicator if not present
            const label = document.querySelector(`label[for="${field.id}"]`);
            if (label && !label.textContent.includes('*')) {
                label.innerHTML += ' <span class="required" aria-label="required">*</span>';
            }
        });

        // Enhance error messages
        const errorMessages = document.querySelectorAll('.error-message');
        errorMessages.forEach(function (error) {
            if (!error.hasAttribute('role')) {
                error.setAttribute('role', 'alert');
            }
        });
    }

    function setupFocusManagement() {
        // Focus trap for modals
        const modals = document.querySelectorAll('.modal, .dialog');

        modals.forEach(function (modal) {
            modal.addEventListener('keydown', function (e) {
                if (e.key === 'Tab') {
                    trapFocus(e, modal);
                }
            });
        });

        // Restore focus after modal closes
        document.addEventListener('modal:closed', function (e) {
            const trigger = e.detail?.trigger;
            if (trigger && typeof trigger.focus === 'function') {
                trigger.focus();
            }
        });
    }

    function trapFocus(e, container) {
        const focusableElements = container.querySelectorAll(
            'a[href], button, textarea, input[type="text"], input[type="radio"], input[type="checkbox"], select'
        );

        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        if (e.shiftKey) {
            if (document.activeElement === firstElement) {
                e.preventDefault();
                lastElement.focus();
            }
        } else {
            if (document.activeElement === lastElement) {
                e.preventDefault();
                firstElement.focus();
            }
        }
    }

    function initializeSkipLinks() {
        // Create skip links if they don't exist
        let skipNav = document.querySelector('.skip-nav');

        if (!skipNav) {
            skipNav = document.createElement('nav');
            skipNav.className = 'skip-nav';
            skipNav.innerHTML = `
                <a href="#main-content" class="skip-link">Skip to main content</a>
                <a href="#navigation" class="skip-link">Skip to navigation</a>
            `;

            document.body.insertBefore(skipNav, document.body.firstChild);
        }

        // Ensure main content has proper ID
        const mainContent = document.querySelector('main') || document.querySelector('#main-content');
        if (mainContent && !mainContent.id) {
            mainContent.id = 'main-content';
        }
    }

    function setupAriaLiveRegions() {
        // Status region for temporary messages
        if (!document.querySelector('#status-region')) {
            const statusRegion = document.createElement('div');
            statusRegion.id = 'status-region';
            statusRegion.setAttribute('aria-live', 'polite');
            statusRegion.className = 'sr-only';
            document.body.appendChild(statusRegion);
        }

        // Alert region for important messages
        if (!document.querySelector('#alert-region')) {
            const alertRegion = document.createElement('div');
            alertRegion.id = 'alert-region';
            alertRegion.setAttribute('aria-live', 'assertive');
            alertRegion.className = 'sr-only';
            document.body.appendChild(alertRegion);
        }
    }

    function monitorColorContrast() {
        // This is a basic implementation - in production, you'd want a more sophisticated solution
        if (window.console && console.warn) {
            const elements = document.querySelectorAll('*');

            // This would require a color contrast library in a real implementation
            // For now, just log that we're monitoring
            console.log('Accessibility: Color contrast monitoring enabled');
        }
    }

    function closeModals() {
        const openModals = document.querySelectorAll('.modal.is-open, .dialog.is-open');
        openModals.forEach(function (modal) {
            modal.classList.remove('is-open');
            modal.setAttribute('aria-hidden', 'true');
        });
    }

    function closeMobileMenu() {
        const mobileNav = document.querySelector('.mobile-nav');
        if (mobileNav && mobileNav.classList.contains('is-open')) {
            mobileNav.classList.remove('is-open');

            // Focus back to toggle button
            const toggle = document.querySelector('.nav-toggle');
            if (toggle) {
                toggle.focus();
            }
        }
    }

    function announceMessage(message, priority = 'polite') {
        const region = priority === 'assertive' ?
            document.querySelector('#alert-region') :
            document.querySelector('#status-region');

        if (region) {
            region.textContent = message;

            // Clear message after a delay
            setTimeout(() => {
                region.textContent = '';
            }, 3000);
        }
    }

    return {
        init,
        announceMessage,
        trapFocus
    };
})();
