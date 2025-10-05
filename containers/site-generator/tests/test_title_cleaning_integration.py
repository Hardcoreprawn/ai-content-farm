"""
Integration tests for title cleaning across the site generator pipeline.

Tests that URL cleaning is applied consistently when:
- Creating markdown content
- Generating HTML pages
- Creating RSS feeds
"""

import pytest
from content_utility_functions import create_markdown_content
from html_page_generation import generate_article_page
from rss_generation import generate_rss_feed
from text_processing import clean_title


@pytest.fixture
def article_with_url_in_title():
    """Article with URL embedded in title (Mastodon-style)."""
    return {
        "title": "OpenAI prepares $4 ChatGPT Go for several new countries https://www.bleepingcomputer.com/news/artifi...",
        "content": "This is article content about OpenAI's new pricing.",
        "topic_id": "ai-chatgpt-pricing",
        "source": "mastodon",
        "url": "ai-chatgpt-pricing",
        "published_date": "2025-10-05",
        "original_url": "https://mastodon.social/@user/12345",
        "source_platform": "mastodon",
    }


@pytest.fixture
def sample_config():
    """Standard site configuration."""
    return {
        "SITE_TITLE": "JabLab Tech News",
        "SITE_DESCRIPTION": "AI-curated technology news",
        "SITE_URL": "https://jablab.com",
        "SITE_DOMAIN": "jablab.com",
    }


class TestMarkdownGeneration:
    """Test title cleaning in markdown generation."""

    def test_create_markdown_content_cleans_title(self, article_with_url_in_title):
        """Test that create_markdown_content removes URLs from title."""
        markdown = create_markdown_content(article_with_url_in_title)

        # Title in frontmatter should be cleaned
        assert "https://" not in markdown
        assert "www.bleepingcomputer.com" not in markdown
        assert "..." not in markdown.split("---")[1]  # Check frontmatter section
        assert "OpenAI prepares $4 ChatGPT Go for several new countries" in markdown

    def test_markdown_preserves_content(self, article_with_url_in_title):
        """Test that content is preserved while title is cleaned."""
        markdown = create_markdown_content(article_with_url_in_title)

        # Content should be preserved
        assert "This is article content about OpenAI's new pricing." in markdown
        assert "topic_id:" in markdown
        assert "source:" in markdown


class TestHTMLPageGeneration:
    """Test title cleaning in HTML page generation."""

    def test_generate_article_page_cleans_title(
        self, article_with_url_in_title, sample_config
    ):
        """Test that generate_article_page removes URLs from title."""
        html = generate_article_page(article_with_url_in_title, sample_config)

        # HTML should contain cleaned title
        assert "https://www.bleepingcomputer.com" not in html
        assert "www.bleepingcomputer.com" not in html
        assert "OpenAI prepares $4 ChatGPT Go for several new countries" in html

    def test_html_preserves_original_url(
        self, article_with_url_in_title, sample_config
    ):
        """Test that original_url (source attribution) is preserved."""
        html = generate_article_page(article_with_url_in_title, sample_config)

        # Original URL (attribution) should still be present
        assert "https://mastodon.social/@user/12345" in html

    def test_html_page_title_is_clean(self, article_with_url_in_title, sample_config):
        """Test that <title> tag contains cleaned title."""
        html = generate_article_page(article_with_url_in_title, sample_config)

        # Page title should be clean
        assert "<title>" in html
        # URL should not be in title tag
        title_start = html.find("<title>")
        title_end = html.find("</title>")
        title_content = html[title_start:title_end]
        assert "https://" not in title_content
        assert "www." not in title_content


class TestRSSFeedGeneration:
    """Test title cleaning in RSS feed generation."""

    def test_generate_rss_feed_cleans_titles(
        self, article_with_url_in_title, sample_config
    ):
        """Test that RSS feed removes URLs from article titles."""
        articles = [article_with_url_in_title]
        rss_xml = generate_rss_feed(articles, sample_config)

        # RSS should contain cleaned title
        assert "https://www.bleepingcomputer.com" not in rss_xml
        assert "www.bleepingcomputer.com" not in rss_xml
        assert "OpenAI prepares $4 ChatGPT Go for several new countries" in rss_xml

    def test_rss_feed_structure_valid(self, article_with_url_in_title, sample_config):
        """Test that RSS feed maintains valid structure with cleaned titles."""
        articles = [article_with_url_in_title]
        rss_xml = generate_rss_feed(articles, sample_config)

        # Should have valid RSS structure
        assert '<?xml version="1.0"' in rss_xml
        assert "<rss" in rss_xml
        assert "<channel>" in rss_xml
        assert "<item>" in rss_xml
        assert "<title><![CDATA[" in rss_xml
        assert "]]></title>" in rss_xml


class TestEndToEndTitleCleaning:
    """Test title cleaning across the complete pipeline."""

    def test_multiple_article_types(self, sample_config):
        """Test title cleaning with various URL patterns."""
        test_articles = [
            {
                "title": "Article with full URL https://example.com/article",
                "content": "Content 1",
                "topic_id": "test-1",
                "source": "rss",
                "url": "test-1",
                "published_date": "2025-10-05",
            },
            {
                "title": "Article with www www.site.com/page",
                "content": "Content 2",
                "topic_id": "test-2",
                "source": "mastodon",
                "url": "test-2",
                "published_date": "2025-10-05",
            },
            {
                "title": "Article with truncated URL site.org/arti...",
                "content": "Content 3",
                "topic_id": "test-3",
                "source": "reddit",
                "url": "test-3",
                "published_date": "2025-10-05",
            },
            {
                "title": "Clean article title without URLs",
                "content": "Content 4",
                "topic_id": "test-4",
                "source": "rss",
                "url": "test-4",
                "published_date": "2025-10-05",
            },
        ]

        # Generate RSS feed with all articles
        rss_xml = generate_rss_feed(test_articles, sample_config)

        # Verify all URLs removed but content preserved
        assert "https://example.com" not in rss_xml
        assert "www.site.com" not in rss_xml
        assert "site.org" not in rss_xml
        assert "..." not in rss_xml

        # Verify clean titles present
        assert "Article with full URL" in rss_xml
        assert "Article with www" in rss_xml
        assert "Article with truncated URL" in rss_xml
        assert "Clean article title without URLs" in rss_xml

    def test_title_cleaning_preserves_quality(self):
        """Test that title cleaning doesn't damage valid content."""
        test_titles = [
            ("AI Revolution 2025", "AI Revolution 2025"),
            ("Tech News: Breaking Updates", "Tech News: Breaking Updates"),
            ("$4.99 ChatGPT Pricing", "$4.99 ChatGPT Pricing"),
            (
                "OpenAI announces https://openai.com/news",
                "OpenAI announces",
            ),
        ]

        for original, expected in test_titles:
            cleaned = clean_title(original)
            assert expected in cleaned or cleaned == expected.strip()
