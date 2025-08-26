"""
Template engine contracts for site-generator testing.
Based on Jinja2 template rendering patterns.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class TemplateContract:
    """Contract for template structure."""

    name: str
    content: str
    variables: Dict[str, Any]

    @classmethod
    def create_mock(
        cls, template_type: str = "index", **overrides
    ) -> "TemplateContract":
        """Create realistic template for testing."""
        templates = {
            "index": {
                "name": "index.html",
                "content": """
<!DOCTYPE html>
<html>
<head>
    <title>{{ site_title }}</title>
    <meta name="description" content="{{ site_description }}">
</head>
<body>
    <h1>{{ site_title }}</h1>
    {% for article in articles %}
    <article>
        <h2>{{ article.title }}</h2>
        <p>{{ article.summary }}</p>
        <span>Score: {{ article.score }}</span>
    </article>
    {% endfor %}
</body>
</html>
                """.strip(),
                "variables": {
                    "site_title": "AI Content Farm",
                    "site_description": "Curated technology news",
                    "articles": [],
                },
            },
            "rss": {
                "name": "feed.xml",
                "content": """
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
    <title>{{ site_title }}</title>
    <description>{{ site_description }}</description>
    {% for article in articles %}
    <item>
        <title>{{ article.title }}</title>
        <description>{{ article.summary }}</description>
        <link>{{ article.url }}</link>
    </item>
    {% endfor %}
</channel>
</rss>
                """.strip(),
                "variables": {
                    "site_title": "AI Content Farm",
                    "site_description": "Curated technology news",
                    "articles": [],
                },
            },
        }

        template_data = templates.get(template_type, templates["index"])
        defaults = {
            "name": template_data["name"],
            "content": template_data["content"],
            "variables": template_data["variables"],
        }
        defaults.update(overrides)
        return cls(**defaults)


@dataclass
class StaticAssetContract:
    """Contract for static assets (CSS, JS)."""

    filename: str
    content: str
    content_type: str

    @classmethod
    def create_mock(cls, asset_type: str = "css", **overrides) -> "StaticAssetContract":
        """Create realistic static asset for testing."""
        assets = {
            "css": {
                "filename": "style.css",
                "content": """
body {
    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
    line-height: 1.6;
    color: #333;
    max-width: 800px;
    margin: 0 auto;
    padding: 20px;
}

article {
    margin-bottom: 2rem;
    padding: 1rem;
    border-left: 3px solid #007acc;
}

h1, h2 {
    color: #2c3e50;
}
                """.strip(),
                "content_type": "text/css",
            },
            "js": {
                "filename": "script.js",
                "content": """
// Simple article interactions
document.addEventListener('DOMContentLoaded', function() {
    console.log('AI Content Farm loaded');

    // Add click tracking for articles
    const articles = document.querySelectorAll('article');
    articles.forEach(article => {
        article.addEventListener('click', function() {
            console.log('Article clicked:', article.querySelector('h2').textContent);
        });
    });
});
                """.strip(),
                "content_type": "application/javascript",
            },
        }

        asset_data = assets.get(asset_type, assets["css"])
        defaults = {
            "filename": asset_data["filename"],
            "content": asset_data["content"],
            "content_type": asset_data["content_type"],
        }
        defaults.update(overrides)
        return cls(**defaults)
