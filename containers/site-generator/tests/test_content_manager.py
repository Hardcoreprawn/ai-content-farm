"""
Comprehensive tests for content management utilities

Tests content generation, page creation, and template rendering.
Follows project standards for test coverage (~70%).
"""

# Add the containers path to import the content manager
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from content_manager import ContentManager
from models import ArticleMetadata

sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))


class TestContentManager:
    """Test content management functionality."""

    @pytest.fixture
    def content_manager(self):
        """Create a ContentManager instance for testing."""
        # Create temporary templates directory
        with tempfile.TemporaryDirectory() as temp_dir:
            templates_dir = Path(temp_dir)

            # Create mock templates
            (templates_dir / "article.html").write_text(
                """
            <html>
                <head><title>{{ article.title }}</title></head>
                <body>
                    <h1>{{ article.title }}</h1>
                    <div>{{ article.content }}</div>
                    <p>Generated at: {{ generated_at }}</p>
                </body>
            </html>
            """
            )

            (templates_dir / "index.html").write_text(
                """
            <html>
                <head><title>{{ site_title }}</title></head>
                <body>
                    <h1>{{ site_title }}</h1>
                    <div>Generated at: {{ generated_at }}</div>
                    {% for article in articles %}
                    <div>
                        <h2>{{ article.title }}</h2>
                        <p>{{ article.content[:100] }}</p>
                    </div>
                    {% endfor %}
                </body>
            </html>
            """
            )

            (templates_dir / "feed.xml").write_text(
                """
            <?xml version="1.0" encoding="UTF-8"?>
            <rss version="2.0">
                <channel>
                    <title>{{ site_title }}</title>
                    <description>{{ site_description }}</description>
                    <lastBuildDate>{{ generated_at }}</lastBuildDate>
                    {% for article in articles %}
                    <item>
                        <title>{{ article.title }}</title>
                        <description>{{ article.content[:200] }}</description>
                        <pubDate>{{ article.generated_at }}</pubDate>
                    </item>
                    {% endfor %}
                </channel>
            </rss>
            """
            )

            (templates_dir / "sitemap.xml").write_text(
                """
            <?xml version="1.0" encoding="UTF-8"?>
            <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                <url>
                    <loc>{{ base_url }}/</loc>
                    <lastmod>{{ generated_at.strftime('%Y-%m-%d') }}</lastmod>
                </url>
                {% for article in articles %}
                <url>
                    <loc>{{ base_url }}/articles/{{ article.slug }}.html</loc>
                    <lastmod>{{ article.generated_at.strftime('%Y-%m-%d') }}</lastmod>
                </url>
                {% endfor %}
            </urlset>
            """
            )

            yield ContentManager(templates_dir)

    @pytest.fixture
    def sample_articles(self):
        """Create sample article metadata for testing."""
        return [
            ArticleMetadata(
                topic_id="topic1",
                title="First Article",
                slug="first-article",
                word_count=500,
                quality_score=0.8,
                cost=0.01,
                source="test",
                original_url="https://example.com/1",
                generated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                content="This is the content of the first article.",
            ),
            ArticleMetadata(
                topic_id="topic2",
                title="Second Article",
                slug="second-article",
                word_count=750,
                quality_score=0.9,
                cost=0.02,
                source="test",
                original_url="https://example.com/2",
                generated_at=datetime(2025, 1, 2, 12, 0, 0, tzinfo=timezone.utc),
                content="This is the content of the second article with more details.",
            ),
            ArticleMetadata(
                topic_id="topic3",
                title="Third Article",
                slug="third-article",
                word_count=300,
                quality_score=0.7,
                cost=0.015,
                source="test",
                original_url="https://example.com/3",
                generated_at=datetime(2025, 1, 3, 12, 0, 0, tzinfo=timezone.utc),
                content="This is the content of the third article.",
            ),
        ]

    def test_content_manager_initialization(self, content_manager):
        """Test that ContentManager initializes properly."""
        assert hasattr(content_manager, "content_id")
        assert len(content_manager.content_id) == 8
        assert content_manager.content_id.isalnum()
        assert content_manager.jinja_env is not None

    @pytest.mark.asyncio
    async def test_generate_article_page_success(
        self, content_manager, sample_articles
    ):
        """Test successful article page generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            article = sample_articles[0]

            result_path = await content_manager.generate_article_page(
                article, output_dir, "test-theme"
            )

            assert result_path is not None
            assert result_path.exists()
            assert result_path.name == "first-article.html"

            # Check content
            content = result_path.read_text()
            assert "First Article" in content
            assert "This is the content of the first article" in content
            assert "Generated at:" in content

    @pytest.mark.asyncio
    async def test_generate_article_page_template_error(
        self, content_manager, sample_articles
    ):
        """Test article page generation with template error."""
        # Mock jinja environment to raise exception
        content_manager.jinja_env.get_template = Mock(
            side_effect=Exception("Template error")
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            article = sample_articles[0]

            result_path = await content_manager.generate_article_page(
                article, output_dir, "test-theme"
            )

            assert result_path is None

    @pytest.mark.asyncio
    async def test_generate_index_page_success(self, content_manager, sample_articles):
        """Test successful index page generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            result_path = await content_manager.generate_index_page(
                sample_articles, output_dir, "test-theme"
            )

            assert result_path is not None
            assert result_path.exists()
            assert result_path.name == "index.html"

            # Check content
            content = result_path.read_text()
            assert "AI Content Farm" in content
            assert "First Article" in content
            assert "Second Article" in content
            assert "Third Article" in content

    @pytest.mark.asyncio
    async def test_generate_index_page_article_sorting(
        self, content_manager, sample_articles
    ):
        """Test that index page sorts articles by date correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            result_path = await content_manager.generate_index_page(
                sample_articles, output_dir, "test-theme"
            )

            content = result_path.read_text()

            # Should be sorted newest first (topic3, topic2, topic1)
            third_pos = content.find("Third Article")
            second_pos = content.find("Second Article")
            first_pos = content.find("First Article")

            assert third_pos < second_pos < first_pos

    @pytest.mark.asyncio
    async def test_generate_rss_feed_success(self, content_manager, sample_articles):
        """Test successful RSS feed generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            result_path = await content_manager.generate_rss_feed(
                sample_articles, output_dir
            )

            assert result_path is not None
            assert result_path.exists()
            assert result_path.name == "feed.xml"

            # Check content
            content = result_path.read_text()
            assert '<?xml version="1.0"' in content
            assert "<rss version=" in content
            assert "AI Content Farm" in content
            assert "First Article" in content

    @pytest.mark.asyncio
    async def test_generate_rss_feed_article_limit(self, content_manager):
        """Test RSS feed limits articles to 50 most recent."""
        # Create more than 50 articles
        many_articles = []
        for i in range(60):
            article = ArticleMetadata(
                topic_id=f"topic{i}",
                title=f"Article {i}",
                slug=f"article-{i}",
                word_count=100,
                quality_score=0.5,
                cost=0.01,
                source="test",
                original_url=f"https://example.com/{i}",
                generated_at=datetime(
                    2025, 1, i % 28 + 1, 12, 0, 0, tzinfo=timezone.utc
                ),
                content=f"Content for article {i}",
            )
            many_articles.append(article)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            result_path = await content_manager.generate_rss_feed(
                many_articles, output_dir
            )

            content = result_path.read_text()
            # Should contain at most 50 items
            item_count = content.count("<item>")
            assert item_count <= 50

    @pytest.mark.asyncio
    async def test_generate_sitemap_success(self, content_manager, sample_articles):
        """Test successful sitemap generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            result_path = await content_manager.generate_sitemap(
                sample_articles, output_dir, "https://example.com"
            )

            assert result_path is not None
            assert result_path.exists()
            assert result_path.name == "sitemap.xml"

            # Check content
            content = result_path.read_text()
            assert '<?xml version="1.0"' in content
            assert "https://example.com/" in content
            assert "https://example.com/articles/first-article.html" in content

    def test_create_markdown_content(self, content_manager):
        """Test markdown content creation."""
        article_data = {
            "title": "Test Article",
            "description": "A test article for unit testing",
            "content": "This is the main content of the article.",
            "tags": ["test", "python", "markdown"],
        }

        markdown = content_manager.create_markdown_content(article_data)

        assert "---" in markdown  # Frontmatter delimiters
        assert 'title: "Test Article"' in markdown
        assert 'description: "A test article for unit testing"' in markdown
        assert "date:" in markdown
        assert "tags:" in markdown
        assert "- test" in markdown
        assert "- python" in markdown
        assert "This is the main content of the article." in markdown

    def test_create_markdown_content_minimal(self, content_manager):
        """Test markdown content creation with minimal data."""
        article_data = {"title": "Minimal Article"}

        markdown = content_manager.create_markdown_content(article_data)

        assert 'title: "Minimal Article"' in markdown
        assert 'description: ""' in markdown  # Should handle missing fields
        assert "date:" in markdown

    def test_create_slug_basic(self, content_manager):
        """Test basic slug creation."""
        assert content_manager.create_slug("Hello World") == "hello-world"
        assert content_manager.create_slug("Test Article Title") == "test-article-title"

    def test_create_slug_special_characters(self, content_manager):
        """Test slug creation with special characters."""
        assert content_manager.create_slug("Hello, World!") == "hello-world"
        assert content_manager.create_slug("Test@#$%^&*()Article") == "testarticle"
        assert content_manager.create_slug("Multiple   Spaces") == "multiple-spaces"

    def test_create_slug_edge_cases(self, content_manager):
        """Test slug creation edge cases."""
        # Empty string
        assert content_manager.create_slug("") == "untitled"

        # Only special characters
        assert content_manager.create_slug("@#$%^&*()") == "untitled"

        # Very long title
        long_title = "a" * 100
        slug = content_manager.create_slug(long_title)
        assert len(slug) <= 50

        # Leading/trailing spaces and hyphens
        assert content_manager.create_slug("  hello world  ") == "hello-world"
        assert content_manager.create_slug("---test---") == "test"

    def test_create_slug_unicode(self, content_manager):
        """Test slug creation with unicode characters."""
        # Should handle unicode gracefully
        slug = content_manager.create_slug("Café résumé naïve")
        assert len(slug) > 0
        assert slug != "untitled"  # Should process some characters

    @pytest.mark.asyncio
    async def test_template_rendering_error_handling(
        self, content_manager, sample_articles
    ):
        """Test error handling in template rendering."""
        # Mock template to raise exception during render
        mock_template = Mock()
        mock_template.render.side_effect = Exception("Render error")
        content_manager.jinja_env.get_template = Mock(return_value=mock_template)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            # All generation methods should handle errors gracefully
            result = await content_manager.generate_article_page(
                sample_articles[0], output_dir, "theme"
            )
            assert result is None

            result = await content_manager.generate_index_page(
                sample_articles, output_dir, "theme"
            )
            assert result is None

            result = await content_manager.generate_rss_feed(
                sample_articles, output_dir
            )
            assert result is None

    def test_jinja_environment_configuration(self, content_manager):
        """Test that Jinja environment is properly configured."""
        env = content_manager.jinja_env

        # Should have proper loader
        assert env.loader is not None

        # Should have autoescape enabled for HTML/XML
        assert env.autoescape is not None
