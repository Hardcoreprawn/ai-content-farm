"""
Tests for Jinja2 template functionality.

Tests template selection, rendering, and error handling.
"""

from typing import Any, Dict

import pytest
import yaml
from markdown_processor import generate_markdown_content
from models import ArticleMetadata


class TestTemplateRendering:
    """Test Jinja2 template rendering."""

    def test_processor_initializes_jinja_environment(
        self, markdown_processor_deps: Dict[str, Any]
    ) -> None:
        """
        GIVEN Jinja environment from dependencies
        WHEN initialized
        THEN Jinja2 environment is configured with templates
        """
        # Arrange
        jinja_env = markdown_processor_deps["jinja_env"]

        # Assert
        assert jinja_env is not None
        assert jinja_env.loader is not None

        # Verify templates are available
        templates = jinja_env.list_templates(filter_func=lambda x: x.endswith(".md.j2"))
        assert len(templates) >= 3  # default, with-toc, minimal
        assert "default.md.j2" in templates
        assert "with-toc.md.j2" in templates
        assert "minimal.md.j2" in templates

    def test_default_template_renders_successfully(
        self, markdown_processor_deps: Dict[str, Any], sample_article_data
    ) -> None:
        """
        GIVEN article data and metadata
        WHEN generating markdown with default template
        THEN markdown is rendered with all sections
        """
        # Arrange
        jinja_env = markdown_processor_deps["jinja_env"]
        metadata = ArticleMetadata(
            title="Test Article",
            url="https://example.com/test",
            source="test-source",
            author="Test Author",
            published_date=None,
            category="technology",
            tags=["ai", "ml"],
            hero_image=None,
            thumbnail=None,
            image_alt=None,
            image_credit=None,
            image_color=None,
        )

        # Act
        markdown = generate_markdown_content(
            sample_article_data, metadata, jinja_env, "default.md.j2"
        )

        # Assert
        assert "---" in markdown  # Frontmatter
        assert "title:" in markdown
        assert "Test Article" in markdown
        assert "## Summary" in markdown
        assert "This is the main content" in markdown  # article_content rendered
        assert "## Key Points" in markdown
        assert "**Source:**" in markdown

    def test_minimal_template_omits_optional_sections(
        self, markdown_processor_deps: Dict[str, Any], sample_article_data
    ) -> None:
        """
        GIVEN article data
        WHEN generating with minimal template
        THEN only essential frontmatter is included
        """
        # Arrange
        jinja_env = markdown_processor_deps["jinja_env"]
        metadata = ArticleMetadata(
            title="Minimal Article",
            url="https://example.com/minimal",
            source="test-source",
            author=None,
            published_date=None,
            category=None,
            tags=[],
            hero_image=None,
            thumbnail=None,
            image_alt=None,
            image_credit=None,
            image_color=None,
        )

        # Act
        markdown = generate_markdown_content(
            sample_article_data, metadata, jinja_env, "minimal.md.j2"
        )

        # Assert
        assert "---" in markdown
        assert "title:" in markdown
        assert "url:" in markdown
        assert "## Summary" not in markdown  # No section headers
        assert "## Content" not in markdown
        assert "## Key Points" not in markdown

    def test_with_toc_template_includes_table_of_contents(
        self, markdown_processor_deps: Dict[str, Any], sample_article_data
    ) -> None:
        """
        GIVEN article data
        WHEN generating with with-toc template
        THEN table of contents is included
        """
        # Arrange
        jinja_env = markdown_processor_deps["jinja_env"]
        metadata = ArticleMetadata(
            title="Article with TOC",
            url="https://example.com/toc",
            source="test-source",
            author=None,
            published_date=None,
            category=None,
            tags=[],
            hero_image=None,
            thumbnail=None,
            image_alt=None,
            image_credit=None,
            image_color=None,
        )

        # Act
        markdown = generate_markdown_content(
            sample_article_data, metadata, jinja_env, "with-toc.md.j2"
        )

        # Assert
        assert "## Table of Contents" in markdown
        assert "[Summary](#summary)" in markdown
        assert "[Key Points](#key-points)" in markdown
        # Note: Content heading removed - article_content includes its own structure

    def test_invalid_template_raises_value_error(
        self, markdown_processor_deps: Dict[str, Any], sample_article_data
    ) -> None:
        """
        GIVEN invalid template name
        WHEN generating markdown
        THEN ValueError is raised
        """
        # Arrange
        jinja_env = markdown_processor_deps["jinja_env"]
        metadata = ArticleMetadata(
            title="Test",
            url="https://example.com",
            source="test",
            author=None,
            published_date=None,
            category=None,
            tags=[],
            hero_image=None,
            thumbnail=None,
            image_alt=None,
            image_credit=None,
            image_color=None,
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Template not found"):
            generate_markdown_content(
                sample_article_data, metadata, jinja_env, "nonexistent.md.j2"
            )

    def test_template_handles_missing_optional_fields(
        self, markdown_processor_deps: Dict[str, Any]
    ) -> None:
        """
        GIVEN article data with missing optional fields
        WHEN generating markdown
        THEN template renders without errors
        """
        # Arrange
        jinja_env = markdown_processor_deps["jinja_env"]
        metadata = ArticleMetadata(
            title="Minimal Data",
            url="https://example.com",
            source="test",
            author=None,
            published_date=None,
            category=None,
            tags=[],
            hero_image=None,
            thumbnail=None,
            image_alt=None,
            image_credit=None,
            image_color=None,
        )
        article_data = {
            "url": "https://example.com",
            "title": "Minimal Data",
            # No summary, content, or key_points
        }

        # Act
        markdown = generate_markdown_content(
            article_data, metadata, jinja_env, "default.md.j2"
        )

        # Assert
        assert "---" in markdown
        assert "title:" in markdown
        # H1 removed from templates - Hugo theme provides it from frontmatter
        assert "# Minimal Data" not in markdown
        # Optional sections should not appear
        assert "## Summary" not in markdown
        assert "## Content" not in markdown
        assert "## Key Points" not in markdown

    @pytest.mark.parametrize(
        "template_name",
        ["default.md.j2", "minimal.md.j2", "with-toc.md.j2"],
    )
    def test_templates_generate_valid_yaml_frontmatter(
        self,
        markdown_processor_deps: Dict[str, Any],
        sample_article_data,
        template_name,
    ) -> None:
        """
        GIVEN article data with URLs containing special YAML characters
        WHEN generating markdown with any template
        THEN YAML frontmatter is valid and parseable
        """
        # Arrange - Use URL with colons and other special chars
        jinja_env = markdown_processor_deps["jinja_env"]
        metadata = ArticleMetadata(
            title="Test Article: A Deep Dive",
            url="https://example.com/article?param=value&test=true",
            source="reddit",
            author="John Doe",
            published_date=None,
            category="technology",
            tags=["ai", "machine learning", "deep-tech"],
            hero_image=None,
            thumbnail=None,
            image_alt=None,
            image_credit=None,
            image_color=None,
        )

        # Act
        markdown = generate_markdown_content(
            sample_article_data, metadata, jinja_env, template_name
        )

        # Extract frontmatter (between first two --- markers)
        parts = markdown.split("---")
        assert len(parts) >= 3, "Markdown should have frontmatter delimiters"
        frontmatter_text = parts[1].strip()

        # Assert - YAML should parse without errors
        try:
            frontmatter = yaml.safe_load(frontmatter_text)
            assert isinstance(frontmatter, dict), "Frontmatter should be a dict"
            # Hugo required fields
            assert "title" in frontmatter
            assert "date" in frontmatter
            assert "draft" in frontmatter
            # Custom fields under params
            assert "params" in frontmatter
            assert "original_url" in frontmatter["params"]
            assert "source" in frontmatter["params"]
            # Verify special characters preserved correctly in params
            assert (
                frontmatter["params"]["original_url"]
                == "https://example.com/article?param=value&test=true"
            )
            # Colon in title should be preserved
            assert ":" in frontmatter["title"]
        except yaml.YAMLError as e:
            pytest.fail(f"YAML frontmatter parsing failed for {template_name}: {e}")


class TestImageDataFlow:
    """Test that image data flows correctly through templates.

    Verifies the complete pipeline:
    1. Image fields in metadata
    2. Frontmatter generation with cover image
    3. Template rendering includes cover structure
    4. Hugo can parse the result
    """

    @pytest.mark.parametrize(
        "template_name",
        ["default.md.j2", "minimal.md.j2", "with-toc.md.j2"],
    )
    def test_image_data_included_in_frontmatter(
        self,
        markdown_processor_deps: Dict[str, Any],
        sample_article_data,
        template_name,
    ) -> None:
        """
        GIVEN article metadata with image fields
        WHEN generating markdown with any template
        THEN frontmatter includes cover image structure
        """
        # Arrange
        jinja_env = markdown_processor_deps["jinja_env"]
        metadata = ArticleMetadata(
            title="Quantum Computing Breakthrough",
            url="https://example.com/quantum",
            source="reddit",
            author="Dr. Jane Smith",
            published_date=None,
            category="technology",
            tags=["quantum", "computing", "ai"],
            # Image fields populated
            hero_image="https://images.unsplash.com/photo-1526374965328-7f5ae4e8cfb6?w=1080&q=80",
            thumbnail="https://images.unsplash.com/photo-1526374965328-7f5ae4e8cfb6?w=400&q=80",
            image_alt="Quantum computer processor with blue lights",
            image_credit="Photo by Author Name on Unsplash",
            image_color="#1a1a2e",
        )

        # Act
        markdown = generate_markdown_content(
            sample_article_data, metadata, jinja_env, template_name
        )

        # Extract and parse frontmatter
        parts = markdown.split("---")
        assert len(parts) >= 3, "Markdown should have frontmatter delimiters"
        frontmatter_text = parts[1].strip()

        # Assert
        try:
            frontmatter = yaml.safe_load(frontmatter_text)

            # Verify cover image structure (PaperMod theme expects this)
            assert "cover" in frontmatter, "Frontmatter should include cover field"
            assert isinstance(frontmatter["cover"], dict), "Cover should be a dict"
            assert frontmatter["cover"]["image"] == metadata.hero_image
            assert frontmatter["cover"]["alt"] == metadata.image_alt
            assert frontmatter["cover"]["caption"] == metadata.image_credit
            assert frontmatter["cover"]["relative"] is False

            # Verify image metadata in params (for template customization)
            assert "params" in frontmatter
            assert frontmatter["params"]["thumbnail"] == metadata.thumbnail
            assert frontmatter["params"]["image_color"] == metadata.image_color

        except yaml.YAMLError as e:
            pytest.fail(f"YAML parsing failed: {e}")

    def test_image_fields_optional_graceful_degradation(
        self,
        markdown_processor_deps: Dict[str, Any],
        sample_article_data,
        create_metadata,
    ) -> None:
        """
        GIVEN article metadata WITHOUT image fields
        WHEN generating markdown
        THEN markdown renders without cover section (graceful degradation)
        """
        # Arrange
        jinja_env = markdown_processor_deps["jinja_env"]
        metadata = create_metadata(
            title="Regular Article",
            url="https://example.com/regular",
            source="rss",
            tags=["tech"],
        )

        # Act
        markdown = generate_markdown_content(
            sample_article_data, metadata, jinja_env, "default.md.j2"
        )

        # Extract and parse frontmatter
        parts = markdown.split("---")
        frontmatter_text = parts[1].strip()
        frontmatter = yaml.safe_load(frontmatter_text)

        # Assert - graceful degradation
        assert "cover" not in frontmatter, "No cover section if no images"
        assert "title" in frontmatter, "Title still present"
        assert "date" in frontmatter, "Date still present"
        assert "params" in frontmatter, "Params still present"
        # Content sections should still render
        assert "## Summary" in markdown
        assert "## Key Points" in markdown

    def test_partial_image_data_handled_correctly(
        self,
        markdown_processor_deps: Dict[str, Any],
        sample_article_data,
        create_metadata,
    ) -> None:
        """
        GIVEN article metadata with some image fields but not all
        WHEN generating markdown
        THEN only provided fields are included (missing fields don't cause errors)
        """
        # Arrange
        jinja_env = markdown_processor_deps["jinja_env"]
        metadata = create_metadata(
            title="Partial Image Article",
            url="https://example.com/partial",
            source="mastodon",
            # Only hero_image and alt provided
            hero_image="https://images.unsplash.com/photo-xxx?w=1080",
            image_alt="A descriptive alt text",
            tags=["tech"],
        )

        # Act
        markdown = generate_markdown_content(
            sample_article_data, metadata, jinja_env, "default.md.j2"
        )

        # Extract and parse frontmatter
        parts = markdown.split("---")
        frontmatter_text = parts[1].strip()
        frontmatter = yaml.safe_load(frontmatter_text)

        # Assert - partial data handled gracefully
        assert "cover" in frontmatter, "Cover section included with provided fields"
        assert frontmatter["cover"]["image"] == metadata.hero_image
        assert frontmatter["cover"]["alt"] == metadata.image_alt
        # caption field should not be in cover if not provided
        assert (
            "caption" not in frontmatter["cover"]
            or frontmatter["cover"]["caption"] is None
        )
        # Content renders normally
        assert len(markdown) > 0

    def test_image_urls_preserved_correctly(
        self,
        markdown_processor_deps: Dict[str, Any],
        sample_article_data,
        create_metadata,
    ) -> None:
        """
        GIVEN image URLs with query parameters and special characters
        WHEN generating markdown
        THEN URLs are preserved exactly as provided
        """
        # Arrange
        jinja_env = markdown_processor_deps["jinja_env"]
        complex_image_url = "https://images.unsplash.com/photo-1234567890?w=1080&q=80&fmt=auto&crop=faces"
        metadata = create_metadata(
            title="Complex URL Test",
            url="https://example.com/test",
            source="reddit",
            hero_image=complex_image_url,
            image_alt="Test image with query params",
            tags=["test"],
        )

        # Act
        markdown = generate_markdown_content(
            sample_article_data, metadata, jinja_env, "default.md.j2"
        )

        # Extract and parse frontmatter
        parts = markdown.split("---")
        frontmatter_text = parts[1].strip()
        frontmatter = yaml.safe_load(frontmatter_text)

        # Assert - URL preserved exactly
        assert frontmatter["cover"]["image"] == complex_image_url
        assert "?" in frontmatter["cover"]["image"], "Query parameters preserved"
        assert "&" in frontmatter["cover"]["image"], "Multiple params preserved"

    def test_image_credit_attribution_preserved(
        self,
        markdown_processor_deps: Dict[str, Any],
        sample_article_data,
        create_metadata,
    ) -> None:
        """
        GIVEN image credit with markdown/HTML formatting
        WHEN generating markdown
        THEN credit text is preserved for template rendering
        """
        # Arrange
        jinja_env = markdown_processor_deps["jinja_env"]
        credit_text = "Photo by [Jane Doe](https://unsplash.com/@jane) on Unsplash"
        metadata = create_metadata(
            title="Image Attribution Test",
            url="https://example.com/test",
            source="rss",
            hero_image="https://images.unsplash.com/photo-test?w=1080",
            image_alt="Test photo",
            image_credit=credit_text,
            tags=["attribution"],
        )

        # Act
        markdown = generate_markdown_content(
            sample_article_data, metadata, jinja_env, "default.md.j2"
        )

        # Extract and parse frontmatter
        parts = markdown.split("---")
        frontmatter_text = parts[1].strip()
        frontmatter = yaml.safe_load(frontmatter_text)

        # Assert - credit preserved for Hugo theme to render
        assert frontmatter["cover"]["caption"] == credit_text
        assert "Jane Doe" in frontmatter["cover"]["caption"]
        assert "https://unsplash.com/@jane" in frontmatter["cover"]["caption"]

    @pytest.mark.parametrize(
        "template_name",
        ["default.md.j2", "minimal.md.j2", "with-toc.md.j2"],
    )
    def test_all_templates_preserve_image_data(
        self,
        markdown_processor_deps: Dict[str, Any],
        sample_article_data,
        template_name,
        create_metadata,
    ) -> None:
        """
        GIVEN different template choices
        WHEN all render markdown with images
        THEN all templates preserve image data in frontmatter
        """
        # Arrange
        jinja_env = markdown_processor_deps["jinja_env"]
        metadata = create_metadata(
            title="Multi-Template Image Test",
            url="https://example.com/test",
            source="reddit",
            hero_image="https://images.unsplash.com/photo-test?w=1080",
            image_alt="Multi-template test image",
            image_credit="Photo by Test Author",
            thumbnail="https://images.unsplash.com/photo-test?w=400",
            image_color="#ff5733",
            tags=["test"],
        )

        # Act
        markdown = generate_markdown_content(
            sample_article_data, metadata, jinja_env, template_name
        )

        # Extract and parse frontmatter
        parts = markdown.split("---")
        frontmatter_text = parts[1].strip()
        frontmatter = yaml.safe_load(frontmatter_text)

        # Assert - all templates preserve image data
        assert "cover" in frontmatter, f"{template_name} should have cover field"
        assert frontmatter["cover"]["image"] is not None
        assert frontmatter["cover"]["alt"] is not None
        assert frontmatter["cover"]["caption"] is not None
        assert "params" in frontmatter
        assert frontmatter["params"]["thumbnail"] is not None
        assert frontmatter["params"]["image_color"] is not None
