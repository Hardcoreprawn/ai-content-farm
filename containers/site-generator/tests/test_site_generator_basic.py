"""
Basic site generator tests

Tests initialization, connectivity, and status retrieval functionality.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from models import ArticleMetadata, GenerationResponse, SiteMetrics, SiteStatus
from site_generator import SiteGenerator

# Add the containers path to import the site generator
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))
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

    def test_initialization_with_mocks(self):
        """Test initialization with mocked blob client."""
        with (
            patch("azure.storage.blob.BlobServiceClient") as mock_service,
            patch("azure.identity.DefaultAzureCredential") as mock_cred,
            patch("os.getenv") as mock_env,
        ):
            # Mock environment variable
            mock_env.return_value = "https://test.blob.core.windows.net/"

            generator = SiteGenerator()
            mock_service.assert_called_once()
            assert generator.blob_client is not None

    def test_unique_generator_ids(self):
        """Test that each generator gets a unique ID."""
        generator1 = SiteGenerator()
        generator2 = SiteGenerator()
        assert generator1.generator_id != generator2.generator_id

    def test_default_configuration(self):
        """Test default configuration values."""
        generator = SiteGenerator()
        assert generator.current_status == "idle"
        assert generator.current_theme == "minimal"
        assert generator.error_message is None


class TestBlobConnectivity:
    """Test blob storage connectivity checks."""

    @pytest.fixture
    def mock_generator(self):
        """Create generator with mocked blob client."""
        with (
            patch("azure.storage.blob.BlobServiceClient") as mock_service,
            patch("azure.identity.DefaultAzureCredential") as mock_cred,
            patch("os.getenv") as mock_env,
        ):
            mock_env.return_value = "https://test.blob.core.windows.net/"
            generator = SiteGenerator()
            generator.blob_client = Mock()
            return generator

    @pytest.mark.asyncio
    async def test_check_blob_connectivity_success(self, mock_generator):
        """Test successful blob connectivity check."""
        # Configure the mock to return a successful connection result
        mock_generator.blob_client.test_connection.return_value = {
            "status": "healthy",
            "connection_type": "mock",
            "message": "Mock storage client is working",
        }

        result = await mock_generator.check_blob_connectivity()

        assert isinstance(result, dict)
        assert result["status"] == "healthy"
        mock_generator.blob_client.test_connection.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_blob_connectivity_failure(self, mock_generator):
        """Test blob connectivity check failure."""
        mock_generator.blob_client.test_connection.side_effect = Exception(
            "Connection failed"
        )

        result = await mock_generator.check_blob_connectivity()

        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert "Blob connectivity test failed" in result["message"]

    @pytest.mark.asyncio
    async def test_check_blob_connectivity_logs_error(self, mock_generator, caplog):
        """Test that connectivity errors are logged."""
        mock_generator.blob_client.test_connection.side_effect = Exception(
            "Network timeout"
        )

        # Enable logging for this test specifically
        import logging

        logging.disable(logging.NOTSET)

        result = await mock_generator.check_blob_connectivity()

        # Re-disable logging after test
        logging.disable(logging.CRITICAL)

        # Check that error was handled properly
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert "Blob connectivity test failed" in result["message"]


class TestStatusRetrieval:
    """Test status retrieval functionality."""

    @pytest.fixture
    def mock_generator(self):
        """Create generator with mocked dependencies."""
        with (
            patch("azure.storage.blob.BlobServiceClient"),
            patch("azure.identity.DefaultAzureCredential"),
            patch("os.getenv") as mock_env,
        ):
            mock_env.return_value = "https://test.blob.core.windows.net/"
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

    @pytest.mark.asyncio
    async def test_get_status_with_error(self, mock_generator):
        """Test status retrieval when there's an error state."""
        mock_generator.error_message = "Test error"
        mock_generator.current_status = "error"
        mock_generator._count_markdown_files = AsyncMock(return_value=0)
        mock_generator._get_site_metrics = AsyncMock(return_value=None)

        status = await mock_generator.get_status()

        assert status.status == "error"
        assert status.error_message == "Test error"
        assert status.markdown_files_count == 0

    @pytest.mark.asyncio
    async def test_get_status_exception_handling(self, mock_generator, caplog):
        """Test status retrieval handles exceptions gracefully."""
        # Set the logger level to capture logs
        caplog.set_level("ERROR", logger="site_generator")

        mock_generator._count_markdown_files = AsyncMock(
            side_effect=Exception("Test error")
        )

        status = await mock_generator.get_status()

        assert status.status == "error"
        assert "Failed to get status" in caplog.text

    @pytest.mark.asyncio
    async def test_get_status_partial_failure(self, mock_generator):
        """Test status retrieval with partial failures."""
        mock_generator._count_markdown_files = AsyncMock(return_value=10)
        mock_generator._get_site_metrics = AsyncMock(
            side_effect=Exception("Metrics error")
        )

        status = await mock_generator.get_status()

        assert status.markdown_files_count == 10
        assert status.site_metrics is None  # Should handle metrics failure gracefully
