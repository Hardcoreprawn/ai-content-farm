"""
Markdown generation functions using Jinja2 templates.

This module contains functions for generating markdown content from article
data using Jinja2 templates.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from jinja2 import Environment, FileSystemLoader
from jinja2.exceptions import TemplateNotFound
from markdown_generation import prepare_frontmatter
from models import ArticleMetadata

logger = logging.getLogger(__name__)

__all__ = [
    "create_jinja_environment",
    "generate_markdown_content",
    "generate_markdown_blob_name",
]


def create_jinja_environment(template_dir: Optional[Path] = None) -> Environment:
    """
    Create configured Jinja2 environment.

    Mostly pure function (filesystem access for template loading).

    Args:
        template_dir: Template directory path (uses default if None)

    Returns:
        Configured Jinja2 Environment

    Examples:
        >>> env = create_jinja_environment()
        >>> env.trim_blocks
        True
    """
    if template_dir is None:
        template_dir = Path(__file__).parent / "templates"

    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    logger.info(f"Initialized Jinja2 templates from: {template_dir}")
    return env


def generate_markdown_content(
    article_data: Dict[str, Any],
    metadata: ArticleMetadata,
    jinja_env: Environment,
    template_name: str = "default.md.j2",
) -> str:
    """
    Generate markdown content with frontmatter using Jinja2 templates.

    Mostly pure function (template rendering with some I/O for loading).

    Args:
        article_data: Complete article data
        metadata: Extracted metadata
        jinja_env: Configured Jinja2 environment
        template_name: Name of template file (default: default.md.j2)

    Returns:
        Complete markdown document as string

    Raises:
        ValueError: If template not found

    Examples:
        >>> # See integration tests
        >>> pass
    """
    try:
        template = jinja_env.get_template(template_name)
    except TemplateNotFound:
        logger.error(f"Template not found: {template_name}")
        raise ValueError(f"Template not found: {template_name}")

    # Generate Hugo-compliant frontmatter
    from datetime import UTC, datetime

    # Extract the actual source URL from article_data (the social media post URL)
    # metadata.url contains the local article URL, but we want original_url from JSON
    source_url = article_data.get("original_url", metadata.url)

    frontmatter = prepare_frontmatter(
        title=metadata.title,
        source=metadata.source,
        original_url=metadata.url,
        generated_at=article_data.get(
            "generated_at", f"{datetime.now(UTC).isoformat()}Z"
        ),
        format="hugo",
        author=metadata.author,
        published_date=metadata.published_date,
        category=metadata.category,
        tags=metadata.tags,
        hero_image=metadata.hero_image,
        thumbnail=metadata.thumbnail,
        image_alt=metadata.image_alt,
        image_credit=metadata.image_credit,
        image_color=metadata.image_color,
        # Add source attribution fields
        source_url=source_url,  # The actual social media post URL
        source_platform=metadata.source,  # mastodon, reddit, rss, etc.
    )

    # Render template with data and pre-generated frontmatter
    markdown_content = template.render(
        frontmatter=frontmatter,
        metadata=metadata,
        article_data=article_data,
    )

    return markdown_content


def generate_markdown_blob_name(json_blob_name: str) -> str:
    """
    Generate markdown blob name from JSON blob name.

    Pure function - simple string transformation.

    Args:
        json_blob_name: Original JSON blob name

    Returns:
        Markdown blob name (.json -> .md)

    Examples:
        >>> generate_markdown_blob_name("article-123.json")
        'article-123.md'
        >>> generate_markdown_blob_name("folder/article.json")
        'folder/article.md'
    """
    return json_blob_name.replace(".json", ".md")
