"""
RSS Feed Generation Functions

Pure functions for generating RSS XML feeds from article data.
Extracted from html_feed_generation.py for better maintainability.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List
from urllib.parse import urljoin

from text_processing import clean_title
from url_utils import get_article_url

from libs import SecureErrorHandler

logger = logging.getLogger(__name__)
error_handler = SecureErrorHandler("rss-generation")


def generate_rss_feed(
    articles: List[Dict[str, Any]], config: Dict[str, Any], max_items: int = 20
) -> str:
    """
    Generate RSS feed XML for articles.

    Pure function that creates RSS XML from articles list and configuration.

    Args:
        articles: List of article dictionaries
        config: Site configuration dictionary
        max_items: Maximum number of items to include in feed

    Returns:
        Complete RSS XML string

    Raises:
        ValueError: If articles data is invalid
    """
    try:
        # Validate articles
        if not isinstance(articles, list):
            raise ValueError("Articles must be a list")

        # Limit articles for RSS
        rss_articles = articles[:max_items]

        # Get current timestamp for feed
        now = datetime.now(timezone.utc)
        build_date = now.strftime("%a, %d %b %Y %H:%M:%S GMT")

        # Site information
        site_title = config.get("SITE_TITLE", "JabLab Tech News")
        site_description = config.get("SITE_DESCRIPTION", "AI-curated technology news")
        site_url = config.get("SITE_URL", "https://jablab.com")

        # Generate RSS items
        rss_items = []
        for article in rss_articles:
            rss_item = _generate_rss_item(article, config, site_url, build_date)
            if rss_item:
                rss_items.append(rss_item)

        # Complete RSS XML
        rss_xml = _build_rss_xml(
            site_title, site_url, site_description, build_date, rss_items, config
        )

        logger.debug(f"Generated RSS feed with {len(rss_items)} items")
        return rss_xml

    except (ValueError, TypeError, KeyError) as e:
        error_response = error_handler.handle_error(
            e,
            "validation",
            context={"article_count": len(articles), "max_items": max_items},
        )
        logger.error(f"RSS feed generation failed: {error_response['message']}")
        raise ValueError(error_response["message"]) from e
    except Exception as e:
        error_response = error_handler.handle_error(
            e,
            "general",
            context={"article_count": len(articles), "max_items": max_items},
        )
        logger.error(
            f"Unexpected RSS feed generation error: {error_response['message']}"
        )
        raise RuntimeError(error_response["message"]) from e


def _generate_rss_item(
    article: Dict[str, Any], config: Dict[str, Any], site_url: str, build_date: str
) -> str:
    """Generate a single RSS item XML."""
    # Validate article data
    if not all(article.get(field) for field in ["title", "url", "published_date"]):
        logger.warning(
            f"Skipping article with missing required fields: {article.get('title', 'Unknown')}"
        )
        return ""

    # Format publication date
    pub_date_str = _format_publication_date(article["published_date"], build_date)

    # Create RSS item
    # Use centralized URL helper for consistency
    item_url = get_article_url(article["url"], base_url=site_url)
    description = _extract_description(article)

    # Clean title for RSS feed
    clean_article_title = clean_title(article["title"])

    return f"""
    <item>
      <title><![CDATA[{clean_article_title}]]></title>
      <link>{item_url}</link>
      <guid>{item_url}</guid>
      <description><![CDATA[{description}]]></description>
      <pubDate>{pub_date_str}</pubDate>
      <author>noreply@{config.get('SITE_DOMAIN', 'jablab.com')} (AI Content Team)</author>
    </item>"""


def _format_publication_date(published_date: Any, fallback_date: str) -> str:
    """Format publication date for RSS."""
    try:
        if isinstance(published_date, str):
            pub_date = datetime.fromisoformat(published_date.replace("Z", "+00:00"))
        else:
            pub_date = published_date

        return pub_date.strftime("%a, %d %b %Y %H:%M:%S GMT")
    except (ValueError, TypeError):
        logger.warning("Invalid published_date, using current time")
        return fallback_date


def _extract_description(article: Dict[str, Any]) -> str:
    """Extract or generate description for RSS item."""
    description = article.get("description", "")
    if not description and article.get("content"):
        # Extract first paragraph as description
        content = article["content"]
        sentences = re.split(r"[.!?]+", content.strip())
        description = (
            sentences[0][:300] + "..."
            if sentences and len(sentences[0]) > 300
            else sentences[0] if sentences else ""
        )
    return description


def _build_rss_xml(
    title: str,
    url: str,
    description: str,
    build_date: str,
    items: List[str],
    config: Dict[str, Any],
) -> str:
    """Build complete RSS XML document."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title><![CDATA[{title}]]></title>
    <link>{url}</link>
    <description><![CDATA[{description}]]></description>
    <language>en-us</language>
    <lastBuildDate>{build_date}</lastBuildDate>
    <ttl>60</ttl>
    <atom:link href="{urljoin(url, '/feed.xml')}" rel="self" type="application/rss+xml" />
    {"".join(items)}
  </channel>
</rss>"""
