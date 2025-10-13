"""
Hugo frontmatter generation utilities.

This module provides functions to generate Hugo-compliant YAML frontmatter
that meets all Hugo specifications for date formatting, field types, and structure.

The primary entry point is prepare_frontmatter(), which provides an extensible
interface for generating frontmatter in different formats (currently Hugo).
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

import yaml

__all__ = [
    "generate_hugo_frontmatter",
    "prepare_frontmatter",
    "validate_frontmatter_fields",
]


def generate_hugo_frontmatter(
    title: str,
    date: Optional[datetime] = None,
    draft: bool = False,
    description: Optional[str] = None,
    keywords: Optional[list[str]] = None,
    **custom_params: Any,
) -> str:
    """
    Generate Hugo-compliant YAML frontmatter.

    Args:
        title: Article title (required by Hugo convention)
        date: Publication date (required by Hugo convention, defaults to now)
        draft: Whether article is a draft (default: False)
        description: Meta description for SEO
        keywords: List of keywords/tags
        **custom_params: Any custom parameters (will be placed under 'params' key)

    Returns:
        Complete YAML frontmatter block with --- delimiters

    Example:
        >>> frontmatter = generate_hugo_frontmatter(
        ...     title="My Article",
        ...     date=datetime(2025, 10, 13, tzinfo=timezone.utc),
        ...     draft=False,
        ...     description="An interesting article",
        ...     keywords=["python", "hugo"],
        ...     author="John Doe",  # Custom param
        ...     source="example.com",  # Custom param
        ... )
    """
    # Build frontmatter dict with Hugo reserved fields
    frontmatter: Dict[str, Any] = {}

    # Required fields (by convention)
    frontmatter["title"] = title
    frontmatter["date"] = _format_hugo_date(date or datetime.now(timezone.utc))

    # Optional Hugo standard fields
    frontmatter["draft"] = draft

    if description:
        frontmatter["description"] = description

    if keywords:
        # Hugo expects arrays of strings for taxonomy fields
        frontmatter["keywords"] = keywords

    # All custom parameters must go under 'params' key
    if custom_params:
        frontmatter["params"] = custom_params

    # Generate YAML with safe dumping
    yaml_content = yaml.safe_dump(
        frontmatter,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,  # Preserve order
    )

    # Return with Hugo YAML delimiters
    return f"---\n{yaml_content}---"


def _format_hugo_date(dt: datetime) -> str:
    """
    Format datetime for Hugo in RFC3339 format.

    Hugo prefers RFC3339 format with timezone offset.

    Args:
        dt: Datetime to format

    Returns:
        RFC3339 formatted string (e.g., "2025-10-13T08:00:00Z")
    """
    if dt.tzinfo is None:
        # Assume UTC if no timezone
        dt = dt.replace(tzinfo=timezone.utc)

    # Format as RFC3339
    return dt.isoformat()


def validate_frontmatter_fields(frontmatter_dict: Dict[str, Any]) -> list[str]:
    """
    Validate frontmatter dictionary against Hugo requirements.

    Args:
        frontmatter_dict: Parsed frontmatter dictionary

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Check required fields
    if "title" not in frontmatter_dict:
        errors.append("Missing required field: title")

    if "date" not in frontmatter_dict:
        errors.append("Missing required field: date")

    # Validate types
    if "title" in frontmatter_dict and not isinstance(frontmatter_dict["title"], str):
        errors.append(
            f"Field 'title' must be string, got {type(frontmatter_dict['title'])}"
        )

    if "date" in frontmatter_dict:
        if not isinstance(frontmatter_dict["date"], str):
            errors.append(
                f"Field 'date' must be string (ISO8601), got {type(frontmatter_dict['date'])}"
            )
        else:
            # Validate date is parseable
            try:
                datetime.fromisoformat(frontmatter_dict["date"].replace("Z", "+00:00"))
            except ValueError as e:
                errors.append(f"Field 'date' must be valid ISO8601 format: {e}")

    if "draft" in frontmatter_dict and not isinstance(frontmatter_dict["draft"], bool):
        errors.append(
            f"Field 'draft' must be boolean, got {type(frontmatter_dict['draft'])}"
        )

    if "keywords" in frontmatter_dict:
        if not isinstance(frontmatter_dict["keywords"], list):
            errors.append("Field 'keywords' must be array/list")
        elif not all(isinstance(k, str) for k in frontmatter_dict["keywords"]):
            errors.append("Field 'keywords' must be array of strings")

    # Hugo reserved fields that shouldn't be used as custom fields
    HUGO_RESERVED = {
        "aliases",
        "build",
        "cascade",
        "date",
        "description",
        "draft",
        "expiryDate",
        "headless",
        "isCJKLanguage",
        "keywords",
        "lastmod",
        "layout",
        "linkTitle",
        "markup",
        "menus",
        "outputs",
        "params",
        "publishDate",
        "resources",
        "sitemap",
        "slug",
        "summary",
        "title",
        "translationKey",
        "type",
        "url",
        "weight",
        "tags",
        "categories",
    }

    # Check for custom fields not under params
    for field in frontmatter_dict.keys():
        if field not in HUGO_RESERVED and field != "params":
            errors.append(f"Custom field '{field}' should be under 'params' key")

    return errors


def prepare_frontmatter(
    title: str,
    source: str,
    original_url: str,
    generated_at: str,
    format: str = "hugo",
    author: Optional[str] = None,
    published_date: Optional[datetime] = None,
    category: Optional[str] = None,
    tags: Optional[list[str]] = None,
    **additional_params: Any,
) -> str:
    """
    Prepare frontmatter in specified format (extensible for future formats).

    This function acts as an adapter between article metadata and format-specific
    frontmatter generators. Currently supports Hugo format, with extensibility
    for future formats like Jekyll, Pelican, etc.

    Args:
        title: Article title
        source: Content source (rss, mastodon, reddit, etc.)
        original_url: Original article URL
        generated_at: ISO8601 timestamp of content generation
        format: Frontmatter format ('hugo' currently, extendable to 'jekyll', etc.)
        author: Article author (optional)
        published_date: Original publication date (optional)
        category: Content category (optional)
        tags: List of content tags (optional)
        **additional_params: Any additional custom parameters

    Returns:
        Formatted frontmatter string with delimiters

    Raises:
        ValueError: If unsupported format specified

    Example:
        >>> frontmatter = prepare_frontmatter(
        ...     title="My Article",
        ...     source="rss",
        ...     original_url="https://example.com/article",
        ...     generated_at="2025-10-13T08:00:00Z",
        ...     format="hugo",
        ...     author="John Doe",
        ...     tags=["tech", "ai"]
        ... )
    """
    if format == "hugo":
        return _prepare_hugo_frontmatter(
            title=title,
            source=source,
            original_url=original_url,
            generated_at=generated_at,
            author=author,
            published_date=published_date,
            category=category,
            tags=tags,
            **additional_params,
        )
    else:
        raise ValueError(
            f"Unsupported frontmatter format: {format}. " f"Supported formats: 'hugo'"
        )


def _prepare_hugo_frontmatter(
    title: str,
    source: str,
    original_url: str,
    generated_at: str,
    author: Optional[str] = None,
    published_date: Optional[datetime] = None,
    category: Optional[str] = None,
    tags: Optional[list[str]] = None,
    **additional_params: Any,
) -> str:
    """
    Prepare Hugo-compliant frontmatter with custom fields under params.

    Internal function that converts article metadata into Hugo format.
    All custom fields (source, url, author, etc.) are placed under the
    'params' key as per Hugo specification.

    Args:
        title: Article title
        source: Content source
        original_url: Original article URL
        generated_at: ISO8601 generation timestamp
        author: Article author
        published_date: Original publication date
        category: Content category
        tags: List of tags
        **additional_params: Additional custom parameters

    Returns:
        Hugo-compliant YAML frontmatter string
    """
    # Parse generated_at into datetime for Hugo date field
    try:
        date = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        date = datetime.now(timezone.utc)

    # Build custom params dict with all custom fields
    custom_params = {
        "source": source,
        "original_url": original_url,
        "generated_at": generated_at,
    }

    if author:
        custom_params["author"] = author

    if published_date:
        custom_params["published_date"] = published_date.isoformat()

    if category:
        custom_params["category"] = category

    # Add any additional custom parameters
    custom_params.update(additional_params)

    # Use generate_hugo_frontmatter with custom params
    return generate_hugo_frontmatter(
        title=title,
        date=date,
        draft=False,  # Published articles are not drafts
        description=None,  # Can be added later if needed
        keywords=tags or [],
        **custom_params,
    )
