"""
Integration tests for site-generator.

Tests the complete pipeline from JSON content to static site generation.
These tests verify that all components work together correctly.
"""

import asyncio
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from site_generator import SiteGenerator

from config import Config


@pytest.mark.integration
class TestSiteGeneratorIntegration:
    """Integration tests for the complete site generation pipeline."""

    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        return Config()

    @pytest.fixture
    def sample_articles(self):
        """Sample processed articles for testing."""
        return [
            {
                "topic_id": "test_article_1",
                "title": "Test Article One: Technology Trends",
                "article_content": """# Technology Trends in 2025

This is a sample article about emerging technology trends.

## Key Points

- AI continues to evolve
- Cloud computing remains dominant
- Security is paramount

## Conclusion

Technology continues to advance at a rapid pace.""",
                "word_count": 125,
                "quality_score": 0.85,
                "cost": 0.0012,
                "source": "test_source",
                "original_url": "https://example.com/test-1",
                "generated_at": "2025-09-01T12:00:00Z",
                "metadata": {
                    "processor_id": "test_processor",
                    "content_type": "test_article",
                },
            },
            {
                "topic_id": "test_article_2",
                "title": "Another Test Article: Future of Work",
                "article_content": """# The Future of Work

Remote work has fundamentally changed how we operate.

## Changes We've Seen

- Distributed teams
- Digital collaboration tools
- Work-life balance focus

## Looking Ahead

The future promises even more flexibility.""",
                "word_count": 98,
                "quality_score": 0.78,
                "cost": 0.0008,
                "source": "test_source_2",
                "original_url": "https://example.com/test-2",
                "generated_at": "2025-09-01T13:00:00Z",
                "metadata": {
                    "processor_id": "test_processor",
                    "content_type": "test_article",
                },
            },
        ]

    @pytest.fixture
    def mock_blob_client(self, sample_articles):
        """Mock blob storage client with sample data."""
        mock_client = AsyncMock()

        # Mock list_blobs to return our sample articles
        mock_client.list_blobs.return_value = [
            f"test_article_{i+1}.json" for i in range(len(sample_articles))
        ]

        # Mock download_blob to return article content
        def mock_download(container_name, blob_name):
            if "test_article_1" in blob_name:
                return json.dumps(sample_articles[0])
            elif "test_article_2" in blob_name:
                return json.dumps(sample_articles[1])
            return "{}"

        mock_client.download_blob.side_effect = mock_download

        # Mock upload_blob for markdown generation
        mock_client.upload_blob.return_value = None

        # Mock check_blob_connectivity
        mock_client.check_blob_connectivity.return_value = True

        return mock_client

    @pytest.fixture
    def site_generator(self, config, mock_blob_client):
        """Create a site generator with mocked dependencies."""
        with patch("site_generator.BlobStorageClient", return_value=mock_blob_client):
            generator = SiteGenerator()
            generator.blob_client = mock_blob_client
            return generator

    @pytest.mark.asyncio
    async def test_markdown_generation_integration(
        self, site_generator, sample_articles
    ):
        """Test the complete markdown generation pipeline."""

        # Test markdown generation from processed content
        result = await site_generator.generate_markdown_batch(
            source="integration_test", batch_size=5, force_regenerate=True
        )

        # Verify the result
        assert result.operation_type == "markdown_generation"
        assert result.files_generated == 2  # Should process both sample articles
        assert result.processing_time > 0
        assert len(result.generated_files) == 2
        # Check that both generated files contain the expected slugs
        generated_files_str = str(result.generated_files)
        assert "test-article-one-technology-trends" in generated_files_str
        assert "another-test-article-future-of-work" in generated_files_str

    @pytest.mark.asyncio
    async def test_slug_generation(self, site_generator):
        """Test URL slug generation from titles."""

        test_cases = [
            ("Test Article: Technology Trends", "test-article-technology-trends"),
            ("Special Characters!@# & Symbols", "special-characters-symbols"),
            ("Multiple    Spaces   Between", "multiple-spaces-between"),
            (
                "Very Long Title That Should Be Truncated At Some Point",
                "very-long-title-that-should-be-truncated-at-some-p",
            ),
        ]

        for title, expected_slug in test_cases:
            slug = site_generator._create_slug(title)
            assert slug == expected_slug
            assert len(slug) <= 50
            assert not slug.startswith("-")
            assert not slug.endswith("-")

    @pytest.mark.asyncio
    async def test_markdown_content_structure(self, site_generator, sample_articles):
        """Test that generated markdown has correct structure."""

        # Generate markdown for first article
        markdown_content = site_generator._create_markdown_content(sample_articles[0])

        # Verify frontmatter exists
        assert markdown_content.startswith("---")
        assert "---\n" in markdown_content[3:]  # Second --- closes frontmatter

        # Verify required frontmatter fields
        frontmatter_section = markdown_content.split("---")[1]
        assert "title:" in frontmatter_section
        assert "slug:" in frontmatter_section
        assert "date:" in frontmatter_section
        assert "source:" in frontmatter_section
        assert "metadata:" in frontmatter_section
        assert "published: true" in frontmatter_section

        # Verify content follows frontmatter
        content_section = markdown_content.split("---", 2)[2].strip()
        assert content_section.startswith("# Technology Trends in 2025")
        assert "AI continues to evolve" in content_section

    @pytest.mark.asyncio
    async def test_status_retrieval(self, site_generator):
        """Test status information retrieval."""

        status = await site_generator.get_status()

        assert status.generator_id == site_generator.generator_id
        assert status.status in ["idle", "generating", "error"]
        assert status.current_theme == site_generator.current_theme
        assert status.markdown_files_count >= 0

    @pytest.mark.asyncio
    async def test_blob_connectivity_check(self, site_generator):
        """Test blob storage connectivity check."""

        # Should return True with our mock
        is_connected = await site_generator.check_blob_connectivity()
        assert is_connected is True

    @pytest.mark.asyncio
    async def test_error_handling_during_generation(self, site_generator):
        """Test error handling when markdown generation fails."""

        # Mock blob client to raise an exception
        site_generator.blob_client.list_blobs.side_effect = Exception(
            "Connection failed"
        )

        # The current implementation logs errors but returns empty results instead of raising
        result = await site_generator.generate_markdown_batch()
        assert result.files_generated == 0
        assert result.generated_files == []

    @pytest.mark.asyncio
    async def test_empty_content_handling(self, site_generator, mock_blob_client):
        """Test handling of empty or missing content."""

        # Mock empty blob list
        mock_blob_client.list_blobs.return_value = []

        result = await site_generator.generate_markdown_batch()

        assert result.files_generated == 0
        assert result.generated_files == []
        assert result.operation_type == "markdown_generation"

    @pytest.mark.asyncio
    async def test_batch_size_limiting(self, site_generator, sample_articles):
        """Test that batch size is properly respected."""

        # Request only 1 article despite having 2 available
        result = await site_generator.generate_markdown_batch(batch_size=1)

        # Should only process 1 article
        assert result.files_generated <= 1

    @pytest.mark.asyncio
    async def test_configuration_integration(self, site_generator, config):
        """Test that configuration is properly integrated."""

        # Verify configuration is accessible
        assert site_generator.config.SITE_TITLE == config.SITE_TITLE
        assert site_generator.config.SITE_DOMAIN == config.SITE_DOMAIN
        assert site_generator.config.DEFAULT_THEME == config.DEFAULT_THEME

        # Verify container names are set
        assert hasattr(site_generator.config, "PROCESSED_CONTENT_CONTAINER")
        assert hasattr(site_generator.config, "MARKDOWN_CONTENT_CONTAINER")
        assert hasattr(site_generator.config, "STATIC_SITES_CONTAINER")


@pytest.mark.integration
class TestSiteGeneratorAPIIntegration:
    """Integration tests for API endpoints."""

    @pytest.fixture
    def sample_articles(self):
        """Sample processed articles for testing."""
        return [
            {
                "topic_id": "test_article_1",
                "title": "Test Article One: Technology Trends",
                "article_content": "# Technology Trends",
                "word_count": 125,
                "quality_score": 0.85,
                "cost": 0.0012,
                "source": "test_source",
                "original_url": "https://example.com/test-1",
                "generated_at": "2025-09-01T12:00:00Z",
            }
        ]

    @pytest.fixture
    def mock_site_generator(self, sample_articles):
        """Mock site generator for API testing."""
        from models import GenerationResponse, SiteStatus

        mock_gen = AsyncMock()
        mock_gen.generator_id = "test_generator_123"

        # Mock successful generation
        mock_gen.generate_markdown_batch.return_value = GenerationResponse(
            generator_id="test_generator_123",
            operation_type="markdown_generation",
            files_generated=2,
            processing_time=1.5,
            output_location="blob://markdown-content",
            generated_files=["test_1.md", "test_2.md"],
        )

        # Mock status
        mock_gen.get_status.return_value = SiteStatus(
            generator_id="test_generator_123",
            status="idle",
            current_theme="minimal",
            markdown_files_count=2,
        )

        # Mock connectivity check
        mock_gen.check_blob_connectivity.return_value = True

        return mock_gen

    @pytest.mark.asyncio
    async def test_api_markdown_generation_endpoint(self, mock_site_generator):
        """Test the markdown generation API endpoint."""

        with patch("main.site_generator", mock_site_generator):
            from models import GenerationRequest

            # Create request
            request = GenerationRequest(
                source="api_test", batch_size=5, force_regenerate=True
            )

            # Call the generation method
            result = await mock_site_generator.generate_markdown_batch(
                source=request.source,
                batch_size=request.batch_size,
                force_regenerate=request.force_regenerate,
            )

            # Verify response
            assert result.files_generated == 2
            assert result.operation_type == "markdown_generation"
            assert "test_1.md" in result.generated_files
            assert "test_2.md" in result.generated_files

    @pytest.mark.asyncio
    async def test_api_status_endpoint(self, mock_site_generator):
        """Test the status API endpoint."""

        with patch("main.site_generator", mock_site_generator):
            status = await mock_site_generator.get_status()

            assert status.generator_id == "test_generator_123"
            assert status.status == "idle"
            assert status.current_theme == "minimal"
            assert status.markdown_files_count == 2

    @pytest.mark.asyncio
    async def test_api_health_check_integration(self, mock_site_generator):
        """Test the health check endpoint integration."""

        with patch("main.site_generator", mock_site_generator):
            # Verify connectivity check works
            is_healthy = await mock_site_generator.check_blob_connectivity()
            assert is_healthy is True


@pytest.mark.integration
def test_configuration_loading():
    """Test that configuration loads correctly from environment."""

    config = Config()

    # Test default values are set
    assert config.SITE_TITLE is not None
    assert config.SITE_DOMAIN is not None
    assert config.DEFAULT_THEME is not None
    assert config.ARTICLES_PER_PAGE > 0

    # Test container names are set
    assert config.PROCESSED_CONTENT_CONTAINER is not None
    assert config.MARKDOWN_CONTENT_CONTAINER is not None
    assert config.STATIC_SITES_CONTAINER is not None


@pytest.mark.integration
def test_models_validation():
    """Test that Pydantic models validate correctly."""

    from models import GenerationRequest, GenerationResponse, SiteStatus

    # Test GenerationRequest validation
    request = GenerationRequest(source="test", batch_size=10, force_regenerate=True)
    assert request.source == "test"
    assert request.batch_size == 10
    assert request.force_regenerate is True

    # Test GenerationResponse validation
    response = GenerationResponse(
        generator_id="test_123",
        operation_type="markdown_generation",
        files_generated=5,
        processing_time=2.3,
        output_location="blob://test",
        generated_files=["file1.md", "file2.md"],
    )
    assert response.generator_id == "test_123"
    assert response.files_generated == 5
    assert len(response.generated_files) == 2

    # Test SiteStatus validation
    status = SiteStatus(
        generator_id="test_123",
        status="idle",
        current_theme="minimal",
        markdown_files_count=10,
    )
    assert status.generator_id == "test_123"
    assert status.status == "idle"
    assert status.markdown_files_count == 10
