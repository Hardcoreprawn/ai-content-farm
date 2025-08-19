"""
Azure Blob Storage Client

Shared module for all containers to handle blob storage operations.
Works with both Azurite (local) and Azure Storage (production).
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, BinaryIO, Union
from datetime import datetime, timezone
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from azure.core.exceptions import AzureError, ResourceNotFoundError
import io

logger = logging.getLogger(__name__)


class BlobStorageClient:
    """Unified blob storage client for all environments."""

    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "development").lower()
        self.connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

        if not self.connection_string:
            raise ValueError(
                "AZURE_STORAGE_CONNECTION_STRING environment variable is required")

        try:
            self.blob_service_client = BlobServiceClient.from_connection_string(
                self.connection_string
            )
            logger.info(
                f"Blob storage client initialized for {self.environment} environment")
        except Exception as e:
            logger.error(f"Failed to initialize blob storage client: {e}")
            raise

    def ensure_container(self, container_name: str) -> ContainerClient:
        """shim: re-export canonical blob client from libs.blob_storage

        This file intentionally re-exports the implementation from the top-level
        `libs` package to avoid duplicating code. Keep this shim so modules that
        import `blob_storage` locally still work during the transition.
        """

        from libs.blob_storage import BlobStorageClient, BlobContainers, get_blob_client, get_timestamped_blob_name

        __all__ = [
            "BlobStorageClient",
            "BlobContainers",
            "get_blob_client",
            "get_timestamped_blob_name",
        ]
