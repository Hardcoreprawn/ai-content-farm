"""
Tests for pure functional blob storage operations.

Black box testing: validates inputs and outputs only, not implementation.

Contract Version: 1.0.0
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest
from blob_operations import (
    check_blob_exists,
    delete_blob,
    detect_content_type,
    download_binary_blob,
    download_json_blob,
    download_text_blob,
    list_blobs_with_prefix,
    serialize_datetime,
    upload_binary_blob,
    upload_json_blob,
    upload_text_blob,
)


class TestSerializeDatetime:
    """Test datetime serialization."""

    def test_serialize_single_datetime(self):
        """Datetime converts to ISO string."""
        dt = datetime(2025, 10, 8, 12, 0, 0, tzinfo=timezone.utc)
        result = serialize_datetime(dt)
        assert result == "2025-10-08T12:00:00+00:00"

    def test_serialize_dict_with_datetime(self):
        """Dict with datetime gets serialized."""
        dt = datetime(2025, 10, 8, 12, 0, 0, tzinfo=timezone.utc)
        data = {"timestamp": dt, "count": 5}
        result = serialize_datetime(data)
        assert result["timestamp"] == "2025-10-08T12:00:00+00:00"
        assert result["count"] == 5

    def test_serialize_nested_structure(self):
        """Nested structures with datetime get serialized."""
        dt = datetime(2025, 10, 8, 12, 0, 0, tzinfo=timezone.utc)
        data = {
            "metadata": {"created": dt, "updated": dt},
            "items": [{"date": dt, "id": 1}],
        }
        result = serialize_datetime(data)
        assert result["metadata"]["created"] == "2025-10-08T12:00:00+00:00"
        assert result["items"][0]["date"] == "2025-10-08T12:00:00+00:00"

    def test_serialize_list_with_datetime(self):
        """List with datetime gets serialized."""
        dt = datetime(2025, 10, 8, 12, 0, 0, tzinfo=timezone.utc)
        data = [dt, "string", 123]
        result = serialize_datetime(data)
        assert result[0] == "2025-10-08T12:00:00+00:00"
        assert result[1] == "string"
        assert result[2] == 123

    def test_serialize_primitives_unchanged(self):
        """Primitive types pass through unchanged."""
        assert serialize_datetime("text") == "text"
        assert serialize_datetime(123) == 123
        assert serialize_datetime(45.67) == 45.67
        assert serialize_datetime(True) is True
        assert serialize_datetime(None) is None


class TestDetectContentType:
    """Test content type detection."""

    def test_markdown_files(self):
        """Markdown files detected correctly."""
        assert detect_content_type("article.md") == "text/markdown"
        assert detect_content_type("path/to/file.md") == "text/markdown"

    def test_json_files(self):
        """JSON files detected correctly."""
        assert detect_content_type("data.json") == "application/json"

    def test_html_files(self):
        """HTML files detected correctly."""
        assert detect_content_type("index.html") == "text/html"

    def test_image_files(self):
        """Image files detected correctly."""
        assert detect_content_type("photo.png") == "image/png"
        assert detect_content_type("photo.jpg") == "image/jpeg"
        assert detect_content_type("photo.jpeg") == "image/jpeg"
        assert detect_content_type("animation.gif") == "image/gif"

    def test_javascript_files(self):
        """JavaScript files detected correctly."""
        assert detect_content_type("script.js") == "application/javascript"

    def test_css_files(self):
        """CSS files detected correctly."""
        assert detect_content_type("style.css") == "text/css"

    def test_unknown_extension(self):
        """Unknown extensions default to text/plain."""
        assert detect_content_type("file.unknown") == "text/plain"
        assert detect_content_type("noextension") == "text/plain"


@pytest.mark.asyncio
class TestUploadJsonBlob:
    """Test JSON blob uploading."""

    async def test_successful_upload(self):
        """Successful upload returns True."""
        mock_client = Mock()
        mock_blob_client = Mock()
        mock_blob_client.upload_blob = AsyncMock()
        mock_client.get_blob_client = Mock(return_value=mock_blob_client)

        result = await upload_json_blob(
            mock_client, "container", "data.json", {"key": "value"}
        )

        assert result is True
        assert mock_client.get_blob_client.called
        assert mock_blob_client.upload_blob.called

    async def test_upload_with_datetime(self):
        """Upload serializes datetime objects."""
        dt = datetime(2025, 10, 8, 12, 0, 0, tzinfo=timezone.utc)
        mock_client = Mock()
        mock_blob_client = Mock()
        mock_client.get_blob_client = Mock(return_value=mock_blob_client)

        await upload_json_blob(mock_client, "container", "data.json", {"timestamp": dt})

        # Verify upload was called with serialized datetime
        call_args = mock_blob_client.upload_blob.call_args
        uploaded_data = call_args[0][0].decode("utf-8")
        assert "2025-10-08T12:00:00+00:00" in uploaded_data

    async def test_upload_failure(self):
        """Upload failure returns False."""
        mock_client = Mock()
        mock_client.get_blob_client = Mock(side_effect=Exception("Upload failed"))

        result = await upload_json_blob(
            mock_client, "container", "data.json", {"key": "value"}
        )

        assert result is False


@pytest.mark.asyncio
class TestDownloadJsonBlob:
    """Test JSON blob downloading."""

    async def test_successful_download(self):
        """Successful download returns parsed JSON."""
        mock_client = Mock()
        mock_blob_client = Mock()
        mock_download = Mock()
        mock_download.readall = AsyncMock(return_value=b'{"key": "value"}')
        mock_blob_client.download_blob = AsyncMock(return_value=mock_download)
        mock_client.get_blob_client = Mock(return_value=mock_blob_client)

        result = await download_json_blob(mock_client, "container", "data.json")

        assert result == {"key": "value"}

    async def test_download_failure(self):
        """Download failure returns None."""
        mock_client = Mock()
        mock_client.get_blob_client = Mock(side_effect=Exception("Download failed"))

        result = await download_json_blob(mock_client, "container", "data.json")

        assert result is None


@pytest.mark.asyncio
class TestUploadTextBlob:
    """Test text blob uploading."""

    async def test_successful_upload(self):
        """Successful text upload returns True."""
        mock_client = Mock()
        mock_blob_client = Mock()
        mock_blob_client.upload_blob = AsyncMock()
        mock_client.get_blob_client = Mock(return_value=mock_blob_client)

        result = await upload_text_blob(
            mock_client, "container", "article.md", "# Article Content"
        )

        assert result is True
        assert mock_blob_client.upload_blob.called

    async def test_auto_detect_content_type(self):
        """Content type is auto-detected from extension."""
        mock_client = Mock()
        mock_blob_client = Mock()
        mock_blob_client.upload_blob = AsyncMock()
        mock_client.get_blob_client = Mock(return_value=mock_blob_client)

        await upload_text_blob(mock_client, "container", "article.md", "# Article")

        call_args = mock_blob_client.upload_blob.call_args
        assert call_args.kwargs["content_type"] == "text/markdown"

    async def test_custom_content_type(self):
        """Custom content type is respected."""
        mock_client = Mock()
        mock_blob_client = Mock()
        mock_blob_client.upload_blob = AsyncMock()
        mock_client.get_blob_client = Mock(return_value=mock_blob_client)

        await upload_text_blob(
            mock_client,
            "container",
            "file.txt",
            "content",
            content_type="custom/type",
        )

        call_args = mock_blob_client.upload_blob.call_args
        assert call_args.kwargs["content_type"] == "custom/type"


@pytest.mark.asyncio
class TestDownloadTextBlob:
    """Test text blob downloading."""

    async def test_successful_download(self):
        """Successful download returns text."""
        mock_client = Mock()
        mock_blob_client = Mock()
        mock_download = Mock()
        mock_download.readall = AsyncMock(return_value=b"# Article Content")
        mock_blob_client.download_blob = AsyncMock(return_value=mock_download)
        mock_client.get_blob_client = Mock(return_value=mock_blob_client)

        result = await download_text_blob(mock_client, "container", "article.md")

        assert result == "# Article Content"

    async def test_download_failure(self):
        """Download failure returns None."""
        mock_client = Mock()
        mock_client.get_blob_client = Mock(side_effect=Exception("Download failed"))

        result = await download_text_blob(mock_client, "container", "article.md")

        assert result is None


@pytest.mark.asyncio
class TestBinaryOperations:
    """Test binary blob operations."""

    async def test_upload_binary(self):
        """Binary upload works correctly."""
        mock_client = Mock()
        mock_blob_client = Mock()
        mock_blob_client.upload_blob = AsyncMock()
        mock_client.get_blob_client = Mock(return_value=mock_blob_client)

        result = await upload_binary_blob(
            mock_client, "container", "image.png", b"\x89PNG", "image/png"
        )

        assert result is True
        call_args = mock_blob_client.upload_blob.call_args
        assert call_args.kwargs["content_type"] == "image/png"

    async def test_download_binary(self):
        """Binary download works correctly."""
        mock_client = Mock()
        mock_blob_client = Mock()
        mock_download = Mock()
        mock_download.readall = AsyncMock(return_value=b"\x89PNG")
        mock_blob_client.download_blob = AsyncMock(return_value=mock_download)
        mock_client.get_blob_client = Mock(return_value=mock_blob_client)

        result = await download_binary_blob(mock_client, "container", "image.png")

        assert result == b"\x89PNG"


@pytest.mark.asyncio
class TestListBlobs:
    """Test blob listing."""

    async def test_list_blobs(self):
        """List blobs returns metadata."""
        mock_client = Mock()
        mock_container = Mock()

        mock_blob = Mock()
        mock_blob.name = "file.json"
        mock_blob.size = 1024
        mock_blob.last_modified = datetime(2025, 10, 8, tzinfo=timezone.utc)
        mock_blob.content_settings = Mock(content_type="application/json")

        # Create async iterator for list_blobs
        async def async_blob_iter():
            yield mock_blob

        mock_container.list_blobs = Mock(return_value=async_blob_iter())
        mock_client.get_container_client = Mock(return_value=mock_container)

        result = await list_blobs_with_prefix(mock_client, "container", "prefix/")

        assert len(result) == 1
        assert result[0]["name"] == "file.json"
        assert result[0]["size"] == 1024
        assert result[0]["content_type"] == "application/json"

    async def test_list_blobs_failure(self):
        """List blobs failure returns empty list."""
        mock_client = Mock()
        mock_client.get_container_client = Mock(side_effect=Exception("List failed"))

        result = await list_blobs_with_prefix(mock_client, "container")

        assert result == []


@pytest.mark.asyncio
class TestBlobManagement:
    """Test blob existence checking and deletion."""

    async def test_check_blob_exists_true(self):
        """Check returns True when blob exists."""
        mock_client = Mock()
        mock_blob_client = Mock()
        mock_blob_client.exists = AsyncMock(return_value=True)
        mock_client.get_blob_client = Mock(return_value=mock_blob_client)

        result = await check_blob_exists(mock_client, "container", "file.json")

        assert result is True

    async def test_check_blob_exists_false(self):
        """Check returns False when blob doesn't exist."""
        mock_client = Mock()
        mock_blob_client = Mock()
        mock_blob_client.exists = AsyncMock(return_value=False)
        mock_client.get_blob_client = Mock(return_value=mock_blob_client)

        result = await check_blob_exists(mock_client, "container", "file.json")

        assert result is False

    async def test_delete_blob_success(self):
        """Delete returns True on success."""
        mock_client = Mock()
        mock_blob_client = Mock()
        mock_blob_client.delete_blob = AsyncMock()
        mock_client.get_blob_client = Mock(return_value=mock_blob_client)

        result = await delete_blob(mock_client, "container", "file.json")

        assert result is True
        assert mock_blob_client.delete_blob.called

    async def test_delete_blob_failure(self):
        """Delete returns False on failure."""
        mock_client = Mock()
        mock_client.get_blob_client = Mock(side_effect=Exception("Delete failed"))

        result = await delete_blob(mock_client, "container", "file.json")

        assert result is False


class TestPurityAndDeterminism:
    """Test that functions are pure (deterministic, no side effects)."""

    def test_serialize_datetime_determinism(self):
        """Same input produces same output."""
        dt = datetime(2025, 10, 8, 12, 0, 0, tzinfo=timezone.utc)
        result1 = serialize_datetime({"date": dt})
        result2 = serialize_datetime({"date": dt})
        assert result1 == result2

    def test_detect_content_type_determinism(self):
        """Same filename produces same content type."""
        result1 = detect_content_type("file.md")
        result2 = detect_content_type("file.md")
        assert result1 == result2 == "text/markdown"

    def test_serialize_empty_structures(self):
        """Empty structures handled correctly."""
        assert serialize_datetime({}) == {}
        assert serialize_datetime([]) == []
        assert serialize_datetime(None) is None
