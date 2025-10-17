import os
from datetime import datetime

import pytest
from jinja2 import Environment, FileSystemLoader


class TestMarkdownGenerationOutcomes:
    """Tests that verify the markdown generation produces expected outcomes."""

    @pytest.fixture
    def jinja_env(self):
        """Setup Jinja2 environment with template directory."""
        template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
        return Environment(loader=FileSystemLoader(template_dir))

    @pytest.fixture
    def sample_article_data(self):
        """Provide sample article data for testing."""
        return {
            "summary": "This is the summary section",
            "content": "This is the main content",
            "article_content": None,
            "key_points": ["First key point", "Second key point", "Third key point"],
        }

    @pytest.fixture
    def sample_metadata(self):
        """Provide sample metadata for testing."""
        return {
            "title": "Test Article",
            "published_date": "2025-10-17T10:00:00Z",
            "tags": ["test", "markdown"],
            "url": "https://example.com/article",
            "source": "Example Source",
        }

    def test_markdown_contains_structured_content(
        self, jinja_env, sample_article_data, sample_metadata
    ):
        """Test that generated markdown contains all expected sections in correct order."""
        template = jinja_env.get_template("default.md.j2")
        markdown_content = template.render(
            metadata=sample_metadata, article_data=sample_article_data
        )

        # Verify sections exist
        assert (
            "## Summary" in markdown_content
        ), "Summary header missing from generated markdown"
        assert (
            "This is the main content" in markdown_content
        ), "Article content missing from generated markdown"
        assert (
            "## Key Points" in markdown_content
        ), "Key Points header missing from generated markdown"
        assert (
            "**Source:**" in markdown_content
        ), "Source footer missing from generated markdown"

        # Verify order: Summary -> Article Content -> Key Points
        summary_idx = markdown_content.index("## Summary")
        article_idx = markdown_content.index("This is the main content")
        key_points_idx = markdown_content.index("## Key Points")

        assert (
            summary_idx < article_idx < key_points_idx
        ), "Sections are not in expected order: Summary -> Content -> Key Points"

    def test_markdown_contains_key_points(
        self, jinja_env, sample_article_data, sample_metadata
    ):
        """Test that all key points are rendered as bullet points."""
        template = jinja_env.get_template("default.md.j2")
        markdown_content = template.render(
            metadata=sample_metadata, article_data=sample_article_data
        )

        for point in sample_article_data["key_points"]:
            assert f"- {point}" in markdown_content, f"Key point missing: {point}"

    def test_markdown_contains_frontmatter(
        self, jinja_env, sample_article_data, sample_metadata
    ):
        """Test that frontmatter is properly formatted."""
        template = jinja_env.get_template("default.md.j2")
        markdown_content = template.render(
            metadata=sample_metadata, article_data=sample_article_data
        )

        # Check for YAML frontmatter markers
        assert markdown_content.startswith(
            "---"
        ), "Markdown should start with frontmatter delimiter"
        assert (
            "---" in markdown_content[1:]
        ), "Frontmatter should have closing delimiter"

        # Check for required frontmatter fields
        assert f'title: "{sample_metadata["title"]}"' in markdown_content
        assert f'date: "{sample_metadata["published_date"]}"' in markdown_content
        assert f'original_url: "{sample_metadata["url"]}"' in markdown_content
        assert f'source: "{sample_metadata["source"]}"' in markdown_content

    def test_markdown_handles_article_content_fallback(
        self, jinja_env, sample_metadata
    ):
        """Test that template falls back to article_content when content is missing."""
        article_data = {
            "summary": "Summary",
            "content": None,  # Missing primary field
            "article_content": "This is fallback content",
            "key_points": ["Point 1"],
        }
        template = jinja_env.get_template("default.md.j2")
        markdown_content = template.render(
            metadata=sample_metadata, article_data=article_data
        )

        assert (
            "This is fallback content" in markdown_content
        ), "Template should use article_content as fallback"

    def test_markdown_skips_missing_optional_sections(self, jinja_env, sample_metadata):
        """Test that template gracefully handles missing optional sections."""
        article_data = {
            "summary": None,
            "content": "Main content only",
            "article_content": None,
            "key_points": None,
        }
        template = jinja_env.get_template("default.md.j2")
        markdown_content = template.render(
            metadata=sample_metadata, article_data=article_data
        )

        # Should contain content and metadata, but not summary/key_points headers
        assert "Main content only" in markdown_content
        assert (
            "## Summary" not in markdown_content
        ), "Summary header should not appear when summary is missing"
        assert (
            "## Key Points" not in markdown_content
        ), "Key Points header should not appear when key_points is missing"
        assert "**Source:**" in markdown_content, "Source footer should always appear"
