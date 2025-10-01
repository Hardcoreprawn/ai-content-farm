"""
Test the functional refactor integration.

This tests that the site-generator functional refactor components
work together correctly.
"""

from unittest.mock import Mock

import pytest
from content_processing_functions import generate_markdown_batch, generate_static_site
from models import GenerationRequest, GenerationResponse


class TestFunctionalRefactorIntegration:
    """Test that functional components integrate correctly after refactor."""

    def test_content_download_operations_import(self):
        """Test that content_download_operations can be imported (resolves blob_operations conflict)."""
        from content_download_operations import download_blob_content

        assert callable(download_blob_content)

    def test_functional_imports_work(self):
        """Test that all functional components can be imported without conflicts."""
        from content_processing_functions import (
            generate_markdown_batch,
            generate_static_site,
        )
        from content_utility_functions import get_processed_articles
        from functional_config import create_generator_context, load_configuration

        # All should be callable
        assert callable(create_generator_context)
        assert callable(load_configuration)
        assert callable(generate_markdown_batch)
        assert callable(generate_static_site)
        assert callable(get_processed_articles)

    def test_models_work_with_functional_approach(self):
        """Test that our data models work correctly with functional implementations."""
        # Test GenerationRequest validation
        request = GenerationRequest(source="test", batch_size=10, force_regenerate=True)
        assert request.source == "test"
        assert request.batch_size == 10
        assert request.force_regenerate is True

        # Test GenerationResponse creation
        response = GenerationResponse(
            generator_id="test-123",
            operation_type="test",
            files_generated=5,
            processing_time=1.0,
            output_location="test/location",
            generated_files=["test1.md", "test2.md"],  # Required field
        )
        assert response.generator_id == "test-123"
        assert response.files_generated == 5

    def test_main_app_components_import(self):
        """Test that main.py components can be imported without initialization errors."""
        # These should import without requiring Azure credentials
        try:
            from main import get_generator_context

            assert callable(get_generator_context)
        except ImportError as e:
            pytest.fail(f"Main app components failed to import: {e}")

    def test_article_loading_uses_correct_blob_operations(self):
        """Test that article_loading uses the renamed content_download_operations."""
        import inspect

        import article_loading

        # Check that article_loading imports the right module
        source = inspect.getsource(article_loading)
        assert "from content_download_operations import download_blob_content" in source
        assert "from blob_operations import" not in source  # Should not use old import

    def test_functional_vs_class_based_separation(self):
        """Test that we can distinguish between functional and class-based implementations."""
        # Functional implementation (site-generator)
        from content_download_operations import download_blob_content

        assert callable(download_blob_content)

        # Class-based implementation (libs)
        from libs.blob_operations import BlobOperations

        assert hasattr(BlobOperations, "__init__")  # Should be a class

        # They should be different types - functions have __init__ too, so check differently
        assert str(type(download_blob_content)) == "<class 'function'>"


class TestImportStrategy:
    """Test that the import strategy works as documented."""

    def test_intra_container_imports(self):
        """Test imports within the same container work correctly."""
        # Should be able to import local modules directly
        from content_download_operations import download_blob_content
        from content_processing_functions import generate_markdown_batch
        from functional_config import create_generator_context

        assert callable(download_blob_content)
        assert callable(create_generator_context)
        assert callable(generate_markdown_batch)

    def test_shared_library_imports(self):
        """Test imports from shared libraries work correctly."""
        from libs import SecureErrorHandler
        from libs.shared_models import StandardResponse
        from libs.simplified_blob_client import SimplifiedBlobClient

        # Should be able to create instances
        response = StandardResponse(
            status="success", message="test", data={}, errors=[]
        )
        assert response.status == "success"

        # Classes should be importable
        assert hasattr(SimplifiedBlobClient, "__init__")
        assert hasattr(SecureErrorHandler, "__init__")

    def test_no_name_conflicts(self):
        """Test that there are no naming conflicts between local and shared modules."""
        # Local version
        from content_download_operations import download_blob_content

        # Shared version
        from libs.blob_operations import BlobOperations

        # Should be different and both work
        assert callable(download_blob_content)
        assert hasattr(BlobOperations, "__init__")

        # Function vs class - clearly different
        assert str(type(download_blob_content)) == "<class 'function'>"
        assert str(type(BlobOperations)) == "<class 'type'>"
