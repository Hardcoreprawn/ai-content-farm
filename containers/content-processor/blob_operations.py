"""
Pure functional wrappers for Azure Blob Storage operations.

Stateless functions that wrap Azure Blob SDK calls for JSON, text, and binary
operations. All configuration passed explicitly, no stored state.

Contract Version: 1.0.0
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from azure.storage.blob.aio import BlobServiceClient

logger = logging.getLogger(__name__)


# ============================================================================
# Datetime Serialization (Pure Helper)
# ============================================================================


def serialize_datetime(obj: Any) -> Any:
    """
    Recursively convert datetime objects to ISO format strings.

    Pure function for handling datetime serialization in JSON data.

    Args:
        obj: Any Python object (dict, list, datetime, primitive)

    Returns:
        Same structure with datetimes converted to ISO strings

    Examples:
        >>> from datetime import datetime, timezone
        >>> dt = datetime(2025, 10, 8, 12, 0, 0, tzinfo=timezone.utc)
        >>> serialize_datetime({"date": dt, "count": 5})
        {'date': '2025-10-08T12:00:00+00:00', 'count': 5}
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: serialize_datetime(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [serialize_datetime(item) for item in obj]
    else:
        return obj


# ============================================================================
# JSON Operations
# ============================================================================


async def upload_json_blob(
    blob_service_client: BlobServiceClient,
    container: str,
    blob_name: str,
    data: Dict[str, Any],
    overwrite: bool = True,
) -> bool:
    """
    Upload JSON data to blob storage.

    Pure async function with automatic datetime serialization.

    Args:
        blob_service_client: Configured Azure BlobServiceClient
        container: Container name
        blob_name: Blob path/name
        data: Dictionary to upload as JSON
        overwrite: Whether to overwrite existing blob

    Returns:
        bool: True if successful, False otherwise

    Examples:
        >>> from azure.storage.blob.aio import BlobServiceClient
        >>> client = BlobServiceClient.from_connection_string("connection_string")
        >>> success = await upload_json_blob(
        ...     client, "my-container", "data.json",
        ...     {"key": "value", "count": 42}
        ... )
        >>> success
        True
    """
    try:
        blob_client = blob_service_client.get_blob_client(
            container=container, blob=blob_name
        )

        # Use functional datetime serialization
        serializable_data = serialize_datetime(data)
        json_bytes = json.dumps(serializable_data, indent=2).encode("utf-8")

        await blob_client.upload_blob(
            json_bytes, overwrite=overwrite, content_type="application/json"
        )

        logger.info(f"Uploaded JSON to {container}/{blob_name}")
        return True

    except Exception as e:
        logger.error(f"Failed to upload JSON to {container}/{blob_name}: {e}")
        return False


async def download_json_blob(
    blob_service_client: BlobServiceClient,
    container: str,
    blob_name: str,
) -> Optional[Dict[str, Any]]:
    """
    Download and parse JSON from blob storage.

    Pure async function with no side effects beyond I/O.

    Args:
        blob_service_client: Configured Azure BlobServiceClient
        container: Container name
        blob_name: Blob path/name

    Returns:
        Dict or None: Parsed JSON data, or None on error

    Examples:
        >>> client = BlobServiceClient.from_connection_string("connection_string")
        >>> data = await download_json_blob(client, "my-container", "data.json")
        >>> data["key"]
        'value'
    """
    try:
        blob_client = blob_service_client.get_blob_client(
            container=container, blob=blob_name
        )

        download_stream = await blob_client.download_blob()
        content = await download_stream.readall()
        if isinstance(content, bytes):
            content = content.decode("utf-8")

        return json.loads(content)

    except Exception as e:
        logger.error(f"Failed to download JSON from {container}/{blob_name}: {e}")
        return None


# ============================================================================
# Text Operations
# ============================================================================


async def upload_text_blob(
    blob_service_client: BlobServiceClient,
    container: str,
    blob_name: str,
    text: str,
    overwrite: bool = True,
    content_type: Optional[str] = None,
) -> bool:
    """
    Upload text content to blob storage.

    Pure async function with automatic content type detection.

    Args:
        blob_service_client: Configured Azure BlobServiceClient
        container: Container name
        blob_name: Blob path/name
        text: Text content to upload
        overwrite: Whether to overwrite existing blob
        content_type: Optional content type (auto-detected if None)

    Returns:
        bool: True if successful, False otherwise

    Examples:
        >>> client = BlobServiceClient.from_connection_string("connection_string")
        >>> success = await upload_text_blob(
        ...     client, "my-container", "article.md",
        ...     "# My Article\\n\\nContent here"
        ... )
        >>> success
        True
    """
    try:
        # Auto-detect content type if not provided
        if content_type is None:
            content_type = detect_content_type(blob_name)

        blob_client = blob_service_client.get_blob_client(
            container=container, blob=blob_name
        )

        await blob_client.upload_blob(
            text.encode("utf-8"), overwrite=overwrite, content_type=content_type
        )

        logger.info(
            f"Uploaded text to {container}/{blob_name} (content_type={content_type})"
        )
        return True

    except Exception as e:
        logger.error(f"Failed to upload text to {container}/{blob_name}: {e}")
        return False


async def download_text_blob(
    blob_service_client: BlobServiceClient,
    container: str,
    blob_name: str,
) -> Optional[str]:
    """
    Download text content from blob storage.

    Pure async function with no side effects beyond I/O.

    Args:
        blob_service_client: Configured Azure BlobServiceClient
        container: Container name
        blob_name: Blob path/name

    Returns:
        str or None: Text content, or None on error

    Examples:
        >>> client = BlobServiceClient.from_connection_string("connection_string")
        >>> text = await download_text_blob(client, "my-container", "article.md")
        >>> "# My Article" in text
        True
    """
    try:
        blob_client = blob_service_client.get_blob_client(
            container=container, blob=blob_name
        )

        download_stream = await blob_client.download_blob()
        content = await download_stream.readall()
        if isinstance(content, bytes):
            return content.decode("utf-8")
        return str(content)

    except Exception as e:
        logger.error(f"Failed to download text from {container}/{blob_name}: {e}")
        return None


# ============================================================================
# Binary Operations
# ============================================================================


async def upload_binary_blob(
    blob_service_client: BlobServiceClient,
    container: str,
    blob_name: str,
    data: bytes,
    content_type: str,
    overwrite: bool = True,
) -> bool:
    """
    Upload binary content to blob storage.

    Pure async function for binary data uploads.

    Args:
        blob_service_client: Configured Azure BlobServiceClient
        container: Container name
        blob_name: Blob path/name
        data: Binary data to upload
        content_type: MIME type of content
        overwrite: Whether to overwrite existing blob

    Returns:
        bool: True if successful, False otherwise

    Examples:
        >>> client = BlobServiceClient.from_connection_string("connection_string")
        >>> success = await upload_binary_blob(
        ...     client, "my-container", "image.png",
        ...     b"\\x89PNG...", "image/png"
        ... )
        >>> success
        True
    """
    try:
        blob_client = blob_service_client.get_blob_client(
            container=container, blob=blob_name
        )

        await blob_client.upload_blob(
            data, overwrite=overwrite, content_type=content_type
        )

        logger.info(f"Uploaded binary to {container}/{blob_name} ({content_type})")
        return True

    except Exception as e:
        logger.error(f"Failed to upload binary to {container}/{blob_name}: {e}")
        return False


async def download_binary_blob(
    blob_service_client: BlobServiceClient,
    container: str,
    blob_name: str,
) -> Optional[bytes]:
    """
    Download binary content from blob storage.

    Pure async function for binary data downloads.

    Args:
        blob_service_client: Configured Azure BlobServiceClient
        container: Container name
        blob_name: Blob path/name

    Returns:
        bytes or None: Binary content, or None on error

    Examples:
        >>> client = BlobServiceClient.from_connection_string("connection_string")
        >>> data = await download_binary_blob(client, "my-container", "image.png")
        >>> isinstance(data, bytes)
        True
    """
    try:
        blob_client = blob_service_client.get_blob_client(
            container=container, blob=blob_name
        )

        download_stream = await blob_client.download_blob()
        return await download_stream.readall()

    except Exception as e:
        logger.error(f"Failed to download binary from {container}/{blob_name}: {e}")
        return None


# ============================================================================
# Listing and Management
# ============================================================================


async def list_blobs_with_prefix(
    blob_service_client: BlobServiceClient,
    container: str,
    prefix: str = "",
) -> List[Dict[str, Any]]:
    """
    List blobs in container with optional prefix filter.

    Pure async function that returns blob metadata.

    Args:
        blob_service_client: Configured Azure BlobServiceClient
        container: Container name
        prefix: Optional prefix filter for blob names

    Returns:
        List of dicts with blob metadata (name, size, last_modified, content_type)

    Examples:
        >>> client = BlobServiceClient.from_connection_string("connection_string")
        >>> blobs = await list_blobs_with_prefix(client, "my-container", "2025/")
        >>> len(blobs) > 0
        True
        >>> "name" in blobs[0]
        True
    """
    try:
        container_client = blob_service_client.get_container_client(container)

        blobs = []
        async for blob in container_client.list_blobs(name_starts_with=prefix):
            blobs.append(
                {
                    "name": blob.name,
                    "size": blob.size,
                    "last_modified": blob.last_modified,
                    "content_type": (
                        blob.content_settings.content_type
                        if blob.content_settings
                        else None
                    ),
                }
            )
        return blobs

    except Exception as e:
        logger.error(f"Failed to list blobs in {container}: {e}")
        return []


async def check_blob_exists(
    blob_service_client: BlobServiceClient,
    container: str,
    blob_name: str,
) -> bool:
    """
    Check if blob exists in storage.

    Pure async function with boolean result.

    Args:
        blob_service_client: Configured Azure BlobServiceClient
        container: Container name
        blob_name: Blob path/name

    Returns:
        bool: True if blob exists, False otherwise

    Examples:
        >>> client = BlobServiceClient.from_connection_string("connection_string")
        >>> exists = await check_blob_exists(client, "my-container", "data.json")
        >>> isinstance(exists, bool)
        True
    """
    try:
        blob_client = blob_service_client.get_blob_client(
            container=container, blob=blob_name
        )
        return await blob_client.exists()

    except Exception as e:
        logger.error(f"Failed to check blob existence {container}/{blob_name}: {e}")
        return False


async def delete_blob(
    blob_service_client: BlobServiceClient,
    container: str,
    blob_name: str,
) -> bool:
    """
    Delete blob from storage.

    Pure async function with boolean result.

    Args:
        blob_service_client: Configured Azure BlobServiceClient
        container: Container name
        blob_name: Blob path/name

    Returns:
        bool: True if deleted successfully, False otherwise

    Examples:
        >>> client = BlobServiceClient.from_connection_string("connection_string")
        >>> success = await delete_blob(client, "my-container", "old-data.json")
        >>> isinstance(success, bool)
        True
    """
    try:
        blob_client = blob_service_client.get_blob_client(
            container=container, blob=blob_name
        )
        await blob_client.delete_blob()

        logger.info(f"Deleted {container}/{blob_name}")
        return True

    except Exception as e:
        logger.error(f"Failed to delete {container}/{blob_name}: {e}")
        return False


# ============================================================================
# Pure Helper Functions
# ============================================================================


def detect_content_type(blob_name: str) -> str:
    """
    Detect content type from blob name extension.

    Pure function with deterministic output.

    Args:
        blob_name: Blob file name/path

    Returns:
        str: MIME type string

    Examples:
        >>> detect_content_type("article.md")
        'text/markdown'
        >>> detect_content_type("data.json")
        'application/json'
        >>> detect_content_type("image.png")
        'image/png'
    """
    if blob_name.endswith(".html"):
        return "text/html"
    elif blob_name.endswith(".xml"):
        return "application/xml"
    elif blob_name.endswith(".json"):
        return "application/json"
    elif blob_name.endswith(".css"):
        return "text/css"
    elif blob_name.endswith(".js"):
        return "application/javascript"
    elif blob_name.endswith(".md"):
        return "text/markdown"
    elif blob_name.endswith(".png"):
        return "image/png"
    elif blob_name.endswith(".jpg") or blob_name.endswith(".jpeg"):
        return "image/jpeg"
    elif blob_name.endswith(".gif"):
        return "image/gif"
    elif blob_name.endswith(".svg"):
        return "image/svg+xml"
    else:
        return "text/plain"
