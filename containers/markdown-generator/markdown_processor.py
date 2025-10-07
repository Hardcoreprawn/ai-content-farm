"""
Core markdown generation logic.

This module handles the conversion of processed JSON articles into
markdown format with proper frontmatter and structure using Jinja2 templates.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import BlobServiceClient

__all__ = ["MarkdownProcessor"]
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from models import ArticleMetadata, MarkdownGenerationResult, ProcessingStatus

from config import Settings

logger = logging.getLogger(__name__)


class MarkdownProcessor:
    """Handles conversion of JSON articles to markdown format using Jinja2."""

    def __init__(
        self, blob_service_client: BlobServiceClient, settings: Settings
    ) -> None:
        """
        Initialize markdown processor.

        Args:
            blob_service_client: Azure Blob Service client
            settings: Application settings
        """
        self.blob_service_client = blob_service_client
        self.settings = settings
        self.input_container = settings.input_container
        self.output_container = settings.output_container

        # Set up Jinja2 environment
        template_dir = Path(__file__).parent / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        logger.info(f"Initialized Jinja2 templates from: {template_dir}")

    def process_article(
        self,
        blob_name: str,
        overwrite: bool = False,
        template_name: str = "default.md.j2",
    ) -> MarkdownGenerationResult:
        """
        Process single article from JSON to markdown.

        Args:
            blob_name: Name of JSON blob to process
            overwrite: Whether to overwrite existing markdown
            template_name: Jinja2 template to use

        Returns:
            MarkdownGenerationResult: Processing result
        """
        start_time = datetime.utcnow()

        try:
            # Read JSON from input container
            article_data = self._read_json_blob(blob_name)

            # Extract metadata
            metadata = self._extract_metadata(article_data)

            # Generate markdown content using template
            markdown_content = self._generate_markdown(
                article_data, metadata, template_name
            )

            # Write markdown to output container
            markdown_blob_name = self._write_markdown_blob(
                blob_name, markdown_content, overwrite
            )

            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            logger.info(
                f"Successfully processed article: {blob_name} -> "
                f"{markdown_blob_name} ({processing_time:.0f}ms) "
                f"using template: {template_name}"
            )

            return MarkdownGenerationResult(
                blob_name=blob_name,
                status=ProcessingStatus.COMPLETED,
                markdown_blob_name=markdown_blob_name,
                error_message=None,
                processing_time_ms=int(processing_time),
            )

        except ResourceNotFoundError:
            error_msg = f"Blob not found: {blob_name}"
            logger.error(error_msg)
            return MarkdownGenerationResult(
                blob_name=blob_name,
                status=ProcessingStatus.FAILED,
                markdown_blob_name=None,
                error_message=error_msg,
                processing_time_ms=None,
            )

        except Exception as e:
            error_msg = f"Failed to process {blob_name}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return MarkdownGenerationResult(
                blob_name=blob_name,
                status=ProcessingStatus.FAILED,
                markdown_blob_name=None,
                error_message=error_msg,
                processing_time_ms=None,
            )

    def _read_json_blob(self, blob_name: str) -> Dict[str, Any]:
        """
        Read and parse JSON blob from storage.

        Args:
            blob_name: Name of blob to read

        Returns:
            Dict containing parsed JSON data

        Raises:
            ResourceNotFoundError: If blob doesn't exist
            ValueError: If blob contains invalid JSON
        """
        container_client = self.blob_service_client.get_container_client(
            self.input_container
        )
        blob_client = container_client.get_blob_client(blob_name)

        blob_data = blob_client.download_blob().readall()
        parsed_data: Dict[str, Any] = json.loads(blob_data)
        return parsed_data

    def _extract_metadata(self, article_data: Dict[str, Any]) -> ArticleMetadata:
        """
        Extract structured metadata from article JSON.

        Args:
            article_data: Raw article data dictionary

        Returns:
            ArticleMetadata: Validated metadata object
        """
        return ArticleMetadata(
            title=article_data.get("title", "Untitled"),
            url=article_data.get("url", ""),
            source=article_data.get("source", "unknown"),
            author=article_data.get("author"),
            published_date=self._parse_date(article_data.get("published_date")),
            tags=article_data.get("tags", []),
            category=article_data.get("category"),
        )

    def _parse_date(self, date_value: Any) -> Optional[datetime]:
        """
        Parse date from various formats.

        Args:
            date_value: Date in string or datetime format

        Returns:
            Parsed datetime or None if invalid
        """
        if isinstance(date_value, datetime):
            return date_value

        if isinstance(date_value, str):
            try:
                return datetime.fromisoformat(date_value.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                logger.warning(f"Could not parse date: {date_value}")

        return None

    def _generate_markdown(
        self,
        article_data: Dict[str, Any],
        metadata: ArticleMetadata,
        template_name: str = "default.md.j2",
    ) -> str:
        """
        Generate markdown content with frontmatter using Jinja2 templates.

        Args:
            article_data: Complete article data
            metadata: Extracted metadata
            template_name: Name of template file (default: default.md.j2)

        Returns:
            Complete markdown document as string

        Raises:
            ValueError: If template not found
        """
        try:
            template = self.jinja_env.get_template(template_name)
        except TemplateNotFound:
            logger.error(f"Template not found: {template_name}")
            raise ValueError(f"Template not found: {template_name}")

        # Render template with data
        markdown_content = template.render(
            metadata=metadata,
            article_data=article_data,
            generated_date=f"{datetime.utcnow().isoformat()}Z",
        )

        return markdown_content

    def _write_markdown_blob(
        self, original_blob_name: str, markdown_content: str, overwrite: bool
    ) -> str:
        """
        Write markdown content to output container.

        Args:
            original_blob_name: Original JSON blob name
            markdown_content: Generated markdown
            overwrite: Whether to overwrite existing files

        Returns:
            Name of created markdown blob

        Raises:
            ValueError: If blob exists and overwrite is False
        """
        # Generate markdown blob name
        markdown_blob_name = original_blob_name.replace(".json", ".md")

        container_client = self.blob_service_client.get_container_client(
            self.output_container
        )
        blob_client = container_client.get_blob_client(markdown_blob_name)

        # Check if exists
        if not overwrite and blob_client.exists():
            raise ValueError(f"Markdown file already exists: {markdown_blob_name}")

        # Upload markdown
        blob_client.upload_blob(
            markdown_content, overwrite=overwrite, content_type="text/markdown"
        )

        return markdown_blob_name
