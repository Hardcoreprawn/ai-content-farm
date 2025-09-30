"""
Functional feed and XML generation for site generator.

Provides pure functions for generating RSS feeds, sitemaps, and other
XML-based content for static site generation.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List
from urllib.parse import urljoin

from libs import SecureErrorHandler

logger = logging.getLogger(__name__)
error_handler = SecureErrorHandler("html-feed-generation")


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

        # Start RSS XML
        rss_items = []

        for article in rss_articles:
            # Validate article data
            if not all(
                article.get(field) for field in ["title", "url", "published_date"]
            ):
                logger.warning(
                    f"Skipping article with missing required fields: {article.get('title', 'Unknown')}"
                )
                continue

            # Format publication date
            try:
                if isinstance(article["published_date"], str):
                    pub_date = datetime.fromisoformat(
                        article["published_date"].replace("Z", "+00:00")
                    )
                else:
                    pub_date = article["published_date"]

                pub_date_str = pub_date.strftime("%a, %d %b %Y %H:%M:%S GMT")
            except (ValueError, TypeError):
                pub_date_str = build_date
                logger.warning(
                    f"Invalid published_date for article {article['title']}, using current time"
                )

            # Create RSS item
            item_url = urljoin(site_url, f"/articles/{article['url']}/")
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

            rss_item = f"""
    <item>
      <title><![CDATA[{article['title']}]]></title>
      <link>{item_url}</link>
      <guid>{item_url}</guid>
      <description><![CDATA[{description}]]></description>
      <pubDate>{pub_date_str}</pubDate>
      <author>noreply@{config.get('SITE_DOMAIN', 'jablab.com')} (AI Content Team)</author>
    </item>"""

            rss_items.append(rss_item)

        # Complete RSS XML
        rss_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title><![CDATA[{site_title}]]></title>
    <link>{site_url}</link>
    <description><![CDATA[{site_description}]]></description>
    <language>en-us</language>
    <lastBuildDate>{build_date}</lastBuildDate>
    <ttl>60</ttl>
    <atom:link href="{urljoin(site_url, '/feed.xml')}" rel="self" type="application/rss+xml" />
    {"".join(rss_items)}
  </channel>
</rss>"""

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

        # Start with static pages
        urls = [
            f"""  <url>
    <loc>{site_url}/</loc>
    <lastmod>{now}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>"""
        ]

        # Add article URLs
        for article in articles:
            if not article.get("url"):
                continue

            try:
                # Format last modified date
                if article.get("published_date"):
                    if isinstance(article["published_date"], str):
                        pub_date = datetime.fromisoformat(
                            article["published_date"].replace("Z", "+00:00")
                        )
                    else:
                        pub_date = article["published_date"]
                    lastmod = pub_date.strftime("%Y-%m-%d")
                else:
                    lastmod = now
            except (ValueError, TypeError):
                lastmod = now

            article_url = urljoin(site_url, f"/articles/{article['url']}/")
            url_entry = f"""  <url>
    <loc>{article_url}</loc>
    <lastmod>{lastmod}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>"""

            urls.append(url_entry)

        # Complete sitemap XML
        sitemap_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{"".join(urls)}
</urlset>"""

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


def generate_robots_txt(config: Dict[str, Any]) -> str:
    """
    Generate robots.txt file for search engine optimization.

    Creates a robots.txt file that allows all search engines to crawl the site
    while providing sitemap location and setting a polite crawl delay.

    Args:
        config: Site configuration dictionary with SITE_URL

    Returns:
        Complete robots.txt content string

    Raises:
        ValueError: If robots.txt generation fails

    Examples:
        >>> config = {"SITE_URL": "https://example.com"}
        >>> robots = generate_robots_txt(config)
        >>> "User-agent: *" in robots
        True
        >>> "Allow: /" in robots
        True
        >>> "Sitemap: https://example.com/sitemap.xml" in robots
        True

        >>> # With default config
        >>> robots = generate_robots_txt({})
        >>> "jablab.com" in robots
        True
    """
    try:
        site_url = config.get("SITE_URL", "https://jablab.com")

        robots_content = f"""User-agent: *
Allow: /

# Sitemaps
Sitemap: {urljoin(site_url, '/sitemap.xml')}

# Crawl-delay for good citizenship
Crawl-delay: 1
"""

        logger.debug("Generated robots.txt")
        return robots_content

    except Exception as e:
        logger.error(f"Robots.txt generation failed: {e}")
        raise ValueError(f"Failed to generate robots.txt: {e}")


def generate_manifest_json(config: Dict[str, Any]) -> str:
    """
    Generate web app manifest JSON for PWA support.

    Creates a Progressive Web App manifest file with site metadata,
    icons, and display settings for mobile and desktop installation.

    Args:
        config: Site configuration dictionary with SITE_TITLE, SITE_DESCRIPTION

    Returns:
        Complete manifest JSON string

    Raises:
        ValueError: If manifest generation fails

    Examples:
        >>> config = {
        ...     "SITE_TITLE": "My Tech News",
        ...     "SITE_DESCRIPTION": "Latest tech updates"
        ... }
        >>> manifest = generate_manifest_json(config)
        >>> import json
        >>> data = json.loads(manifest)
        >>> data["name"]
        'My Tech News'
        >>> data["display"]
        'standalone'

        >>> # Handles short_name truncation
        >>> long_config = {"SITE_TITLE": "Very Long Site Title Name"}
        >>> manifest = generate_manifest_json(long_config)
        >>> data = json.loads(manifest)
        >>> len(data["short_name"]) <= 12
        True
    """
    try:
        import json

        manifest_data = {
            "name": config.get("SITE_TITLE", "JabLab Tech News"),
            "short_name": config.get("SITE_TITLE", "JabLab")[:12],
            "description": config.get("SITE_DESCRIPTION", "AI-curated technology news"),
            "start_url": "/",
            "display": "standalone",
            "background_color": "#ffffff",
            "theme_color": "#333333",
            "icons": [
                {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"},
                {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"},
            ],
        }

        manifest_json = json.dumps(manifest_data, indent=2)

        logger.debug("Generated web app manifest")
        return manifest_json

    except Exception as e:
        logger.error(f"Manifest generation failed: {e}")
        raise ValueError(f"Failed to generate manifest: {e}")


def generate_css_styles(config: Dict[str, Any]) -> str:
    """
    Generate enhanced CSS styles for the site.

    Args:
        config: Site configuration dictionary

    Returns:
        Complete CSS stylesheet content
    """
    try:
        css_content = """
/* Enhanced Site Styles */
:root {
    --primary-color: #333;
    --secondary-color: #666;
    --accent-color: #0066cc;
    --background-color: #ffffff;
    --text-color: #333;
    --border-color: #eee;
    --hover-color: #f5f5f5;
}

* {
    box-sizing: border-box;
}

body {
    font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    line-height: 1.6;
    margin: 0;
    padding: 20px;
    max-width: 800px;
    margin: 0 auto;
    color: var(--text-color);
    background-color: var(--background-color);
}

.header {
    border-bottom: 2px solid var(--border-color);
    padding-bottom: 20px;
    margin-bottom: 30px;
}

.site-title {
    font-size: 1.8em;
    margin: 0;
    color: var(--primary-color);
    text-decoration: none;
    font-weight: 700;
}

.site-title:hover {
    color: var(--accent-color);
}

.site-description {
    color: var(--secondary-color);
    margin-top: 5px;
    font-size: 1.1em;
}

.article-preview {
    margin-bottom: 30px;
    padding-bottom: 20px;
    border-bottom: 1px solid var(--border-color);
    transition: all 0.2s ease;
}

.article-preview:hover {
    background-color: var(--hover-color);
    padding: 15px;
    border-radius: 5px;
    margin: -15px -15px 15px -15px;
}

.article-preview h2 {
    margin: 0 0 10px 0;
    font-size: 1.4em;
}

.article-preview h2 a {
    color: var(--primary-color);
    text-decoration: none;
}

.article-preview h2 a:hover {
    color: var(--accent-color);
}

.article-meta {
    color: var(--secondary-color);
    font-size: 0.9em;
    margin-bottom: 10px;
}

.article-description {
    color: var(--text-color);
}

.article-content {
    margin-bottom: 30px;
    line-height: 1.7;
}

.article-content h1, .article-content h2, .article-content h3 {
    color: var(--primary-color);
    margin-top: 30px;
    margin-bottom: 15px;
}

.article-content p {
    margin-bottom: 15px;
}

.tags {
    margin: 20px 0;
}

.tag {
    background: var(--border-color);
    padding: 4px 8px;
    margin-right: 8px;
    border-radius: 3px;
    font-size: 0.8em;
    color: var(--secondary-color);
    display: inline-block;
    margin-bottom: 5px;
}

.pagination {
    text-align: center;
    margin: 40px 0;
    padding: 20px 0;
}

.pagination a {
    color: var(--accent-color);
    text-decoration: none;
    margin: 0 20px;
    padding: 8px 16px;
    border: 1px solid var(--border-color);
    border-radius: 4px;
    transition: all 0.2s ease;
}

.pagination a:hover {
    background-color: var(--accent-color);
    color: white;
}

.page-info {
    color: var(--secondary-color);
    margin: 0 20px;
}

.footer {
    border-top: 2px solid var(--border-color);
    padding-top: 20px;
    margin-top: 40px;
    color: var(--secondary-color);
    font-size: 0.9em;
    text-align: center;
}

.footer a {
    color: var(--accent-color);
    text-decoration: none;
}

.footer a:hover {
    text-decoration: underline;
}

/* Responsive design */
@media (max-width: 600px) {
    body {
        padding: 10px;
    }

    .site-title {
        font-size: 1.5em;
    }

    .article-preview h2 {
        font-size: 1.2em;
    }

    .pagination a {
        margin: 0 5px;
        padding: 6px 12px;
    }
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
    :root {
        --primary-color: #ffffff;
        --secondary-color: #cccccc;
        --accent-color: #66aaff;
        --background-color: #1a1a1a;
        --text-color: #ffffff;
        --border-color: #333333;
        --hover-color: #2a2a2a;
    }
}
"""

        logger.debug("Generated enhanced CSS styles")
        return css_content.strip()

    except Exception as e:
        logger.error(f"CSS generation failed: {e}")
        raise ValueError(f"Failed to generate CSS: {e}")
