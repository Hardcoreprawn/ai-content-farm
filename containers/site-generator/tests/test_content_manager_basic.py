"""
Content manager basic tests

Tests initialization, basic functionality, and article page generation.
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


class TestContentManagerBasics:
    """Test basic content manager functionality."""

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
                    <ul>
                    {% for article in articles %}
                        <li><a href="{{ article.slug }}.html">{{ article.title }}</a></li>
                    {% endfor %}
                    </ul>
                </body>
            </html>
            """
            )

            (templates_dir / "rss.xml").write_text(
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
                    </item>
                    {% endfor %}
                </channel>
            </rss>
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

    def test_jinja_environment_configuration(self, content_manager):
        """Test that Jinja environment is properly configured."""
        env = content_manager.jinja_env

        # Should have proper loader
        assert env.loader is not None

        # Should have autoescape enabled for HTML/XML
        assert env.autoescape is not None

    def test_unique_content_ids(self):
        """Test that each content manager gets a unique ID."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager1 = ContentManager(Path(temp_dir))
            manager2 = ContentManager(Path(temp_dir))
            assert manager1.content_id != manager2.content_id


class TestArticlePageGeneration:
    """Test article page generation functionality."""

    @pytest.fixture
    def content_manager(self):
        """Create a ContentManager instance for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            templates_dir = Path(temp_dir)
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
            yield ContentManager(templates_dir)

    @pytest.fixture
    def sample_article(self):
        """Create a sample article for testing."""
        return ArticleMetadata(
            topic_id="topic1",
            title="Test Article",
            slug="test-article",
            word_count=500,
            quality_score=0.8,
            cost=0.01,
            source="test",
            original_url="https://example.com/test",
            generated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            content="This is test article content.",
        )

    @pytest.mark.asyncio
    async def test_generate_article_page_success(self, content_manager, sample_article):
        """Test successful article page generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            result_path = await content_manager.generate_article_page(
                sample_article, output_dir, "test-theme"
            )

            assert result_path is not None
            assert result_path.exists()
            assert result_path.name == "test-article.html"

            # Check content
            content = result_path.read_text()
            assert "Test Article" in content
            assert "This is test article content" in content
            assert "Generated at:" in content

    @pytest.mark.asyncio
    async def test_generate_article_page_template_error(
        self, content_manager, sample_article
    ):
        """Test article page generation with template error."""
        # Mock jinja environment to raise exception
        content_manager.jinja_env.get_template = Mock(
            side_effect=Exception("Template error")
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            result_path = await content_manager.generate_article_page(
                sample_article, output_dir, "test-theme"
            )

            assert result_path is None

    @pytest.mark.asyncio
    async def test_generate_article_page_write_error(
        self, content_manager, sample_article
    ):
        """Test article page generation with file write error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            # Make output directory read-only to cause write error
            output_dir.chmod(0o444)

            result_path = await content_manager.generate_article_page(
                sample_article, output_dir, "test-theme"
            )

            assert result_path is None

    @pytest.mark.asyncio
    async def test_generate_article_page_custom_theme(
        self, content_manager, sample_article
    ):
        """Test article page generation with custom theme context."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            result_path = await content_manager.generate_article_page(
                sample_article, output_dir, "custom-theme"
            )

            assert result_path is not None
            assert result_path.exists()

            # Check that theme was passed to template context
            content = result_path.read_text()
            assert "Test Article" in content
