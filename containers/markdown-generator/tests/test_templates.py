"""
Tests for Jinja2 template functionality.

Tests template selection, rendering, and error handling.
"""

from typing import cast

import pytest
from models import ArticleMetadata
from pydantic import HttpUrl


class TestTemplateRendering:
    """Test Jinja2 template rendering."""

    def test_processor_initializes_jinja_environment(self, markdown_processor) -> None:
        """
        GIVEN a MarkdownProcessor instance
        WHEN initialized
        THEN Jinja2 environment is configured with templates
        """
        # Assert
        assert markdown_processor.jinja_env is not None
        assert markdown_processor.jinja_env.loader is not None

        # Verify templates are available
        templates = markdown_processor.jinja_env.list_templates(
            filter_func=lambda x: x.endswith(".md.j2")
        )
        assert len(templates) >= 3  # default, with-toc, minimal
        assert "default.md.j2" in templates
        assert "with-toc.md.j2" in templates
        assert "minimal.md.j2" in templates

    def test_default_template_renders_successfully(
        self, markdown_processor, sample_article_data
    ) -> None:
        """
        GIVEN article data and metadata
        WHEN generating markdown with default template
        THEN markdown is rendered with all sections
        """
        # Arrange
        metadata = ArticleMetadata(
            title="Test Article",
            url=cast(HttpUrl, "https://example.com/test"),
            source="test-source",
            author="Test Author",
            published_date=None,
            category="technology",
            tags=["ai", "ml"],
        )

        # Act
        markdown = markdown_processor._generate_markdown(
            sample_article_data, metadata, "default.md.j2"
        )

        # Assert
        assert "---" in markdown  # Frontmatter
        assert "title:" in markdown
        assert "Test Article" in markdown
        assert "## Summary" in markdown
        assert "## Content" in markdown
        assert "## Key Points" in markdown
        assert "**Source:**" in markdown

    def test_minimal_template_omits_optional_sections(
        self, markdown_processor, sample_article_data
    ) -> None:
        """
        GIVEN article data
        WHEN generating with minimal template
        THEN only essential frontmatter is included
        """
        # Arrange
        metadata = ArticleMetadata(
            title="Minimal Article",
            url=cast(HttpUrl, "https://example.com/minimal"),
            source="test-source",
            author=None,
            published_date=None,
            category=None,
        )

        # Act
        markdown = markdown_processor._generate_markdown(
            sample_article_data, metadata, "minimal.md.j2"
        )

        # Assert
        assert "---" in markdown
        assert "title:" in markdown
        assert "url:" in markdown
        assert "## Summary" not in markdown  # No section headers
        assert "## Content" not in markdown
        assert "## Key Points" not in markdown

    def test_with_toc_template_includes_table_of_contents(
        self, markdown_processor, sample_article_data
    ) -> None:
        """
        GIVEN article data
        WHEN generating with with-toc template
        THEN table of contents is included
        """
        # Arrange
        metadata = ArticleMetadata(
            title="Article with TOC",
            url=cast(HttpUrl, "https://example.com/toc"),
            source="test-source",
            author=None,
            published_date=None,
            category=None,
        )

        # Act
        markdown = markdown_processor._generate_markdown(
            sample_article_data, metadata, "with-toc.md.j2"
        )

        # Assert
        assert "## Table of Contents" in markdown
        assert "[Summary](#summary)" in markdown
        assert "[Content](#content)" in markdown
        assert "[Key Points](#key-points)" in markdown

    def test_invalid_template_raises_value_error(
        self, markdown_processor, sample_article_data
    ) -> None:
        """
        GIVEN invalid template name
        WHEN generating markdown
        THEN ValueError is raised
        """
        # Arrange
        metadata = ArticleMetadata(
            title="Test",
            url=cast(HttpUrl, "https://example.com"),
            source="test",
            author=None,
            published_date=None,
            category=None,
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Template not found"):
            markdown_processor._generate_markdown(
                sample_article_data, metadata, "nonexistent.md.j2"
            )

    def test_template_handles_missing_optional_fields(self, markdown_processor) -> None:
        """
        GIVEN article data with missing optional fields
        WHEN generating markdown
        THEN template renders without errors
        """
        # Arrange
        metadata = ArticleMetadata(
            title="Minimal Data",
            url=cast(HttpUrl, "https://example.com"),
            source="test",
            author=None,
            published_date=None,
            category=None,
        )
        article_data = {
            "url": "https://example.com",
            "title": "Minimal Data",
            # No summary, content, or key_points
        }

        # Act
        markdown = markdown_processor._generate_markdown(
            article_data, metadata, "default.md.j2"
        )

        # Assert
        assert "---" in markdown
        assert "title:" in markdown
        assert "# Minimal Data" in markdown
        # Optional sections should not appear
        assert "## Summary" not in markdown
        assert "## Content" not in markdown
        assert "## Key Points" not in markdown
