"""
Functional HTML page generation for site generator.

Provides pure functions for generating HTML pages and content
that replace the mutable MarkdownService and SiteService classes.
"""

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from article_processing import calculate_last_updated
from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape
from text_processing import clean_title, register_jinja_filters

from libs import SecureErrorHandler

logger = logging.getLogger(__name__)
error_handler = SecureErrorHandler("html-page-generation")

# Initialize Jinja2 environment
_jinja_env = None


def get_jinja_environment(theme: str = "minimal") -> Environment:
    """
    Get or create Jinja2 environment for template rendering.

    Registers custom filters for markdown conversion and text processing.

    Args:
        theme: Theme name to use for template loading

    Returns:
        Configured Jinja2 Environment instance with custom filters
    """
    global _jinja_env

    if _jinja_env is None:
        templates_dir = Path(__file__).parent / "templates"

        if not templates_dir.exists():
            logger.error(f"Templates directory not found: {templates_dir}")
            raise FileNotFoundError(f"Templates directory not found: {templates_dir}")

        _jinja_env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Register custom filters for markdown and text processing
        _jinja_env = register_jinja_filters(_jinja_env)

        logger.info(
            f"Initialized Jinja2 environment with templates from: {templates_dir}"
        )

    return _jinja_env


def generate_article_page(
    article: Dict[str, Any],
    config: Dict[str, Any],
    template_data: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Generate HTML for a single article page.

    Pure function that creates article HTML from article data and configuration.

    Args:
        article: Article data dictionary with content, metadata
        config: Site configuration dictionary
        template_data: Optional template data for customization

    Returns:
        Complete HTML string for article page

    Raises:
        ValueError: If article data is invalid or incomplete
    """
    try:
        # Validate required article fields
        required_fields = ["title", "content", "url", "published_date"]
        missing_fields = [field for field in required_fields if not article.get(field)]
        if missing_fields:
            raise ValueError(f"Missing required article fields: {missing_fields}")

        # Extract and clean article data
        title = clean_title(article["title"])  # Remove URLs and artifacts
        content = article["content"]
        url = article["url"]
        published_date = article["published_date"]
        author = article.get("author", "AI Content Team")
        description = article.get("description", "")
        tags = article.get("tags", [])

        # Generate meta description
        if not description and content:
            # Extract first sentence as description
            sentences = re.split(r"[.!?]+", content.strip())
            description = (
                sentences[0][:160] + "..."
                if sentences and len(sentences[0]) > 160
                else sentences[0] if sentences else ""
            )

        # Create template context
        template_context = {
            "article": {
                "title": title,
                "content": content,
                "url": url,
                "published_date": published_date,
                "author": author,
                "description": description,
                "tags": tags,
                # Source attribution fields
                "original_url": article.get("original_url"),
                "source_platform": article.get("source_platform")
                or article.get("source"),
                "source_author": article.get("author"),  # Original author
                "original_date": article.get("original_date")
                or article.get("created_at"),
            },
            "site": {
                "title": config.get("SITE_TITLE", "JabLab Tech News"),
                "description": config.get(
                    "SITE_DESCRIPTION", "AI-curated technology news"
                ),
                "url": config.get("SITE_URL", "https://jablab.com"),
                "domain": config.get("SITE_DOMAIN", "jablab.com"),
            },
            "page": {
                "title": f"{title} | {config.get('SITE_TITLE', 'JabLab')}",
                "description": description,
                "url": urljoin(config.get("SITE_URL", ""), f"/articles/{url}/"),
                "type": "article",
            },
        }

        # Merge custom template data
        if template_data:
            template_context.update(template_data)

        # Generate HTML using template
        html_content = render_article_template(template_context)

        logger.debug(f"Generated article page for: {title}")
        return html_content

    except (ValueError, TypeError, KeyError) as e:
        error_response = error_handler.handle_error(
            e, "validation", context={"article_title": article.get("title", "unknown")}
        )
        logger.error(f"Article page generation failed: {error_response['message']}")
        raise ValueError(error_response["message"]) from e
    except Exception as e:
        error_response = error_handler.handle_error(
            e, "general", context={"article_title": article.get("title", "unknown")}
        )
        logger.error(
            f"Unexpected article page generation error: {error_response['message']}"
        )
        raise RuntimeError(error_response["message"]) from e


def generate_index_page(
    articles: List[Dict[str, Any]],
    config: Dict[str, Any],
    page_number: int = 1,
    template_data: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Generate HTML for site index page with article listings.

    Pure function that creates index HTML from articles list and configuration.

    Args:
        articles: List of article dictionaries
        config: Site configuration dictionary
        page_number: Page number for pagination (1-based)
        template_data: Optional template data for customization

    Returns:
        Complete HTML string for index page

    Raises:
        ValueError: If articles data is invalid
    """
    try:
        # Validate articles
        if not isinstance(articles, list):
            raise ValueError("Articles must be a list")

        # Calculate pagination
        articles_per_page = config.get("ARTICLES_PER_PAGE", 10)
        start_idx = (page_number - 1) * articles_per_page
        end_idx = start_idx + articles_per_page
        page_articles = articles[start_idx:end_idx]

        total_pages = (len(articles) + articles_per_page - 1) // articles_per_page
        has_prev = page_number > 1
        has_next = page_number < total_pages

        # Calculate last_updated from articles using pure function
        last_updated = calculate_last_updated(articles)

        # Use current time if no article dates found
        if last_updated is None:
            last_updated = datetime.now(timezone.utc)

        # Create template context
        template_context = {
            "articles": page_articles,
            "last_updated": last_updated,
            "site": {
                "title": config.get("SITE_TITLE", "JabLab Tech News"),
                "description": config.get(
                    "SITE_DESCRIPTION", "AI-curated technology news"
                ),
                "url": config.get("SITE_URL", "https://jablab.com"),
                "domain": config.get("SITE_DOMAIN", "jablab.com"),
            },
            "page": {
                "title": config.get("SITE_TITLE", "JabLab Tech News"),
                "description": config.get(
                    "SITE_DESCRIPTION", "AI-curated technology news"
                ),
                "url": config.get("SITE_URL", "https://jablab.com"),
                "type": "website",
                "number": page_number,
            },
            "pagination": {
                "current_page": page_number,
                "total_pages": total_pages,
                "has_prev": has_prev,
                "has_next": has_next,
                "prev_page": page_number - 1 if has_prev else None,
                "next_page": page_number + 1 if has_next else None,
                "articles_per_page": articles_per_page,
                "total_articles": len(articles),
            },
        }

        # Merge custom template data
        if template_data:
            template_context.update(template_data)

        # Generate HTML using template
        html_content = render_index_template(template_context)

        logger.debug(
            f"Generated index page {page_number} with {len(page_articles)} articles"
        )
        return html_content

    except (ValueError, TypeError, KeyError) as e:
        error_response = error_handler.handle_error(
            e,
            "validation",
            context={"page_number": page_number, "article_count": len(page_articles)},
        )
        logger.error(f"Index page generation failed: {error_response['message']}")
        raise ValueError(error_response["message"]) from e
    except Exception as e:
        error_response = error_handler.handle_error(
            e,
            "general",
            context={"page_number": page_number, "article_count": len(page_articles)},
        )
        logger.error(
            f"Unexpected index page generation error: {error_response['message']}"
        )
        raise RuntimeError(error_response["message"]) from e


def render_article_template(context: Dict[str, Any], theme: str = "minimal") -> str:
    """
    Render HTML template for article page using Jinja2.

    Args:
        context: Template context with article, site, and page data
        theme: Theme name to use for template rendering

    Returns:
        Rendered HTML string

    Raises:
        TemplateNotFound: If article template doesn't exist for theme
    """
    try:
        # Get Jinja2 environment
        env = get_jinja_environment(theme)

        # Prepare template context with proper data structure
        article = context["article"]
        site = context["site"]

        # Ensure article has required date fields
        if "generated_at" in article and isinstance(article["generated_at"], str):
            article["generated_at"] = datetime.fromisoformat(
                article["generated_at"].replace("Z", "+00:00")
            )

        # Prepare context for Jinja2 template
        template_context = {
            "article": article,
            "site": site,
            "current_year": datetime.now(timezone.utc).year,
        }

        # Load and render template
        template = env.get_template(f"{theme}/article.html")
        html_content = template.render(**template_context)

        logger.debug(f"Rendered article template using theme: {theme}")
        return html_content

    except TemplateNotFound as e:
        logger.error(f"Template not found for theme '{theme}': {e}")
        # Fall back to minimal theme
        if theme != "minimal":
            logger.info("Falling back to minimal theme")
            return render_article_template(context, theme="minimal")
        raise
    except Exception as e:
        error_response = error_handler.handle_error(
            e,
            "general",
            context={
                "theme": theme,
                "article_title": context.get("article", {}).get("title", "unknown"),
            },
        )
        logger.error(f"Failed to render article template: {error_response['message']}")
        raise RuntimeError(error_response["message"]) from e


def render_index_template(context: Dict[str, Any], theme: str = "minimal") -> str:
    """
    Render HTML template for index page using Jinja2.

    Args:
        context: Template context with articles, site, page, and pagination data
        theme: Theme name to use for template rendering

    Returns:
        Rendered HTML string

    Raises:
        TemplateNotFound: If index template doesn't exist for theme
    """
    try:
        # Get Jinja2 environment
        env = get_jinja_environment(theme)

        # Prepare template context
        articles = context["articles"]
        site = context["site"]

        # Ensure articles have proper date fields
        for article in articles:
            if "generated_at" in article and isinstance(article["generated_at"], str):
                article["generated_at"] = datetime.fromisoformat(
                    article["generated_at"].replace("Z", "+00:00")
                )

        # Prepare context for Jinja2 template
        template_context = {
            "articles": articles,
            "site": site,
            "last_updated": datetime.now(timezone.utc),
            "current_year": datetime.now(timezone.utc).year,
            "pagination": context.get("pagination", {}),
        }

        # Load and render template
        template = env.get_template(f"{theme}/index.html")
        html_content = template.render(**template_context)

        logger.debug(
            f"Rendered index template with {len(articles)} articles using theme: {theme}"
        )
        return html_content

    except TemplateNotFound as e:
        logger.error(f"Template not found for theme '{theme}': {e}")
        # Fall back to minimal theme
        if theme != "minimal":
            logger.info("Falling back to minimal theme")
            return render_index_template(context, theme="minimal")
        raise
    except Exception as e:
        error_response = error_handler.handle_error(
            e,
            "general",
            context={"theme": theme, "article_count": len(context.get("articles", []))},
        )
        logger.error(f"Failed to render index template: {error_response['message']}")
        raise RuntimeError(error_response["message"]) from e
