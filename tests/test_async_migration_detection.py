"""
Breaking change detection tests for blob storage async migration.

These tests verify that all blob storage method calls are properly awaited,
and will fail if any synchronous calls are found in the codebase.
"""

import ast
import os
from pathlib import Path
from typing import List, Tuple

import pytest


class BlobStorageAsyncChecker(ast.NodeVisitor):
    """AST visitor to find blob storage method calls."""

    def __init__(self):
        self.sync_calls: List[Tuple[str, int, str]] = []
        self.async_calls: List[Tuple[str, int, str]] = []
        self.current_file = ""

    def visit_Call(self, node):
        """Check for blob storage method calls."""
        blob_methods = {
            "upload_json",
            "upload_text",
            "upload_binary",
            "download_json",
            "download_text",
            "list_blobs",
            "delete_blob",
        }

        # Check if this is a method call on blob_client or storage
        if isinstance(node.func, ast.Attribute) and node.func.attr in blob_methods:

            # Check if the call is awaited
            parent = getattr(node, "parent", None)
            is_awaited = isinstance(parent, ast.Await)

            call_info = (self.current_file, node.lineno, f"{node.func.attr}()")

            if is_awaited:
                self.async_calls.append(call_info)
            else:
                self.sync_calls.append(call_info)

        self.generic_visit(node)

    def visit(self, node):
        """Override visit to track parent nodes."""
        for child in ast.iter_child_nodes(node):
            child.parent = node
        return super().visit(node)


def find_python_files(directory: str) -> List[Path]:
    """Find all Python files in directory."""
    path = Path(directory)
    return list(path.rglob("*.py"))


class TestBlobStorageAsyncMigration:
    """Test blob storage async migration compliance."""

    def test_no_sync_blob_calls_in_containers(self):
        """Test that all blob storage calls in containers are async."""
        checker = BlobStorageAsyncChecker()
        container_files = find_python_files("containers")

        for file_path in container_files:
            if not file_path.exists():
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    source = f.read()

                tree = ast.parse(source)
                checker.current_file = str(file_path)
                checker.visit(tree)

            except (SyntaxError, UnicodeDecodeError):
                # Skip files that can't be parsed
                continue

        # Report findings
        if checker.sync_calls:
            sync_call_details = "\n".join(
                [
                    f"  {file}:{line} - {method}"
                    for file, line, method in checker.sync_calls
                ]
            )
            pytest.fail(
                f"Found {len(checker.sync_calls)} synchronous blob storage calls that need to be updated to async:\n"
                f"{sync_call_details}\n\n"
                f"These calls should be updated to use 'await' keyword."
            )

        # Verify we found some async calls (sanity check)
        assert (
            len(checker.async_calls) > 0
        ), "Expected to find some async blob storage calls"

    def test_blob_storage_method_signatures_are_async(self):
        """Test that blob storage methods are properly defined as async."""
        import inspect

        from libs.blob_storage import BlobStorageClient

        client = BlobStorageClient()

        async_methods = [
            "upload_json",
            "upload_text",
            "upload_binary",
            "download_json",
            "download_text",
            "list_blobs",
            "delete_blob",
        ]

        for method_name in async_methods:
            method = getattr(client, method_name)
            assert inspect.iscoroutinefunction(
                method
            ), f"BlobStorageClient.{method_name} should be an async method"


class TestContainerAsyncPatterns:
    """Test that containers properly use async patterns."""

    @pytest.mark.asyncio
    async def test_content_collector_async_compatibility(self):
        """Test that content collector can work with async blob storage."""
        # Create client in mock mode
        import os

        from libs.blob_storage import BlobStorageClient

        with pytest.MonkeyPatch.context() as m:
            m.setenv("BLOB_STORAGE_MOCK", "true")
            client = BlobStorageClient()

            # Test that we can perform async operations
            test_data = {"test": "content_collector"}
            url = await client.upload_json("test-collector", "test.json", test_data)
            assert url is not None

            downloaded = await client.download_json("test-collector", "test.json")
            assert downloaded == test_data

    @pytest.mark.asyncio
    async def test_site_generator_async_compatibility(self):
        """Test that site generator can work with async blob storage."""
        import os

        from libs.blob_storage import BlobStorageClient

        with pytest.MonkeyPatch.context() as m:
            m.setenv("BLOB_STORAGE_MOCK", "true")
            client = BlobStorageClient()

            # Test site generation workflow
            html_content = "<html><body>Test Site</body></html>"
            url = await client.upload_text(
                "published-sites",
                "test-site.html",
                html_content,
                content_type="text/html",
            )
            assert url is not None

            # Test listing capability
            blobs = await client.list_blobs("published-sites")
            assert len(blobs) >= 1
            assert any(blob["name"] == "test-site.html" for blob in blobs)


class TestAsyncMigrationGuide:
    """Tests that provide migration guidance for async transition."""

    def test_sync_to_async_conversion_examples(self):
        """Provide examples of how to convert sync calls to async."""
        # This test documents the required changes

        sync_examples = [
            "storage.upload_json(container, name, data)",
            "content = storage.download_json(container, name)",
            "blobs = storage.list_blobs(container)",
            "deleted = storage.delete_blob(container, name)",
        ]

        async_examples = [
            "await storage.upload_json(container, name, data)",
            "content = await storage.download_json(container, name)",
            "blobs = await storage.list_blobs(container)",
            "deleted = await storage.delete_blob(container, name)",
        ]

        print("\n=== ASYNC MIGRATION GUIDE ===")
        print("Convert these synchronous calls:")
        for sync_call in sync_examples:
            print(f"  BEFORE: {sync_call}")

        print("\nTo these asynchronous calls:")
        for async_call in async_examples:
            print(f"  AFTER:  {async_call}")

        print("\nALSO REQUIRED:")
        print("  1. Add 'async' to function definitions that call blob storage")
        print("  2. Add 'await' when calling functions that use blob storage")
        print("  3. Update tests to use @pytest.mark.asyncio")
        print("  4. Update FastAPI routes to be async if they use blob storage")

        # This test always passes but documents the migration
        assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
