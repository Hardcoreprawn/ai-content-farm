"""
Comprehensive tests for model definitions

Tests data model validation, creation, and business logic.
Follows project standards for test coverage (~70%).
"""

# Add the containers path to import the models
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import pytest
from models import (
    ArticleMetadata,
    GenerationRequest,
    GenerationResponse,
    MarkdownFile,
    SiteManifest,
    SiteMetrics,
    SiteStatus,
)
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))


# Add the containers path to import the models
sys.path.insert(0, "/workspaces/ai-content-farm/containers/site-generator")


class TestGenerationRequest:
    """Test GenerationRequest model validation."""

    def test_default_values(self):
        """Test default field values."""
        request = GenerationRequest()

        assert request.source == "manual"
        assert request.batch_size == 10
        assert request.theme is None
        assert request.force_regenerate is False

    def test_valid_request(self):
        """Test valid request creation."""
        request = GenerationRequest(
            source="test_source", batch_size=5, theme="minimal", force_regenerate=True
        )

        assert request.source == "test_source"
        assert request.batch_size == 5
        assert request.theme == "minimal"
        assert request.force_regenerate is True

    def test_batch_size_validation(self):
        """Test batch size constraints."""
        # Valid batch sizes
        GenerationRequest(batch_size=1)
        GenerationRequest(batch_size=50)
        GenerationRequest(batch_size=100)

        # Invalid batch sizes
        with pytest.raises(ValidationError):
            GenerationRequest(batch_size=0)

        with pytest.raises(ValidationError):
            GenerationRequest(batch_size=101)

        with pytest.raises(ValidationError):
            GenerationRequest(batch_size=-1)

    def test_serialization(self):
        """Test model serialization."""
        request = GenerationRequest(
            source="api_test", batch_size=25, theme="modern", force_regenerate=True
        )

        data = request.model_dump()
        assert data["source"] == "api_test"
        assert data["batch_size"] == 25
        assert data["theme"] == "modern"
        assert data["force_regenerate"] is True


class TestGenerationResponse:
    """Test GenerationResponse model validation."""

    def test_required_fields(self):
        """Test required field validation."""
        # Missing required fields should raise ValidationError
        with pytest.raises(ValidationError):
            GenerationResponse()

        # Valid creation with all required fields
        response = GenerationResponse(
            generator_id="test_123",
            operation_type="markdown_generation",
            files_generated=5,
            processing_time=2.5,
            output_location="blob://test",
            generated_files=["file1.md", "file2.md"],
        )

        assert response.generator_id == "test_123"
        assert response.operation_type == "markdown_generation"
        assert response.files_generated == 5
        assert response.processing_time == 2.5
        assert response.output_location == "blob://test"
        assert len(response.generated_files) == 2
        assert response.errors == []

    def test_optional_fields(self):
        """Test optional field handling."""
        response = GenerationResponse(
            generator_id="test_456",
            operation_type="site_generation",
            files_generated=0,
            pages_generated=10,
            processing_time=5.2,
            output_location="blob://static",
            generated_files=[],
            errors=["warning: missing theme"],
        )

        assert response.pages_generated == 10
        assert response.errors == ["warning: missing theme"]

    def test_default_values(self):
        """Test default values for optional fields."""
        response = GenerationResponse(
            generator_id="test_789",
            operation_type="test",
            files_generated=1,
            processing_time=0.5,
            output_location="test://location",
            generated_files=["test.md"],
        )

        assert response.pages_generated is None
        assert response.errors == []


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


class TestModelInteroperability:
    """Test how models work together."""

    def test_site_status_with_metrics(self):
        """Test SiteStatus containing SiteMetrics."""
        test_time = datetime.now(timezone.utc)

        metrics = SiteMetrics(
            total_articles=50,
            total_pages=15,
            total_size_bytes=256000,
            last_build_time=5.0,
            build_timestamp=test_time,
        )

        status = SiteStatus(
            generator_id="gen_test",
            status="idle",
            current_theme="minimal",
            markdown_files_count=50,
            site_metrics=metrics,
        )

        # Verify nested model access
        assert status.site_metrics.total_articles == 50
        assert status.site_metrics.last_build_time == 5.0

    def test_manifest_with_articles(self):
        """Test SiteManifest containing ArticleMetadata."""
        test_time = datetime.now(timezone.utc)

        articles = [
            ArticleMetadata(
                topic_id=f"topic_{i}",
                title=f"Article {i}",
                slug=f"article-{i}",
                word_count=300 + i * 50,
                quality_score=0.8 + i * 0.05,
                cost=0.001 + i * 0.0001,
                source="test",
                original_url=f"https://test.com/{i}",
                generated_at=test_time,
                content=f"Content for article {i}",
            )
            for i in range(3)
        ]

        manifest = SiteManifest(
            site_id="multi_article_site",
            version="1.0.0",
            build_timestamp=test_time,
            theme="minimal",
            total_files=len(articles) + 5,
            articles=articles,
            index_pages=["index.html"],
            static_assets=["style.css"],
        )

        assert len(manifest.articles) == 3
        assert manifest.articles[0].title == "Article 0"
        assert manifest.articles[2].word_count == 400
        assert manifest.total_files == 8

    def test_response_with_file_list(self):
        """Test GenerationResponse with generated files."""
        generated_files = ["article-1.md", "article-2.md", "index.html", "archive.html"]

        response = GenerationResponse(
            generator_id="test_gen",
            operation_type="site_generation",
            files_generated=len(generated_files),
            processing_time=10.5,
            output_location="blob://static-sites/test",
            generated_files=generated_files,
        )

        assert len(response.generated_files) == 4
        assert "article-1.md" in response.generated_files
        assert "index.html" in response.generated_files
        assert response.files_generated == len(generated_files)
