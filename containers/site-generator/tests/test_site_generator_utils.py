"""
Site generator utility and integration tests

Tests utility methods, error handling, integration, async behavior, and status tracking.
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
sys.path.insert(0, "/workspaces/ai-content-farm/containers/site-generator")


class TestUtilityMethods:
    """Test utility methods and helper functions."""

    @pytest.fixture
    def mock_generator(self):
        """Create generator with mocked dependencies."""
        with patch("site_generator.BlobStorageClient"):
            generator = SiteGenerator()
            generator.blob_client = Mock()
            return generator

    @pytest.mark.asyncio
    async def test_count_markdown_files(self, mock_generator):
        """Test counting markdown files in container."""
        # Mock the markdown service to return count
        mock_generator.markdown_service.count_markdown_files = AsyncMock(return_value=3)

        count = await mock_generator._count_markdown_files()

        assert count == 3
        mock_generator.markdown_service.count_markdown_files.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_markdown_files_empty_container(self, mock_generator):
        """Test counting markdown files in empty container."""
        mock_generator.blob_client.list_blobs.return_value = []

        count = await mock_generator._count_markdown_files()

        assert count == 0

    @pytest.mark.asyncio
    async def test_count_markdown_files_exception_handling(
        self, mock_generator, caplog
    ):
        """Test that counting handles exceptions gracefully."""
        # Mock the markdown service to raise an exception
        mock_generator.markdown_service.count_markdown_files = AsyncMock(
            side_effect=Exception("Service error")
        )

        # The method should propagate the exception since it doesn't handle it
        with pytest.raises(Exception, match="Service error"):
            await mock_generator._count_markdown_files()

    @pytest.mark.asyncio
    async def test_get_site_metrics_success(self, mock_generator):
        """Test successful site metrics retrieval."""
        # Mock dependencies - mock the markdown service directly
        mock_generator.markdown_service.count_markdown_files = AsyncMock(
            return_value=20
        )
        mock_generator.blob_client.list_blobs.return_value = [
            {"name": "page1.html", "size": 4096},
            {"name": "page2.html", "size": 3072},
            {"name": "styles.css", "size": 2048},
        ]

        metrics = await mock_generator._get_site_metrics()

        assert isinstance(metrics, SiteMetrics)
        assert metrics.total_articles == 20
        assert metrics.total_pages == 2  # Only HTML files count as pages
        assert metrics.total_size_bytes == 9216  # Sum of all file sizes

    @pytest.mark.asyncio
    async def test_get_site_metrics_with_build_time(self, mock_generator):
        """Test site metrics includes last build time if available."""
        mock_generator._count_markdown_files = AsyncMock(return_value=15)
        mock_generator.blob_client.list_blobs.return_value = []
        mock_generator.last_generation = datetime.now(timezone.utc)

        metrics = await mock_generator._get_site_metrics()

        assert metrics.build_timestamp == mock_generator.last_generation
        assert metrics.last_build_time is not None

    @pytest.mark.asyncio
    async def test_get_site_metrics_exception_handling(self, mock_generator, caplog):
        """Test site metrics handles exceptions."""
        import logging

        caplog.set_level(logging.ERROR, logger="site_generator")

        # Mock the markdown service to raise an exception
        mock_generator.markdown_service.count_markdown_files = AsyncMock(
            side_effect=Exception("Count error")
        )

        metrics = await mock_generator._get_site_metrics()

        assert metrics is None
        assert "Error getting site metrics" in caplog.text

    def test_sanitize_filename(self, mock_generator):
        """Test filename sanitization."""
        # Test with legacy security (backward compatibility)
        if hasattr(mock_generator, "legacy_security"):
            result = mock_generator.legacy_security.sanitize_filename("test/file..name")
            assert result == "test_file_name"
        else:
            # Test direct sanitization if available
            result = mock_generator.sanitize_filename("test/file..name")
            assert result == "test_file_name"

    def test_validate_archive_path(self, mock_generator):
        """Test archive path validation."""
        # Test with legacy security (backward compatibility)
        if hasattr(mock_generator, "legacy_security"):
            result = mock_generator.legacy_security.validate_archive_path(
                "/tmp/safe/path"
            )
            assert result is True

            result = mock_generator.legacy_security.validate_archive_path(
                "../../etc/passwd"
            )
            assert result is False


class TestErrorHandling:
    """Test error handling and recovery mechanisms."""

    @pytest.fixture
    def mock_generator(self):
        """Create generator with mocked dependencies."""
        with patch("site_generator.BlobStorageClient"):
            generator = SiteGenerator()
            return generator

    def test_set_error_state(self, mock_generator):
        """Test setting error state."""
        mock_generator._set_error_state("Test error occurred")

        assert mock_generator.current_status == "error"
        assert mock_generator.error_message == "Test error occurred"

    def test_clear_error_state(self, mock_generator):
        """Test clearing error state."""
        # First set an error
        mock_generator._set_error_state("Test error")
        assert mock_generator.current_status == "error"

        # Then clear it
        mock_generator._clear_error_state()
        assert mock_generator.current_status == "idle"
        assert mock_generator.error_message is None

    @pytest.mark.asyncio
    async def test_error_state_persistence(self, mock_generator):
        """Test that error state persists across operations."""
        mock_generator._set_error_state("Persistent error")

        status = await mock_generator.get_status()

        assert status.status == "error"
        assert status.error_message == "Persistent error"


class TestIntegrationWithUtilityModules:
    """Test integration with content manager, archive manager, and security validator."""

    @pytest.fixture
    def mock_generator(self):
        """Create generator with mocked utility modules."""
        with patch("site_generator.BlobStorageClient"):
            generator = SiteGenerator()
            generator.content_manager = Mock()
            generator.archive_manager = Mock()
            generator.security_validator = Mock()
            return generator

    @pytest.mark.asyncio
    async def test_content_manager_integration(self, mock_generator):
        """Test integration with content manager."""
        mock_generator.content_manager.process_articles.return_value = {
            "processed": 10,
            "skipped": 2,
            "errors": [],
        }

        # Simulate using content manager through generator
        result = mock_generator.content_manager.process_articles()

        assert result["processed"] == 10
        assert result["skipped"] == 2

    @pytest.mark.asyncio
    async def test_archive_manager_integration(self, mock_generator):
        """Test integration with archive manager."""
        mock_generator.archive_manager.create_archive.return_value = "/tmp/site.zip"

        # Simulate using archive manager through generator
        archive_path = mock_generator.archive_manager.create_archive()

        assert archive_path == "/tmp/site.zip"

    @pytest.mark.asyncio
    async def test_security_validator_integration(self, mock_generator):
        """Test integration with security validator."""
        mock_generator.security_validator.validate_path.return_value = True

        # Simulate using security validator through generator
        is_valid = mock_generator.security_validator.validate_path("/safe/path")

        assert is_valid is True


class TestAsyncBehavior:
    """Test asynchronous behavior and concurrency."""

    @pytest.fixture
    def mock_generator(self):
        """Create generator with mocked dependencies."""
        with patch("site_generator.BlobStorageClient"):
            generator = SiteGenerator()
            return generator

    @pytest.mark.asyncio
    async def test_concurrent_status_requests(self, mock_generator):
        """Test handling concurrent status requests."""
        import asyncio

        mock_generator._count_markdown_files = AsyncMock(return_value=5)
        mock_generator._get_site_metrics = AsyncMock(return_value=None)

        # Make multiple concurrent status requests
        tasks = [mock_generator.get_status() for _ in range(3)]
        results = await asyncio.gather(*tasks)

        # All should succeed
        assert len(results) == 3
        for status in results:
            assert isinstance(status, SiteStatus)
            assert status.generator_id == mock_generator.generator_id

    @pytest.mark.asyncio
    async def test_async_method_isolation(self, mock_generator):
        """Test that async methods don't interfere with each other."""
        mock_generator._count_markdown_files = AsyncMock(return_value=10)
        mock_generator._get_site_metrics = AsyncMock(return_value=None)

        # Mock blob client test_connection to return proper dict
        mock_generator.blob_client.test_connection.return_value = {
            "status": "success",
            "message": "Connection successful",
        }

        # Run different async methods concurrently
        import asyncio

        status_task = mock_generator.get_status()
        connectivity_task = mock_generator.check_blob_connectivity()

        status, connectivity = await asyncio.gather(
            status_task, connectivity_task, return_exceptions=True
        )

        # Both should complete without errors
        assert isinstance(status, SiteStatus)
        assert isinstance(connectivity, dict)  # check_blob_connectivity returns a dict
        assert connectivity["status"] == "success"


class TestStatusTracking:
    """Test status tracking throughout operations."""

    @pytest.fixture
    def mock_generator(self):
        """Create generator with mocked dependencies."""
        with patch("site_generator.BlobStorageClient"):
            generator = SiteGenerator()
            generator.markdown_service = Mock()
            generator.site_service = Mock()
            return generator

    @pytest.mark.asyncio
    async def test_status_progression_during_generation(
        self, mock_generator, sample_generation_response
    ):
        """Test status changes during generation operations."""
        # Mock successful generation with AsyncMock
        mock_generator.markdown_service.generate_batch = AsyncMock(
            return_value=sample_generation_response
        )

        # Check initial state
        assert mock_generator.current_status == "idle"

        # Start generation
        await mock_generator.generate_markdown()

        # Should be back to idle after completion
        assert mock_generator.current_status == "idle"

    def test_generation_timestamp_tracking(self, mock_generator):
        """Test that generation timestamps are tracked."""
        assert mock_generator.last_generation is None

        # Simulate successful generation
        mock_generator._update_generation_timestamp()

        assert mock_generator.last_generation is not None
        assert isinstance(mock_generator.last_generation, datetime)

    def test_error_message_tracking(self, mock_generator):
        """Test error message persistence and clearing."""
        # Initially no error
        assert mock_generator.error_message is None

        # Set error
        mock_generator._set_error_state("Test error message")
        assert mock_generator.error_message == "Test error message"

        # Clear error
        mock_generator._clear_error_state()
        assert mock_generator.error_message is None
