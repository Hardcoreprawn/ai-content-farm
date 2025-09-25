"""
Migration Integration Test

Tests SimplifiedBlobClient against real Azure Storage to ensure
it works correctly before migrating containers.

Run this script to validate the new API in your environment:
python tests/test_migration_integration.py
"""

import asyncio
import json
import os
import sys
from datetime import datetime

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from simplified_blob_client import SimplifiedBlobClient

# Add libs to path first
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "libs"))


async def test_simplified_client():
    """Integration test with real Azure Storage."""

    print("🧪 Testing SimplifiedBlobClient integration...")

    # Initialize with Azure authentication
    try:
        # Use the same storage account as existing containers
        storage_account_url = os.getenv("AZURE_STORAGE_ACCOUNT_URL")
        if not storage_account_url:
            print("❌ AZURE_STORAGE_ACCOUNT_URL environment variable not set")
            return False

        credential = DefaultAzureCredential()
        blob_service_client = BlobServiceClient(
            account_url=storage_account_url, credential=credential
        )

        client = SimplifiedBlobClient(blob_service_client)

    except Exception as e:
        print(f"❌ Failed to initialize Azure client: {e}")
        return False

    # Test container for migration validation
    test_container = "pipeline-logs"  # Use existing container
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    try:
        print(f"📝 Testing JSON operations in container '{test_container}'...")

        # Test 1: Upload JSON (content collector pattern)
        test_data = {
            "test_timestamp": timestamp,
            "topics": [
                {"id": "test_1", "title": "Test Topic 1", "score": 0.95},
                {"id": "test_2", "title": "Test Topic 2", "score": 0.87},
            ],
            "metadata": {"source": "migration_test", "version": "1.0"},
        }

        json_blob = f"test-data-{timestamp}.json"
        result = await client.upload_json(test_container, json_blob, test_data)
        if not result:
            print("❌ Failed to upload JSON")
            return False
        print(f"✅ JSON uploaded successfully: {json_blob}")

        # Test 2: Download JSON (content processor pattern)
        downloaded_data = await client.download_json(test_container, json_blob)
        if downloaded_data != test_data:
            print("❌ Downloaded JSON doesn't match uploaded data")
            print(f"Expected: {test_data}")
            print(f"Got: {downloaded_data}")
            return False
        print("✅ JSON downloaded and verified successfully")

        # Test 3: Upload Text (site generator pattern)
        markdown_content = f"""# Test Article {timestamp}

This is a test markdown article generated during migration testing.

## Topics Found
- {test_data['topics'][0]['title']} (Score: {test_data['topics'][0]['score']})
- {test_data['topics'][1]['title']} (Score: {test_data['topics'][1]['score']})

Generated at: {test_data['test_timestamp']}
"""

        text_blob = f"test-article-{timestamp}.md"
        result = await client.upload_text(test_container, text_blob, markdown_content)
        if not result:
            print("❌ Failed to upload text/markdown")
            return False
        print(f"✅ Markdown uploaded successfully: {text_blob}")

        # Test 4: Download Text (site generator HTML conversion)
        downloaded_text = await client.download_text(test_container, text_blob)
        if downloaded_text != markdown_content:
            print("❌ Downloaded text doesn't match uploaded content")
            return False
        print("✅ Text downloaded and verified successfully")

        # Test 5: Binary operations (future media support)
        binary_data = b"PNG fake image data for testing: " + timestamp.encode("utf-8")
        binary_blob = f"test-image-{timestamp}.png"

        result = await client.upload_binary(
            test_container, binary_blob, binary_data, "image/png"
        )
        if not result:
            print("❌ Failed to upload binary data")
            return False
        print(f"✅ Binary data uploaded successfully: {binary_blob}")

        downloaded_binary = await client.download_binary(test_container, binary_blob)
        if downloaded_binary != binary_data:
            print("❌ Downloaded binary doesn't match uploaded data")
            return False
        print("✅ Binary data downloaded and verified successfully")

        # Test 6: List blobs (cleanup operations)
        blobs = await client.list_blobs(test_container, f"test-")
        expected_blobs = [json_blob, text_blob, binary_blob]

        for expected_blob in expected_blobs:
            if expected_blob not in blobs:
                print(f"❌ Expected blob not found in listing: {expected_blob}")
                print(f"Found blobs: {blobs}")
                return False
        print(f"✅ Blob listing verified ({len(expected_blobs)} blobs found)")

        # Test 7: Cleanup (delete operations)
        for blob in expected_blobs:
            result = await client.delete_blob(test_container, blob)
            if not result:
                print(f"❌ Failed to delete blob: {blob}")
                return False
        print(f"✅ Cleanup completed ({len(expected_blobs)} blobs deleted)")

        # Verify cleanup
        remaining_blobs = await client.list_blobs(test_container, f"test-{timestamp}")
        if remaining_blobs:
            print(f"⚠️  Warning: Some test blobs were not cleaned up: {remaining_blobs}")

        print("\n🎉 All SimplifiedBlobClient tests passed!")
        print("✅ Safe to proceed with container migration")
        return True

    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_compatibility_layer():
    """Test the compatibility adapter for gradual migration."""

    print("\n🔄 Testing compatibility layer for gradual migration...")

    try:
        storage_account_url = os.getenv("AZURE_STORAGE_ACCOUNT_URL")
        credential = DefaultAzureCredential()
        blob_service_client = BlobServiceClient(
            account_url=storage_account_url, credential=credential
        )

        from simplified_blob_client import BlobClientAdapter, SimplifiedBlobClient

        simplified_client = SimplifiedBlobClient(blob_service_client)
        adapter = BlobClientAdapter(simplified_client)

        # Test legacy methods still work
        test_container = "pipeline-logs"  # Use existing container
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

        # Legacy upload_data method
        legacy_data = f"Legacy test data: {timestamp}"
        result = await adapter.upload_data(
            test_container, f"legacy-{timestamp}.txt", legacy_data
        )
        if not result:
            print("❌ Legacy upload_data method failed")
            return False
        print("✅ Legacy upload_data method works")

        # Legacy download_data method
        downloaded = await adapter.download_data(
            test_container, f"legacy-{timestamp}.txt"
        )
        if downloaded != legacy_data:
            print("❌ Legacy download_data method failed")
            return False
        print("✅ Legacy download_data method works")

        # Cleanup
        await simplified_client.delete_blob(test_container, f"legacy-{timestamp}.txt")

        print("✅ Compatibility layer works - containers can migrate gradually")
        return True

    except Exception as e:
        print(f"❌ Compatibility test failed: {e}")
        return False


async def main():
    """Run all migration tests."""

    print("🚀 Starting SimplifiedBlobClient Migration Tests")
    print("=" * 60)

    # Check environment
    if not os.getenv("AZURE_STORAGE_ACCOUNT_URL"):
        print("💡 Set AZURE_STORAGE_ACCOUNT_URL to run integration tests")
        print(
            "   Example: export AZURE_STORAGE_ACCOUNT_URL='https://youraccount.blob.core.windows.net'"
        )
        return

    success = True

    # Test new simplified client
    success &= await test_simplified_client()

    # Test compatibility for migration
    success &= await test_compatibility_layer()

    print("\n" + "=" * 60)
    if success:
        print("🎉 ALL TESTS PASSED - Ready for container migration!")
        print("\n📋 Migration Plan:")
        print("1. Deploy SimplifiedBlobClient to libs/")
        print("2. Update containers one by one to use new API")
        print("3. Use BlobClientAdapter for gradual migration")
        print("4. Remove old BlobOperations once all containers migrated")
        print("5. Clean up 300+ lines of redundant code")
    else:
        print("❌ TESTS FAILED - Fix issues before migrating containers")


if __name__ == "__main__":
    asyncio.run(main())
