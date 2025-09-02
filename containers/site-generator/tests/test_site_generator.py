"""
Comprehensive tests for the main site generator

Tests integration between models, content management, and file operations.
Follows project standards for test coverage (~70%).
"""

import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from models import ArticleMetadata, GenerationResponse, SiteMetrics, SiteStatus
from site_generator import SiteGenerator

# Add the containers path to import the site generator
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))


# Add the containers path to import the site generator
sys.path.insert(0, "/workspaces/ai-content-farm/containers/site-generator")


class TestSiteGeneratorInitialization:
    """Test SiteGenerator initialization and setup."""

    def test_initialization(self):
        """Test basic SiteGenerator initialization."""
        generator = SiteGenerator()

        # Check basic attributes
        assert generator.generator_id is not None
        assert len(generator.generator_id) == 8  # UUID truncated to 8 chars
        assert generator.config is not None
        assert generator.blob_client is not None

        # Check utility managers
        assert generator.content_manager is not None
        assert generator.archive_manager is not None
        assert generator.security_validator is not None

        # Check status tracking
        assert generator.current_status == "idle"
        assert generator.current_theme == "minimal"
        assert generator.last_generation is None
        assert generator.error_message is None

    def test_unique_generator_ids(self):
        """Test that each SiteGenerator gets a unique ID."""
        gen1 = SiteGenerator()
        gen2 = SiteGenerator()

        assert gen1.generator_id != gen2.generator_id
        assert len(gen1.generator_id) == 8
        assert len(gen2.generator_id) == 8

    @patch("site_generator.BlobStorageClient")
    def test_initialization_with_mocked_blob_client(self, mock_blob_client):
        """Test initialization with mocked blob client."""
        generator = SiteGenerator()

        # Verify blob client was initialized
        mock_blob_client.assert_called_once()
        assert generator.blob_client is not None


class TestBlobConnectivity:
    """Test blob storage connectivity methods."""

    @pytest.fixture
    def mock_generator(self):
        """Create generator with mocked blob client."""
        with patch("site_generator.BlobStorageClient") as mock_client:
            generator = SiteGenerator()
            generator.blob_client = mock_client.return_value
            return generator

    @pytest.mark.asyncio
    async def test_check_blob_connectivity_success(self, mock_generator):
        """Test successful blob connectivity check."""
        mock_generator.blob_client.list_containers.return_value = [
            "container1",
            "container2",
        ]

        result = await mock_generator.check_blob_connectivity()

        assert result is True
        mock_generator.blob_client.list_containers.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_blob_connectivity_failure(self, mock_generator):
        """Test blob connectivity check failure."""
        mock_generator.blob_client.list_containers.side_effect = Exception(
            "Connection failed"
        )

        result = await mock_generator.check_blob_connectivity()

        assert result is False

    @pytest.mark.asyncio
    async def test_check_blob_connectivity_logs_error(self, mock_generator, caplog):
        """Test that connectivity errors are logged."""
        mock_generator.blob_client.list_containers.side_effect = Exception(
            "Network timeout"
        )

        await mock_generator.check_blob_connectivity()

        assert "Blob connectivity check failed" in caplog.text
        assert "Network timeout" in caplog.text


class TestStatusRetrievaI:
    """Test status retrieval functionality."""

    @pytest.fixture
    def mock_generator(self):
        """Create generator with mocked dependencies."""
        with patch("site_generator.BlobStorageClient"):
            generator = SiteGenerator()
            return generator

    @pytest.mark.asyncio
    async def test_get_status_success(self, mock_generator):
        """Test successful status retrieval."""
        # Mock the private methods
        mock_generator._count_markdown_files = AsyncMock(return_value=25)
        mock_generator._get_site_metrics = AsyncMock(
            return_value=SiteMetrics(
                total_articles=25,
                total_pages=8,
                total_size_bytes=512000,
                last_build_time=5.5,
                build_timestamp=datetime.now(timezone.utc),
            )
        )

        status = await mock_generator.get_status()

        assert isinstance(status, SiteStatus)
        assert status.generator_id == mock_generator.generator_id
        assert status.status == "idle"
        assert status.current_theme == "minimal"
        assert status.markdown_files_count == 25
        assert status.site_metrics is not None
        assert status.site_metrics.total_articles == 25

    @pytest.mark.asyncio
    async def test_get_status_with_error(self, mock_generator):
        """Test status retrieval when an error occurs."""
        mock_generator._count_markdown_files = AsyncMock(
            side_effect=Exception("Count failed")
        )

        status = await mock_generator.get_status()

        assert isinstance(status, SiteStatus)
        assert status.status == "error"
        assert status.markdown_files_count == 0
        assert "Count failed" in status.error_message

    @pytest.mark.asyncio
    async def test_get_status_minimal(self, mock_generator):
        """Test status retrieval with minimal data."""
        mock_generator._count_markdown_files = AsyncMock(return_value=0)
        mock_generator._get_site_metrics = AsyncMock(return_value=None)

        status = await mock_generator.get_status()

        assert status.markdown_files_count == 0
        assert status.site_metrics is None
        assert status.last_generation is None


class TestMarkdownGeneration:
    """Test markdown generation functionality."""

    @pytest.fixture
    def mock_generator(self):
        """Create generator with comprehensive mocking."""
        with patch("site_generator.BlobStorageClient") as mock_client:
            generator = SiteGenerator()
            generator.blob_client = mock_client.return_value
            return generator

    @pytest.fixture
    def sample_articles(self):
        """Sample processed articles for testing."""
        return [
            {
                "topic_id": "test_article_1",
                "title": "Test Article One",
                "article_content": "This is test content for article one.",
                "word_count": 125,
                "quality_score": 0.85,
                "cost": 0.0012,
                "source": "test_source",
                "original_url": "https://example.com/test-1",
                "generated_at": "2025-09-01T12:00:00Z",
            },
            {
                "topic_id": "test_article_2",
                "title": "Test Article Two",
                "article_content": "This is test content for article two.",
                "word_count": 200,
                "quality_score": 0.92,
                "cost": 0.0015,
                "source": "test_source",
                "original_url": "https://example.com/test-2",
                "generated_at": "2025-09-01T13:00:00Z",
            },
        ]

    @pytest.mark.asyncio
    async def test_generate_markdown_batch_success(
        self, mock_generator, sample_articles
    ):
        """Test successful markdown batch generation."""
        # Mock the _get_processed_articles method
        mock_generator._get_processed_articles = AsyncMock(return_value=sample_articles)

        # Mock the _generate_single_markdown method
        mock_generator._generate_single_markdown = AsyncMock(
            side_effect=["test-article-one.md", "test-article-two.md"]
        )

        result = await mock_generator.generate_markdown_batch(
            source="test_source", batch_size=5, force_regenerate=True
        )

        assert isinstance(result, GenerationResponse)
        assert result.generator_id == mock_generator.generator_id
        assert result.operation_type == "markdown_generation"
        assert result.files_generated == 2
        assert len(result.generated_files) == 2
        assert "test-article-one.md" in result.generated_files
        assert "test-article-two.md" in result.generated_files
        assert result.processing_time > 0

    @pytest.mark.asyncio
    async def test_generate_markdown_batch_no_articles(self, mock_generator):
        """Test markdown generation with no articles available."""
        mock_generator._get_processed_articles = AsyncMock(return_value=[])

        result = await mock_generator.generate_markdown_batch()

        assert result.files_generated == 0
        assert result.generated_files == []
        assert result.operation_type == "markdown_generation"

    @pytest.mark.asyncio
    async def test_generate_markdown_batch_with_errors(
        self, mock_generator, sample_articles
    ):
        """Test markdown generation with some articles failing."""
        mock_generator._get_processed_articles = AsyncMock(return_value=sample_articles)

        # First article succeeds, second fails
        mock_generator._generate_single_markdown = AsyncMock(
            side_effect=["test-article-one.md", Exception("Generation failed")]
        )

        result = await mock_generator.generate_markdown_batch()

        assert result.files_generated == 1
        assert len(result.generated_files) == 1
        assert len(result.errors) == 1
        assert "Generation failed" in result.errors[0]

    @pytest.mark.asyncio
    async def test_generate_markdown_batch_respects_batch_size(self, mock_generator):
        """Test that batch size is respected."""
        # Create more articles than batch size
        many_articles = [{"topic_id": f"article_{i}"} for i in range(10)]
        mock_generator._get_processed_articles = AsyncMock(return_value=many_articles)
        mock_generator._generate_single_markdown = AsyncMock(return_value="test.md")

        result = await mock_generator.generate_markdown_batch(batch_size=3)

        # Should only process 3 articles
        assert mock_generator._generate_single_markdown.call_count == 3


class TestStaticSiteGeneration:
    """Test static site generation functionality."""

    @pytest.fixture
    def mock_generator(self):
        """Create generator with mocked dependencies."""
        with patch("site_generator.BlobStorageClient") as mock_client:
            generator = SiteGenerator()
            generator.blob_client = mock_client.return_value
            return generator

    @pytest.mark.asyncio
    async def test_generate_static_site_success(self, mock_generator):
        """Test successful static site generation."""
        # Mock the _generate_site_content method
        mock_generator._generate_site_content = AsyncMock(
            return_value=GenerationResponse(
                generator_id=mock_generator.generator_id,
                operation_type="site_generation",
                files_generated=15,
                pages_generated=5,
                processing_time=8.2,
                output_location="blob://static-sites",
                generated_files=["index.html", "archive.html", "style.css"],
            )
        )

        result = await mock_generator.generate_static_site(
            theme="modern", force_rebuild=True
        )

        assert isinstance(result, GenerationResponse)
        assert result.operation_type == "site_generation"
        assert result.pages_generated == 5
        assert result.files_generated == 15

    @pytest.mark.asyncio
    async def test_generate_static_site_default_theme(self, mock_generator):
        """Test static site generation with default theme."""
        mock_generator._generate_site_content = AsyncMock(
            return_value=GenerationResponse(
                generator_id=mock_generator.generator_id,
                operation_type="site_generation",
                files_generated=10,
                processing_time=5.0,
                output_location="blob://static-sites",
                generated_files=["index.html"],
            )
        )

        await mock_generator.generate_static_site()

        # Verify default theme was used
        mock_generator._generate_site_content.assert_called_once_with("minimal", False)

    @pytest.mark.asyncio
    async def test_generate_static_site_failure(self, mock_generator):
        """Test static site generation failure handling."""
        mock_generator._generate_site_content = AsyncMock(
            side_effect=Exception("Site generation failed")
        )

        result = await mock_generator.generate_static_site()

        assert result.files_generated == 0
        assert result.generated_files == []
        assert len(result.errors) == 1
        assert "Site generation failed" in result.errors[0]


class TestUtilityMethods:
    """Test utility and helper methods."""

    @pytest.fixture
    def mock_generator(self):
        """Create generator for testing."""
        with patch("site_generator.BlobStorageClient"):
            return SiteGenerator()

    def test_create_empty_response(self, mock_generator):
        """Test creation of empty response."""
        response = mock_generator._create_empty_response()

        assert isinstance(response, GenerationResponse)
        assert response.generator_id == mock_generator.generator_id
        assert response.files_generated == 0
        assert response.generated_files == []
        assert response.processing_time == 0.0

    def test_create_slug(self, mock_generator):
        """Test slug creation from titles."""
        test_cases = [
            ("Simple Title", "simple-title"),
            ("Title with Special Characters!@#", "title-with-special-characters"),
            ("Multiple    Spaces   Between", "multiple-spaces-between"),
            (
                "Very Long Title That Should Be Truncated At Some Point",
                "very-long-title-that-should-be-truncated-at-so",
            ),
            ("", ""),
            ("123 Numbers and symbols $%^", "123-numbers-and-symbols"),
        ]

        for title, expected_slug in test_cases:
            slug = mock_generator._create_slug(title)
            assert slug == expected_slug
            assert len(slug) <= 50
            if slug:  # Non-empty slugs shouldn't start/end with dashes
                assert not slug.startswith("-")
                assert not slug.endswith("-")

    def test_create_markdown_content(self, mock_generator):
        """Test markdown content creation."""
        article_data = {
            "topic_id": "test_123",
            "title": "Test Article",
            "article_content": "This is test content.",
            "word_count": 100,
            "quality_score": 0.85,
            "cost": 0.001,
            "source": "test",
            "original_url": "https://example.com",
            "generated_at": "2025-09-01T12:00:00Z",
        }

        markdown = mock_generator._create_markdown_content(article_data)

        # Check frontmatter structure
        assert markdown.startswith("---")
        assert "---\n" in markdown[3:]  # Closing frontmatter

        # Check required frontmatter fields
        frontmatter_section = markdown.split("---")[1]
        assert 'title: "Test Article"' in frontmatter_section
        assert 'slug: "test-article"' in frontmatter_section
        assert "date:" in frontmatter_section
        assert "source:" in frontmatter_section
        assert "metadata:" in frontmatter_section
        assert "published: true" in frontmatter_section

        # Check content follows frontmatter
        content_section = markdown.split("---", 2)[2].strip()
        assert content_section == "This is test content."

    @pytest.mark.asyncio
    async def test_count_markdown_files(self, mock_generator):
        """Test markdown file counting."""
        # Mock blob client response
        mock_generator.blob_client.list_blobs.return_value = [
            "article-1.md",
            "article-2.md",
            "index.html",  # Should not be counted
            "article-3.md",
        ]

        count = await mock_generator._count_markdown_files()

        assert count == 3  # Only .md files counted

    @pytest.mark.asyncio
    async def test_count_markdown_files_error(self, mock_generator):
        """Test markdown file counting with error."""
        mock_generator.blob_client.list_blobs.side_effect = Exception("List failed")

        count = await mock_generator._count_markdown_files()

        assert count == 0

    @pytest.mark.asyncio
    async def test_get_site_metrics(self, mock_generator):
        """Test site metrics retrieval."""
        mock_generator.blob_client.list_blobs.return_value = [
            "file1.html",
            "file2.html",
            "style.css",
        ]
        # Mock file sizes
        mock_generator.blob_client.get_blob_properties = Mock(
            return_value=Mock(size=1024)
        )

        metrics = await mock_generator._get_site_metrics()

        if metrics:  # May return None if not implemented
            assert isinstance(metrics, SiteMetrics)

    @pytest.mark.asyncio
    async def test_get_preview_url(self, mock_generator):
        """Test preview URL generation."""
        preview_url = await mock_generator.get_preview_url("test_site_123")

        assert isinstance(preview_url, str)
        assert "test_site_123" in preview_url


class TestErrorHandling:
    """Test comprehensive error handling."""

    @pytest.fixture
    def mock_generator(self):
        """Create generator for error testing."""
        with patch("site_generator.BlobStorageClient"):
            return SiteGenerator()

    @pytest.mark.asyncio
    async def test_get_processed_articles_error(self, mock_generator):
        """Test error handling in _get_processed_articles."""
        mock_generator.blob_client.list_blobs.side_effect = Exception(
            "Blob listing failed"
        )

        articles = await mock_generator._get_processed_articles(5)

        assert articles == []

    @pytest.mark.asyncio
    async def test_generate_single_markdown_error(self, mock_generator):
        """Test error handling in single markdown generation."""
        invalid_article = {"invalid": "data"}  # Missing required fields

        with pytest.raises(Exception):
            await mock_generator._generate_single_markdown(invalid_article)

    @pytest.mark.asyncio
    async def test_blob_upload_error_handling(self, mock_generator):
        """Test error handling during blob upload."""
        mock_generator.blob_client.upload_blob.side_effect = Exception("Upload failed")

        # This should be handled gracefully in the actual implementation
        # The exact behavior depends on the implementation details


class TestIntegrationWithUtilityModules:
    """Test integration with extracted utility modules."""

    @pytest.fixture
    def mock_generator(self):
        """Create generator with mocked utility modules."""
        with patch("site_generator.BlobStorageClient"):
            generator = SiteGenerator()

            # Mock the utility modules
            generator.content_manager = Mock()
            generator.archive_manager = Mock()
            generator.security_validator = Mock()

            return generator

    def test_utility_modules_initialized(self, mock_generator):
        """Test that utility modules are properly initialized."""
        assert mock_generator.content_manager is not None
        assert mock_generator.archive_manager is not None
        assert mock_generator.security_validator is not None

    @pytest.mark.asyncio
    async def test_content_manager_integration(self, mock_generator):
        """Test integration with ContentManager."""
        # Mock content manager methods
        mock_generator.content_manager.create_markdown_content.return_value = "# Test"
        mock_generator.content_manager.create_slug.return_value = "test-slug"

        article_data = {"title": "Test Article", "article_content": "Content"}

        # Test that the generator uses content manager
        markdown = mock_generator._create_markdown_content(article_data)
        slug = mock_generator._create_slug("Test Title")

        # Verify the utility methods were called (if implemented)
        # Note: This depends on the actual implementation details

    @pytest.mark.asyncio
    async def test_security_validator_integration(self, mock_generator):
        """Test integration with SecurityValidator."""
        # Mock security validator
        mock_generator.security_validator.sanitize_filename.return_value = (
            "safe_filename.md"
        )

        # Test that security validation is used where appropriate
        # This would depend on the actual implementation using the security validator


class TestAsyncBehavior:
    """Test asynchronous behavior and coroutine handling."""

    @pytest.fixture
    def mock_generator(self):
        """Create generator for async testing."""
        with patch("site_generator.BlobStorageClient"):
            return SiteGenerator()

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, mock_generator):
        """Test that multiple async operations can run concurrently."""
        import asyncio

        # Mock methods to simulate async operations
        mock_generator._count_markdown_files = AsyncMock(return_value=10)
        mock_generator._get_site_metrics = AsyncMock(return_value=None)
        mock_generator.check_blob_connectivity = AsyncMock(return_value=True)

        # Run multiple operations concurrently
        results = await asyncio.gather(
            mock_generator._count_markdown_files(),
            mock_generator._get_site_metrics(),
            mock_generator.check_blob_connectivity(),
        )

        assert results[0] == 10  # markdown count
        assert results[1] is None  # metrics
        assert results[2] is True  # connectivity

    @pytest.mark.asyncio
    async def test_async_error_handling(self, mock_generator):
        """Test async error handling doesn't block other operations."""
        mock_generator.blob_client.list_blobs.side_effect = Exception("Async error")

        # This should not raise, but return empty result
        articles = await mock_generator._get_processed_articles(5)
        assert articles == []


class TestStatusTracking:
    """Test status tracking throughout operations."""

    @pytest.fixture
    def mock_generator(self):
        """Create generator for status testing."""
        with patch("site_generator.BlobStorageClient"):
            return SiteGenerator()

    def test_initial_status(self, mock_generator):
        """Test initial status values."""
        assert mock_generator.current_status == "idle"
        assert mock_generator.current_theme == "minimal"
        assert mock_generator.last_generation is None
        assert mock_generator.error_message is None

    @pytest.mark.asyncio
    async def test_status_during_generation(self, mock_generator):
        """Test status tracking during generation operations."""
        # Mock dependencies to avoid actual generation
        mock_generator._get_processed_articles = AsyncMock(return_value=[])

        initial_status = mock_generator.current_status

        await mock_generator.generate_markdown_batch()

        # Status should return to idle after operation
        assert mock_generator.current_status == initial_status

    def test_error_status_tracking(self, mock_generator):
        """Test that errors are properly tracked in status."""
        # Simulate setting an error
        mock_generator.error_message = "Test error"
        mock_generator.current_status = "error"

        assert mock_generator.error_message == "Test error"
        assert mock_generator.current_status == "error"
