/**
 * Article Management Module
 * Handles article filtering, search, sorting, and interactions
 */

window.ArticleManager = (function () {
    'use strict';

    let articles = [];
    let filteredArticles = [];
    let currentFilters = {
        search: '',
        category: '',
        sort: 'newest'
    };

    function init() {
        cacheArticles();
        initializeSearch();
        initializeFiltering();
        initializeSorting();
        initializeReadingProgress();
        initializeLazyLoading();
    }

    function cacheArticles() {
        const articleCards = document.querySelectorAll('.article-card');

        articles = Array.from(articleCards).map(function (card) {
            const title = card.querySelector('.article-title')?.textContent || '';
            const description = card.querySelector('.article-description')?.textContent || '';
            const category = card.dataset.category || '';
            const date = card.dataset.date || '';
            const tags = Array.from(card.querySelectorAll('.tag')).map(tag => tag.textContent);

            return {
                element: card,
                title: title.toLowerCase(),
                description: description.toLowerCase(),
                category: category.toLowerCase(),
                date: new Date(date),
                tags: tags.map(tag => tag.toLowerCase())
            };
        });

        filteredArticles = [...articles];
    }

    function initializeSearch() {
        const searchInput = document.querySelector('#search');

        if (searchInput) {
            let searchTimeout;

            searchInput.addEventListener('input', function () {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {
                    currentFilters.search = this.value.toLowerCase().trim();
                    applyFilters();
                }, 300); // Debounce search
            });

            // Clear search button
            const clearButton = document.querySelector('.search-clear');
            if (clearButton) {
                clearButton.addEventListener('click', function () {
                    searchInput.value = '';
                    currentFilters.search = '';
                    applyFilters();
                });
            }
        }
    }

    function initializeFiltering() {
        const categoryFilter = document.querySelector('#category-filter');

        if (categoryFilter) {
            categoryFilter.addEventListener('change', function () {
                currentFilters.category = this.value.toLowerCase();
                applyFilters();
            });
        }

        // Tag filtering
        const tagFilters = document.querySelectorAll('.tag-filter');
        tagFilters.forEach(function (tagFilter) {
            tagFilter.addEventListener('click', function () {
                const tag = this.dataset.tag;
                toggleTagFilter(tag);
            });
        });
    }

    function initializeSorting() {
        const sortSelect = document.querySelector('#sort-select');

        if (sortSelect) {
            sortSelect.addEventListener('change', function () {
                currentFilters.sort = this.value;
                applyFilters();
            });
        }
    }

    function applyFilters() {
        filteredArticles = articles.filter(function (article) {
            // Search filter
            if (currentFilters.search) {
                const searchMatch = article.title.includes(currentFilters.search) ||
                    article.description.includes(currentFilters.search) ||
                    article.tags.some(tag => tag.includes(currentFilters.search));

                if (!searchMatch) return false;
            }

            // Category filter
            if (currentFilters.category && currentFilters.category !== '') {
                if (article.category !== currentFilters.category) return false;
            }

            return true;
        });

        // Apply sorting
        sortArticles();

        // Update display
        updateArticleDisplay();
        updateResultsCount();
    }

    function sortArticles() {
        switch (currentFilters.sort) {
            case 'oldest':
                filteredArticles.sort((a, b) => a.date - b.date);
                break;
            case 'title':
                filteredArticles.sort((a, b) => a.title.localeCompare(b.title));
                break;
            case 'newest':
            default:
                filteredArticles.sort((a, b) => b.date - a.date);
                break;
        }
    }

    function updateArticleDisplay() {
        const articlesContainer = document.querySelector('.articles-grid');

        if (!articlesContainer) return;

        // Hide all articles first
        articles.forEach(function (article) {
            article.element.style.display = 'none';
            article.element.classList.remove('filtered-in');
        });

        // Show filtered articles with animation
        filteredArticles.forEach(function (article, index) {
            article.element.style.display = 'block';

            // Stagger animation
            setTimeout(() => {
                article.element.classList.add('filtered-in');
            }, index * 50);
        });

        // Handle empty state
        const emptyState = document.querySelector('.empty-state');
        if (filteredArticles.length === 0) {
            if (!emptyState) {
                createEmptyState();
            } else {
                emptyState.style.display = 'block';
            }
        } else if (emptyState) {
            emptyState.style.display = 'none';
        }
    }

    function createEmptyState() {
        const articlesContainer = document.querySelector('.articles-grid');
        if (!articlesContainer) return;

        const emptyState = document.createElement('div');
        emptyState.className = 'empty-state';
        emptyState.innerHTML = `
            <div class="empty-state-icon">📝</div>
            <h2 class="empty-state-title">No articles found</h2>
            <p class="empty-state-description">
                Try adjusting your search terms or filters to find what you're looking for.
            </p>
            <button class="btn btn-primary" onclick="ArticleManager.clearFilters()">
                Clear Filters
            </button>
        `;

        articlesContainer.parentNode.appendChild(emptyState);
    }

    function updateResultsCount() {
        const resultsCount = document.querySelector('.results-count');
        if (resultsCount) {
            const count = filteredArticles.length;
            const total = articles.length;
            resultsCount.textContent = `Showing ${count} of ${total} articles`;
        }
    }

    function clearFilters() {
        currentFilters = {
            search: '',
            category: '',
            sort: 'newest'
        };

        // Reset form controls
        const searchInput = document.querySelector('#search');
        const categoryFilter = document.querySelector('#category-filter');
        const sortSelect = document.querySelector('#sort-select');

        if (searchInput) searchInput.value = '';
        if (categoryFilter) categoryFilter.value = '';
        if (sortSelect) sortSelect.value = 'newest';

        applyFilters();
    }

    function initializeReadingProgress() {
        const progressBar = document.querySelector('.reading-progress');

        if (progressBar) {
            window.addEventListener('scroll', function () {
                const winHeight = window.innerHeight;
                const docHeight = document.documentElement.scrollHeight;
                const scrollTop = window.pageYOffset;

                const progress = (scrollTop / (docHeight - winHeight)) * 100;
                progressBar.style.width = Math.min(progress, 100) + '%';
            }, { passive: true });
        }
    }

    function initializeLazyLoading() {
        const images = document.querySelectorAll('img[data-src]');

        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver(function (entries) {
                entries.forEach(function (entry) {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        img.src = img.dataset.src;
                        img.classList.remove('lazy');
                        imageObserver.unobserve(img);
                    }
                });
            });

            images.forEach(function (img) {
                imageObserver.observe(img);
            });
        }
    }

    function toggleTagFilter(tag) {
        // Implementation for tag filtering
        console.log('Tag filter toggled:', tag);
    }

    return {
        init,
        clearFilters,
        applyFilters
    };
})();
