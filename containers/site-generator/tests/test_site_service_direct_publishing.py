"""
Test suite for direct site publishing functionality.

Tests the direct publishing of site files to the $web blob container
for immediate live static website hosting.
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from site_service import SiteService

from config import Config


class TestSiteServiceDirectPublishing:
    """Test direct site publishing to $web container."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = MagicMock(spec=Config)
        config.MARKDOWN_CONTENT_CONTAINER = "markdown-content"
        config.STATIC_SITES_CONTAINER = "static-sites"
        return config

    @pytest.fixture
    def mock_blob_client(self):
        """Create mock blob client."""
        return AsyncMock()

    @pytest.fixture
    def mock_content_manager(self):
        """Create mock content manager."""
        return AsyncMock()

    @pytest.fixture
    def mock_archive_manager(self):
        """Create mock archive manager."""
        return AsyncMock()

    @pytest.fixture
    def site_service(
        self, mock_blob_client, mock_config, mock_content_manager, mock_archive_manager
    ):
        """Create SiteService instance with mocked dependencies."""
        return SiteService(
            blob_client=mock_blob_client,
            config=mock_config,
            content_manager=mock_content_manager,
            archive_manager=mock_archive_manager,
        )

    @pytest.mark.asyncio
    async def test_publish_site_directly_basic(self, site_service, mock_blob_client):
        """Test basic direct site publishing functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            site_dir = Path(temp_dir)

            # Create mock site files
            (site_dir / "index.html").write_text("<html><body>Home</body></html>")
            (site_dir / "404.html").write_text("<html><body>Not Found</body></html>")
            (site_dir / "style.css").write_text("body { font-family: Arial; }")

            # Create articles subdirectory
            articles_dir = site_dir / "articles"
            articles_dir.mkdir()
            (articles_dir / "article1.html").write_text(
                "<html><body>Article 1</body></html>"
            )

            # Test the publishing method
            await site_service._publish_site_directly(site_dir)

        # Verify uploads were called correctly (all text files in this test)
        assert mock_blob_client.upload_text.call_count == 4
        assert mock_blob_client.upload_binary.call_count == 0

        # Check specific uploads
        upload_calls = mock_blob_client.upload_text.call_args_list

        # Extract blob names from calls
        uploaded_files = {call[1]["blob_name"] for call in upload_calls}
        expected_files = {
            "index.html",
            "404.html",
            "style.css",
            "articles/article1.html",
        }

        assert uploaded_files == expected_files

        # Verify container name is $web for all uploads
        for call in upload_calls:
            assert call[1]["container_name"] == "$web"

    @pytest.mark.asyncio
    async def test_publish_site_directly_content_types(
        self, site_service, mock_blob_client
    ):
        """Test that correct content types are set for different file types."""
        with tempfile.TemporaryDirectory() as temp_dir:
            site_dir = Path(temp_dir)

            # Create files with different extensions
            (site_dir / "index.html").write_text("<html></html>")
            (site_dir / "style.css").write_text("body {}")
            (site_dir / "script.js").write_text("console.log('test');")
            (site_dir / "data.json").write_text('{"test": true}')
            (site_dir / "feed.xml").write_text('<?xml version="1.0"?>')

            await site_service._publish_site_directly(site_dir)

        # Check content types were set correctly
        upload_calls = mock_blob_client.upload_text.call_args_list
        content_types = {}

        for call in upload_calls:
            blob_name = call[1]["blob_name"]
            content_type = call[1]["content_type"]
            content_types[blob_name] = content_type

        expected_content_types = {
            "index.html": "text/html",
            "style.css": "text/css",
            "script.js": "application/javascript",
            "data.json": "application/json",
            "feed.xml": "application/xml",
        }

        assert content_types == expected_content_types

    @pytest.mark.asyncio
    async def test_publish_site_directly_nested_structure(
        self, site_service, mock_blob_client
    ):
        """Test publishing with nested directory structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            site_dir = Path(temp_dir)

            # Create nested structure
            (site_dir / "index.html").write_text("<html></html>")

            # Articles subdirectory
            articles_dir = site_dir / "articles"
            articles_dir.mkdir()
            tech_dir = articles_dir / "tech"
            tech_dir.mkdir()
            (tech_dir / "ai.html").write_text("<html>AI Article</html>")

            # Assets subdirectory
            assets_dir = site_dir / "assets"
            assets_dir.mkdir()
            css_dir = assets_dir / "css"
            css_dir.mkdir()
            (css_dir / "main.css").write_text("body { margin: 0; }")

            await site_service._publish_site_directly(site_dir)

        # Verify nested paths are handled correctly
        upload_calls = mock_blob_client.upload_text.call_args_list
        uploaded_files = {call[1]["blob_name"] for call in upload_calls}

        expected_files = {
            "index.html",
            "articles/tech/ai.html",
            "assets/css/main.css",
        }

        assert uploaded_files == expected_files

    @pytest.mark.asyncio
    async def test_publish_site_directly_upload_error(
        self, site_service, mock_blob_client
    ):
        """Test error handling when upload fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            site_dir = Path(temp_dir)
            (site_dir / "index.html").write_text("<html></html>")

            # Mock upload to raise an exception
            mock_blob_client.upload_text.side_effect = Exception("Upload failed")

            # Should raise the exception
            with pytest.raises(Exception, match="Upload failed"):
                await site_service._publish_site_directly(site_dir)

    def test_get_content_type(self, site_service):
        """Test content type detection for various file extensions."""
        assert site_service._get_content_type(".html") == "text/html"
        assert site_service._get_content_type(".css") == "text/css"
        assert site_service._get_content_type(".js") == "application/javascript"
        assert site_service._get_content_type(".json") == "application/json"
        assert site_service._get_content_type(".xml") == "application/xml"
        assert site_service._get_content_type(".png") == "image/png"
        assert site_service._get_content_type(".jpg") == "image/jpeg"
        assert site_service._get_content_type(".ico") == "image/x-icon"
        assert site_service._get_content_type(".unknown") == "application/octet-stream"

        # Test case insensitivity
        assert site_service._get_content_type(".HTML") == "text/html"
        assert site_service._get_content_type(".CSS") == "text/css"

    @pytest.mark.asyncio
    async def test_publish_site_directly_empty_directory(
        self, site_service, mock_blob_client
    ):
        """Test publishing an empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            site_dir = Path(temp_dir)

            # Directory exists but is empty
            await site_service._publish_site_directly(site_dir)

        # Should not call upload since no files exist
        assert mock_blob_client.upload_text.call_count == 0
        assert mock_blob_client.upload_binary.call_count == 0

    @pytest.mark.asyncio
    async def test_publish_site_directly_with_subdirectories_only(
        self, site_service, mock_blob_client
    ):
        """Test that empty subdirectories don't cause issues."""
        with tempfile.TemporaryDirectory() as temp_dir:
            site_dir = Path(temp_dir)

            # Create directories but no files
            (site_dir / "articles").mkdir()
            (site_dir / "assets" / "css").mkdir(parents=True)

            await site_service._publish_site_directly(site_dir)

        # Should not upload anything since no files exist
        assert mock_blob_client.upload_text.call_count == 0
        assert mock_blob_client.upload_binary.call_count == 0
