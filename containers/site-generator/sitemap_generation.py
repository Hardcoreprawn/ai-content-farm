"""
Sitemap XML Generation Functions

Pure functions for generating sitemap XML from article data and static pages.
Extracted from html_feed_generation.py for better maintainability.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from url_utils import get_article_url

from libs import SecureErrorHandler

logger = logging.getLogger(__name__)
error_handler = SecureErrorHandler("sitemap-generation")


def generate_sitemap_xml(articles: List[Dict[str, Any]], config: Dict[str, Any]) -> str:
    """
    Generate sitemap XML for articles and static pages.

    Pure function that creates sitemap XML from articles and configuration.

    Args:
        articles: List of article dictionaries
        config: Site configuration dictionary

    Returns:
        Complete sitemap XML string
    """
    try:
        site_url = config.get("SITE_URL", "https://jablab.com")
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Generate all URLs
        urls = []
        urls.extend(_generate_static_page_urls(site_url, now))
        urls.extend(_generate_article_urls(articles, site_url, now))

        # Complete sitemap XML
        sitemap_xml = _build_sitemap_xml(urls)

        logger.debug(f"Generated sitemap with {len(urls)} URLs")
        return sitemap_xml

    except (ValueError, TypeError, KeyError) as e:
        error_response = error_handler.handle_error(
            e, "validation", context={"article_count": len(articles)}
        )
        logger.error(f"Sitemap generation failed: {error_response['message']}")
        raise ValueError(error_response["message"]) from e
    except Exception as e:
        error_response = error_handler.handle_error(
            e, "general", context={"article_count": len(articles)}
        )
        logger.error(
            f"Unexpected sitemap generation error: {error_response['message']}"
        )
        raise RuntimeError(error_response["message"]) from e


def _generate_static_page_urls(site_url: str, current_date: str) -> List[str]:
    """Generate URL entries for static pages."""
    return [
        f"""  <url>
    <loc>{site_url}/</loc>
    <lastmod>{current_date}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>"""
    ]


def _generate_article_urls(
    articles: List[Dict[str, Any]], site_url: str, fallback_date: str
) -> List[str]:
    """Generate URL entries for articles."""
    urls = []

    for article in articles:
        if not article.get("url"):
            continue

        lastmod = _format_article_date(article.get("published_date"), fallback_date)
        # Use centralized URL helper for consistency
        article_url = get_article_url(article["url"], base_url=site_url)

        url_entry = f"""  <url>
    <loc>{article_url}</loc>
    <lastmod>{lastmod}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>"""

        urls.append(url_entry)

    return urls


def _format_article_date(published_date: Any, fallback_date: str) -> str:
    """Format article publication date for sitemap."""
    try:
        if published_date:
            if isinstance(published_date, str):
                pub_date = datetime.fromisoformat(published_date.replace("Z", "+00:00"))
            else:
                pub_date = published_date
            return pub_date.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        pass

    return fallback_date


def _build_sitemap_xml(urls: List[str]) -> str:
    """Build complete sitemap XML document."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{"".join(urls)}
</urlset>"""
