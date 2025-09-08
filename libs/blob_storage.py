"""
Azure Blob Storage Client

Shared module for all containers to handle blob storage operations.
Works with both Azurite (local) and Azure Storage (production).
Uses managed identity and secure authentication patterns for Azure environments.

Updated: 2025-08-26 - Testing optimized CI/CD pipeline (fixed checkout steps)
"""

import io
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, BinaryIO, Dict, List, Optional, Union, cast
from unittest.mock import MagicMock

from azure.core.exceptions import AzureError, ResourceNotFoundError
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from azure.storage.blob import (
    BlobClient,
    BlobProperties,
    BlobServiceClient,
    ContainerClient,
)

logger = logging.getLogger(__name__)


# Module-level stores for mock mode so all instances share state
_MOCK_CONTAINERS: Dict[str, Dict[str, Any]] = {}
_MOCK_BLOBS: Dict[str, Dict[str, Any]] = {}


class BlobStorageClient:
    """Unified blob storage client for all environments with secure authentication."""

    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "development").lower()
        self._mock = os.getenv("BLOB_STORAGE_MOCK", "false").lower() == "true"
        self.storage_account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME", "")
        self.connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")

        try:
            if self._mock:
                # In-memory mock mode for fast tests without Azurite/Azure
                # Use module-level dictionaries to share state across instances
                logger.info("Blob storage client initialized in MOCK mode")
                return

            if self.environment == "development" and self.connection_string:
                # Local development with Azurite or connection string
                self.blob_service_client = BlobServiceClient.from_connection_string(
                    self.connection_string
                )
                logger.info(
                    "Blob storage client initialized with connection string (development)"
                )

            elif self.storage_account_name:
                # Production/Azure environment - use Container Apps managed identity
                # Following Microsoft's official Container Apps documentation pattern
                azure_client_id = os.getenv("AZURE_CLIENT_ID", "")

                # Debug authentication setup
                logger.info("=== AUTHENTICATION DEBUG ===")
                logger.info(f"AZURE_CLIENT_ID: {azure_client_id}")
                logger.info(f"Storage Account: {self.storage_account_name}")
                logger.info("Using Container Apps Managed Identity")

                # Add role assignment debug info
                logger.info("Expected RBAC: Storage Blob Data Contributor")
                logger.info("Expected scope: Storage Account level")
                logger.info("Role propagation: Can take up to 30 minutes")

                # Use DefaultAzureCredential with user-assigned managed identity
                # This is the officially supported pattern for Container Apps
                if azure_client_id:
                    credential = DefaultAzureCredential(
                        managed_identity_client_id=azure_client_id
                    )
                    logger.info(
                        f"Using DefaultAzureCredential with user-assigned managed identity: {azure_client_id}"
                    )
                else:
                    # Fallback to system-assigned managed identity
                    credential = DefaultAzureCredential()
                    logger.info(
                        "Using DefaultAzureCredential with system-assigned managed identity"
                    )

                account_url = (
                    f"https://{self.storage_account_name}.blob.core.windows.net"
                )
                self.blob_service_client = BlobServiceClient(
                    account_url=account_url, credential=credential
                )
                logger.info(
                    f"Blob storage client initialized for account: {self.storage_account_name}"
                )
                logger.info("=== END AUTHENTICATION DEBUG ===")

            else:
                # Fallback to connection string if provided
                if self.connection_string:
                    self.blob_service_client = BlobServiceClient.from_connection_string(
                        self.connection_string
                    )
                    logger.warning(
                        "Using connection string authentication - consider using managed identity for production"
                    )
                else:
                    raise ValueError(
                        "Either AZURE_STORAGE_ACCOUNT_NAME (for managed identity) or "
                        "AZURE_STORAGE_CONNECTION_STRING must be provided"
                    )

        except Exception as e:
            logger.error(f"Failed to initialize blob storage client: {e}")
            raise

    def test_connection(self, timeout_seconds: float = None) -> Dict[str, Any]:
        """Test the blob storage connection with retry logic for authentication failures.

        Args:
            timeout_seconds: Optional timeout for fast health checks. If provided,
                           limits total retry time to this value.
        """
        import random
        import time

        if self._mock:
            return {
                "status": "healthy",
                "connection_type": "mock",
                "message": "Mock storage client is working",
            }

        # Adjust retry behavior for health checks
        if timeout_seconds and timeout_seconds < 10:
            # Fast health check mode - single attempt with minimal delay
            max_retries = 1
            base_delay = 0.5
            max_delay = timeout_seconds / 2
        else:
            # Normal mode - full retry logic
            max_retries = 3
            base_delay = 2.0  # Start with 2 seconds
            max_delay = 30.0  # Cap at 30 seconds

        start_total = time.time()

        for attempt in range(max_retries):
            try:
                logger.info(
                    f"=== AUTHENTICATION TEST ATTEMPT {attempt + 1}/{max_retries} ==="
                )

                # Test access to the specific container we need (created by Terraform)
                start_time = time.time()
                logger.info("Testing access to container 'collected-content'...")

                # Get container client and test access
                container_client = self.ensure_container("collected-content")

                # Test that we can access the container properties
                container_props = container_client.get_container_properties()
                token_time = time.time() - start_time

                logger.info(
                    f"✅ Container access successful in {token_time:.2f}s, container: {container_props.name}"
                )

                return {
                    "status": "healthy",
                    "connection_type": (
                        "managed_identity"
                        if self.storage_account_name
                        else "connection_string"
                    ),
                    "environment": self.environment,
                    "storage_account": self.storage_account_name,
                    "message": f"Container access successful (token acquired in {token_time:.2f}s), container: collected-content",
                    "attempt": attempt + 1,
                    "token_acquisition_time": token_time,
                    "container_name": "collected-content",
                }

            except Exception as auth_error:
                error_msg = str(auth_error)
                error_type = type(auth_error).__name__
                is_last_attempt = attempt == max_retries - 1

                # Detailed error analysis for better diagnostics
                http_status = None
                request_id = None
                error_code = None

                if hasattr(auth_error, "response"):
                    response = getattr(auth_error, "response", None)
                    if response:
                        http_status = getattr(response, "status_code", None)
                        headers = getattr(response, "headers", {})
                        request_id = headers.get("x-ms-request-id", "N/A")

                        # Extract Azure error code from response content
                        if hasattr(response, "text"):
                            import re

                            # Handle both text property and text() method
                            response_text = (
                                response.text()
                                if callable(response.text)
                                else response.text
                            )
                            if isinstance(response_text, str):
                                error_code_match = re.search(
                                    r"<Code>([^<]+)</Code>", response_text
                                )
                                if error_code_match:
                                    error_code = error_code_match.group(1)

                # Categorize the error type for better diagnostics
                if (
                    "AuthorizationFailure" in error_msg
                    or error_code == "AuthorizationFailure"
                ):
                    error_category = "AUTHORIZATION_FAILURE"
                    diagnostic_msg = "Container has valid authentication but lacks required RBAC permissions"
                elif (
                    "AuthenticationFailed" in error_msg
                    or error_code == "AuthenticationFailed"
                ):
                    error_category = "AUTHENTICATION_FAILURE"
                    diagnostic_msg = (
                        "Failed to authenticate with Azure - managed identity issue"
                    )
                elif "Forbidden" in error_msg or http_status == 403:
                    error_category = "ACCESS_FORBIDDEN"
                    diagnostic_msg = (
                        "Access forbidden - check network rules and IP allowlist"
                    )
                elif (
                    "TokenUnavailable" in error_msg
                    or "CredentialUnavailable" in error_msg
                ):
                    error_category = "TOKEN_UNAVAILABLE"
                    diagnostic_msg = "Cannot acquire authentication token - managed identity not configured"
                else:
                    error_category = "UNKNOWN_ERROR"
                    diagnostic_msg = f"Unexpected error type: {error_type}"

                logger.error(f"❌ Storage access error (attempt {attempt + 1}):")
                logger.error(f"   Category: {error_category}")
                logger.error(f"   Error type: {error_type}")
                logger.error(f"   HTTP Status: {http_status or 'N/A'}")
                logger.error(f"   Azure Error Code: {error_code or 'N/A'}")
                logger.error(f"   Request ID: {request_id}")
                logger.error(f"   Error message: {error_msg}")
                logger.error(f"   Diagnosis: {diagnostic_msg}")

                # Check if this is a retryable error
                retryable_errors = [
                    "AuthorizationFailure",  # RBAC propagation delay
                    "TokenUnavailable",  # Temporary token issues
                    "CredentialUnavailableError",  # Temporary credential issues
                    "timeout",  # Network timeouts
                    "Connection",  # Connection issues
                ]

                is_retryable = any(err in error_msg for err in retryable_errors)

                if is_retryable and not is_last_attempt:
                    # Check if we're running out of time for health checks
                    if timeout_seconds:
                        elapsed = time.time() - start_total
                        if elapsed + base_delay > timeout_seconds:
                            logger.warning(
                                f"Health check timeout approaching ({elapsed:.1f}s/{timeout_seconds}s), skipping retry"
                            )
                            break

                    # Calculate exponential backoff with jitter
                    delay = min(base_delay * (2**attempt), max_delay)
                    jitter = random.uniform(0.1, 0.3) * delay  # 10-30% jitter
                    total_delay = delay + jitter

                    logger.warning(
                        f"Authentication attempt {attempt + 1} failed: {error_msg}. "
                        f"Retrying in {total_delay:.1f}s..."
                    )
                    time.sleep(total_delay)
                    continue
                else:
                    # Final attempt or non-retryable error
                    logger.error(
                        f"Authentication failed after {attempt + 1} attempts: {error_msg}"
                    )

                    return {
                        "status": "unhealthy",
                        "connection_type": (
                            "workload_identity"
                            if os.getenv("AZURE_FEDERATED_TOKEN_FILE", "")
                            else (
                                "managed_identity"
                                if self.storage_account_name
                                else "connection_string"
                            )
                        ),
                        "environment": self.environment,
                        "storage_account": self.storage_account_name,
                        "error": error_msg,
                        "error_type": error_type,
                        "error_category": error_category,
                        "http_status": http_status,
                        "azure_error_code": error_code,
                        "request_id": request_id,
                        "attempts": attempt + 1,
                        "azure_client_id": os.getenv("AZURE_CLIENT_ID", ""),
                        "federated_token_file": os.getenv(
                            "AZURE_FEDERATED_TOKEN_FILE", ""
                        ),
                        "message": diagnostic_msg,
                        "troubleshooting": {
                            "error_category": error_category,
                            "next_steps": (
                                "Wait 5-10 minutes for RBAC propagation"
                                if error_category == "AUTHORIZATION_FAILURE"
                                else (
                                    "Check managed identity configuration"
                                    if error_category == "AUTHENTICATION_FAILURE"
                                    else (
                                        "Verify network rules and IP allowlist"
                                        if error_category == "ACCESS_FORBIDDEN"
                                        else (
                                            "Check managed identity setup in Container Apps"
                                            if error_category == "TOKEN_UNAVAILABLE"
                                            else "Check logs for detailed error information"
                                        )
                                    )
                                )
                            ),
                            "check_rbac": f"az role assignment list --assignee {os.getenv('AZURE_CLIENT_ID', 'UNKNOWN')}",
                            "check_network": f"Verify Container Apps IP is allowed in storage account network rules",
                            "check_identity": f"Verify managed identity {os.getenv('AZURE_CLIENT_ID', 'UNKNOWN')} exists and is assigned to Container App",
                            "credential_chain": "DefaultAzureCredential tries: Environment → Workload Identity → Managed Identity → Local",
                        },
                    }

        # Should never reach here, but just in case
        return {
            "status": "unhealthy",
            "connection_type": (
                "managed_identity" if self.storage_account_name else "connection_string"
            ),
            "environment": self.environment,
            "storage_account": self.storage_account_name,
            "error": "Maximum retry attempts exceeded",
            "attempts": max_retries,
            "message": "Authentication failed after all retry attempts",
        }

    def ensure_container(self, container_name: str) -> ContainerClient:
        """Get container client for existing container (containers are created by Terraform)."""
        try:
            if self._mock:
                # Create container namespace if missing
                _MOCK_CONTAINERS.setdefault(container_name, {})
                # For mock mode, return a mock client to satisfy the type checker
                # The actual value won't be used since methods check self._mock first
                return cast(ContainerClient, MagicMock())

            # Container is guaranteed to exist via Terraform infrastructure
            # No need to check existence or create - just get the client
            container_client = self.blob_service_client.get_container_client(
                container_name
            )

            logger.debug(
                f"Using existing container '{container_name}' (created by Terraform)"
            )
            return container_client

        except Exception as e:
            logger.error(f"Failed to get container client for '{container_name}': {e}")
            raise

    def upload_json(
        self,
        container_name: str,
        blob_name: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """Upload JSON data to blob storage."""
        try:
            if self._mock:
                self.ensure_container(container_name)
                key = f"{container_name}/{blob_name}"
                _MOCK_BLOBS[key] = {
                    "content": json.dumps(data, indent=2, default=str),
                    "content_type": "application/json",
                    "metadata": metadata or {},
                    "last_modified": datetime.now(timezone.utc),
                }
                return f"mock://{key}"

            container_client = self.ensure_container(container_name)

            # Convert data to JSON string
            json_data = json.dumps(data, indent=2, default=str)

            # Prepare metadata
            blob_metadata = {
                "content_type": "application/json",
                "uploaded_at": datetime.now(timezone.utc).isoformat(),
                "service": "ai-content-farm",
            }
            if metadata:
                blob_metadata.update(metadata)

            # Upload blob
            blob_client = container_client.get_blob_client(blob_name)
            blob_client.upload_blob(
                json_data,
                overwrite=True,
                content_type="application/json",
                metadata=blob_metadata,
            )

            blob_url = blob_client.url
            logger.info(f"Uploaded JSON to blob: {container_name}/{blob_name}")
            return blob_url

        except Exception as e:
            logger.error(f"Failed to upload JSON to {container_name}/{blob_name}: {e}")
            raise

    def upload_text(
        self,
        container_name: str,
        blob_name: str,
        content: str,
        content_type: str = "text/plain",
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """Upload text content to blob storage."""
        try:
            if self._mock:
                self.ensure_container(container_name)
                key = f"{container_name}/{blob_name}"
                _MOCK_BLOBS[key] = {
                    "content": content,
                    "content_type": content_type,
                    "metadata": metadata or {},
                    "last_modified": datetime.now(timezone.utc),
                }
                return f"mock://{key}"

            container_client = self.ensure_container(container_name)

            # Prepare metadata
            blob_metadata = {
                "content_type": content_type,
                "uploaded_at": datetime.now(timezone.utc).isoformat(),
                "service": "ai-content-farm",
            }
            if metadata:
                blob_metadata.update(metadata)

            # Upload blob
            blob_client = container_client.get_blob_client(blob_name)
            blob_client.upload_blob(
                content,
                overwrite=True,
                content_type=content_type,
                metadata=blob_metadata,
            )

            blob_url = blob_client.url
            logger.info(f"Uploaded text to blob: {container_name}/{blob_name}")
            return blob_url

        except Exception as e:
            logger.error(f"Failed to upload text to {container_name}/{blob_name}: {e}")
            raise

    async def upload_binary(
        self,
        container_name: str,
        blob_name: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """Upload binary data to blob storage."""
        try:
            if self._mock:
                self.ensure_container(container_name)
                key = f"{container_name}/{blob_name}"
                blob_metadata = {
                    "uploaded_at": datetime.now(timezone.utc).isoformat(),
                    "service": "ai-content-farm",
                }
                if metadata:
                    blob_metadata.update(metadata)
                _MOCK_BLOBS[key] = {
                    "content": data,
                    "content_type": content_type,
                    "metadata": blob_metadata,
                    "last_modified": datetime.now(timezone.utc),
                }
                return f"mock://{key}"

            container_client = self.ensure_container(container_name)

            # Prepare metadata
            blob_metadata = {
                "uploaded_at": datetime.now(timezone.utc).isoformat(),
                "service": "ai-content-farm",
            }
            if metadata:
                blob_metadata.update(metadata)

            # Upload blob
            blob_client = container_client.get_blob_client(blob_name)
            blob_client.upload_blob(
                data,
                overwrite=True,
                content_type=content_type,
                metadata=blob_metadata,
            )

            blob_url = blob_client.url
            logger.info(f"Uploaded binary data to blob: {container_name}/{blob_name}")
            return blob_url

        except Exception as e:
            logger.error(
                f"Failed to upload binary data to {container_name}/{blob_name}: {e}"
            )
            raise

    def upload_html_site(
        self,
        container_name: str,
        site_files: Dict[str, str],
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """Upload an entire HTML site to blob storage."""
        try:
            if self._mock:
                self.ensure_container(container_name)
                base_metadata = {
                    "site_generated_at": datetime.now(timezone.utc).isoformat(),
                    "service": "ai-content-farm-ssg",
                }
                if metadata:
                    base_metadata.update(metadata)
                uploaded = {}
                for file_path, content in site_files.items():
                    key = f"{container_name}/{file_path}"
                    _MOCK_BLOBS[key] = {
                        "content": content,
                        "content_type": self._get_content_type(file_path),
                        "metadata": {**base_metadata, "file_path": file_path},
                        "last_modified": datetime.now(timezone.utc),
                    }
                    uploaded[file_path] = f"mock://{key}"
                return uploaded

            container_client = self.ensure_container(container_name)

            # Prepare base metadata
            base_metadata = {
                "site_generated_at": datetime.now(timezone.utc).isoformat(),
                "service": "ai-content-farm-ssg",
            }
            if metadata:
                base_metadata.update(metadata)

            uploaded_files = {}

            for file_path, content in site_files.items():
                # Determine content type based on file extension
                content_type = self._get_content_type(file_path)

                # Prepare file-specific metadata
                file_metadata = base_metadata.copy()
                file_metadata["file_path"] = file_path

                # Upload file
                blob_client = container_client.get_blob_client(file_path)
                blob_client.upload_blob(
                    content,
                    overwrite=True,
                    content_type=content_type,
                    metadata=file_metadata,
                )

                uploaded_files[file_path] = blob_client.url
                logger.debug(f"Uploaded site file: {file_path}")

            logger.info(
                f"Uploaded {len(uploaded_files)} site files to container '{container_name}'"
            )
            return uploaded_files

        except Exception as e:
            logger.error(f"Failed to upload site files to {container_name}: {e}")
            raise

    def download_json(self, container_name: str, blob_name: str) -> Dict[str, Any]:
        """Download and parse JSON data from blob storage."""
        try:
            if self._mock:
                key = f"{container_name}/{blob_name}"
                blob = _MOCK_BLOBS.get(key)
                if not blob:
                    logger.warning(f"Blob not found: {key}")
                    return {}
                return (
                    json.loads(blob["content"])
                    if isinstance(blob.get("content"), str)
                    else blob.get("content", {})
                )

            container_client = self.ensure_container(container_name)
            blob_client = container_client.get_blob_client(blob_name)

            blob_data = blob_client.download_blob().readall()
            json_data = json.loads(blob_data.decode("utf-8"))

            logger.debug(f"Downloaded JSON from blob: {container_name}/{blob_name}")
            return json_data

        except ResourceNotFoundError:
            logger.warning(f"Blob not found: {container_name}/{blob_name}")
            return {}
        except Exception as e:
            logger.error(
                f"Failed to download JSON from {container_name}/{blob_name}: {e}"
            )
            raise

    def download_text(self, container_name: str, blob_name: str) -> str:
        """Download text content from blob storage."""
        try:
            if self._mock:
                key = f"{container_name}/{blob_name}"
                blob = _MOCK_BLOBS.get(key)
                if not blob:
                    logger.warning(f"Blob not found: {key}")
                    return ""
                content = blob.get("content", "")
                return content if isinstance(content, str) else json.dumps(content)

            container_client = self.ensure_container(container_name)
            blob_client = container_client.get_blob_client(blob_name)

            blob_data = blob_client.download_blob().readall()
            text_content = blob_data.decode("utf-8")

            logger.debug(f"Downloaded text from blob: {container_name}/{blob_name}")
            return text_content

        except ResourceNotFoundError:
            logger.warning(f"Blob not found: {container_name}/{blob_name}")
            return ""
        except Exception as e:
            logger.error(
                f"Failed to download text from {container_name}/{blob_name}: {e}"
            )
            raise

    def list_blobs(self, container_name: str, prefix: str = "") -> List[Dict[str, Any]]:
        """List blobs in a container with optional prefix filter."""
        try:
            if self._mock:
                results = []
                for key, blob in _MOCK_BLOBS.items():
                    if not key.startswith(f"{container_name}/"):
                        continue
                    name = key.split(f"{container_name}/", 1)[1]
                    if prefix and not name.startswith(prefix):
                        continue
                    results.append(
                        {
                            "name": name,
                            "size": (
                                len(blob.get("content", ""))
                                if isinstance(blob.get("content", ""), str)
                                else 0
                            ),
                            "last_modified": (
                                last_mod.isoformat()
                                if (last_mod := blob.get("last_modified")) is not None
                                else None
                            ),
                            "content_type": blob.get("content_type"),
                            "metadata": blob.get("metadata", {}),
                        }
                    )
                return results

            container_client = self.ensure_container(container_name)

            blobs = []
            blob_properties: BlobProperties
            for blob_properties in container_client.list_blobs(name_starts_with=prefix):
                blobs.append(
                    {
                        "name": blob_properties.name,
                        "size": blob_properties.size,
                        "last_modified": (
                            blob_properties.last_modified.isoformat()
                            if blob_properties.last_modified
                            else None
                        ),
                        "content_type": (
                            blob_properties.content_settings.content_type
                            if blob_properties.content_settings
                            else None
                        ),
                        "metadata": blob_properties.metadata or {},
                    }
                )

            logger.debug(
                f"Listed {len(blobs)} blobs from {container_name} with prefix '{prefix}'"
            )
            return blobs

        except Exception as e:
            logger.error(f"Failed to list blobs from {container_name}: {e}")
            raise

    def delete_blob(self, container_name: str, blob_name: str) -> bool:
        """Delete a blob from storage."""
        try:
            if self._mock:
                key = f"{container_name}/{blob_name}"
                if key in _MOCK_BLOBS:
                    del _MOCK_BLOBS[key]
                    return True
                return False

            container_client = self.ensure_container(container_name)
            blob_client = container_client.get_blob_client(blob_name)

            blob_client.delete_blob()
            logger.info(f"Deleted blob: {container_name}/{blob_name}")
            return True

        except ResourceNotFoundError:
            logger.warning(f"Blob not found for deletion: {container_name}/{blob_name}")
            return False
        except Exception as e:
            logger.error(f"Failed to delete blob {container_name}/{blob_name}: {e}")
            raise

    def get_blob_url(self, container_name: str, blob_name: str) -> str:
        """Get the URL for a blob."""
        try:
            if self._mock:
                return f"mock://{container_name}/{blob_name}"

            container_client = self.ensure_container(container_name)
            blob_client = container_client.get_blob_client(blob_name)
            return blob_client.url
        except Exception as e:
            logger.error(
                f"Failed to get blob URL for {container_name}/{blob_name}: {e}"
            )
            raise

    def _get_content_type(self, file_path: str) -> str:
        """Determine content type based on file extension."""
        extension = file_path.lower().split(".")[-1] if "." in file_path else ""

        content_types = {
            "html": "text/html",
            "htm": "text/html",
            "css": "text/css",
            "js": "application/javascript",
            "json": "application/json",
            "xml": "application/xml",
            "txt": "text/plain",
            "md": "text/markdown",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
            "svg": "image/svg+xml",
            "ico": "image/x-icon",
        }

        return content_types.get(extension, "application/octet-stream")

    def health_check(self) -> Dict[str, Any]:
        """Perform health check on blob storage connectivity."""
        try:
            if self._mock:
                return {
                    "status": "healthy",
                    "connection_type": "mock",
                    "environment": self.environment,
                    "containers_accessible": len(
                        set(k.split("/", 1)[0] for k in _MOCK_BLOBS.keys())
                    ),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            # Try to list containers to verify connectivity
            containers = list(self.blob_service_client.list_containers())

            return {
                "status": "healthy",
                "connection_type": (
                    "managed_identity"
                    if self.storage_account_name
                    else "connection_string"
                ),
                "environment": self.environment,
                "storage_account": self.storage_account_name
                or "connection_string_based",
                "containers_accessible": len(containers),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "connection_type": (
                    "managed_identity"
                    if self.storage_account_name
                    else "connection_string"
                ),
                "environment": self.environment,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }


# Container names for different services
class BlobContainers:
    """Standard container names for different content types."""

    COLLECTED_CONTENT = "collected-content"
    PROCESSED_CONTENT = "processed-content"
    ENRICHED_CONTENT = "enriched-content"
    RANKED_CONTENT = "ranked-content"
    MARKDOWN_CONTENT = "markdown-content"
    STATIC_SITES = "static-sites"
    PIPELINE_LOGS = "pipeline-logs"
    CMS_EXPORTS = "cms-exports"


def get_blob_client() -> BlobStorageClient:
    """Get a configured blob storage client."""
    return BlobStorageClient()


def get_timestamped_blob_name(prefix: str, extension: str = "json") -> str:
    """Generate a timestamped blob name."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.{extension}"
