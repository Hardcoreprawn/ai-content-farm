"""
Pure functions for text processing and markdown conversion.

Provides secure, functional utilities for converting markdown to HTML,
cleaning titles, and generating previews. Uses standard markdown library
instead of reinventing the wheel.

Following project standards:
- Use existing libraries (markdown, bleach) over bespoke solutions
- Functional programming (pure functions)
- Security first (HTML sanitization, input validation)
- Clear separation of concerns
"""

import logging
import re
from html import escape
from typing import Optional

import bleach
import markdown
from markdown.extensions import fenced_code, nl2br, tables

logger = logging.getLogger(__name__)

# Allowed HTML tags after markdown conversion (for bleach sanitization)
ALLOWED_TAGS = [
    "p",
    "br",
    "strong",
    "em",
    "u",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "a",
    "ul",
    "ol",
    "li",
    "blockquote",
    "code",
    "pre",
    "hr",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
]

ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "rel"],
    "code": ["class"],  # For syntax highlighting
}


def markdown_to_html(content: Optional[str], sanitize: bool = True) -> str:
    """
    Convert markdown text to clean, secure HTML using standard markdown library.

    Uses Python-Markdown library (already in requirements.txt) with security
    sanitization via bleach to prevent XSS attacks.

    Args:
        content: Markdown-formatted text
        sanitize: Whether to sanitize HTML output (default: True)

    Returns:
        Valid HTML string with proper tag nesting

    Examples:
        >>> markdown_to_html("# Hello World")
        '<h1>Hello World</h1>'

        >>> markdown_to_html("This is **bold** text")
        '<p>This is <strong>bold</strong> text</p>'

        >>> markdown_to_html("<script>alert('xss')</script>")
        '<p>alert(&#39;xss&#39;)</p>'
    """
    if not content:
        return ""

    try:
        # Convert markdown to HTML using standard library
        # Extensions:
        # - fenced_code: Support ```code blocks```
        # - tables: Support markdown tables
        # - nl2br: Convert newlines to <br> tags
        md = markdown.Markdown(
            extensions=[
                "fenced_code",
                "tables",
                "nl2br",
                "sane_lists",  # Better list handling
            ],
            output_format="html",  # 'html' or 'xhtml', not 'html5'
        )

        html = md.convert(content)

        # Security: Sanitize output to prevent XSS
        if sanitize:
            html = bleach.clean(
                html,
                tags=ALLOWED_TAGS,
                attributes=ALLOWED_ATTRIBUTES,
                strip=True,  # Strip disallowed tags instead of escaping
            )

        logger.debug(
            f"Converted markdown to HTML: {len(content)} chars -> {len(html)} chars"
        )

        return html

    except Exception as e:
        logger.error(f"Markdown conversion failed: {e}")
        # Fallback: return escaped content as paragraph
        return f"<p>{escape(content)}</p>"


def create_plain_text_preview(content: Optional[str], max_length: int = 200) -> str:
    """
    Create clean plain-text preview from markdown content.

    Strips all markdown formatting, structural headers, and URLs to create
    a clean, readable preview suitable for article cards and listings.

    Uses standard library approach: markdown -> HTML -> strip tags -> clean text

    Args:
        content: Markdown-formatted content
        max_length: Maximum preview length in characters (default: 200)

    Returns:
        Clean plain text preview with ellipsis if truncated

    Examples:
        >>> create_plain_text_preview("**Title:** My Article\\n\\nThis is content")
        'Title: My Article This is content'

        >>> create_plain_text_preview("Check out https://example.com for more")
        'Check out for more'

        >>> create_plain_text_preview("A" * 300, max_length=50)
        'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA...'
    """
    if not content:
        return "No preview available"

    # First convert markdown to HTML to properly handle formatting
    html = markdown_to_html(content, sanitize=True)

    # Strip HTML tags to get plain text
    text = strip_html_tags(html)

    # Remove structural markers common in AI-generated content
    text = re.sub(
        r"(Title|Introduction|Key Insights?|Conclusion|Summary):\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # Remove URLs (full and truncated)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"www\.\S+", "", text)

    # Clean up multiple spaces
    text = re.sub(r"\s+", " ", text).strip()

    # Remove leading/trailing punctuation left from cleaning
    text = re.sub(r"^[.,;:\s]+", "", text)
    text = re.sub(r"[.,;:\s]+$", "", text)

    # Truncate at word boundary if needed
    if len(text) > max_length:
        # Find last space before max_length
        truncated = text[:max_length]
        last_space = truncated.rfind(" ")
        if last_space > 0:
            text = truncated[:last_space] + "..."
        else:
            text = truncated + "..."

    logger.debug(f"Created preview: {len(content)} chars -> {len(text)} chars")

    return text if text else "No preview available"


def clean_title(title: Optional[str]) -> str:
    """
    Remove URLs and artifacts from article titles.

    Cleans titles by removing embedded URLs, truncated URL fragments,
    and common URL patterns that leak into titles from content sources.

    Args:
        title: Raw article title possibly containing URLs

    Returns:
        Cleaned title without URLs or truncation artifacts

    Examples:
        >>> clean_title("Article Title https://example.com/article")
        'Article Title'

        >>> clean_title("News Story www.site.com/news/arti...")
        'News Story'

        >>> clean_title("Title:  Multiple   Spaces")
        'Title: Multiple Spaces'
    """
    if not title:
        return ""

    # Remove full URLs (http/https)
    title = re.sub(r"https?://\S+", "", title)

    # Remove www. URLs
    title = re.sub(r"www\.\S+", "", title)

    # Remove truncated URLs (anything ending with ...)
    title = re.sub(r"\S*\.{3,}", "", title)

    # Remove common URL fragments
    title = re.sub(r"\S+\.com\S*", "", title)
    title = re.sub(r"\S+\.org\S*", "", title)
    title = re.sub(r"\S+\.net\S*", "", title)

    # Clean up multiple spaces
    title = re.sub(r"\s+", " ", title).strip()

    # Remove trailing punctuation left from URL removal
    title = re.sub(r"\s+[.,;:]+$", "", title)

    # Remove leading punctuation
    title = re.sub(r"^[.,;:\s]+", "", title)

    logger.debug(f"Cleaned title: removed URLs and artifacts")

    return title


def strip_html_tags(html: Optional[str]) -> str:
    """
    Strip HTML tags to get plain text content.

    Utility function for extracting text from HTML when needed.
    Preserves text content while removing all tags.

    Args:
        html: HTML string

    Returns:
        Plain text without HTML tags

    Examples:
        >>> strip_html_tags("<p>Hello <strong>world</strong></p>")
        'Hello world'

        >>> strip_html_tags("<a href='#'>Link</a> text")
        'Link text'
    """
    if not html:
        return ""

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", html)

    # Decode HTML entities
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&amp;", "&")
    text = text.replace("&quot;", '"')
    text = text.replace("&#x27;", "'")
    text = text.replace("&#39;", "'")

    # Clean up whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def sanitize_filename(text: Optional[str], max_length: int = 100) -> str:
    """
    Convert text to safe filename.

    Creates URL-safe, filesystem-safe filenames from arbitrary text.
    Used for generating article slugs and file paths.

    Args:
        text: Text to convert to filename
        max_length: Maximum filename length (default: 100)

    Returns:
        Safe filename string

    Examples:
        >>> sanitize_filename("Hello World!")
        'hello-world'

        >>> sanitize_filename("Article: Special & Characters?")
        'article-special-characters'

        >>> sanitize_filename("A" * 150, max_length=50)
        'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
    """
    if not text:
        return "unnamed"

    # Convert to lowercase
    filename = text.lower()

    # Remove URLs first
    filename = re.sub(r"https?://\S+", "", filename)

    # Replace spaces and underscores with hyphens
    filename = re.sub(r"[\s_]+", "-", filename)

    # Remove non-alphanumeric characters (except hyphens)
    filename = re.sub(r"[^a-z0-9-]", "", filename)

    # Remove multiple consecutive hyphens
    filename = re.sub(r"-+", "-", filename)

    # Remove leading/trailing hyphens
    filename = filename.strip("-")

    # Truncate to max length
    if len(filename) > max_length:
        filename = filename[:max_length].rstrip("-")

    # Ensure we have something
    if not filename:
        return "unnamed"

    return filename


def validate_html_structure(html: Optional[str]) -> bool:
    """
    Validate basic HTML structure for common issues.

    Checks for unclosed tags and malformed HTML patterns that
    could cause rendering issues.

    Args:
        html: HTML string to validate

    Returns:
        True if HTML appears valid, False otherwise

    Examples:
        >>> validate_html_structure("<p>Valid paragraph</p>")
        True

        >>> validate_html_structure("<p>Unclosed paragraph")
        False

        >>> validate_html_structure("<strong>Text<strong>")
        False
    """
    if not html:
        return True

    # Check for basic tag balance
    tag_stack = []
    tag_pattern = re.compile(r"<(/?)([a-z][a-z0-9]*)\b[^>]*>", re.IGNORECASE)

    for match in tag_pattern.finditer(html):
        is_closing = match.group(1) == "/"
        tag_name = match.group(2).lower()

        # Skip self-closing tags
        if tag_name in ["br", "hr", "img", "input", "meta", "link"]:
            continue

        if is_closing:
            if not tag_stack or tag_stack[-1] != tag_name:
                logger.warning(f"Unmatched closing tag: </{tag_name}>")
                return False
            tag_stack.pop()
        else:
            tag_stack.append(tag_name)

    # Check if all tags were closed
    if tag_stack:
        logger.warning(f"Unclosed tags: {tag_stack}")
        return False

    return True


def register_jinja_filters(jinja_env):
    """
    Register custom Jinja2 filters for text processing.

    Add custom filters to Jinja2 environment for use in templates:
    - markdown: Convert markdown to HTML
    - preview: Create plain text preview
    - clean_title: Remove URLs from titles

    Args:
        jinja_env: Jinja2 Environment instance

    Returns:
        Modified Jinja2 Environment with custom filters

    Example:
        >>> from jinja2 import Environment
        >>> env = Environment()
        >>> env = register_jinja_filters(env)
        >>> '{{ content | markdown }}' in env.from_string('{{ content | markdown }}').render(content='# Hello')
        True
    """
    jinja_env.filters["markdown"] = markdown_to_html
    jinja_env.filters["preview"] = create_plain_text_preview
    jinja_env.filters["clean_title"] = clean_title
    jinja_env.filters["strip_html"] = strip_html_tags

    logger.info(
        "Registered custom Jinja2 filters: markdown, preview, clean_title, strip_html"
    )

    return jinja_env
