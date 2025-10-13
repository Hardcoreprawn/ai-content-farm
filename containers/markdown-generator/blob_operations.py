"""
I/O functions for Azure Blob Storage operations.

This module contains functions with explicit side effects for reading and
writing data to Azure Blob Storage.
"""

import json
import logging
from typing import Any, Dict

from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import BlobServiceClient

logger = logging.getLogger(__name__)

__all__ = [
    "read_json_from_blob",
    "write_markdown_to_blob",
]


def read_json_from_blob(
    blob_service_client: BlobServiceClient, container_name: str, blob_name: str
) -> Dict[str, Any]:
    """
    Read and parse JSON blob from storage.

    I/O function with explicit side effects (Azure read operation).

    Args:
        blob_service_client: Azure Blob Service client
        container_name: Container to read from
        blob_name: Name of blob to read

    Returns:
        Dict containing parsed JSON data

    Raises:
        ResourceNotFoundError: If blob doesn't exist
        ValueError: If blob contains invalid JSON

    Examples:
        >>> # See integration tests
        >>> pass
    """
    container_client = blob_service_client.get_container_client(container_name)
    blob_client = container_client.get_blob_client(blob_name)

    blob_data = blob_client.download_blob().readall()
    parsed_data: Dict[str, Any] = json.loads(blob_data)
    return parsed_data


def write_markdown_to_blob(
    blob_service_client: BlobServiceClient,
    container_name: str,
    blob_name: str,
    markdown_content: str,
    overwrite: bool,
) -> str:
    """
    Write markdown content to blob storage.

    I/O function with explicit side effects (Azure write operation).

    Args:
        blob_service_client: Azure Blob Service client
        container_name: Container to write to
        blob_name: Name of blob to create
        markdown_content: Markdown content to write
        overwrite: Whether to overwrite existing blob

    Returns:
        Name of created blob

    Raises:
        ValueError: If blob exists and overwrite is False

    Examples:
        >>> # See integration tests
        >>> pass
    """
    container_client = blob_service_client.get_container_client(container_name)
    blob_client = container_client.get_blob_client(blob_name)

    # Check if exists
    if not overwrite and blob_client.exists():
        raise ValueError(f"Markdown file already exists: {blob_name}")

    # Upload markdown
    blob_client.upload_blob(
        markdown_content, overwrite=overwrite, content_type="text/markdown"
    )

    return blob_name
