"""
Advanced model tests

Tests for complex models and interactions.
Focused on metadata models and business logic.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from models import ArticleMetadata, MarkdownFile, SiteManifest, SiteMetrics, SiteStatus
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))


class TestMarkdownFile:
    """Test MarkdownFile model validation."""

    def test_valid_markdown_file(self):
        """Test valid markdown file metadata."""
        test_time = datetime.now(timezone.utc)

        file_meta = MarkdownFile(
            filename="test-article.md",
            title="Test Article",
            slug="test-article",
            word_count=500,
            generated_at=test_time,
            source_article_id="article_123",
        )

        assert file_meta.filename == "test-article.md"
        assert file_meta.title == "Test Article"
        assert file_meta.slug == "test-article"
        assert file_meta.word_count == 500
        assert file_meta.generated_at == test_time
        assert file_meta.source_article_id == "article_123"

    def test_required_fields(self):
        """Test that all fields are required."""
        with pytest.raises(ValidationError):
            MarkdownFile()

        with pytest.raises(ValidationError):
            MarkdownFile(filename="test.md")


class TestSiteMetrics:
    """Test SiteMetrics model validation."""

    def test_valid_metrics(self):
        """Test valid site metrics."""
        test_time = datetime.now(timezone.utc)

        metrics = SiteMetrics(
            total_articles=100,
            total_pages=25,
            total_size_bytes=1024000,
            last_build_time=15.5,
            build_timestamp=test_time,
        )

        assert metrics.total_articles == 100
        assert metrics.total_pages == 25
        assert metrics.total_size_bytes == 1024000
        assert metrics.last_build_time == 15.5
        assert metrics.build_timestamp == test_time


class TestSiteStatus:
    """Test SiteStatus model validation."""

    def test_minimal_status(self):
        """Test minimal valid status."""
        status = SiteStatus(
            generator_id="gen_123",
            status="idle",
            current_theme="minimal",
            markdown_files_count=50,
        )

        assert status.generator_id == "gen_123"
        assert status.status == "idle"
        assert status.current_theme == "minimal"
        assert status.markdown_files_count == 50
        assert status.site_metrics is None
        assert status.last_generation is None
        assert status.error_message is None

    def test_complete_status(self):
        """Test status with all optional fields."""
        test_time = datetime.now(timezone.utc)
        test_metrics = SiteMetrics(
            total_articles=75,
            total_pages=20,
            total_size_bytes=512000,
            last_build_time=8.2,
            build_timestamp=test_time,
        )

        status = SiteStatus(
            generator_id="gen_456",
            status="generating",
            current_theme="modern",
            markdown_files_count=75,
            site_metrics=test_metrics,
            last_generation=test_time,
            error_message=None,
        )

        assert status.site_metrics == test_metrics
        assert status.last_generation == test_time

    def test_error_status(self):
        """Test status with error message."""
        status = SiteStatus(
            generator_id="gen_error",
            status="error",
            current_theme="minimal",
            markdown_files_count=0,
            error_message="Connection failed",
        )

        assert status.status == "error"
        assert status.error_message == "Connection failed"


class TestArticleMetadata:
    """Test ArticleMetadata model validation."""

    def test_valid_article_metadata(self):
        """Test valid article metadata creation."""
        test_time = datetime.now(timezone.utc)

        article = ArticleMetadata(
            topic_id="topic_123",
            title="Sample Article",
            slug="sample-article",
            word_count=750,
            quality_score=0.85,
            cost=0.0012,
            source="reddit",
            original_url="https://example.com/article",
            generated_at=test_time,
            content="This is the article content.",
        )

        assert article.topic_id == "topic_123"
        assert article.title == "Sample Article"
        assert article.slug == "sample-article"
        assert article.word_count == 750
        assert article.quality_score == 0.85
        assert article.cost == 0.0012
        assert article.source == "reddit"
        assert article.original_url == "https://example.com/article"
        assert article.generated_at == test_time
        assert article.content == "This is the article content."

    def test_all_fields_required(self):
        """Test that all ArticleMetadata fields are required."""
        with pytest.raises(ValidationError):
            ArticleMetadata()

        with pytest.raises(ValidationError):
            ArticleMetadata(topic_id="test", title="Test")


class TestSiteManifest:
    """Test SiteManifest model validation."""

    def test_minimal_manifest(self):
        """Test minimal valid manifest."""
        test_time = datetime.now(timezone.utc)

        manifest = SiteManifest(
            site_id="site_123",
            version="1.0.0",
            build_timestamp=test_time,
            theme="minimal",
            total_files=10,
            articles=[],
            index_pages=["index.html"],
            static_assets=["style.css"],
        )

        assert manifest.site_id == "site_123"
        assert manifest.version == "1.0.0"
        assert manifest.build_timestamp == test_time
        assert manifest.theme == "minimal"
        assert manifest.total_files == 10
        assert manifest.articles == []
        assert manifest.index_pages == ["index.html"]
        assert manifest.static_assets == ["style.css"]
        assert manifest.deployment_url is None

    def test_complete_manifest(self):
        """Test manifest with all fields populated."""
        test_time = datetime.now(timezone.utc)

        article = ArticleMetadata(
            topic_id="topic_1",
            title="Test Article",
            slug="test-article",
            word_count=500,
            quality_score=0.9,
            cost=0.001,
            source="test",
            original_url="https://test.com",
            generated_at=test_time,
            content="Test content",
        )

        manifest = SiteManifest(
            site_id="site_complete",
            version="2.0.0",
            build_timestamp=test_time,
            theme="modern",
            total_files=25,
            articles=[article],
            index_pages=["index.html", "archive.html"],
            static_assets=["style.css", "script.js", "logo.png"],
            deployment_url="https://example.com",
        )

        assert len(manifest.articles) == 1
        assert manifest.articles[0] == article
        assert len(manifest.index_pages) == 2
        assert len(manifest.static_assets) == 3
        assert manifest.deployment_url == "https://example.com"
