"""
Outcome-based tests for markdown-generator.

These tests focus on verifiable outcomes rather than implementation details.
"""

import json
from typing import Any, Dict

import pytest
from azure.core.exceptions import ResourceNotFoundError
from markdown_processor import process_article
from models import ProcessingStatus


class TestMarkdownGenerationOutcomes:
    """Test observable outcomes of markdown generation."""

    @pytest.mark.asyncio
    async def test_successful_processing_produces_markdown_blob(
        self, markdown_processor_deps: Dict[str, Any]
    ) -> None:
        """
        GIVEN a valid JSON article blob
        WHEN processing is requested
        THEN a markdown blob is created in the output container
        """
        # Arrange
        blob_name = "test-article.json"

        # Act - Call functional API directly
        result = await process_article(
            blob_name=blob_name,
            overwrite=False,
            template_name="default.md.j2",
            **markdown_processor_deps,
        )

        # Assert - Verify outcome
        assert result.status == ProcessingStatus.COMPLETED
        assert result.markdown_blob_name == "test-article.md"
        assert result.processing_time_ms is not None
        assert result.error_message is None

    @pytest.mark.asyncio
    async def test_markdown_contains_frontmatter_with_metadata(
        self,
        markdown_processor_deps: Dict[str, Any],
        mock_blob_service_client: Any,
    ) -> None:
        """
        GIVEN an article with complete metadata
        WHEN markdown is generated
        THEN the output contains YAML frontmatter with all metadata fields
        """
        # Arrange
        blob_name = "test-article.json"

        # Act - Call functional API directly
        result = await process_article(
            blob_name=blob_name,
            overwrite=False,
            template_name="default.md.j2",
            **markdown_processor_deps,
        )

        # Assert - Check what was written
        container_client = mock_blob_service_client.get_container_client("test-output")
        blob_client = container_client.get_blob_client("test-article.md")
        write_calls = blob_client.upload_blob.call_args_list
        assert len(write_calls) > 0

        markdown_content = write_calls[0][0][0]  # First positional arg

        # Verify frontmatter structure (Hugo compliant)
        assert markdown_content.startswith("---")
        assert "title:" in markdown_content
        assert "date:" in markdown_content  # Hugo required field
        assert "draft:" in markdown_content  # Hugo required field
        assert "params:" in markdown_content  # Custom fields under params
        # Custom fields now under params:
        assert "original_url:" in markdown_content
        assert "source:" in markdown_content

    @pytest.mark.asyncio
    async def test_markdown_contains_structured_content(
        self,
        markdown_processor_deps: Dict[str, Any],
        mock_blob_service_client: Any,
    ) -> None:
        """
        GIVEN an article with summary, content, and key points
        WHEN markdown is generated
        THEN the output contains all sections in proper order
        """
        # Arrange
        blob_name = "test-article.json"

        # Act - Call functional API directly
        await process_article(
            blob_name=blob_name,
            overwrite=False,
            template_name="default.md.j2",
            **markdown_processor_deps,
        )

        # Assert - Check content structure
        container_client = mock_blob_service_client.get_container_client("test-output")
        blob_client = container_client.get_blob_client("test-article.md")
        write_calls = blob_client.upload_blob.call_args_list
        markdown_content = write_calls[0][0][0]

        # Verify sections exist
        assert "## Summary" in markdown_content, "Summary header missing from generated markdown"
        assert "This is the main content" in markdown_content, "Article content missing from generated markdown"
        assert "## Key Points" in markdown_content, "Key Points header missing from generated markdown"
        assert "**Source:**" in markdown_content, "Source footer missing from generated markdown"

        # Verify order: Summary -> Article Content -> Key Points
        summary_idx = markdown_content.index("## Summary")
        article_idx = markdown_content.index("This is the main content")
        key_points_idx = markdown_content.index("## Key Points")

        assert summary_idx < article_idx < key_points_idx, "Sections are not in expected order: Summary -> Content -> Key Points"

    @pytest.mark.asyncio
    async def test_missing_blob_returns_failed_status(
        self,
        markdown_processor_deps: Dict[str, Any],
        mock_blob_service_client: Any,
    ) -> None:
        """
        GIVEN a non-existent blob name
        WHEN processing is requested
        THEN status is FAILED with appropriate error message
        """
        # Arrange
        container_client = mock_blob_service_client.get_container_client("test-input")
        blob_client = container_client.get_blob_client("nonexistent.json")
        blob_client.download_blob.side_effect = ResourceNotFoundError("Blob not found")

        blob_name = "nonexistent.json"

        # Act - Call functional API directly
        result = await process_article(
            blob_name=blob_name,
            overwrite=False,
            template_name="default.md.j2",
            **markdown_processor_deps,
        )

        # Assert - Verify failure outcome
        assert result.status == ProcessingStatus.FAILED
        assert result.markdown_blob_name is None
        assert result.error_message is not None
        assert "not found" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_existing_markdown_prevents_overwrite_by_default(
        self,
        markdown_processor_deps: Dict[str, Any],
        mock_blob_service_client: Any,
    ) -> None:
        """
        GIVEN a markdown blob that already exists
        WHEN processing is requested without overwrite flag
        THEN processing fails with appropriate error
        """
        # Arrange
        container_client = mock_blob_service_client.get_container_client("test-output")
        blob_client = container_client.get_blob_client("existing-article.md")
        blob_client.exists.return_value = True

        blob_name = "existing-article.json"

        # Act - Call functional API directly
        result = await process_article(
            blob_name=blob_name,
            overwrite=False,
            template_name="default.md.j2",
            **markdown_processor_deps,
        )

        # Assert - Verify overwrite protection
        assert result.status == ProcessingStatus.FAILED
        assert result.error_message is not None
        assert "already exists" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_overwrite_flag_allows_replacing_existing_markdown(
        self,
        markdown_processor_deps: Dict[str, Any],
        mock_blob_service_client: Any,
    ) -> None:
        """
        GIVEN a markdown blob that already exists
        WHEN processing is requested WITH overwrite flag
        THEN processing succeeds and blob is replaced
        """
        # Arrange
        container_client = mock_blob_service_client.get_container_client("test-output")
        blob_client = container_client.get_blob_client("existing-article.md")
        blob_client.exists.return_value = True

        blob_name = "existing-article.json"

        # Act - Call functional API directly with overwrite=True
        result = await process_article(
            blob_name=blob_name,
            overwrite=True,
            template_name="default.md.j2",
            **markdown_processor_deps,
        )

        # Assert - Verify successful overwrite
        assert result.status == ProcessingStatus.COMPLETED
        assert result.markdown_blob_name == "existing-article.md"

        # Verify upload_blob was called with overwrite=True
        container_client = mock_blob_service_client.get_container_client("test-output")
        blob_client = container_client.get_blob_client("existing-article.md")
        upload_calls = blob_client.upload_blob.call_args_list
        assert len(upload_calls) > 0
        assert upload_calls[0][1]["overwrite"] is True

    @pytest.mark.asyncio
    async def test_processing_time_is_reasonable(
        self, markdown_processor_deps: Dict[str, Any]
    ) -> None:
        """
        GIVEN a standard article
        WHEN processing completes
        THEN processing time is within acceptable range (<5000ms)
        """
        # Arrange
        blob_name = "test-article.json"

        # Act - Call functional API directly
        result = await process_article(
            blob_name=blob_name,
            overwrite=False,
            template_name="default.md.j2",
            **markdown_processor_deps,
        )

        # Assert - Verify performance outcome
        assert result.status == ProcessingStatus.COMPLETED
        assert result.processing_time_ms is not None
        assert result.processing_time_ms < 5000  # Should be <5 seconds

    @pytest.mark.asyncio
    async def test_malformed_json_returns_failed_status(
        self,
        markdown_processor_deps: Dict[str, Any],
        mock_blob_service_client: Any,
    ) -> None:
        """
        GIVEN a blob with invalid JSON content
        WHEN processing is requested
        THEN status is FAILED with JSON parse error
        """
        # Arrange
        container_client = mock_blob_service_client.get_container_client("test-input")
        blob_client = container_client.get_blob_client("malformed.json")
        blob_client.download_blob.return_value.readall.return_value = (
            b"{ invalid json }"
        )

        blob_name = "malformed.json"

        # Act - Call functional API directly
        result = await process_article(
            blob_name=blob_name,
            overwrite=False,
            template_name="default.md.j2",
            **markdown_processor_deps,
        )

        # Assert - Verify error handling
        assert result.status == ProcessingStatus.FAILED
        assert result.error_message is not None

    @pytest.mark.asyncio
    async def test_minimal_article_data_still_produces_valid_markdown(
        self,
        markdown_processor_deps: Dict[str, Any],
        mock_blob_service_client: Any,
    ) -> None:
        """
        GIVEN an article with only required fields (title, url)
        WHEN markdown is generated
        THEN valid markdown is produced without errors
        """
        # Arrange
        minimal_data = {
            "title": "Minimal Article",
            "url": "https://example.com/minimal",
        }

        container_client = mock_blob_service_client.get_container_client("test-input")
        blob_client = container_client.get_blob_client("minimal.json")
        blob_client.download_blob.return_value.readall.return_value = json.dumps(
            minimal_data
        ).encode("utf-8")

        blob_name = "minimal.json"

        # Act - Call functional API directly
        result = await process_article(
            blob_name=blob_name,
            overwrite=False,
            template_name="default.md.j2",
            **markdown_processor_deps,
        )

        # Assert - Verify graceful handling
        assert result.status == ProcessingStatus.COMPLETED
        assert result.markdown_blob_name is not None

        # Verify minimal frontmatter still valid
        container_client = mock_blob_service_client.get_container_client("test-output")
        blob_client = container_client.get_blob_client("minimal.md")
        write_calls = blob_client.upload_blob.call_args_list
        markdown_content = write_calls[0][0][0]

        assert markdown_content.startswith("---")
        assert "title:" in markdown_content
        assert "url:" in markdown_content
