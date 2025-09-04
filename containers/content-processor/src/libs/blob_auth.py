"""
Blob storage authentication and connection management

Handles authentication and connection setup for Azure Blob Storage.
Supports multiple authentication methods and environments.
"""

import logging
import os
from typing import Optional

from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from azure.storage.blob import BlobServiceClient

logger = logging.getLogger(__name__)


class BlobAuthManager:
    """Manages authentication and connections for blob storage."""

    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "development").lower()
        self.storage_account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME", "")
        self.connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")

    def get_blob_service_client(self) -> Optional[BlobServiceClient]:
        """Get authenticated blob service client."""
        try:
            if self.connection_string:
                # Use connection string (works for both Azurite and Azure)
                client = BlobServiceClient.from_connection_string(
                    conn_str=self.connection_string
                )
                logger.info("Connected to blob storage using connection string")
                return client

            elif self.storage_account_name:
                # Use managed identity for secure Azure authentication
                if self.environment == "production":
                    # Production: Use system-assigned managed identity
                    credential = ManagedIdentityCredential()
                    logger.info("Using managed identity for production authentication")
                else:
                    # Development/testing: Use default credential chain
                    credential = DefaultAzureCredential()
                    logger.info("Using default Azure credential for authentication")

                account_url = (
                    f"https://{self.storage_account_name}.blob.core.windows.net"
                )
                client = BlobServiceClient(
                    account_url=account_url, credential=credential
                )
                logger.info(f"Connected to Azure blob storage: {account_url}")
                return client

            else:
                logger.warning("No blob storage credentials found")
                return None

        except Exception as e:
            logger.error(f"Failed to initialize blob storage client: {e}")
            return None

    def test_connection(self) -> bool:
        """Test blob storage connection."""
        try:
            client = self.get_blob_service_client()
            if not client:
                return False

            # Test by listing containers (minimal operation)
            list(client.list_containers())
            return True

        except Exception as e:
            logger.error(f"Blob storage connection test failed: {e}")
            return False
