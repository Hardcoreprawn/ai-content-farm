"""
Unit tests for text_processing module.

Tests markdown conversion, preview generation, title cleaning,
and HTML validation using standard libraries (markdown, bleach).
"""

import pytest
from jinja2 import Environment
from text_processing import (
    clean_title,
    create_plain_text_preview,
    markdown_to_html,
    register_jinja_filters,
    sanitize_filename,
    strip_html_tags,
    validate_html_structure,
)


class TestMarkdownToHtml:
    """Test markdown to HTML conversion using standard markdown library."""

    def test_converts_headers(self):
        """Test conversion of markdown headers to HTML."""
        assert "<h1>Hello World</h1>" in markdown_to_html("# Hello World")
        assert "<h2>Section</h2>" in markdown_to_html("## Section")
        assert "<h3>Subsection</h3>" in markdown_to_html("### Subsection")

    def test_converts_bold_text(self):
        """Test conversion of bold markdown to HTML."""
        result = markdown_to_html("This is **bold** text")
        assert "<strong>bold</strong>" in result
        assert "<p>" in result

    def test_converts_italic_text(self):
        """Test conversion of italic markdown to HTML."""
        result = markdown_to_html("This is *italic* text")
        assert "<em>italic</em>" in result

    def test_converts_links(self):
        """Test conversion of markdown links to HTML."""
        result = markdown_to_html("[Click here](https://example.com)")
        assert '<a href="https://example.com">Click here</a>' in result

    def test_handles_empty_content(self):
        """Test handling of empty content."""
        assert markdown_to_html("") == ""
        assert markdown_to_html(None) == ""

    def test_sanitizes_xss_attempts(self):
        """Test that XSS attempts are sanitized."""
        result = markdown_to_html("<script>alert('xss')</script>")
        # Script tags should be stripped or escaped
        assert "<script>" not in result
        assert "alert" in result  # Content preserved but script tags removed

    def test_handles_mixed_formatting(self):
        """Test handling of mixed markdown formatting."""
        content = "# Title\n\nThis is **bold** and *italic* text with a [link](https://example.com)"
        result = markdown_to_html(content)
        assert "<h1>Title</h1>" in result
        assert "<strong>bold</strong>" in result
        assert "<em>italic</em>" in result
        assert "https://example.com" in result

    def test_handles_code_blocks(self):
        """Test handling of fenced code blocks."""
        content = "```python\nprint('hello')\n```"
        result = markdown_to_html(content)
        assert "<code>" in result or "<pre>" in result

    def test_handles_lists(self):
        """Test handling of markdown lists."""
        content = "- Item 1\n- Item 2\n- Item 3"
        result = markdown_to_html(content)
        assert "<ul>" in result or "<li>" in result


class TestCreatePlainTextPreview:
    """Test plain text preview generation from markdown."""

    def test_strips_markdown_formatting(self):
        """Test that markdown formatting is stripped."""
        content = "**Title:** My Article\n\nThis is **bold** and *italic* text"
        preview = create_plain_text_preview(content)
        assert "**" not in preview
        assert "*" not in preview
        assert "Title:" in preview or "My Article" in preview

    def test_removes_urls(self):
        """Test that URLs are removed from previews."""
        content = "Check out https://example.com for more info"
        preview = create_plain_text_preview(content)
        assert "https://example.com" not in preview
        assert "Check out" in preview

    def test_truncates_long_content(self):
        """Test that long content is truncated with ellipsis."""
        content = "A" * 300
        preview = create_plain_text_preview(content, max_length=50)
        assert len(preview) <= 53  # 50 + "..."
        assert preview.endswith("...")

    def test_handles_empty_content(self):
        """Test handling of empty content."""
        assert create_plain_text_preview("") == "No preview available"
        assert create_plain_text_preview(None) == "No preview available"

    def test_removes_structural_headers(self):
        """Test that structural headers are removed."""
        content = "**Introduction:** This is the article content"
        preview = create_plain_text_preview(content)
        assert "Introduction:" not in preview or preview.startswith("This is")

    def test_preserves_readable_text(self):
        """Test that readable text is preserved."""
        content = "This is a simple article about technology and innovation."
        preview = create_plain_text_preview(content)
        assert "technology" in preview
        assert "innovation" in preview

    def test_truncates_at_word_boundary(self):
        """Test that truncation happens at word boundaries."""
        content = "The quick brown fox jumps over the lazy dog many times"
        preview = create_plain_text_preview(content, max_length=30)
        # Should not cut words in half
        assert not preview.replace("...", "").endswith("jump")
        assert preview.endswith("...")


class TestCleanTitle:
    """Test title cleaning to remove URLs and artifacts."""

    def test_removes_full_urls(self):
        """Test removal of full URLs from titles."""
        title = "Article Title https://example.com/article"
        cleaned = clean_title(title)
        assert "https://example.com" not in cleaned
        assert "Article Title" in cleaned

    def test_removes_www_urls(self):
        """Test removal of www. URLs."""
        title = "News Story www.site.com/news"
        cleaned = clean_title(title)
        assert "www.site.com" not in cleaned
        assert "News Story" in cleaned

    def test_removes_truncated_urls(self):
        """Test removal of truncated URL fragments."""
        title = "Article www.example.com/arti..."
        cleaned = clean_title(title)
        assert "..." not in cleaned
        assert "www." not in cleaned

    def test_cleans_whitespace(self):
        """Test whitespace cleaning."""
        title = "Title:  Multiple   Spaces"
        cleaned = clean_title(title)
        assert "  " not in cleaned
        assert cleaned == "Title: Multiple Spaces"

    def test_handles_empty_title(self):
        """Test handling of empty titles."""
        assert clean_title("") == ""
        assert clean_title(None) == ""

    def test_preserves_valid_titles(self):
        """Test that valid titles are preserved."""
        title = "This is a Valid Article Title"
        cleaned = clean_title(title)
        assert cleaned == title


class TestStripHtmlTags:
    """Test HTML tag stripping."""

    def test_strips_simple_tags(self):
        """Test stripping of simple HTML tags."""
        html = "<p>Hello <strong>world</strong></p>"
        text = strip_html_tags(html)
        assert "<p>" not in text
        assert "<strong>" not in text
        assert "Hello world" in text

    def test_decodes_html_entities(self):
        """Test decoding of HTML entities."""
        html = "Test &amp; example &lt;tag&gt;"
        text = strip_html_tags(html)
        assert "&amp;" not in text
        assert "&lt;" not in text
        assert "&" in text
        assert "<" in text

    def test_handles_empty_html(self):
        """Test handling of empty HTML."""
        assert strip_html_tags("") == ""
        assert strip_html_tags(None) == ""


class TestSanitizeFilename:
    """Test filename sanitization."""

    def test_converts_to_lowercase(self):
        """Test conversion to lowercase."""
        assert sanitize_filename("Hello World") == "hello-world"

    def test_replaces_spaces_with_hyphens(self):
        """Test space replacement."""
        assert sanitize_filename("my test file") == "my-test-file"

    def test_removes_special_characters(self):
        """Test removal of special characters."""
        filename = sanitize_filename("Article: Special & Characters?")
        assert ":" not in filename
        assert "&" not in filename
        assert "?" not in filename

    def test_removes_urls(self):
        """Test URL removal from filenames."""
        filename = sanitize_filename("Article https://example.com")
        assert "https" not in filename
        assert "example" not in filename

    def test_truncates_long_filenames(self):
        """Test truncation of long filenames."""
        long_name = "A" * 150
        filename = sanitize_filename(long_name, max_length=50)
        assert len(filename) <= 50

    def test_handles_empty_input(self):
        """Test handling of empty input."""
        assert sanitize_filename("") == "unnamed"
        assert sanitize_filename(None) == "unnamed"


class TestValidateHtmlStructure:
    """Test HTML structure validation."""

    def test_validates_correct_html(self):
        """Test validation of correct HTML."""
        assert validate_html_structure("<p>Valid paragraph</p>") is True
        assert validate_html_structure("<div><p>Nested</p></div>") is True

    def test_detects_unclosed_tags(self):
        """Test detection of unclosed tags."""
        assert validate_html_structure("<p>Unclosed paragraph") is False
        assert validate_html_structure("<div><p>Nested</div>") is False

    def test_detects_unmatched_closing_tags(self):
        """Test detection of unmatched closing tags."""
        assert validate_html_structure("</p>") is False
        assert validate_html_structure("<strong>Text<strong>") is False

    def test_ignores_self_closing_tags(self):
        """Test that self-closing tags are ignored."""
        assert validate_html_structure("<br>") is True
        assert validate_html_structure("<hr>") is True
        assert validate_html_structure("<img src='test.jpg'>") is True

    def test_handles_empty_html(self):
        """Test handling of empty HTML."""
        assert validate_html_structure("") is True
        assert validate_html_structure(None) is True


class TestRegisterJinjaFilters:
    """Test Jinja2 filter registration."""

    def test_registers_filters(self):
        """Test that filters are registered correctly."""
        env = Environment()
        env = register_jinja_filters(env)

        # Check that filters are registered
        assert "markdown" in env.filters
        assert "preview" in env.filters
        assert "clean_title" in env.filters
        assert "strip_html" in env.filters

    def test_markdown_filter_works_in_template(self):
        """Test that markdown filter works in templates."""
        env = Environment()
        env = register_jinja_filters(env)

        template = env.from_string("{{ content | markdown }}")
        result = template.render(content="**Bold text**")
        assert "<strong>Bold text</strong>" in result

    def test_preview_filter_works_in_template(self):
        """Test that preview filter works in templates."""
        env = Environment()
        env = register_jinja_filters(env)

        template = env.from_string("{{ content | preview(50) }}")
        result = template.render(content="A" * 100)
        assert len(result) <= 53  # 50 + "..."

    def test_clean_title_filter_works_in_template(self):
        """Test that clean_title filter works in templates."""
        env = Environment()
        env = register_jinja_filters(env)

        template = env.from_string("{{ title | clean_title }}")
        result = template.render(title="Article https://example.com")
        assert "https://" not in result
        assert "Article" in result


# Integration test
class TestTextProcessingIntegration:
    """Integration tests for text processing pipeline."""

    def test_full_article_processing_pipeline(self):
        """Test full pipeline: markdown -> HTML -> preview."""
        # Original markdown content
        markdown_content = """# Introduction

This is an **important** article about *technology*.

Check out https://example.com for more details.

## Key Points

- Point 1
- Point 2
- Point 3
"""

        # Convert to HTML
        html = markdown_to_html(markdown_content)
        assert "<h1>Introduction</h1>" in html
        assert "<strong>important</strong>" in html
        assert "<em>technology</em>" in html

        # Generate preview
        preview = create_plain_text_preview(markdown_content)
        assert "**" not in preview
        assert "*" not in preview
        assert "https://example.com" not in preview
        assert "Introduction" in preview or "important" in preview

        # Validate HTML structure
        assert validate_html_structure(html) is True

    def test_handles_malformed_markdown_gracefully(self):
        """Test graceful handling of malformed markdown."""
        # Unclosed bold markers
        content = "This is **unclosed bold text"
        html = markdown_to_html(content)
        # Should still produce valid HTML
        assert validate_html_structure(html) is True

        # Can still generate preview
        preview = create_plain_text_preview(content)
        assert preview  # Should not be empty or error
