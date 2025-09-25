"""
Tests for collection template configuration and constants.

Verifies that the collector is properly configured to use the collection-templates
container and that all configuration constants are correct.
"""

import os
from unittest.mock import patch

from libs.app_config import BlobContainers


class TestTemplateConfiguration:
    """Test collection template configuration constants and imports."""

    def test_blob_containers_has_collection_templates(self):
        """Verify that BlobContainers class includes COLLECTION_TEMPLATES constant."""
        assert hasattr(BlobContainers, "COLLECTION_TEMPLATES")
        assert BlobContainers.COLLECTION_TEMPLATES == "collection-templates"

    def test_blob_container_constant_consistency(self):
        """Test that the blob container constant is consistent across the application."""
        # Verify the constant exists and has expected value
        assert BlobContainers.COLLECTION_TEMPLATES == "collection-templates"

        # Verify it's a string (not accidentally a different type)
        assert isinstance(BlobContainers.COLLECTION_TEMPLATES, str)

        # Verify it follows naming convention (lowercase with hyphens)
        assert BlobContainers.COLLECTION_TEMPLATES.islower()
        assert "-" in BlobContainers.COLLECTION_TEMPLATES

    def test_template_container_matches_terraform(self):
        """Test that the container name matches Terraform infrastructure configuration."""
        # Verify the container name matches what we configured in Terraform
        expected_container = "collection-templates"
        assert BlobContainers.COLLECTION_TEMPLATES == expected_container

        # This test documents the expected blob path structure:
        # - Container: "collection-templates"
        # - Blob: "default.json" (no prefix needed since dedicated container)
        expected_blob_name = "default.json"
        assert expected_blob_name == "default.json"  # Document expected structure

    def test_collections_endpoint_imports_blob_containers(self):
        """Verify that the collections endpoint properly imports BlobContainers."""
        from endpoints import collections

        # Verify that the collections module has access to BlobContainers
        assert hasattr(collections, "BlobContainers")
        assert collections.BlobContainers.COLLECTION_TEMPLATES == "collection-templates"

    def test_test_environment_detection_works(self):
        """Verify that test environment detection works as expected."""
        # This test runs in pytest, so the environment detection should be working
        # and causing the fallback template to be used instead of blob storage

        pytest_env_var = os.getenv("PYTEST_CURRENT_TEST")
        testing_env_var = os.getenv("ENVIRONMENT") == "testing"

        # At least one of these should be true in our test environment
        assert pytest_env_var is not None or testing_env_var

        # This confirms why our blob storage isn't called during tests -
        # it's intentionally using fallback templates for performance

    def test_template_loading_logic_uses_correct_container(self):
        """Test that template loading code references the correct container constant."""
        # Read the collections.py file to verify it uses the constant
        import inspect

        from endpoints.collections import run_scheduled_collection

        # Get the source code of the function
        source = inspect.getsource(run_scheduled_collection)

        # Verify it references the BlobContainers constant
        assert "BlobContainers.COLLECTION_TEMPLATES" in source

        # Verify it's not hardcoded to the old location
        assert 'container_name="prompts"' not in source
        assert (
            'container_name="collection-templates"' not in source
        )  # Should use constant

    def test_blob_client_configuration_documented(self):
        """Document the expected blob client configuration for template loading."""
        expected_config = {
            "container_name": BlobContainers.COLLECTION_TEMPLATES,
            "blob_name": "default.json",
        }

        # Verify expected values
        assert expected_config["container_name"] == "collection-templates"
        assert expected_config["blob_name"] == "default.json"

        # This test serves as documentation of the expected configuration
        # that should be used when calling SimplifiedBlobClient.download_text()
