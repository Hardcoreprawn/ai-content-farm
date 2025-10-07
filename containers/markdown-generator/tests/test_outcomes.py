"""
Outcome-based tests for markdown-generator.

These tests focus on verifiable outcomes rather than implementation details.
"""

import json
from typing import Any

from azure.core.exceptions import ResourceNotFoundError
from markdown_processor import MarkdownProcessor
from models import ProcessingStatus


class TestMarkdownGenerationOutcomes:
    """Test observable outcomes of markdown generation."""

    def test_successful_processing_produces_markdown_blob(
        self, markdown_processor: MarkdownProcessor
    ) -> None:
        """
        GIVEN a valid JSON article blob
        WHEN processing is requested
        THEN a markdown blob is created in the output container
        """
        # Arrange
        blob_name = "test-article.json"

        # Act
        result = markdown_processor.process_article(blob_name)

        # Assert - Verify outcome
        assert result.status == ProcessingStatus.COMPLETED
        assert result.markdown_blob_name == "test-article.md"
        assert result.processing_time_ms is not None
        assert result.error_message is None

    def test_markdown_contains_frontmatter_with_metadata(
        self,
        markdown_processor: MarkdownProcessor,
        mock_blob_service_client: Any,
    ) -> None:
        """
        GIVEN an article with complete metadata
        WHEN markdown is generated
        THEN the output contains YAML frontmatter with all metadata fields
        """
        # Arrange
        blob_name = "test-article.json"

        # Act
        markdown_processor.process_article(blob_name)

        # Assert - Check what was written
        container_client = mock_blob_service_client.get_container_client("test-output")
        blob_client = container_client.get_blob_client("test-article.md")
        write_calls = blob_client.upload_blob.call_args_list
        assert len(write_calls) > 0

        markdown_content = write_calls[0][0][0]  # First positional arg

        # Verify frontmatter structure
        assert markdown_content.startswith("---")
        assert "title:" in markdown_content
        assert "url:" in markdown_content
        assert "source:" in markdown_content
        assert "author:" in markdown_content
        assert "published_date:" in markdown_content
        assert "category:" in markdown_content
        assert "tags:" in markdown_content
        assert "generated_date:" in markdown_content

    def test_markdown_contains_structured_content(
        self,
        markdown_processor: MarkdownProcessor,
        mock_blob_service_client: Any,
    ) -> None:
        """
        GIVEN an article with summary, content, and key points
        WHEN markdown is generated
        THEN the output contains all sections in proper order
        """
        # Arrange
        blob_name = "test-article.json"

        # Act
        markdown_processor.process_article(blob_name)

        # Assert - Check content structure
        container_client = mock_blob_service_client.get_container_client("test-output")
        blob_client = container_client.get_blob_client("test-article.md")
        write_calls = blob_client.upload_blob.call_args_list
        markdown_content = write_calls[0][0][0]

        # Verify sections exist and are in order
        summary_pos = markdown_content.find("## Summary")
        content_pos = markdown_content.find("## Content")
        key_points_pos = markdown_content.find("## Key Points")

        assert summary_pos > 0
        assert content_pos > summary_pos
        assert key_points_pos > content_pos
        assert "**Source:**" in markdown_content

    def test_missing_blob_returns_failed_status(
        self,
        markdown_processor: MarkdownProcessor,
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

        # Act
        result = markdown_processor.process_article(blob_name)

        # Assert - Verify failure outcome
        assert result.status == ProcessingStatus.FAILED
        assert result.markdown_blob_name is None
        assert result.error_message is not None
        assert "not found" in result.error_message.lower()

    def test_existing_markdown_prevents_overwrite_by_default(
        self,
        markdown_processor: MarkdownProcessor,
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

        # Act
        result = markdown_processor.process_article(blob_name, overwrite=False)

        # Assert - Verify overwrite protection
        assert result.status == ProcessingStatus.FAILED
        assert result.error_message is not None
        assert "already exists" in result.error_message.lower()

    def test_overwrite_flag_allows_replacing_existing_markdown(
        self,
        markdown_processor: MarkdownProcessor,
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

        # Act
        result = markdown_processor.process_article(blob_name, overwrite=True)

        # Assert - Verify successful overwrite
        assert result.status == ProcessingStatus.COMPLETED
        assert result.markdown_blob_name == "existing-article.md"

        # Verify upload_blob was called with overwrite=True
        container_client = mock_blob_service_client.get_container_client("test-output")
        blob_client = container_client.get_blob_client("existing-article.md")
        upload_calls = blob_client.upload_blob.call_args_list
        assert len(upload_calls) > 0
        assert upload_calls[0][1]["overwrite"] is True

    def test_processing_time_is_reasonable(
        self, markdown_processor: MarkdownProcessor
    ) -> None:
        """
        GIVEN a standard article
        WHEN processing completes
        THEN processing time is within acceptable range (<5000ms)
        """
        # Arrange
        blob_name = "test-article.json"

        # Act
        result = markdown_processor.process_article(blob_name)

        # Assert - Verify performance outcome
        assert result.status == ProcessingStatus.COMPLETED
        assert result.processing_time_ms is not None
        assert result.processing_time_ms < 5000  # Should be <5 seconds

    def test_malformed_json_returns_failed_status(
        self,
        markdown_processor: MarkdownProcessor,
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

        # Act
        result = markdown_processor.process_article(blob_name)

        # Assert - Verify error handling
        assert result.status == ProcessingStatus.FAILED
        assert result.error_message is not None

    def test_minimal_article_data_still_produces_valid_markdown(
        self,
        markdown_processor: MarkdownProcessor,
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

        # Act
        result = markdown_processor.process_article(blob_name)

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
