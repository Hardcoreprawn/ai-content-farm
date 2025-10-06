"""
Test URL consistency across all components.

Ensures that all URL generation uses the centralized get_article_url function
to prevent URL mismatch issues between sitemap, RSS, and HTML generation.
"""

import pytest
from url_utils import get_article_url


class TestURLConsistency:
    """Test centralized URL generation for consistency."""

    def test_get_article_url_basic(self):
        """Test basic article URL generation."""
        url = get_article_url("123-my-article")
        assert url == "/articles/123-my-article.html"

    def test_get_article_url_with_base_url(self):
        """Test article URL generation with base URL."""
        url = get_article_url("123-my-article", base_url="https://jablab.com")
        assert url == "https://jablab.com/articles/123-my-article.html"

    def test_get_article_url_without_html_extension(self):
        """Test article URL generation without .html extension."""
        url = get_article_url("123-my-article", include_html_extension=False)
        assert url == "/articles/123-my-article"

    def test_get_article_url_with_complex_slug(self):
        """Test URL generation with complex slugs."""
        url = get_article_url("12345-my-complex-article-title-here")
        assert url == "/articles/12345-my-complex-article-title-here.html"

    def test_get_article_url_empty_slug_raises_error(self):
        """Test that empty slug raises ValueError."""
        with pytest.raises(ValueError, match="article_slug cannot be empty"):
            get_article_url("")

    def test_get_article_url_none_slug_raises_error(self):
        """Test that None slug raises ValueError."""
        with pytest.raises(ValueError):
            get_article_url(None)


class TestURLConsistencyAcrossComponents:
    """Test that all components use the same URL format."""

    def test_sitemap_uses_get_article_url(self):
        """Verify sitemap generation uses get_article_url."""
        from sitemap_generation import _generate_article_urls

        articles = [
            {
                "url": "123-test-article",
                "published_date": "2025-10-06",
            }
        ]

        urls = _generate_article_urls(articles, "https://jablab.com", "2025-10-06")

        # Check that the URL matches our centralized format
        assert len(urls) == 1
        assert "https://jablab.com/articles/123-test-article.html" in urls[0]
        assert "<loc>https://jablab.com/articles/123-test-article.html</loc>" in urls[0]

    def test_rss_uses_consistent_url_format(self):
        """Verify RSS generation uses consistent URL format."""
        from rss_generation import _generate_rss_item

        article = {
            "title": "Test Article",
            "url": "123-test-article",
            "published_date": "2025-10-06T12:00:00Z",
            "content": "Test content here.",
            "description": "Test description",
        }

        config = {
            "SITE_DOMAIN": "jablab.com",
        }

        rss_item = _generate_rss_item(
            article, config, "https://jablab.com", "Mon, 06 Oct 2025 12:00:00 +0000"
        )

        # Check that the URL matches our centralized format
        assert "https://jablab.com/articles/123-test-article.html" in rss_item
        assert (
            "<link>https://jablab.com/articles/123-test-article.html</link>" in rss_item
        )
        assert (
            "<guid>https://jablab.com/articles/123-test-article.html</guid>" in rss_item
        )

    def test_html_page_uses_consistent_url_format(self):
        """Verify HTML page generation uses consistent URL format."""
        from html_page_generation import generate_article_page

        article = {
            "title": "Test Article",
            "url": "123-test-article",
            "content": "# Test Content\n\nThis is a test article.",
            "published_date": "2025-10-06T12:00:00Z",
        }

        config = {
            "SITE_TITLE": "Test Site",
            "SITE_DESCRIPTION": "Test Description",
            "SITE_URL": "https://jablab.com",
            "SITE_DOMAIN": "jablab.com",
        }

        html = generate_article_page(article, config)

        # Check that the canonical URL matches our centralized format
        assert "https://jablab.com/articles/123-test-article.html" in html

    def test_all_components_generate_same_url(self):
        """Integration test: verify all components generate identical URLs for same article."""
        article_slug = "123-test-article"
        base_url = "https://jablab.com"

        # Get canonical URL from helper
        canonical_url = get_article_url(article_slug, base_url=base_url)

        # Test sitemap
        from sitemap_generation import _generate_article_urls

        sitemap_urls = _generate_article_urls(
            [{"url": article_slug, "published_date": "2025-10-06"}],
            base_url,
            "2025-10-06",
        )
        assert canonical_url in sitemap_urls[0]

        # Test RSS
        from rss_generation import _generate_rss_item

        rss_item = _generate_rss_item(
            {
                "title": "Test",
                "url": article_slug,
                "published_date": "2025-10-06T12:00:00Z",
                "content": "Test",
            },
            {"SITE_DOMAIN": "jablab.com"},
            base_url,
            "Mon, 06 Oct 2025 12:00:00 +0000",
        )
        assert canonical_url in rss_item

        # Test HTML
        from html_page_generation import generate_article_page

        html = generate_article_page(
            {
                "title": "Test",
                "url": article_slug,
                "content": "Test",
                "published_date": "2025-10-06T12:00:00Z",
            },
            {
                "SITE_TITLE": "Test",
                "SITE_URL": base_url,
                "SITE_DOMAIN": "jablab.com",
            },
        )
        assert canonical_url in html

        print(f"✓ All components use consistent URL: {canonical_url}")
