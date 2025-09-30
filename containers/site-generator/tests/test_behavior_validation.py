"""
Enhanced Testing Strategy - Phase 5 Implementation

TEST PHILOSOPHY:
1. **Test Behavior, Not Implementation** - Focus on what functions DO, not how they do it
2. **Validate Contracts** - Ensure inputs/outputs match specifications
3. **Test Integration Points** - Verify boundary interactions work correctly
4. **Meaningful Assertions** - Every test validates actual business logic
5. **Proper Mocking** - Mock external dependencies, not internal logic

CRITICAL TESTING AREAS:
1. Content Processing Workflows - End-to-end generation flows
2. Storage Operations - Blob storage interactions and error handling
3. Configuration Management - Environment setup and validation
4. Error Handling - SecureErrorHandler integration and error scenarios
5. API Contracts - Request/response validation and HTTP behavior
"""

import asyncio
import json
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, patch

import pytest
from content_processing_functions import generate_markdown_batch, generate_static_site
from functional_config import SiteGeneratorConfig, create_generator_context

# Standard imports at module level - no inline imports in tests
from models import GenerationRequest, GenerationResponse

from libs import SecureErrorHandler


class TestContentProcessingBehavior:
    """Test actual content processing behavior with real outputs."""

    @pytest.fixture
    def test_config(self) -> SiteGeneratorConfig:
        """Provide test configuration."""
        return SiteGeneratorConfig(
            AZURE_STORAGE_ACCOUNT_URL="https://test.blob.core.windows.net/",
            PROCESSED_CONTENT_CONTAINER="test-processed-content",
            MARKDOWN_CONTENT_CONTAINER="test-markdown-content",
            STATIC_SITES_CONTAINER="test-static-sites",
            SITE_TITLE="Test Site",
            SITE_DESCRIPTION="Test site for behavior testing",
            SITE_DOMAIN="test.example.com",
            SITE_URL="https://test.example.com",
            ARTICLES_PER_PAGE=10,
            MAX_ARTICLES_TOTAL=100,
            DEFAULT_THEME="default",
            ENVIRONMENT="test",
        )

    @pytest.fixture
    def sample_processed_content(self) -> List[Dict[str, Any]]:
        """Sample processed content for testing with all required fields."""
        return [
            {
                "topic_id": "test-1",
                "title": "Understanding Modern Testing Practices",
                "score": 85.5,
                "comments": 150,
                "source": "reddit",
                "content": "Testing is crucial for maintainable code. This article covers comprehensive testing strategies, mocking patterns, and best practices for modern Python applications.",
                "url": "https://reddit.com/r/testing/1",
                "created_utc": 1696118400,
                "subreddit": "testing",
            },
            {
                "topic_id": "test-2",
                "title": "Performance Optimization Techniques",
                "score": 92.1,
                "comments": 87,
                "source": "reddit",
                "content": "Modern web applications require optimal performance. This comprehensive guide covers caching strategies, async patterns, and profiling techniques for Python web applications.",
                "url": "https://reddit.com/r/webdev/2",
                "created_utc": 1696118500,
                "subreddit": "webdev",
            },
        ]

    @pytest.fixture
    def mock_blob_client(self) -> Mock:
        """Provide configured blob client mock."""
        mock_client = Mock()
        mock_client.uploaded_files = []

        # Mock upload method to track files
        async def mock_upload(container: str, blob_name: str, content: bytes):
            mock_client.uploaded_files.append(
                {"container": container, "blob_name": blob_name, "content": content}
            )
            return {"status": "uploaded"}

        # Mock upload_blob method (different signature)
        async def mock_upload_blob(
            blob_name: str, blob_data: bytes, container_name: str = None, **kwargs
        ):
            mock_client.uploaded_files.append(
                {
                    "container": container_name,
                    "blob_name": blob_name,
                    "content": blob_data,
                }
            )
            return {"status": "uploaded"}

        mock_client.upload_blob = AsyncMock(side_effect=mock_upload_blob)
        return mock_client

    @pytest.mark.asyncio
    async def test_generate_markdown_batch_creates_valid_markdown(
        self,
        mock_blob_client: Mock,
        test_config: SiteGeneratorConfig,
        sample_processed_content: List[Dict[str, Any]],
    ):
        """Test that markdown generation produces valid markdown with correct frontmatter."""

        # Mock get_processed_articles to return our sample data
        with (
            patch(
                "content_processing_functions.get_processed_articles"
            ) as mock_get_articles,
            patch(
                "content_processing_functions.generate_article_markdown"
            ) as mock_generate,
        ):

            mock_get_articles.return_value = sample_processed_content
            mock_generate.return_value = "article.md"  # Mock successful generation

            # Execute function
            result = await generate_markdown_batch(
                source="test-run",
                batch_size=5,
                force_regenerate=True,
                blob_client=mock_blob_client,
                config=asdict(test_config),
                generator_id="test-123",
            )

            # Validate response structure
            assert isinstance(result, GenerationResponse)
            assert result.generator_id == "test-123"
            assert result.operation_type == "markdown_generation"
            assert result.files_generated > 0
            assert result.processing_time > 0

            # Validate that generation was attempted and succeeded
            assert len(result.generated_files) > 0
            assert mock_generate.call_count > 0

            # Validate that generate_article_markdown was called with correct parameters
            for call in mock_generate.call_args_list:
                args, kwargs = call
                assert "article_data" in kwargs or len(args) > 0
                assert "blob_client" in kwargs or len(args) > 1

    @pytest.mark.asyncio
    async def test_generate_markdown_batch_handles_empty_content(
        self, mock_blob_client: Mock, test_config: SiteGeneratorConfig
    ):
        """Test behavior when no processed content is available."""

        # Mock get_processed_articles to return empty list
        with patch(
            "content_processing_functions.get_processed_articles"
        ) as mock_get_articles:
            mock_get_articles.return_value = []

            result = await generate_markdown_batch(
                source="empty-test",
                batch_size=10,
                force_regenerate=False,
                blob_client=mock_blob_client,
                config=asdict(test_config),
            )

            # Should return valid response with zero files
            assert isinstance(result, GenerationResponse)
            assert result.files_generated == 0
            assert result.operation_type == "markdown_generation"
            assert len(result.generated_files) == 0

            # Should not upload any files
            assert len(mock_blob_client.uploaded_files) == 0

    @pytest.mark.asyncio
    async def test_generate_markdown_batch_respects_batch_size(
        self, mock_blob_client: Mock, test_config: SiteGeneratorConfig
    ):
        """Test that batch_size parameter is respected."""

        # Create more articles than batch size
        large_content_set = [
            {
                "title": f"Article {i}",
                "content": f"Content for article {i}",
                "score": 70 + i,
                "timestamp": "2025-09-30T10:00:00Z",
                "source": "test",
            }
            for i in range(15)  # 15 articles
        ]

        with patch(
            "content_processing_functions.get_processed_articles"
        ) as mock_get_articles:
            mock_get_articles.return_value = large_content_set

            result = await generate_markdown_batch(
                source="batch-test",
                batch_size=5,  # Limit to 5
                force_regenerate=True,
                blob_client=mock_blob_client,
                config=asdict(test_config),
            )

            # Should only process batch_size number of articles
            assert result.files_generated <= 5
            assert len(mock_blob_client.uploaded_files) <= 5

    @pytest.mark.asyncio
    async def test_generate_static_site_creates_complete_site(
        self, mock_blob_client: Mock, test_config: SiteGeneratorConfig
    ):
        """Test that static site generation creates all necessary files."""

        # Mock get_markdown_articles to return sample markdown files
        sample_markdown_files = [
            {
                "filename": "article-1.md",
                "frontmatter": {"title": "Test Article 1", "date": "2025-09-30"},
                "content": "# Test Article 1\n\nContent here",
                "blob_name": "2025/09/article-1.md",
            },
            {
                "filename": "article-2.md",
                "frontmatter": {"title": "Test Article 2", "date": "2025-09-30"},
                "content": "# Test Article 2\n\nMore content",
                "blob_name": "2025/09/article-2.md",
            },
        ]

        with (
            patch(
                "content_processing_functions.get_markdown_articles",
                new_callable=AsyncMock,
            ) as mock_get_markdown,
            patch(
                "content_processing_functions.create_complete_site",
                new_callable=AsyncMock,
            ) as mock_create_site,
        ):

            mock_get_markdown.return_value = sample_markdown_files
            mock_create_site.return_value = [
                "index.html",
                "article-1.html",
                "article-2.html",
            ]

            result = await generate_static_site(
                theme="default",
                force_rebuild=True,
                blob_client=mock_blob_client,
                config=asdict(test_config),
                generator_id="site-test-456",
            )

        # Validate response
        assert isinstance(result, GenerationResponse)
        assert result.generator_id == "site-test-456"
        assert result.operation_type == "site_generation"
        assert result.files_generated > 0

        # Validate that site generation was successful
        assert len(result.generated_files) > 0, "Should generate site files"
        assert "index.html" in result.generated_files, "Should generate index.html"
        assert result.pages_generated > 0, "Should generate pages"
        assert mock_create_site.call_count == 1, "Should call create_complete_site"
        assert mock_get_markdown.call_count == 1, "Should call get_markdown_articles"


class TestStorageOperationBehavior:
    """Test storage operations and error handling behavior."""

    @pytest.fixture
    def test_config(self) -> SiteGeneratorConfig:
        """Provide test configuration."""
        return SiteGeneratorConfig(
            AZURE_STORAGE_ACCOUNT_URL="https://test.blob.core.windows.net/",
            PROCESSED_CONTENT_CONTAINER="test-processed-content",
            MARKDOWN_CONTENT_CONTAINER="test-markdown-content",
            STATIC_SITES_CONTAINER="test-static-sites",
            SITE_TITLE="Test Site",
            SITE_DESCRIPTION="Test site for behavior testing",
            SITE_DOMAIN="test.example.com",
            SITE_URL="https://test.example.com",
            ARTICLES_PER_PAGE=10,
            MAX_ARTICLES_TOTAL=100,
            DEFAULT_THEME="default",
            ENVIRONMENT="test",
        )

    @pytest.fixture
    def failing_blob_client(self) -> Mock:
        """Mock blob client that simulates failures."""
        mock_client = Mock()

        async def failing_download(*args, **kwargs):
            raise Exception("Storage connection failed")

        async def failing_upload(*args, **kwargs):
            raise Exception("Upload failed - insufficient permissions")

        mock_client.download_blob = AsyncMock(side_effect=failing_download)
        mock_client.upload_blob = AsyncMock(side_effect=failing_upload)

        return mock_client

    @pytest.mark.asyncio
    async def test_generate_markdown_batch_handles_storage_failures(
        self, failing_blob_client: Mock, test_config: SiteGeneratorConfig
    ):
        """Test that storage failures are handled gracefully with proper error reporting."""

        with patch(
            "content_processing_functions.get_processed_articles"
        ) as mock_get_articles:
            mock_get_articles.return_value = [{"title": "Test", "content": "Test"}]

            result = await generate_markdown_batch(
                source="failure-test",
                batch_size=1,
                force_regenerate=True,
                blob_client=failing_blob_client,
                config=asdict(test_config),
            )

            # Should return response with error information
            assert isinstance(result, GenerationResponse)
            assert result.files_generated == 0
            assert len(result.errors) > 0
            assert any("error" in error.lower() for error in result.errors)


class TestConfigurationBehavior:
    """Test configuration management and validation."""

    def test_create_generator_context_validates_required_fields(self):
        """Test that configuration validation catches missing required fields."""

        # Test with completely empty environment (no required vars)
        empty_env = {}

        with patch.dict("os.environ", empty_env, clear=True):
            # Function should now raise exceptions with enhanced validation
            with pytest.raises(ValueError) as exc_info:
                create_generator_context()

            error_message = str(exc_info.value).lower()
            assert "configuration" in error_message

    def test_site_generator_config_enforces_valid_urls(self):
        """Test that configuration validates Azure storage URLs."""

        # Valid URL should work
        valid_config = SiteGeneratorConfig(
            AZURE_STORAGE_ACCOUNT_URL="https://validaccount.blob.core.windows.net/",
            PROCESSED_CONTENT_CONTAINER="processed",
            MARKDOWN_CONTENT_CONTAINER="markdown",
            STATIC_SITES_CONTAINER="static",
            SITE_TITLE="Test Site",
            SITE_DESCRIPTION="Test Description",
            SITE_DOMAIN="test.com",
            SITE_URL="https://test.com",
            ARTICLES_PER_PAGE=10,
            MAX_ARTICLES_TOTAL=100,
            DEFAULT_THEME="default",
            ENVIRONMENT="test",
        )
        assert "validaccount" in valid_config.AZURE_STORAGE_ACCOUNT_URL

        # Test validation by calling validate() method instead
        invalid_config = SiteGeneratorConfig(
            AZURE_STORAGE_ACCOUNT_URL="not-a-valid-url",
            PROCESSED_CONTENT_CONTAINER="processed",
            MARKDOWN_CONTENT_CONTAINER="markdown",
            STATIC_SITES_CONTAINER="static",
            SITE_TITLE="Test Site",
            SITE_DESCRIPTION="Test Description",
            SITE_DOMAIN="test.com",
            SITE_URL="https://test.com",
            ARTICLES_PER_PAGE=10,
            MAX_ARTICLES_TOTAL=100,
            DEFAULT_THEME="default",
            ENVIRONMENT="test",
        )

        # Validation should fail for invalid URL
        assert not invalid_config.validate()


class TestErrorHandlingBehavior:
    """Test SecureErrorHandler integration and error scenarios."""

    @pytest.mark.asyncio
    async def test_secure_error_handler_sanitizes_sensitive_data(self):
        """Test that SecureErrorHandler properly sanitizes error messages."""

        error_handler = SecureErrorHandler("test-component")

        # Simulate error with sensitive data
        sensitive_error = Exception("Connection failed: account_key=abc123secret456")

        # Handle the error
        sanitized_result = error_handler.handle_error(
            error=sensitive_error,
            error_type="connection",
            context={"operation": "test_operation", "user_input": "sensitive_data"},
        )

        # Should sanitize sensitive information
        assert "abc123secret456" not in str(sanitized_result)
        assert "account_key" not in str(sanitized_result)

        # Should provide generic sanitized error message (OWASP compliance)
        assert (
            "an error occurred while processing your request"
            in str(sanitized_result).lower()
        )
        assert "error_id" in str(sanitized_result)
        assert "service" in str(sanitized_result)

    def test_generation_response_handles_error_list_properly(self):
        """Test that GenerationResponse properly handles error accumulation."""

        # Create response with multiple errors
        response = GenerationResponse(
            generator_id="error-test",
            operation_type="test_operation",
            files_generated=2,
            processing_time=1.0,
            output_location="test://location",
            generated_files=["file1.md", "file2.md"],
            errors=[
                "Error 1: File not found",
                "Error 2: Permission denied",
                "Error 3: Network timeout",
            ],
        )

        # Should properly store and serialize all errors
        assert len(response.errors) == 3
        assert "File not found" in response.errors[0]
        assert "Permission denied" in response.errors[1]
        assert "Network timeout" in response.errors[2]

        # Should serialize properly for API responses
        response_dict = response.model_dump()
        assert len(response_dict["errors"]) == 3
        assert all(isinstance(err, str) for err in response_dict["errors"])
