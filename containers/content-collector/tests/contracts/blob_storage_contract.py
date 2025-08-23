"""
Azure Blob Storage API Contract - Defines expected Azure Blob Storage behavior.

This ensures our mocks behave exactly like Azure Blob Storage, including
error conditions, response formats, and edge cases.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json


@dataclass
class BlobPropertiesContract:
    """Contract for Azure Blob properties."""

    name: str
    size: int
    last_modified: datetime
    etag: str
    content_type: str = "application/json"
    metadata: Optional[Dict[str, str]] = None

    @classmethod
    def create_mock(cls, name: str, **overrides) -> "BlobPropertiesContract":
        """Create mock blob properties."""
        defaults = {
            "name": name,
            "size": 1024,
            "last_modified": datetime.now(),
            "etag": f'"0x8D{name.replace("/", "").replace(".", "")}"',
            "content_type": "application/json",
            "metadata": {}
        }
        defaults.update(overrides)
        return cls(**defaults)


class MockBlobStorageContract:
    """Contract-based mock for Azure Blob Storage that behaves like the real service."""

    def __init__(self):
        """Initialize with realistic blob storage behavior."""
        self._containers: Dict[str, Dict[str, str]] = {}
        self._blob_properties: Dict[str, BlobPropertiesContract] = {}

    def upload_text(self, container_name: str, blob_name: str, content: str) -> Dict[str, Any]:
        """Upload text content to blob storage.

        Mimics Azure Blob Storage upload_blob response format.
        """
        # Ensure container exists
        if container_name not in self._containers:
            self._containers[container_name] = {}

        # Store the content
        self._containers[container_name][blob_name] = content

        # Create blob properties
        blob_key = f"{container_name}/{blob_name}"
        self._blob_properties[blob_key] = BlobPropertiesContract.create_mock(
            name=blob_name,
            size=len(content.encode('utf-8'))
        )

        # Return Azure-style response
        return {
            "etag": self._blob_properties[blob_key].etag,
            "last_modified": self._blob_properties[blob_key].last_modified,
            "version_id": None,
            "encryption_scope": None,
            "request_server_encrypted": True
        }

    def download_text(self, container_name: str, blob_name: str) -> str:
        """Download text content from blob storage.

        Mimics Azure Blob Storage download behavior including errors.
        """
        if container_name not in self._containers:
            raise Exception(f"Container '{container_name}' not found")

        if blob_name not in self._containers[container_name]:
            raise Exception(f"Blob '{blob_name}' not found in container '{container_name}'")

        return self._containers[container_name][blob_name]

    def list_blobs(self, container_name: str, prefix: str = "") -> List[Dict[str, Any]]:
        """List blobs in container with optional prefix filter.

        Returns Azure-style blob listing.
        """
        if container_name not in self._containers:
            return []

        blobs = []
        for blob_name, content in self._containers[container_name].items():
            if blob_name.startswith(prefix):
                blob_key = f"{container_name}/{blob_name}"
                properties = self._blob_properties.get(blob_key)

                blobs.append({
                    "name": blob_name,
                    "size": len(content.encode('utf-8')) if content else 0,
                    "last_modified": properties.last_modified if properties else datetime.now(),
                    "etag": properties.etag if properties else f'"mock_etag_{blob_name}"',
                    "content_type": "application/json"
                })

        return sorted(blobs, key=lambda x: x["name"])

    def container_exists(self, container_name: str) -> bool:
        """Check if container exists."""
        return container_name in self._containers

    def create_container(self, container_name: str) -> Dict[str, Any]:
        """Create a new container."""
        if container_name not in self._containers:
            self._containers[container_name] = {}
            return {"created": True}
        return {"created": False}  # Already exists


def create_realistic_collection_data(collection_id: str, items: List[Dict[str, Any]]) -> str:
    """Create realistic content collection data that matches production format."""
    collection_data = {
        "collection_id": collection_id,
        "metadata": {
            "total_collected": len(items),
            "timestamp": datetime.now().isoformat(),
            "collection_version": "1.0.0",
            "processing_summary": {
                "sources_processed": 1,
                "items_collected": len(items),
                "deduplication_enabled": True,
                "quality_filtering_applied": True
            }
        },
        "items": items,
        "provenance": {
            "collector_version": "1.2.0",
            "collection_method": "reddit_api_v1",
            "quality_checks": ["content_length", "score_threshold", "spam_detection"]
        }
    }

    return json.dumps(collection_data, indent=2)
