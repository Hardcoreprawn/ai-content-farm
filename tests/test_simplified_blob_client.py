"""
Comprehensive tests for SimplifiedBlobClient

Tests both the new simplified API and migration compatibility.
Ensures we can safely migrate containers without breaking existing functionality.
"""

import json
import os
import sys
from unittest.mock import AsyncMock, Mock, patch

import pytest
from azure.storage.blob import BlobServiceClient
from simplified_blob_client import SimplifiedBlobClient

# Add the libs directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "libs"))

# Import the simplified client (we'll create this in libs/)


class TestSimplifiedBlobClient:
    """Test suite for SimplifiedBlobClient."""

    @pytest.fixture
    def mock_blob_service_client(self):
        """Mock Azure BlobServiceClient."""
        return Mock(spec=BlobServiceClient)

    @pytest.fixture
    def mock_blob_client(self):
        """Mock individual blob client."""
        mock = Mock()
        mock.upload_blob = Mock()
        mock.download_blob = Mock()
        mock.delete_blob = Mock()
        return mock

    @pytest.fixture
    def mock_container_client(self):
        """Mock container client for listing operations."""
        mock = Mock()
        mock.list_blobs = Mock()
        return mock

    @pytest.fixture
    def simplified_client(self, mock_blob_service_client):
        """Create SimplifiedBlobClient with mocked dependencies."""
        return SimplifiedBlobClient(mock_blob_service_client)

    @pytest.mark.asyncio
    async def test_upload_json_success(
        self, simplified_client, mock_blob_service_client, mock_blob_client
    ):
        """Test successful JSON upload."""
        # Setup
        mock_blob_service_client.get_blob_client.return_value = mock_blob_client
        test_data = {"topic": "AI trends", "score": 0.95, "articles": [1, 2, 3]}

        # Execute
        result = await simplified_client.upload_json(
            "test-container", "data.json", test_data
        )

        # Verify
        assert result is True
        mock_blob_service_client.get_blob_client.assert_called_once_with(
            container="test-container", blob="data.json"
        )

        # Verify JSON serialization and upload call
        call_args = mock_blob_client.upload_blob.call_args
        uploaded_data = call_args[0][0]  # First positional argument
        assert json.loads(uploaded_data.decode("utf-8")) == test_data
        assert call_args[1]["content_type"] == "application/json"
        assert call_args[1]["overwrite"] is True

    @pytest.mark.asyncio
    async def test_download_json_success(
        self, simplified_client, mock_blob_service_client, mock_blob_client
    ):
        """Test successful JSON download."""
        # Setup
        test_data = {"processed": True, "topics": ["AI", "ML"]}
        mock_download = Mock()
        mock_download.readall.return_value = json.dumps(test_data).encode("utf-8")
        mock_blob_client.download_blob.return_value = mock_download
        mock_blob_service_client.get_blob_client.return_value = mock_blob_client

        # Execute
        result = await simplified_client.download_json("processed", "topics.json")

        # Verify
        assert result == test_data
        mock_blob_service_client.get_blob_client.assert_called_once_with(
            container="processed", blob="topics.json"
        )

    @pytest.mark.asyncio
    async def test_upload_text_success(
        self, simplified_client, mock_blob_service_client, mock_blob_client
    ):
        """Test successful text upload (markdown articles)."""
        # Setup
        mock_blob_service_client.get_blob_client.return_value = mock_blob_client
        markdown_content = "# AI Trends 2025\n\nArtificial intelligence is..."

        # Execute
        result = await simplified_client.upload_text(
            "articles", "ai-trends.md", markdown_content
        )

        # Verify
        assert result is True
        call_args = mock_blob_client.upload_blob.call_args
        uploaded_data = call_args[0][0]  # First positional argument
        assert uploaded_data.decode("utf-8") == markdown_content
        assert call_args[1]["content_type"] == "text/plain"

    @pytest.mark.asyncio
    async def test_download_text_success(
        self, simplified_client, mock_blob_service_client, mock_blob_client
    ):
        """Test successful text download."""
        # Setup
        html_content = "<html><body><h1>Generated Article</h1></body></html>"
        mock_download = Mock()
        mock_download.readall.return_value = html_content.encode("utf-8")
        mock_blob_client.download_blob.return_value = mock_download
        mock_blob_service_client.get_blob_client.return_value = mock_blob_client

        # Execute
        result = await simplified_client.download_text("static-site", "article.html")

        # Verify
        assert result == html_content

    @pytest.mark.asyncio
    async def test_upload_binary_success(
        self, simplified_client, mock_blob_service_client, mock_blob_client
    ):
        """Test successful binary upload (images, audio)."""
        # Setup
        mock_blob_service_client.get_blob_client.return_value = mock_blob_client
        image_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR..."  # Fake PNG header

        # Execute
        result = await simplified_client.upload_binary(
            "media", "hero.jpg", image_bytes, "image/jpeg"
        )

        # Verify
        assert result is True
        call_args = mock_blob_client.upload_blob.call_args
        assert call_args[0][0] == image_bytes
        assert call_args[1]["content_type"] == "image/jpeg"

    @pytest.mark.asyncio
    async def test_download_binary_success(
        self, simplified_client, mock_blob_service_client, mock_blob_client
    ):
        """Test successful binary download."""
        # Setup
        audio_bytes = b"ID3\x04\x00..."  # Fake MP3 header
        mock_download = Mock()
        mock_download.readall.return_value = audio_bytes
        mock_blob_client.download_blob.return_value = mock_download
        mock_blob_service_client.get_blob_client.return_value = mock_blob_client

        # Execute
        result = await simplified_client.download_binary("media", "podcast.mp3")

        # Verify
        assert result == audio_bytes

    @pytest.mark.asyncio
    async def test_list_blobs_success(
        self, simplified_client, mock_blob_service_client, mock_container_client
    ):
        """Test successful blob listing."""
        # Setup
        mock_blob1 = Mock()
        mock_blob1.name = "topics-2025-09-25.json"
        mock_blob2 = Mock()
        mock_blob2.name = "topics-2025-09-24.json"

        mock_container_client.list_blobs.return_value = [mock_blob1, mock_blob2]
        mock_blob_service_client.get_container_client.return_value = (
            mock_container_client
        )

        # Execute
        result = await simplified_client.list_blobs("raw-content", "topics-2025")

        # Verify
        assert result == ["topics-2025-09-25.json", "topics-2025-09-24.json"]
        mock_container_client.list_blobs.assert_called_once_with(
            name_starts_with="topics-2025"
        )

    @pytest.mark.asyncio
    async def test_delete_blob_success(
        self, simplified_client, mock_blob_service_client, mock_blob_client
    ):
        """Test successful blob deletion."""
        # Setup
        mock_blob_service_client.get_blob_client.return_value = mock_blob_client

        # Execute
        result = await simplified_client.delete_blob("temp-data", "old-topics.json")

        # Verify
        assert result is True
        mock_blob_client.delete_blob.assert_called_once()

    # Error handling tests
    @pytest.mark.asyncio
    async def test_upload_json_failure(
        self, simplified_client, mock_blob_service_client, mock_blob_client
    ):
        """Test JSON upload failure handling."""
        # Setup
        mock_blob_client.upload_blob.side_effect = Exception("Network error")
        mock_blob_service_client.get_blob_client.return_value = mock_blob_client

        # Execute
        result = await simplified_client.upload_json(
            "test", "data.json", {"test": "data"}
        )

        # Verify
        assert result is False

    @pytest.mark.asyncio
    async def test_download_json_failure(
        self, simplified_client, mock_blob_service_client, mock_blob_client
    ):
        """Test JSON download failure handling."""
        # Setup
        mock_blob_client.download_blob.side_effect = Exception("Blob not found")
        mock_blob_service_client.get_blob_client.return_value = mock_blob_client

        # Execute
        result = await simplified_client.download_json("missing", "data.json")

        # Verify
        assert result is None

    @pytest.mark.asyncio
    async def test_download_json_invalid_json(
        self, simplified_client, mock_blob_service_client, mock_blob_client
    ):
        """Test JSON download with invalid JSON content."""
        # Setup
        mock_download = Mock()
        mock_download.readall.return_value = b"invalid json content {"
        mock_blob_client.download_blob.return_value = mock_download
        mock_blob_service_client.get_blob_client.return_value = mock_blob_client

        # Execute
        result = await simplified_client.download_json("test", "invalid.json")

        # Verify
        assert result is None


class TestMigrationCompatibility:
    """Test migration compatibility with existing container patterns."""

    @pytest.mark.asyncio
    async def test_content_collector_pattern(self):
        """Test pattern used by content-collector container."""
        # This tests the typical collector workflow
        with patch("azure.storage.blob.BlobServiceClient") as mock_service:
            mock_blob_client = Mock()
            mock_service.return_value.get_blob_client.return_value = mock_blob_client

            client = SimplifiedBlobClient(mock_service.return_value)

            # Simulate content collector saving topics
            topics_data = {
                "collection_date": "2025-09-25T14:00:00Z",
                "topics": [
                    {"id": "topic_1", "title": "AI Breakthrough", "score": 0.95},
                    {"id": "topic_2", "title": "Quantum Computing", "score": 0.87},
                ],
            }

            result = await client.upload_json(
                "raw-content", "topics-2025-09-25.json", topics_data
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_content_processor_pattern(self):
        """Test pattern used by content-processor container."""
        with patch("azure.storage.blob.BlobServiceClient") as mock_service:
            # Setup download mock
            mock_blob_client = Mock()
            mock_download = Mock()
            topics_data = {"topics": [{"id": "1", "score": 0.5}]}
            mock_download.readall.return_value = json.dumps(topics_data).encode("utf-8")
            mock_blob_client.download_blob.return_value = mock_download
            mock_service.return_value.get_blob_client.return_value = mock_blob_client

            client = SimplifiedBlobClient(mock_service.return_value)

            # Read input data
            input_data = await client.download_json("raw-content", "topics.json")
            assert input_data == topics_data

            # Process and save (simulate ranking)
            processed_data = {"processed_topics": input_data["topics"], "ranked": True}
            result = await client.upload_json(
                "processed-content", "ranked-topics.json", processed_data
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_site_generator_pattern(self):
        """Test pattern used by site-generator container (full workflow)."""
        with patch("azure.storage.blob.BlobServiceClient") as mock_service:
            mock_blob_client = Mock()
            mock_service.return_value.get_blob_client.return_value = mock_blob_client

            # Setup download mocks
            processed_data = {"topics": [{"title": "AI News", "content": "..."}]}
            mock_download_json = Mock()
            mock_download_json.readall.return_value = json.dumps(processed_data).encode(
                "utf-8"
            )

            markdown_content = "# AI News\n\nThis is the article content..."
            mock_download_text = Mock()
            mock_download_text.readall.return_value = markdown_content.encode("utf-8")

            # Configure mock to return different values for different calls
            mock_blob_client.download_blob.side_effect = [
                mock_download_json,
                mock_download_text,
            ]

            client = SimplifiedBlobClient(mock_service.return_value)

            # 1. Read processed topics
            topics = await client.download_json(
                "processed-content", "ranked-topics.json"
            )
            assert topics == processed_data

            # 2. Generate and save markdown
            result = await client.upload_text(
                "articles", "ai-news.md", markdown_content
            )
            assert result is True

            # 3. Read markdown for HTML conversion
            markdown = await client.download_text("articles", "ai-news.md")
            assert markdown == markdown_content

            # 4. Save final HTML
            html_content = "<html><body><h1>AI News</h1><p>This is the article content...</p></body></html>"
            result = await client.upload_text(
                "static-site", "ai-news.html", html_content
            )
            assert result is True


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
