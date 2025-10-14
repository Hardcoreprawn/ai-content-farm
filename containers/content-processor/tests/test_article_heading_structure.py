"""
Test article content heading structure validation.

Ensures AI-generated article content follows Hugo/HTML best practices:
- No H1 headings (# syntax) in article_content
- Uses only H2-H6 headings (##, ###, ####, #####, ######)
- Headings are reasonably sized (< 100 chars recommended)
- No full paragraphs formatted as headings

Follows TDD, functional design, and PEP8.
"""

import re
from typing import List, Tuple

import pytest


# Pure validation functions (functional design)
def extract_heading_lines(markdown_text: str) -> List[Tuple[int, str, str]]:
    """
    Extract all heading lines from markdown text.

    Pure function with deterministic output.

    Args:
        markdown_text: Markdown content to analyze

    Returns:
        List of tuples: (heading_level, heading_text, full_line)
        where heading_level is 1-6

    Examples:
        >>> text = "# Main\\n## Section\\nContent"
        >>> headings = extract_heading_lines(text)
        >>> len(headings)
        2
        >>> headings[0][0]  # First heading level
        1
    """
    heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
    matches = heading_pattern.finditer(markdown_text)

    result = []
    for match in matches:
        hashes = match.group(1)
        text = match.group(2).strip()
        level = len(hashes)
        result.append((level, text, match.group(0)))

    return result


def has_h1_headings(markdown_text: str) -> bool:
    """
    Check if markdown contains H1 headings (functional predicate).

    Args:
        markdown_text: Markdown content to check

    Returns:
        True if H1 headings (# prefix) found, False otherwise

    Examples:
        >>> has_h1_headings("# Title\\n## Section")
        True
        >>> has_h1_headings("## Section\\n### Subsection")
        False
    """
    h1_pattern = re.compile(r"^#\s+.+$", re.MULTILINE)
    return bool(h1_pattern.search(markdown_text))


def find_overlong_headings(
    markdown_text: str, max_length: int = 100
) -> List[Tuple[int, str]]:
    """
    Find headings exceeding recommended length.

    Pure function for validation.

    Args:
        markdown_text: Markdown content
        max_length: Maximum recommended heading length (default: 100 chars)

    Returns:
        List of tuples: (heading_level, heading_text) for overlong headings

    Examples:
        >>> text = "## Short\\n## " + ("x" * 150)
        >>> overlong = find_overlong_headings(text, max_length=100)
        >>> len(overlong)
        1
    """
    headings = extract_heading_lines(markdown_text)
    return [(level, text) for level, text, _ in headings if len(text) > max_length]


def validate_heading_hierarchy(markdown_text: str) -> dict:
    """
    Validate heading structure in markdown (pure function).

    Returns comprehensive validation results as a dictionary.

    Args:
        markdown_text: Markdown content to validate

    Returns:
        Dict with validation results:
            - has_h1: bool
            - h1_count: int
            - total_headings: int
            - heading_levels: dict (count per level)
            - overlong_headings: list
            - valid: bool (overall validation status)

    Examples:
        >>> text = "## Good Section\\n### Subsection"
        >>> result = validate_heading_hierarchy(text)
        >>> result['valid']
        True
        >>> result['has_h1']
        False
    """
    headings = extract_heading_lines(markdown_text)

    heading_levels = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}
    for level, _, _ in headings:
        heading_levels[level] += 1

    overlong = find_overlong_headings(markdown_text)

    return {
        "has_h1": heading_levels[1] > 0,
        "h1_count": heading_levels[1],
        "total_headings": len(headings),
        "heading_levels": heading_levels,
        "overlong_headings": overlong,
        "valid": heading_levels[1] == 0 and len(overlong) == 0,
    }


# Test article_content samples
@pytest.fixture
def valid_article_content() -> str:
    """Sample article content following H2-H6 guidelines."""
    return """## Introduction

This is the introduction to our article.

## Main Section

### Subsection A

Content about subsection A.

### Subsection B

Content about subsection B.

#### Deep Dive

More detailed content.

## Conclusion

Summary and takeaways.
"""


@pytest.fixture
def invalid_article_with_h1() -> str:
    """Sample article content with H1 (should fail)."""
    return """# Main Title

## Section

This content incorrectly uses H1.

## Another Section

More content.
"""


@pytest.fixture
def article_with_overlong_heading() -> str:
    """Sample article with excessively long heading."""
    return """## Introduction

## In conclusion, the GStreamer Conference 2025 promises to be a rich and rewarding experience for all attendees, offering a comprehensive look at the future of multimedia technology through the lens of open-source innovation.

Content here.
"""


# Tests for validation functions (meta-tests)
def test_extract_heading_lines() -> None:
    """Test the heading extraction function."""
    markdown = """# Title
## Section
### Subsection
Regular text
## Another Section"""

    headings = extract_heading_lines(markdown)

    assert len(headings) == 4
    assert headings[0] == (1, "Title", "# Title")
    assert headings[1] == (2, "Section", "## Section")
    assert headings[2] == (3, "Subsection", "### Subsection")
    assert headings[3] == (2, "Another Section", "## Another Section")


def test_has_h1_headings_predicate() -> None:
    """Test H1 detection predicate."""
    assert has_h1_headings("# Title") is True
    assert has_h1_headings("## Section") is False
    assert has_h1_headings("# Title\n## Section") is True
    assert has_h1_headings("Content without headings") is False


def test_find_overlong_headings() -> None:
    """Test overlong heading detection."""
    short_heading = "## Short Title"
    long_heading = "## " + ("x" * 150)

    overlong = find_overlong_headings(long_heading, max_length=100)
    assert len(overlong) == 1
    assert overlong[0][0] == 2  # H2 level

    overlong = find_overlong_headings(short_heading, max_length=100)
    assert len(overlong) == 0


# Critical validation tests for article_content
def test_article_content_should_not_contain_h1_headings(
    valid_article_content: str,
) -> None:
    """
    Test that valid article content does NOT contain H1 headings.

    CRITICAL: This is the primary issue found in production.
    Hugo theme provides H1 from frontmatter. Article content
    must use H2-H6 only.

    Args:
        valid_article_content: Sample valid content
    """
    # Arrange
    validation = validate_heading_hierarchy(valid_article_content)

    # Assert
    assert not validation["has_h1"], "Article content must not contain H1 headings"
    assert validation["h1_count"] == 0, "Expected zero H1 headings"
    assert validation["heading_levels"][2] > 0, "Should have H2 headings"


def test_article_content_with_h1_should_fail_validation(
    invalid_article_with_h1: str,
) -> None:
    """
    Test that content with H1 headings fails validation.

    This test should PASS (detecting the problem correctly).

    Args:
        invalid_article_with_h1: Sample invalid content with H1
    """
    # Arrange
    validation = validate_heading_hierarchy(invalid_article_with_h1)

    # Assert
    assert validation["has_h1"] is True, "Should detect H1 heading"
    assert validation["h1_count"] >= 1, "Should count H1 headings"
    assert validation["valid"] is False, "Content with H1 should be invalid"


def test_article_headings_should_be_reasonably_sized(
    valid_article_content: str,
) -> None:
    """
    Test that headings are not excessively long.

    Headings should be concise (< 100 chars recommended).
    Full paragraphs should not be formatted as headings.

    Args:
        valid_article_content: Sample valid content
    """
    # Arrange
    validation = validate_heading_hierarchy(valid_article_content)

    # Assert
    assert (
        len(validation["overlong_headings"]) == 0
    ), f"Found overlong headings: {validation['overlong_headings']}"


def test_article_with_overlong_heading_should_fail_validation(
    article_with_overlong_heading: str,
) -> None:
    """
    Test that content with overlong headings fails validation.

    This is the second issue found in production: 448-character H2 heading.

    Args:
        article_with_overlong_heading: Sample content with overlong heading
    """
    # Arrange
    validation = validate_heading_hierarchy(article_with_overlong_heading)

    # Assert
    assert len(validation["overlong_headings"]) > 0, "Should detect overlong heading"
    assert (
        validation["valid"] is False
    ), "Content with overlong headings should be invalid"

    # Check the specific overlong heading
    overlong_heading_text = validation["overlong_headings"][0][1]
    assert len(overlong_heading_text) > 100, "Heading should exceed 100 characters"


def test_validate_heading_hierarchy_comprehensive() -> None:
    """
    Test comprehensive heading hierarchy validation.

    Validates all aspects of heading structure.
    """
    # Arrange
    markdown_with_issues = (
        """# Top Level (H1 - Invalid)

## Section 1

### Subsection

## """
        + ("x" * 150)
        + """

Content here.
"""
    )

    # Act
    validation = validate_heading_hierarchy(markdown_with_issues)

    # Assert
    assert validation["has_h1"] is True
    assert validation["h1_count"] == 1
    assert validation["total_headings"] == 4
    assert len(validation["overlong_headings"]) == 1
    assert validation["valid"] is False


def test_article_content_uses_h2_as_top_level() -> None:
    """
    Test that article content starts with H2, not H1.

    Best practice: H1 is page title (from Hugo theme).
    Article sections should be H2 level.
    """
    # Arrange
    good_structure = """## Introduction

Content introduction.

## Main Section

Main content.

### Subsection

Details.
"""

    bad_structure = """# Main Title

## Section

Content.
"""

    # Act
    good_validation = validate_heading_hierarchy(good_structure)
    bad_validation = validate_heading_hierarchy(bad_structure)

    # Assert
    assert good_validation["h1_count"] == 0, "Good structure has no H1"
    assert (
        good_validation["heading_levels"][2] >= 1
    ), "Good structure uses H2 as top level"

    assert bad_validation["h1_count"] >= 1, "Bad structure has H1"
    assert bad_validation["valid"] is False, "Bad structure should be invalid"


def test_heading_content_edge_cases() -> None:
    """Test edge cases in heading validation."""
    # Empty content
    empty_validation = validate_heading_hierarchy("")
    assert empty_validation["valid"] is True
    assert empty_validation["total_headings"] == 0

    # Only H1s (invalid)
    only_h1 = "# Title 1\n\n# Title 2"
    h1_validation = validate_heading_hierarchy(only_h1)
    assert h1_validation["valid"] is False
    assert h1_validation["h1_count"] == 2

    # Mixed valid headings
    mixed_valid = "## H2\n### H3\n#### H4\n##### H5\n###### H6"
    mixed_validation = validate_heading_hierarchy(mixed_valid)
    assert mixed_validation["valid"] is True
    assert mixed_validation["total_headings"] == 5


# Integration test for prompt building
def test_article_generation_prompt_should_instruct_h2_h6_only() -> None:
    """
    Test that article generation prompts instruct AI to use H2-H6 only.

    This test will initially FAIL, then we'll update the prompt.
    """
    # Import the prompt building function
    from operations.openai_operations import build_article_prompt

    # Arrange & Act
    prompt = build_article_prompt(
        topic_title="Test Article",
        target_word_count=3000,
    )

    # Assert - Check if prompt contains heading guidance
    # NOTE: This will FAIL initially, which is expected in TDD
    assert (
        "H2" in prompt or "##" in prompt or "heading" in prompt.lower()
    ), "Prompt should mention heading structure"

    # Ideally, prompt should explicitly forbid H1
    # This assertion will likely FAIL initially:
    heading_guidance_keywords = ["H1", "single #", "title heading", "##"]
    has_heading_guidance = any(
        keyword in prompt for keyword in heading_guidance_keywords
    )

    assert has_heading_guidance, (
        "Prompt should include explicit guidance about heading levels. "
        "Expected instruction to use H2-H6 (##-######) only, not H1 (#)"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
