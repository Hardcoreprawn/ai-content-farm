/**
 * Navigation Management Module
 * Handles mobile menu, navigation interactions, and scroll behavior
 */

window.NavigationManager = (function () {
    'use strict';

    let mobileMenuOpen = false;

    function init() {
        initializeMobileMenu();
        initializeScrollEffects();
        initializeBackToTop();
        initializeKeyboardNavigation();
    }

    function initializeMobileMenu() {
        const mobileMenuToggle = document.querySelector('.mobile-menu-toggle');
        const mobileNav = document.querySelector('.nav-menu');

        if (mobileMenuToggle && mobileNav) {
            mobileMenuToggle.addEventListener('click', function () {
                if (mobileMenuOpen) {
                    closeMobileMenu();
                } else {
                    openMobileMenu();
                }
            });

            // Close menu when clicking outside
            document.addEventListener('click', function (event) {
                if (mobileMenuOpen &&
                    !mobileMenuToggle.contains(event.target) &&
                    !mobileNav.contains(event.target)) {
                    closeMobileMenu();
                }
            });

            // Close menu on escape key
            document.addEventListener('keydown', function (event) {
                if (event.key === 'Escape' && mobileMenuOpen) {
                    closeMobileMenu();
                }
            });
        }
    }

    function openMobileMenu() {
        const mobileNav = document.querySelector('.nav-menu');
        const mobileMenuToggle = document.querySelector('.mobile-menu-toggle');

        if (mobileNav && mobileMenuToggle) {
            mobileNav.classList.add('active');
            mobileMenuToggle.setAttribute('aria-expanded', 'true');
            mobileMenuOpen = true;

            // Focus first menu item for accessibility
            const firstMenuItem = mobileNav.querySelector('a');
            if (firstMenuItem) {
                firstMenuItem.focus();
            }
        }
    }

    function closeMobileMenu() {
        const mobileNav = document.querySelector('.nav-menu');
        const mobileMenuToggle = document.querySelector('.mobile-menu-toggle');

        if (mobileNav && mobileMenuToggle) {
            mobileNav.classList.remove('active');
            mobileMenuToggle.setAttribute('aria-expanded', 'false');
            mobileMenuOpen = false;
        }
    }

    function initializeScrollEffects() {
        const header = document.querySelector('.site-header');
        let lastScrollTop = 0;

        if (!header) return;

        window.addEventListener('scroll', function () {
            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;

            // Add/remove scrolled class for styling
            if (scrollTop > 100) {
                header.classList.add('scrolled');
            } else {
                header.classList.remove('scrolled');
            }

            // Hide/show header on scroll (optional)
            if (scrollTop > lastScrollTop && scrollTop > 200) {
                header.classList.add('header-hidden');
            } else {
                header.classList.remove('header-hidden');
            }

            lastScrollTop = scrollTop;
        }, { passive: true });
    }

    function initializeBackToTop() {
        const backToTopButton = document.querySelector('.back-to-top');

        if (backToTopButton) {
            window.addEventListener('scroll', function () {
                if (window.pageYOffset > 300) {
                    backToTopButton.classList.add('visible');
                } else {
                    backToTopButton.classList.remove('visible');
                }
            }, { passive: true });

            backToTopButton.addEventListener('click', function (e) {
                e.preventDefault();
                window.scrollTo({
                    top: 0,
                    behavior: 'smooth'
                });
            });
        }
    }

    function initializeKeyboardNavigation() {
        // Handle keyboard navigation for dropdowns and menus
        const menuItems = document.querySelectorAll('.nav-link');

        menuItems.forEach(function (item) {
            item.addEventListener('keydown', function (e) {
                // Handle Enter and Space for menu activation
                if (e.key === 'Enter' || e.key === ' ') {
                    if (item.getAttribute('aria-expanded')) {
                        e.preventDefault();
                        item.click();
                    }
                }
            });
        });
    }

    return {
        init,
        openMobileMenu,
        closeMobileMenu
    };
})();
