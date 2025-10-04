"""
Functional HTML page generation for site generator.

Provides pure functions for generating HTML pages and content
that replace the mutable MarkdownService and SiteService classes.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from article_processing import calculate_last_updated

from libs import SecureErrorHandler

logger = logging.getLogger(__name__)
error_handler = SecureErrorHandler("html-page-generation")


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

        # Extract article data
        title = article["title"]
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


def render_article_template(context: Dict[str, Any]) -> str:
    """
    Render HTML template for article page.

    Args:
        context: Template context with article, site, and page data

    Returns:
        Rendered HTML string
    """
    article = context["article"]
    site = context["site"]
    page = context["page"]

    # Format published date for display
    try:
        if isinstance(article["published_date"], str):
            pub_date = datetime.fromisoformat(
                article["published_date"].replace("Z", "+00:00")
            )
        else:
            pub_date = article["published_date"]
        formatted_date = pub_date.strftime("%B %d, %Y")
    except (ValueError, TypeError):
        formatted_date = "Recently"

    # Generate tags HTML
    tags_html = ""
    if article.get("tags"):
        tag_items = [f'<span class="tag">{tag}</span>' for tag in article["tags"][:5]]
        tags_html = f'<div class="tags">{"".join(tag_items)}</div>'

    # Basic HTML template
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page['title']}</title>
    <meta name="description" content="{page['description']}">
    <link rel="canonical" href="{page['url']}">
    <link rel="alternate" type="application/rss+xml" title="{site['title']}" href="{site['url']}/feed.xml">

    <!-- Open Graph -->
    <meta property="og:title" content="{article['title']}">
    <meta property="og:description" content="{page['description']}">
    <meta property="og:url" content="{page['url']}">
    <meta property="og:type" content="article">
    <meta property="og:site_name" content="{site['title']}">

    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary">
    <meta name="twitter:title" content="{article['title']}">
    <meta name="twitter:description" content="{page['description']}">

    <style>
        body {{ font-family: system-ui, -apple-system, sans-serif; line-height: 1.6; margin: 0; padding: 20px; max-width: 800px; margin: 0 auto; }}
        .header {{ border-bottom: 1px solid #eee; padding-bottom: 20px; margin-bottom: 30px; }}
        .site-title {{ font-size: 1.8em; margin: 0; color: #333; text-decoration: none; }}
        .article-meta {{ color: #666; font-size: 0.9em; margin-bottom: 20px; }}
        .article-content {{ margin-bottom: 30px; }}
        .tags {{ margin: 20px 0; }}
        .tag {{ background: #f0f0f0; padding: 4px 8px; margin-right: 8px; border-radius: 3px; font-size: 0.8em; }}
        .footer {{ border-top: 1px solid #eee; padding-top: 20px; margin-top: 40px; color: #666; font-size: 0.9em; }}
    </style>
</head>
<body>
    <header class="header">
        <h1><a href="/" class="site-title">{site['title']}</a></h1>
    </header>

    <main>
        <article>
            <h1>{article['title']}</h1>
            <div class="article-meta">
                Published {formatted_date} by {article['author']}
            </div>
            <div class="article-content">
                {article['content']}
            </div>
            {tags_html}
        </article>
    </main>

    <footer class="footer">
        <p>&copy; 2024 {site['title']}. Powered by AI content curation.</p>
    </footer>
</body>
</html>"""

    return html


def render_index_template(context: Dict[str, Any]) -> str:
    """
    Render HTML template for index page.

    Args:
        context: Template context with articles, site, page, and pagination data

    Returns:
        Rendered HTML string
    """
    articles = context["articles"]
    site = context["site"]
    page = context["page"]
    pagination = context["pagination"]

    # Generate article previews
    article_items = []
    for article in articles:
        # Format date
        try:
            if isinstance(article["published_date"], str):
                pub_date = datetime.fromisoformat(
                    article["published_date"].replace("Z", "+00:00")
                )
            else:
                pub_date = article["published_date"]
            formatted_date = pub_date.strftime("%B %d, %Y")
        except (ValueError, TypeError):
            formatted_date = "Recently"

        # Create preview
        description = article.get("description", "")
        if not description and article.get("content"):
            content = article["content"]
            sentences = re.split(r"[.!?]+", content.strip())
            description = (
                sentences[0][:200] + "..."
                if sentences and len(sentences[0]) > 200
                else sentences[0] if sentences else ""
            )

        # Use article URL directly (already contains /articles/ prefix)
        article_url = article["url"]

        article_html = f"""
        <article class="article-preview">
            <h2><a href="{article_url}">{article['title']}</a></h2>
            <div class="article-meta">{formatted_date}</div>
            <div class="article-description">{description}</div>
        </article>"""

        article_items.append(article_html)

    # Generate pagination
    pagination_html = ""
    if pagination["total_pages"] > 1:
        prev_link = (
            f'<a href="/page/{pagination["prev_page"]}/">&larr; Previous</a>'
            if pagination["has_prev"]
            else ""
        )
        next_link = (
            f'<a href="/page/{pagination["next_page"]}/">Next &rarr;</a>'
            if pagination["has_next"]
            else ""
        )

        pagination_html = f"""
        <nav class="pagination">
            {prev_link}
            <span class="page-info">Page {pagination["current_page"]} of {pagination["total_pages"]}</span>
            {next_link}
        </nav>"""

    # Basic HTML template
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page['title']}</title>
    <meta name="description" content="{page['description']}">
    <link rel="canonical" href="{page['url']}">
    <link rel="alternate" type="application/rss+xml" title="{site['title']}" href="{site['url']}/feed.xml">

    <!-- Open Graph -->
    <meta property="og:title" content="{site['title']}">
    <meta property="og:description" content="{page['description']}">
    <meta property="og:url" content="{page['url']}">
    <meta property="og:type" content="website">

    <style>
        body {{ font-family: system-ui, -apple-system, sans-serif; line-height: 1.6; margin: 0; padding: 20px; max-width: 800px; margin: 0 auto; }}
        .header {{ border-bottom: 1px solid #eee; padding-bottom: 20px; margin-bottom: 30px; }}
        .site-title {{ font-size: 1.8em; margin: 0; color: #333; text-decoration: none; }}
        .site-description {{ color: #666; margin-top: 5px; }}
        .article-preview {{ margin-bottom: 30px; padding-bottom: 20px; border-bottom: 1px solid #f0f0f0; }}
        .article-preview h2 {{ margin: 0 0 10px 0; }}
        .article-preview h2 a {{ color: #333; text-decoration: none; }}
        .article-preview h2 a:hover {{ color: #0066cc; }}
        .article-meta {{ color: #666; font-size: 0.9em; margin-bottom: 10px; }}
        .article-description {{ color: #444; }}
        .pagination {{ text-align: center; margin: 40px 0; }}
        .pagination a {{ color: #0066cc; text-decoration: none; margin: 0 20px; }}
        .page-info {{ color: #666; }}
        .footer {{ border-top: 1px solid #eee; padding-top: 20px; margin-top: 40px; color: #666; font-size: 0.9em; text-align: center; }}
    </style>
</head>
<body>
    <header class="header">
        <h1><a href="/" class="site-title">{site['title']}</a></h1>
        <div class="site-description">{site['description']}</div>
    </header>

    <main>
        {"".join(article_items)}
        {pagination_html}
    </main>

    <footer class="footer">
        <p>&copy; 2024 {site['title']}. Powered by AI content curation.</p>
        <p><a href="/feed.xml">RSS Feed</a></p>
    </footer>
</body>
</html>"""

    return html
