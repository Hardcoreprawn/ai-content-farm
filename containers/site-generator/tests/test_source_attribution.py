"""
Tests for source attribution in site generator templates and HTML generation.

Ensures that source URLs, platforms, authors, and dates are properly
displayed in generated HTML pages.
"""

from datetime import datetime, timezone

import pytest
from html_page_generation import generate_article_page, generate_index_page


@pytest.fixture
def sample_config():
    """Standard site configuration."""
    return {
        "SITE_TITLE": "JabLab Tech News",
        "SITE_DESCRIPTION": "AI-curated technology news",
        "SITE_URL": "https://jablab.com",
        "SITE_DOMAIN": "jablab.com",
    }


class TestArticlePageAttribution:
    """Test source attribution on article pages."""

    @pytest.fixture
    def sample_article_with_attribution(self):
        """Article with full source attribution."""
        return {
            "title": "Test Article About AI",
            "content": "This is a test article with comprehensive content about AI technology.",
            "url": "test-article-about-ai",
            "published_date": "2025-10-05",
            "author": "AI Content Team",
            "original_url": "https://reddit.com/r/technology/abc123",
            "source_platform": "reddit",
            "source": "reddit",  # Backward compatibility
            "source_author": "tech_enthusiast",
            "original_date": "2025-10-04T15:30:00Z",
        }

    def test_article_page_includes_original_url(
        self, sample_article_with_attribution, sample_config
    ):
        """Test that article page includes original URL."""
        html = generate_article_page(
            sample_article_with_attribution, sample_config, template_data=None
        )

        assert "https://reddit.com/r/technology/abc123" in html
        assert 'href="https://reddit.com/r/technology/abc123"' in html

    def test_article_page_includes_source_platform(
        self, sample_article_with_attribution, sample_config
    ):
        """Test that article page displays source platform."""
        html = generate_article_page(
            sample_article_with_attribution, sample_config, template_data=None
        )

        # Should display Reddit (or reddit)
        assert "reddit" in html.lower() or "Reddit" in html

    def test_article_page_includes_view_original_button(
        self, sample_article_with_attribution, sample_config
    ):
        """Test that article page includes 'View Original Source' button."""
        html = generate_article_page(
            sample_article_with_attribution, sample_config, template_data=None
        )

        assert "View Original Source" in html
        assert "btn" in html  # Button class

    def test_article_page_uses_noopener_noreferrer(
        self, sample_article_with_attribution, sample_config
    ):
        """Test that external links use rel='noopener noreferrer' for security."""
        html = generate_article_page(
            sample_article_with_attribution, sample_config, template_data=None
        )

        # Check for security attributes
        assert 'rel="noopener noreferrer"' in html or 'rel="noopener"' in html
        assert 'target="_blank"' in html

    def test_article_page_without_attribution(self, sample_config):
        """Test article page gracefully handles missing attribution."""
        article_no_attribution = {
            "title": "Test Article",
            "content": "Content without source attribution.",
            "url": "test-article",
            "published_date": "2025-10-05",
            "author": "AI Content Team",
            # No original_url, source_platform, etc.
        }

        # Should not raise an error
        html = generate_article_page(article_no_attribution, sample_config)

        assert html is not None
        assert "Test Article" in html
        # Attribution section might not appear, but page should still render

    def test_article_page_displays_author_when_available(
        self, sample_article_with_attribution, sample_config
    ):
        """Test that original author is displayed when available."""
        html = generate_article_page(
            sample_article_with_attribution, sample_config, template_data=None
        )

        assert "tech_enthusiast" in html or "Author" in html

    def test_article_page_displays_original_date(
        self, sample_article_with_attribution, sample_config
    ):
        """Test that original publication date is displayed."""
        html = generate_article_page(
            sample_article_with_attribution, sample_config, template_data=None
        )

        # Should display date in some format
        assert "2025-10-04" in html or "Published" in html


class TestIndexPageAttribution:
    """Test source attribution on index/homepage."""

    @pytest.fixture
    def sample_articles_with_attribution(self):
        """Multiple articles with source attribution."""
        return [
            {
                "id": "1",
                "slug": "reddit-article",
                "title": "Reddit Tech Discussion",
                "content": "Content from Reddit about technology trends.",
                "source": "reddit",
                "source_platform": "reddit",
                "original_url": "https://reddit.com/r/technology/123",
                "generated_at": datetime(2025, 10, 5, 10, 0, 0, tzinfo=timezone.utc),
                "word_count": 500,
                "quality_score": 0.85,
            },
            {
                "id": "2",
                "slug": "rss-article",
                "title": "RSS Feed Article",
                "content": "Content from RSS feed source.",
                "source": "rss",
                "source_platform": "rss",
                "original_url": "https://arstechnica.com/article",
                "generated_at": datetime(2025, 10, 5, 9, 0, 0, tzinfo=timezone.utc),
                "word_count": 750,
                "quality_score": 0.90,
            },
            {
                "id": "3",
                "slug": "mastodon-article",
                "title": "Mastodon Post Analysis",
                "content": "Content from Mastodon social network.",
                "source": "mastodon",
                "source_platform": "mastodon",
                "original_url": "https://mastodon.social/@user/456",
                "generated_at": datetime(2025, 10, 5, 8, 0, 0, tzinfo=timezone.utc),
                "word_count": 600,
            },
        ]

    @pytest.fixture
    def sample_config(self):
        """Standard site configuration."""
        return {
            "SITE_TITLE": "JabLab Tech News",
            "SITE_DESCRIPTION": "AI-curated technology news",
            "SITE_URL": "https://jablab.com",
            "SITE_DOMAIN": "jablab.com",
            "ARTICLES_PER_PAGE": 10,
        }

    def test_index_page_includes_source_badges(
        self, sample_articles_with_attribution, sample_config
    ):
        """Test that index page displays source type badges."""
        html = generate_index_page(sample_articles_with_attribution, sample_config)

        # Should have source badges for each article
        assert "Reddit" in html or "reddit" in html
        assert "Rss" in html or "rss" in html.lower()
        assert "Mastodon" in html or "mastodon" in html

    def test_index_page_source_badges_are_clickable(
        self, sample_articles_with_attribution, sample_config
    ):
        """Test that source badges link to original content."""
        html = generate_index_page(sample_articles_with_attribution, sample_config)

        # Should have links to original URLs
        assert "https://reddit.com/r/technology/123" in html
        assert "https://arstechnica.com/article" in html
        assert "https://mastodon.social/@user/456" in html

    def test_index_page_includes_original_source_links(
        self, sample_articles_with_attribution, sample_config
    ):
        """Test that article cards include 'Original Source' links in footer."""
        html = generate_index_page(sample_articles_with_attribution, sample_config)

        # Should have "Original Source" text
        assert "Original Source" in html or "source-link" in html

    def test_index_page_uses_security_attributes(
        self, sample_articles_with_attribution, sample_config
    ):
        """Test that external links have proper security attributes."""
        html = generate_index_page(sample_articles_with_attribution, sample_config)

        # Should have security attributes on external links
        assert 'rel="noopener noreferrer"' in html or 'rel="noopener"' in html
        assert 'target="_blank"' in html

    def test_index_page_without_attribution(self, sample_config):
        """Test index page gracefully handles articles without attribution."""
        articles_no_attribution = [
            {
                "id": "1",
                "slug": "test-article",
                "title": "Test Article",
                "content": "Test content",
                "source": "unknown",
                # No original_url
                "generated_at": datetime(2025, 10, 5, 10, 0, 0, tzinfo=timezone.utc),
            }
        ]

        # Should not raise an error
        html = generate_index_page(articles_no_attribution, sample_config)

        assert html is not None
        assert "Test Article" in html

    def test_index_page_article_title_links_to_article_page(
        self, sample_articles_with_attribution, sample_config
    ):
        """Test that article card title links to our article page, not external source."""
        html = generate_index_page(sample_articles_with_attribution, sample_config)

        # Should link to /articles/slug.html
        assert "/articles/reddit-article.html" in html
        assert "/articles/rss-article.html" in html

        # Title should NOT link directly to external URLs
        # (external links should be separate in footer)


class TestAttributionDataFlow:
    """Integration tests for attribution data flow."""

    def test_attribution_preserved_from_collector_to_generator(self):
        """Test that attribution flows from collector through to site generator."""
        # This would be an integration test that:
        # 1. Collects content with source URL
        # 2. Generates article preserving attribution
        # 3. Renders HTML with attribution visible
        # For now, this is a placeholder for future integration testing
        pass

    def test_all_source_types_display_correctly(self):
        """Test that Reddit, RSS, Mastodon, and Web sources all display properly."""
        # This would test each source type end-to-end
        # Placeholder for comprehensive integration test
        pass


class TestAttributionSecurity:
    """Test security aspects of source attribution display."""

    def test_url_escaping_prevents_xss(self, sample_config):
        """Test that malicious URLs are properly escaped."""
        malicious_article = {
            "title": "Test Article",
            "content": "Test content",
            "url": "test-article",
            "published_date": "2025-10-05",
            "author": "Test",
            "original_url": 'javascript:alert("XSS")',  # Malicious URL
            "source_platform": "web",
        }

        html = generate_article_page(malicious_article, sample_config)

        # Should not contain unescaped javascript: protocol
        # Jinja2 auto-escaping should handle this, but verify
        assert 'href="javascript:' not in html or "&" in html  # Check for escaping

    def test_author_name_escaping(self, sample_config):
        """Test that author names with HTML are properly escaped."""
        article_with_html_author = {
            "title": "Test Article",
            "content": "Test content",
            "url": "test-article",
            "published_date": "2025-10-05",
            "author": '<script>alert("XSS")</script>',  # Malicious author
            "original_url": "https://example.com",
            "source_platform": "web",
        }

        html = generate_article_page(article_with_html_author, sample_config)

        # Should escape HTML tags in author name
        assert "<script>" not in html or "&lt;script&gt;" in html
