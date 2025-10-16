"""
Test fixes for site generation issues.

Tests the critical fixes for:
1. Missing article content (field name mismatch)
2. Wrong source attribution (extract from nested field)
3. Wrong source URL (use source_metadata.source_url)
"""

from datetime import datetime, timezone

import pytest
from jinja2 import DictLoader, Environment
from markdown_generator import generate_markdown_content
from metadata_utils import extract_metadata_from_article


def test_article_content_field_extraction():
    """Test that article content is extracted from 'content' field."""
    article_data = {
        "title": "Test Article",
        "url": "/articles/test",
        "content": "## Test Content\n\nThis is the article body.",
        "published_date": "2025-10-16T10:00:00Z",
    }

    metadata = extract_metadata_from_article(article_data)

    # Create minimal Jinja template
    template_str = """{{ frontmatter }}
{%- if article_data.content %}
{{ article_data.content }}
{%- endif %}"""

    env = Environment(loader=DictLoader({"test.md.j2": template_str}))

    # Mock frontmatter
    from unittest.mock import patch

    with patch("markdown_generator.prepare_frontmatter") as mock_fm:
        mock_fm.return_value = "---\ntitle: Test\n---"

        result = generate_markdown_content(
            article_data=article_data,
            metadata=metadata,
            jinja_env=env,
            template_name="test.md.j2",
        )

    assert "## Test Content" in result
    assert "This is the article body." in result


def test_source_extraction_from_nested_metadata():
    """Test that source is extracted from source_metadata.source."""
    article_data = {
        "title": "Test Article",
        "url": "/articles/test",
        "source_metadata": {
            "source": "mastodon",
            "source_url": "https://mastodon.social/@user/123456",
        },
    }

    metadata = extract_metadata_from_article(article_data)

    assert metadata.source == "mastodon"
    assert metadata.source != "unknown"


def test_source_url_from_nested_metadata():
    """Test that source_url is extracted from source_metadata."""
    article_data = {
        "title": "Test Article",
        "url": "/articles/test",
        "source_metadata": {
            "source": "mastodon",
            "source_url": "https://mastodon.social/@user/123456",
            "original_title": "Original Title",
        },
    }

    metadata = extract_metadata_from_article(article_data)

    # Create minimal Jinja template with source attribution
    template_str = """{{ frontmatter }}
{%- if article_data.source_metadata and article_data.source_metadata.source_url %}
Originally posted on {{ article_data.source_metadata.source|title }}: {{ article_data.source_metadata.source_url }}
{%- endif %}"""

    env = Environment(loader=DictLoader({"test.md.j2": template_str}))

    from unittest.mock import patch

    with patch("markdown_generator.prepare_frontmatter") as mock_fm:
        mock_fm.return_value = "---\ntitle: Test\n---"

        result = generate_markdown_content(
            article_data=article_data,
            metadata=metadata,
            jinja_env=env,
            template_name="test.md.j2",
        )

    assert "Originally posted on Mastodon" in result
    assert "https://mastodon.social/@user/123456" in result


def test_fallback_to_unknown_source():
    """Test that source falls back to 'unknown' when not in source_metadata."""
    article_data = {
        "title": "Test Article",
        "url": "/articles/test",
    }

    metadata = extract_metadata_from_article(article_data)

    assert metadata.source == "unknown"


def test_real_world_mastodon_article():
    """Test with real-world Mastodon article structure."""
    article_data = {
        "article_id": "article_20251016_104549",
        "topic_id": "mastodon_mastodon.social_115383358597059180",
        "title": "Windows Zero-Day Vulnerabilities: A Critical Security Concern",
        "url": "/articles/2025-10-16-windows-zero-days.html",
        "published_date": "2025-10-16T10:45:49.229784+00:00",
        "content": "## Windows Zero-Day Vulnerabilities\n\nDetailed article content here...",
        "source_metadata": {
            "source": "mastodon",
            "source_url": "https://mastodon.social/@security/123456",
            "original_title": "Windows Zero-Days Exploited",
        },
    }

    metadata = extract_metadata_from_article(article_data)

    # Verify correct extraction
    assert metadata.source == "mastodon"
    assert (
        metadata.title
        == "Windows Zero-Day Vulnerabilities: A Critical Security Concern"
    )

    # Verify content would be included in markdown
    template_str = """{{ frontmatter }}
{%- if article_data.content %}
{{ article_data.content }}
{%- endif %}
---
{%- if article_data.source_metadata and article_data.source_metadata.source_url %}
Originally posted on {{ article_data.source_metadata.source|title }}: [View original]({{ article_data.source_metadata.source_url }})
{%- endif %}"""

    env = Environment(loader=DictLoader({"test.md.j2": template_str}))

    from unittest.mock import patch

    with patch("markdown_generator.prepare_frontmatter") as mock_fm:
        mock_fm.return_value = "---\ntitle: Test\n---"

        result = generate_markdown_content(
            article_data=article_data,
            metadata=metadata,
            jinja_env=env,
            template_name="test.md.j2",
        )

    # All critical elements should be present
    assert "## Windows Zero-Day Vulnerabilities" in result
    assert "Detailed article content here..." in result
    assert "Originally posted on Mastodon" in result
    assert "https://mastodon.social/@security/123456" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
