"""
Content manager advanced tests

Tests index page generation, RSS feed generation, and utility functions.
"""

import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from content_manager import ContentManager
from models import ArticleMetadata

sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))


class TestIndexPageGeneration:
    """Test index page generation functionality."""

    @pytest.fixture
    def content_manager(self):
        """Create a ContentManager instance for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            templates_dir = Path(temp_dir)
            (templates_dir / "index.html").write_text(
                """
            <html>
                <head><title>{{ site_title }}</title></head>
                <body>
                    <h1>{{ site_title }}</h1>
                    <ul>
                    {% for article in articles %}
                        <li><a href="{{ article.slug }}.html">{{ article.title }}</a></li>
                    {% endfor %}
                    </ul>
                    <p>Total articles: {{ articles|length }}</p>
                </body>
            </html>
            """
            )
            yield ContentManager(templates_dir)

    @pytest.fixture
    def sample_articles(self):
        """Create sample articles for testing."""
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
                content="Content of first article.",
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
                content="Content of second article.",
            ),
        ]

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
            assert "AI Content Farm" in content  # Actual site title
            assert "first-article.html" in content
            assert "second-article.html" in content
            assert "Total articles: 2" in content

    @pytest.mark.asyncio
    async def test_generate_index_page_empty_articles(self, content_manager):
        """Test index page generation with empty articles list."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            result_path = await content_manager.generate_index_page(
                [], output_dir, "test-theme"
            )

            assert result_path is not None
            assert result_path.exists()

            content = result_path.read_text()
            assert "Total articles: 0" in content

    @pytest.mark.asyncio
    async def test_generate_index_page_template_error(
        self, content_manager, sample_articles
    ):
        """Test index page generation with template error."""
        content_manager.jinja_env.get_template = Mock(
            side_effect=Exception("Template error")
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            result_path = await content_manager.generate_index_page(
                sample_articles, output_dir, "test-theme"
            )

            assert result_path is None


class TestRSSFeedGeneration:
    """Test RSS feed generation functionality."""

    @pytest.fixture
    def content_manager(self):
        """Create a ContentManager instance for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            templates_dir = Path(temp_dir)
            (templates_dir / "feed.xml").write_text(
                """
            <?xml version="1.0" encoding="UTF-8"?>
            <rss version="2.0">
                <channel>
                    <title>{{ site_title }}</title>
                    <description>{{ site_description }}</description>
                    {% for article in articles %}
                    <item>
                        <title>{{ article.title }}</title>
                        <description>{{ article.content[:200] }}</description>
                        <pubDate>{{ article.generated_at }}</pubDate>
                        <link>{{ article.slug }}.html</link>
                    </item>
                    {% endfor %}
                </channel>
            </rss>
            """
            )
            yield ContentManager(templates_dir)

    @pytest.fixture
    def sample_articles(self):
        """Create sample articles for testing."""
        return [
            ArticleMetadata(
                topic_id="topic1",
                title="RSS Article 1",
                slug="rss-article-1",
                word_count=500,
                quality_score=0.8,
                cost=0.01,
                source="test",
                original_url="https://example.com/1",
                generated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                content="This is the content of the first RSS article with enough text to test truncation behavior.",
            ),
            ArticleMetadata(
                topic_id="topic2",
                title="RSS Article 2",
                slug="rss-article-2",
                word_count=300,
                quality_score=0.7,
                cost=0.015,
                source="test",
                original_url="https://example.com/2",
                generated_at=datetime(2025, 1, 2, 12, 0, 0, tzinfo=timezone.utc),
                content="Short content for second RSS article.",
            ),
        ]

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
            assert "<?xml version=" in content
            assert "<rss version=" in content
            assert "RSS Article 1" in content
            assert "RSS Article 2" in content
            assert "rss-article-1.html" in content

    @pytest.mark.asyncio
    async def test_generate_rss_feed_empty_articles(self, content_manager):
        """Test RSS feed generation with empty articles list."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            result_path = await content_manager.generate_rss_feed([], output_dir)

            assert result_path is not None
            assert result_path.exists()

            content = result_path.read_text()
            assert "<?xml version=" in content
            assert "<rss version=" in content

    @pytest.mark.asyncio
    async def test_generate_rss_feed_template_error(
        self, content_manager, sample_articles
    ):
        """Test RSS feed generation with template error."""
        content_manager.jinja_env.get_template = Mock(
            side_effect=Exception("Template error")
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            result_path = await content_manager.generate_rss_feed(
                sample_articles, output_dir
            )

            assert result_path is None


class TestUtilityFunctions:
    """Test utility functions and helper methods."""

    @pytest.fixture
    def content_manager(self):
        """Create a basic ContentManager instance."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield ContentManager(Path(temp_dir))

    def test_create_slug_basic(self, content_manager):
        """Test basic slug creation."""
        assert content_manager.create_slug("Hello World") == "hello-world"
        assert content_manager.create_slug("Test Article Title") == "test-article-title"
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

    def test_create_slug_consistency(self, content_manager):
        """Test that slug creation is consistent."""
        title = "Test Article Title"
        slug1 = content_manager.create_slug(title)
        slug2 = content_manager.create_slug(title)
        assert slug1 == slug2

    def test_create_slug_case_insensitive(self, content_manager):
        """Test that slug creation is case insensitive."""
        assert content_manager.create_slug("HELLO WORLD") == "hello-world"
        assert content_manager.create_slug("Hello World") == "hello-world"
        assert content_manager.create_slug("hello world") == "hello-world"


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.fixture
    def content_manager(self):
        """Create a ContentManager instance for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            templates_dir = Path(temp_dir)
            (templates_dir / "article.html").write_text(
                "<html>{{ article.title }}</html>"
            )
            (templates_dir / "index.html").write_text("<html>{{ site_title }}</html>")
            (templates_dir / "rss.xml").write_text("<rss>{{ site_title }}</rss>")
            yield ContentManager(templates_dir)

    @pytest.fixture
    def sample_articles(self):
        """Create sample articles for testing."""
        return [
            ArticleMetadata(
                topic_id="topic1",
                title="Test Article",
                slug="test-article",
                word_count=500,
                quality_score=0.8,
                cost=0.01,
                source="test",
                original_url="https://example.com/test",
                generated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                content="Test content.",
            )
        ]

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

    @pytest.mark.asyncio
    async def test_invalid_output_directory(self, content_manager, sample_articles):
        """Test handling of invalid output directory."""
        # Use a non-existent directory path
        invalid_dir = Path("/nonexistent/path/that/should/not/exist")

        result = await content_manager.generate_article_page(
            sample_articles[0], invalid_dir, "theme"
        )
        assert result is None

        result = await content_manager.generate_index_page(
            sample_articles, invalid_dir, "theme"
        )
        assert result is None

        result = await content_manager.generate_rss_feed(sample_articles, invalid_dir)
        assert result is None
