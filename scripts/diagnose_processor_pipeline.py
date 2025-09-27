#!/usr/bin/env python3
"""
Content Processor Diagnostic Tool

Tests each layer of the blob reading pipeline independently to identify
exactly where the failure occurs. Run this to diagnose why the processor
isn't finding blobs or processing content.

Usage: python3 scripts/diagnose_processor_pipeline.py
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

from libs.blob_auth import BlobAuthManager
from libs.data_contracts import ContractValidator, DataContractError
from libs.simplified_blob_client import SimplifiedBlobClient

# Add repository root to path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ProcessorDiagnostics:
    """Comprehensive processor pipeline diagnostics."""

    def __init__(self):
        self.results = {}

    async def run_all_tests(self):
        """Run complete diagnostic suite."""
        logger.info("🔍 Starting Content Processor Pipeline Diagnostics")
        logger.info("=" * 60)

        # Test each layer
        await self.test_environment_variables()
        await self.test_blob_authentication()
        await self.test_blob_connectivity()
        await self.test_container_access()
        await self.test_blob_discovery()
        await self.test_blob_download()
        await self.test_data_validation()

        # Summary
        self.print_summary()

    async def test_environment_variables(self):
        """Test required environment variables."""
        logger.info("1️⃣ Testing Environment Variables")

        required_vars = [
            "AZURE_STORAGE_ACCOUNT_NAME",
            "AZURE_STORAGE_CONNECTION_STRING",
            "AZURE_CLIENT_ID",
        ]

        found_vars = {}
        for var in required_vars:
            value = os.getenv(var)
            found_vars[var] = "✅ Present" if value else "❌ Missing"
            if value:
                logger.info(f"   {var}: {value[:20]}...")

        # Check if we have at least one auth method
        has_connection_string = bool(os.getenv("AZURE_STORAGE_CONNECTION_STRING"))
        has_account_name = bool(os.getenv("AZURE_STORAGE_ACCOUNT_NAME"))

        if has_connection_string:
            auth_status = "✅ Connection string available"
        elif has_account_name:
            auth_status = "✅ Account name + managed identity"
        else:
            auth_status = "❌ No authentication method available"

        self.results["environment"] = {
            "status": (
                "✅ Pass" if (has_connection_string or has_account_name) else "❌ Fail"
            ),
            "details": found_vars,
            "auth_method": auth_status,
        }

        logger.info(f"   Result: {self.results['environment']['status']}")
        logger.info("")

    async def test_blob_authentication(self):
        """Test blob storage authentication."""
        logger.info("2️⃣ Testing Blob Authentication")

        try:
            auth_manager = BlobAuthManager()
            blob_service_client = auth_manager.get_blob_service_client()

            if blob_service_client:
                logger.info("   ✅ BlobServiceClient created successfully")
                self.results["authentication"] = {
                    "status": "✅ Pass",
                    "client_created": True,
                    "account_url": (
                        blob_service_client.account_name
                        if hasattr(blob_service_client, "account_name")
                        else "Unknown"
                    ),
                }
            else:
                logger.error("   ❌ Failed to create BlobServiceClient")
                self.results["authentication"] = {
                    "status": "❌ Fail",
                    "client_created": False,
                    "error": "No client returned",
                }

        except Exception as e:
            logger.error(f"   ❌ Authentication failed: {e}")
            self.results["authentication"] = {"status": "❌ Fail", "error": str(e)}

        logger.info(f"   Result: {self.results['authentication']['status']}")
        logger.info("")

    async def test_blob_connectivity(self):
        """Test basic blob storage connectivity."""
        logger.info("3️⃣ Testing Blob Storage Connectivity")

        try:
            blob_client = SimplifiedBlobClient()
            connection_result = blob_client.test_connection()

            logger.info(f"   Connection status: {connection_result['status']}")
            logger.info(f"   Message: {connection_result['message']}")

            self.results["connectivity"] = {
                "status": (
                    "✅ Pass" if connection_result["status"] == "healthy" else "❌ Fail"
                ),
                "details": connection_result,
            }

        except Exception as e:
            logger.error(f"   ❌ Connectivity test failed: {e}")
            self.results["connectivity"] = {"status": "❌ Fail", "error": str(e)}

        logger.info(f"   Result: {self.results['connectivity']['status']}")
        logger.info("")

    async def test_container_access(self):
        """Test access to collected-content container."""
        logger.info("4️⃣ Testing Container Access")

        try:
            blob_client = SimplifiedBlobClient()

            # Try to list any blobs in the container (even empty result is success)
            blobs = await blob_client.list_blobs("collected-content", prefix="")

            logger.info(f"   ✅ Container accessible, found {len(blobs)} blobs")

            self.results["container_access"] = {
                "status": "✅ Pass",
                "blob_count": len(blobs),
                "container": "collected-content",
            }

        except Exception as e:
            logger.error(f"   ❌ Container access failed: {e}")
            self.results["container_access"] = {
                "status": "❌ Fail",
                "error": str(e),
                "container": "collected-content",
            }

        logger.info(f"   Result: {self.results['container_access']['status']}")
        logger.info("")

    async def test_blob_discovery(self):
        """Test blob discovery with actual collections."""
        logger.info("5️⃣ Testing Blob Discovery")

        try:
            blob_client = SimplifiedBlobClient()

            # List blobs with collections prefix
            blobs = await blob_client.list_blobs(
                "collected-content", prefix="collections/"
            )

            logger.info(f"   Found {len(blobs)} collection blobs")

            if blobs:
                # Show recent blobs
                recent_blobs = sorted(
                    blobs, key=lambda b: b["last_modified"], reverse=True
                )[:3]
                logger.info("   Recent collections:")
                for blob in recent_blobs:
                    logger.info(
                        f"     - {blob['name']} ({blob['size']} bytes, {blob['last_modified']})"
                    )

                self.results["blob_discovery"] = {
                    "status": "✅ Pass",
                    "total_blobs": len(blobs),
                    "recent_blobs": [b["name"] for b in recent_blobs],
                }
            else:
                logger.warning("   ⚠️ No collection blobs found")
                self.results["blob_discovery"] = {
                    "status": "⚠️ Warning",
                    "total_blobs": 0,
                    "message": "No collections found - check collector",
                }

        except Exception as e:
            logger.error(f"   ❌ Blob discovery failed: {e}")
            self.results["blob_discovery"] = {"status": "❌ Fail", "error": str(e)}

        logger.info(f"   Result: {self.results['blob_discovery']['status']}")
        logger.info("")

    async def test_blob_download(self):
        """Test downloading and parsing a collection blob."""
        logger.info("6️⃣ Testing Blob Download & Parsing")

        try:
            blob_client = SimplifiedBlobClient()

            # Get a recent collection to test with
            blobs = await blob_client.list_blobs(
                "collected-content", prefix="collections/"
            )
            if not blobs:
                logger.warning("   ⚠️ No blobs to test download")
                self.results["blob_download"] = {
                    "status": "⚠️ Skip",
                    "message": "No blobs available",
                }
                return

            # Download the most recent blob
            recent_blob = sorted(blobs, key=lambda b: b["last_modified"], reverse=True)[
                0
            ]
            blob_name = recent_blob["name"]

            logger.info(f"   Testing download of: {blob_name}")

            collection_data = await blob_client.download_json(
                "collected-content", blob_name
            )

            if collection_data:
                items_count = len(collection_data.get("items", []))
                logger.info(f"   ✅ Downloaded and parsed JSON successfully")
                logger.info(f"   Collection has {items_count} items")

                # Show sample item
                if items_count > 0:
                    sample_item = collection_data["items"][0]
                    logger.info(
                        f"   Sample item: {sample_item.get('title', 'No title')[:50]}..."
                    )

                self.results["blob_download"] = {
                    "status": "✅ Pass",
                    "blob_tested": blob_name,
                    "items_count": items_count,
                    "has_metadata": "metadata" in collection_data,
                }
            else:
                logger.error("   ❌ Download returned None")
                self.results["blob_download"] = {
                    "status": "❌ Fail",
                    "error": "Download returned None",
                }

        except Exception as e:
            logger.error(f"   ❌ Blob download failed: {e}")
            self.results["blob_download"] = {"status": "❌ Fail", "error": str(e)}

        logger.info(f"   Result: {self.results['blob_download']['status']}")
        logger.info("")

    async def test_data_validation(self):
        """Test data contract validation."""
        logger.info("7️⃣ Testing Data Validation")

        try:
            blob_client = SimplifiedBlobClient()

            # Get a recent collection
            blobs = await blob_client.list_blobs(
                "collected-content", prefix="collections/"
            )
            if not blobs:
                logger.warning("   ⚠️ No blobs to test validation")
                self.results["data_validation"] = {
                    "status": "⚠️ Skip",
                    "message": "No blobs available",
                }
                return

            recent_blob = sorted(blobs, key=lambda b: b["last_modified"], reverse=True)[
                0
            ]
            collection_data = await blob_client.download_json(
                "collected-content", recent_blob["name"]
            )

            if not collection_data:
                logger.error("   ❌ No data to validate")
                self.results["data_validation"] = {
                    "status": "❌ Fail",
                    "error": "No data",
                }
                return

            # Test collection validation
            try:
                validated_collection = ContractValidator.validate_collection_data(
                    collection_data
                )
                logger.info(
                    f"   ✅ Collection validation passed ({len(validated_collection.items)} items)"
                )

                # Test item validation
                valid_items = 0
                # Test first 3 items
                for item_data in collection_data.get("items", [])[:3]:
                    try:
                        validated_item = ContractValidator.validate_collection_item(
                            item_data
                        )
                        valid_items += 1
                    except DataContractError:
                        pass  # Expected for some items

                logger.info(
                    f"   ✅ Item validation: {valid_items}/3 sample items valid"
                )

                self.results["data_validation"] = {
                    "status": "✅ Pass",
                    "collection_valid": True,
                    "sample_items_valid": valid_items,
                    "total_items": len(collection_data.get("items", [])),
                }

            except DataContractError as e:
                logger.warning(f"   ⚠️ Collection validation failed: {e}")
                self.results["data_validation"] = {
                    "status": "⚠️ Warning",
                    "collection_valid": False,
                    "error": str(e),
                    "message": "Validation issues - debug_bypass recommended",
                }

        except Exception as e:
            logger.error(f"   ❌ Data validation test failed: {e}")
            self.results["data_validation"] = {"status": "❌ Fail", "error": str(e)}

        logger.info(f"   Result: {self.results['data_validation']['status']}")
        logger.info("")

    def print_summary(self):
        """Print diagnostic summary."""
        logger.info("📊 DIAGNOSTIC SUMMARY")
        logger.info("=" * 60)

        for test_name, result in self.results.items():
            status = result.get("status", "❓ Unknown")
            logger.info(f"{test_name.replace('_', ' ').title()}: {status}")

        # Overall assessment
        failures = [
            name
            for name, result in self.results.items()
            if result.get("status", "").startswith("❌")
        ]
        warnings = [
            name
            for name, result in self.results.items()
            if result.get("status", "").startswith("⚠️")
        ]

        logger.info("")
        if failures:
            logger.error(f"❌ {len(failures)} CRITICAL FAILURES: {', '.join(failures)}")
            logger.error("Pipeline will not work until these are resolved.")
        elif warnings:
            logger.warning(f"⚠️ {len(warnings)} WARNINGS: {', '.join(warnings)}")
            logger.warning("Consider using debug_bypass=true to skip validation.")
        else:
            logger.info("✅ ALL TESTS PASSED - Pipeline should work normally!")

        logger.info("")
        logger.info("🔧 RECOMMENDATIONS:")

        if "environment" in failures:
            logger.info(
                "- Set AZURE_STORAGE_ACCOUNT_NAME or AZURE_STORAGE_CONNECTION_STRING"
            )
        if "authentication" in failures:
            logger.info("- Check managed identity configuration")
            logger.info("- Verify AZURE_CLIENT_ID if using user-assigned identity")
        if "container_access" in failures:
            logger.info("- Verify 'collected-content' container exists")
            logger.info("- Check Storage Blob Data Reader role assignment")
        if "blob_discovery" in warnings:
            logger.info("- Run collector to generate content")
            logger.info("- Check collection scheduling")
        if "data_validation" in warnings:
            logger.info("- Use debug_bypass=true in wake-up requests")
            logger.info("- Check collection format compliance")


async def main():
    """Run diagnostics."""
    diagnostics = ProcessorDiagnostics()
    await diagnostics.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
