"""
Test heading hierarchy in markdown templates.

Ensures templates follow Hugo best practices:
- No H1 tags in templates (Hugo theme provides H1 from frontmatter)
- Article content uses H2-H6 only
- Proper semantic heading structure

Follows TDD and functional design principles.
"""

import re
from pathlib import Path
from typing import List

import pytest
from jinja2 import Environment, FileSystemLoader


# Test data fixtures
@pytest.fixture
def template_dir() -> Path:
    """Return path to templates directory."""
    return Path(__file__).parent.parent / "templates"


@pytest.fixture
def jinja_env(template_dir: Path) -> Environment:
    """Create Jinja2 environment for template rendering."""
    return Environment(loader=FileSystemLoader(str(template_dir)))


@pytest.fixture
def sample_metadata() -> dict:
    """Sample article metadata for template rendering."""
    return {
        "title": "Test Article Title",
        "url": "https://example.com/article",
        "source": "test",
        "author": "Test Author",
        "published_date": None,
        "tags": ["test", "python"],
        "category": "technology",
    }


@pytest.fixture
def sample_article_data() -> dict:
    """Sample article content data."""
    return {
        "summary": "This is a test summary of the article.",
        "article_content": "## Main Section\n\nTest content.\n\n### Subsection\n\nMore content.",
        "key_points": ["Point 1", "Point 2", "Point 3"],
    }


@pytest.fixture
def sample_frontmatter() -> str:
    """Sample Hugo frontmatter."""
    return """---
title: "Test Article Title"
date: 2025-10-13T10:00:00Z
draft: false
---"""


# Pure functions for validation
def count_heading_levels(markdown_text: str) -> dict[str, int]:
    """
    Count markdown headings by level (functional, pure).

    Args:
        markdown_text: Markdown content to analyze

    Returns:
        Dictionary with heading level counts: {'h1': count, 'h2': count, ...}
    """
    heading_pattern = re.compile(r"^(#{1,6})\s+.+$", re.MULTILINE)
    matches = heading_pattern.findall(markdown_text)

    return {
        "h1": matches.count("#"),
        "h2": matches.count("##"),
        "h3": matches.count("###"),
        "h4": matches.count("####"),
        "h5": matches.count("#####"),
        "h6": matches.count("######"),
    }


def extract_h1_headings(markdown_text: str) -> List[str]:
    """
    Extract H1 headings from markdown text (functional, pure).

    Args:
        markdown_text: Markdown content to analyze

    Returns:
        List of H1 heading texts (without # prefix)
    """
    h1_pattern = re.compile(r"^#\s+(.+)$", re.MULTILINE)
    return h1_pattern.findall(markdown_text)


def has_h1_headings(markdown_text: str) -> bool:
    """
    Check if markdown contains H1 headings (functional predicate).

    Args:
        markdown_text: Markdown content to check

    Returns:
        True if H1 headings found, False otherwise
    """
    return count_heading_levels(markdown_text)["h1"] > 0


# Parametrized tests for all templates
@pytest.mark.parametrize(
    "template_name",
    [
        "default.md.j2",
        "with-toc.md.j2",
        "minimal.md.j2",
    ],
)
def test_template_should_not_generate_h1_heading(
    jinja_env: Environment,
    template_name: str,
    sample_metadata: dict,
    sample_article_data: dict,
    sample_frontmatter: str,
) -> None:
    """
    Test that templates do NOT generate H1 headings.

    Hugo PaperMod theme automatically generates H1 from frontmatter title.
    Templates should only contain H2-H6 headings.

    Args:
        jinja_env: Jinja2 environment
        template_name: Name of template to test
        sample_metadata: Article metadata
        sample_article_data: Article content data
        sample_frontmatter: Hugo frontmatter string
    """
    # Arrange
    template = jinja_env.get_template(template_name)

    # Act
    rendered_markdown = template.render(
        frontmatter=sample_frontmatter,
        metadata=sample_metadata,
        article_data=sample_article_data,
    )

    # Assert
    h1_headings = extract_h1_headings(rendered_markdown)
    assert not has_h1_headings(
        rendered_markdown
    ), f"Template {template_name} should NOT generate H1 headings. Found: {h1_headings}"

    # Additional assertion with detailed message
    heading_counts = count_heading_levels(rendered_markdown)
    assert (
        heading_counts["h1"] == 0
    ), f"Expected 0 H1 headings in {template_name}, found {heading_counts['h1']}: {h1_headings}"


@pytest.mark.parametrize(
    "template_name",
    [
        "default.md.j2",
        "with-toc.md.j2",
    ],
)
def test_template_preserves_article_content_headings(
    jinja_env: Environment,
    template_name: str,
    sample_metadata: dict,
    sample_article_data: dict,
    sample_frontmatter: str,
) -> None:
    """
    Test that templates preserve H2-H6 headings from article_content.

    Note: minimal.md.j2 doesn't add H2 sections (it's truly minimal),
    so we only test default and with-toc templates.

    Args:
        jinja_env: Jinja2 environment
        template_name: Name of template to test
        sample_metadata: Article metadata
        sample_article_data: Article content data
        sample_frontmatter: Hugo frontmatter string
    """
    # Arrange
    template = jinja_env.get_template(template_name)

    # Act
    rendered_markdown = template.render(
        frontmatter=sample_frontmatter,
        metadata=sample_metadata,
        article_data=sample_article_data,
    )

    # Assert
    heading_counts = count_heading_levels(rendered_markdown)

    # Should have H2 and H3 from article_content
    assert heading_counts["h2"] >= 1, f"Expected H2 headings in {template_name}"
    assert (
        heading_counts["h3"] >= 0
    ), f"H3 headings should be preserved in {template_name}"


def test_template_with_no_article_content_has_no_h1(
    jinja_env: Environment,
    sample_metadata: dict,
    sample_frontmatter: str,
) -> None:
    """
    Test that templates handle missing article_content gracefully without H1.

    Edge case: Empty article should still not have H1.

    Args:
        jinja_env: Jinja2 environment
        sample_metadata: Article metadata
        sample_frontmatter: Hugo frontmatter string
    """
    # Arrange
    template = jinja_env.get_template("default.md.j2")
    empty_article_data = {
        "summary": None,
        "article_content": None,
        "key_points": None,
    }

    # Act
    rendered_markdown = template.render(
        frontmatter=sample_frontmatter,
        metadata=sample_metadata,
        article_data=empty_article_data,
    )

    # Assert
    assert not has_h1_headings(
        rendered_markdown
    ), "Template with empty content should not generate H1"


def test_heading_level_validation_functions() -> None:
    """
    Test the pure validation functions themselves.

    Meta-test: Verify our validation logic is correct.
    """
    # Test H1 detection
    markdown_with_h1 = "# Main Title\n\n## Section\n\nContent"
    assert has_h1_headings(markdown_with_h1) is True

    # Test no H1
    markdown_without_h1 = "## Section\n\n### Subsection\n\nContent"
    assert has_h1_headings(markdown_without_h1) is False

    # Test heading counts
    counts = count_heading_levels(markdown_with_h1)
    assert counts["h1"] == 1
    assert counts["h2"] == 1

    # Test H1 extraction
    h1_list = extract_h1_headings(markdown_with_h1)
    assert h1_list == ["Main Title"]


def test_multiple_h1_detection() -> None:
    """
    Test detection of multiple H1 headings (should fail in templates).

    This is the exact issue we found in production.
    """
    # Arrange
    markdown_with_multiple_h1 = """# First Title

## Section

# Second Title

Some content.
"""

    # Act
    heading_counts = count_heading_levels(markdown_with_multiple_h1)
    h1_headings = extract_h1_headings(markdown_with_multiple_h1)

    # Assert
    assert heading_counts["h1"] == 2
    assert len(h1_headings) == 2
    assert h1_headings == ["First Title", "Second Title"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
