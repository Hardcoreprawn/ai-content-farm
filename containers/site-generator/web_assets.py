"""
Web Assets Generation Functions

Pure functions for generating web assets like robots.txt, manifest.json, and CSS.
Extracted from html_feed_generation.py for better maintainability.
"""

import json
import logging
from typing import Any, Dict
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


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
    """
    try:
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
        css_content = """/* Enhanced Site Styles */
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
}"""

        logger.debug("Generated enhanced CSS styles")
        return css_content.strip()

    except Exception as e:
        logger.error(f"CSS generation failed: {e}")
        raise ValueError(f"Failed to generate CSS: {e}")
