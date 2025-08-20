#!/usr/bin/env python3
"""
Quick debug test for blob storage.
"""

import os
import sys

from libs.blob_storage import BlobContainers, BlobStorageClient

sys.path.append("/workspaces/ai-content-farm/libs")


def test_blob_operations():
    """Test basic blob operations."""
    client = BlobStorageClient()

    # Test upload
    test_data = {"id": "debug_test", "content": "test"}
    client.upload_json(BlobContainers.ENRICHED_CONTENT, "debug_test.json", test_data)

    # Test list
    blobs = client.list_blobs(BlobContainers.ENRICHED_CONTENT)
    print("Blobs found:", len(blobs))
    for blob in blobs:
        print(f"  - {blob['name']}")

    # Test download
    downloaded = client.download_json(
        BlobContainers.ENRICHED_CONTENT, "debug_test.json"
    )
    print("Downloaded:", downloaded)


if __name__ == "__main__":
    test_blob_operations()
