"""
Static Site Generator API

FastAPI application for generating static websites from curated content.
Uses Jinja2 templates to create responsive, modern websites.
Outputs to Azure Blob Storage for proper cloud-native operation.
"""

from libs.blob_storage import BlobStorageClient, BlobContainers, get_timestamped_blob_name
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
import httpx
import asyncio
import logging
import re

# Import blob storage client
import sys
sys.path.append('/app/shared')

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Static Site Generator API",
    description="API for generating static websites from curated content",
    version="1.0.0"
)


class GenerationRequest(BaseModel):
    """Request to generate static site."""
    content_source: str = "ranked"  # ranked, enriched, or direct
    theme: str = "modern"
    include_analytics: bool = True
    deploy_preview: bool = True


class SiteConfig(BaseModel):
    """Site configuration."""
    title: str = "AI Content Farm"
    description: str = "Curated Technology News & Insights"
    domain: str = "localhost:8005"
    author: str = "AI Content Farm"
    theme: str = "modern"


# Set up templates and static files
STATIC_DIR = "/app/static"
TEMPLATES_DIR = "/app/templates"
SITE_OUTPUT_DIR = "/app/site"

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(SITE_OUTPUT_DIR, exist_ok=True)

templates = Jinja2Templates(directory=TEMPLATES_DIR)


class StaticSiteGenerator:
    """Generates static websites from content data."""

    def __init__(self, config: SiteConfig):
        self.config = config
        self.output_dir = SITE_OUTPUT_DIR

    async def fetch_content_from_ranker(self) -> List[Dict[str, Any]]:
        """Fetch ranked content from the ranker service."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://content-ranker:8000/ranking/top", timeout=30.0)
                if response.status_code == 200:
                    data = response.json()
                    return data.get('items', [])
                else:
                    logger.warning(
                        f"Ranker service returned {response.status_code}")
                    return []
        except Exception as e:
            logger.error(f"Failed to fetch from ranker: {e}")
            # Fallback to local files if available
            return await self._load_fallback_content()

    async def _load_fallback_content(self) -> List[Dict[str, Any]]:
        """Load content from local output files as fallback."""
        try:
            # Look for recent pipeline output
            output_files = list(
                Path("/app/output").glob("enriched_topics_*.json"))
            if output_files:
                latest_file = max(
                    output_files, key=lambda x: x.stat().st_mtime)
                with open(latest_file, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
                    return data.get('items', [])
        except Exception as e:
            logger.error(f"Failed to load fallback content: {e}")

        # Return sample content if nothing else available
        return self._get_sample_content()

    def _get_sample_content(self) -> List[Dict[str, Any]]:
        """Generate sample content for demonstration."""
        return [
            {
                "title": "Welcome to AI Content Farm",
                "clean_title": "Welcome to AI Content Farm",
                "ai_summary": "Your automated content curation system is ready! This is a sample article to demonstrate the static site generation.",
                "topics": ["AI", "Content", "Technology"],
                "sentiment": "positive",
                "final_score": 0.95,
                "source_url": "#",
                "source_metadata": {
                    "site_name": "AI Content Farm",
                    "published_at": datetime.now(timezone.utc).isoformat()
                },
                "content_type": "article"
            }
        ]

    async def generate_site(self) -> Dict[str, Any]:
        """Generate the complete static site."""
        logger.info("Starting static site generation...")

        # Fetch content
        content_items = await self.fetch_content_from_ranker()
        logger.info(f"Fetched {len(content_items)} content items")

        # Ensure output directory is clean
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
        os.makedirs(self.output_dir, exist_ok=True)

        # Generate pages
        await self._generate_homepage(content_items)
        await self._generate_article_pages(content_items)
        await self._generate_topic_pages(content_items)
        await self._copy_static_assets()
        await self._generate_sitemap(content_items)
        await self._generate_rss_feed(content_items)

        return {
            "status": "success",
            # articles + home + topics + sitemap
            "pages_generated": len(content_items) + 3,
            "output_directory": self.output_dir,
            "preview_url": f"http://{self.config.domain}/",
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

    async def _generate_homepage(self, content_items: List[Dict[str, Any]]):
        """Generate the homepage."""
        # Sort by score and take top articles
        featured_articles = sorted(
            content_items,
            key=lambda x: x.get('final_score', 0),
            reverse=True
        )[:10]

        # Group articles by topic
        topics = {}
        for item in content_items:
            for topic in item.get('topics', []):
                if topic not in topics:
                    topics[topic] = []
                topics[topic].append(item)

        homepage_html = self._render_template('homepage.html', {
            'config': self.config,
            'featured_articles': featured_articles,
            'topics': topics,
            'total_articles': len(content_items),
            'generated_at': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        })

        with open(os.path.join(self.output_dir, 'index.html'), 'w') as f:
            f.write(homepage_html)

    async def _generate_article_pages(self, content_items: List[Dict[str, Any]]):
        """Generate individual article pages."""
        articles_dir = os.path.join(self.output_dir, 'articles')
        os.makedirs(articles_dir, exist_ok=True)

        for item in content_items:
            slug = self._create_slug(
                item.get('clean_title', item.get('title', 'untitled')))
            article_html = self._render_template('article.html', {
                'config': self.config,
                'article': item,
                'related_articles': self._get_related_articles(item, content_items)
            })

            with open(os.path.join(articles_dir, f'{slug}.html'), 'w') as f:
                f.write(article_html)

    async def _generate_topic_pages(self, content_items: List[Dict[str, Any]]):
        """Generate topic listing pages."""
        topics_dir = os.path.join(self.output_dir, 'topics')
        os.makedirs(topics_dir, exist_ok=True)

        # Group by topics
        topics = {}
        for item in content_items:
            for topic in item.get('topics', []):
                if topic not in topics:
                    topics[topic] = []
                topics[topic].append(item)

        # Generate topic index
        topic_index_html = self._render_template('topics.html', {
            'config': self.config,
            'topics': topics
        })

        with open(os.path.join(topics_dir, 'index.html'), 'w') as f:
            f.write(topic_index_html)

        # Generate individual topic pages
        for topic, articles in topics.items():
            topic_slug = self._create_slug(topic)
            topic_html = self._render_template('topic.html', {
                'config': self.config,
                'topic': topic,
                'articles': sorted(articles, key=lambda x: x.get('final_score', 0), reverse=True)
            })

            with open(os.path.join(topics_dir, f'{topic_slug}.html'), 'w') as f:
                f.write(topic_html)

    async def _copy_static_assets(self):
        """Copy static assets (CSS, JS, images)."""
        static_output_dir = os.path.join(self.output_dir, 'static')

        # Create default CSS if templates don't exist
        os.makedirs(static_output_dir, exist_ok=True)

        # Generate modern CSS
        css_content = self._generate_modern_css()
        with open(os.path.join(static_output_dir, 'style.css'), 'w') as f:
            f.write(css_content)

        # Copy any existing static files
        if os.path.exists(STATIC_DIR):
            for item in os.listdir(STATIC_DIR):
                src = os.path.join(STATIC_DIR, item)
                dst = os.path.join(static_output_dir, item)
                if os.path.isfile(src):
                    shutil.copy2(src, dst)
                elif os.path.isdir(src):
                    shutil.copytree(src, dst, dirs_exist_ok=True)

    async def _generate_sitemap(self, content_items: List[Dict[str, Any]]):
        """Generate XML sitemap."""
        sitemap_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>http://{self.config.domain}/</loc>
        <lastmod>{datetime.now(timezone.utc).strftime('%Y-%m-%d')}</lastmod>
        <changefreq>daily</changefreq>
        <priority>1.0</priority>
    </url>
    <url>
        <loc>http://{self.config.domain}/topics/</loc>
        <lastmod>{datetime.now(timezone.utc).strftime('%Y-%m-%d')}</lastmod>
        <changefreq>weekly</changefreq>
        <priority>0.8</priority>
    </url>
'''

        for item in content_items:
            slug = self._create_slug(
                item.get('clean_title', item.get('title', 'untitled')))
            sitemap_content += f'''    <url>
        <loc>http://{self.config.domain}/articles/{slug}.html</loc>
        <lastmod>{datetime.now(timezone.utc).strftime('%Y-%m-%d')}</lastmod>
        <changefreq>weekly</changefreq>
        <priority>0.6</priority>
    </url>
'''

        sitemap_content += '</urlset>'

        with open(os.path.join(self.output_dir, 'sitemap.xml'), 'w') as f:
            f.write(sitemap_content)

    async def _generate_rss_feed(self, content_items: List[Dict[str, Any]]):
        """Generate RSS feed."""
        latest_articles = sorted(
            content_items,
            key=lambda x: x.get('source_metadata', {}).get('published_at', ''),
            reverse=True
        )[:20]

        rss_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>{self.config.title}</title>
        <description>{self.config.description}</description>
        <link>http://{self.config.domain}/</link>
        <lastBuildDate>{datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')}</lastBuildDate>
'''

        for item in latest_articles:
            slug = self._create_slug(
                item.get('clean_title', item.get('title', 'untitled')))
            title = item.get('clean_title', item.get('title', 'Untitled'))
            summary = item.get('ai_summary', 'Summary not available')

            rss_content += f'''        <item>
            <title><![CDATA[{title}]]></title>
            <description><![CDATA[{summary}]]></description>
            <link>http://{self.config.domain}/articles/{slug}.html</link>
            <guid>http://{self.config.domain}/articles/{slug}.html</guid>
            <pubDate>{datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')}</pubDate>
        </item>
'''

        rss_content += '''    </channel>
</rss>'''

        with open(os.path.join(self.output_dir, 'feed.xml'), 'w') as f:
            f.write(rss_content)

    def _get_related_articles(self, current_article: Dict[str, Any], all_articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find related articles based on topics."""
        current_topics = set(current_article.get('topics', []))
        related = []

        for article in all_articles:
            if article == current_article:
                continue

            article_topics = set(article.get('topics', []))
            if current_topics & article_topics:  # Has common topics
                related.append(article)

        return sorted(related, key=lambda x: x.get('final_score', 0), reverse=True)[:5]

    def _create_slug(self, title: str) -> str:
        """Create URL-friendly slug from title."""
        slug = title.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[-\s]+', '-', slug)
        return slug.strip('-')

    def _render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render template or return basic HTML if template doesn't exist."""
        template_path = os.path.join(TEMPLATES_DIR, template_name)

        if not os.path.exists(template_path):
            return self._generate_basic_html(template_name, context)

        try:
            template = templates.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            logger.warning(f"Template rendering failed: {e}")
            return self._generate_basic_html(template_name, context)

    def _generate_basic_html(self, template_name: str, context: Dict[str, Any]) -> str:
        """Generate basic HTML when templates are missing."""
        config = context.get('config', self.config)

        if template_name == 'homepage.html':
            return self._generate_homepage_html(context)
        elif template_name == 'article.html':
            return self._generate_article_html(context)
        elif template_name == 'topics.html':
            return self._generate_topics_html(context)
        elif template_name == 'topic.html':
            return self._generate_topic_html(context)
        else:
            return f"<html><body><h1>Template {template_name} not found</h1></body></html>"

    def _generate_homepage_html(self, context: Dict[str, Any]) -> str:
        """Generate homepage HTML."""
        config = context['config']
        featured_articles = context['featured_articles']
        topics = context['topics']

        articles_html = ""
        for article in featured_articles:
            slug = self._create_slug(article.get(
                'clean_title', article.get('title', 'untitled')))
            score = article.get('final_score', 0)
            sentiment = article.get('sentiment', 'neutral')
            topics_list = ', '.join(article.get('topics', []))

            articles_html += f'''
            <article class="article-card">
                <h3><a href="/articles/{slug}.html">{article.get('clean_title', article.get('title', 'Untitled'))}</a></h3>
                <p class="article-meta">
                    <span class="score">Score: {score:.2f}</span> | 
                    <span class="sentiment sentiment-{sentiment}">{sentiment.title()}</span> |
                    <span class="topics">{topics_list}</span>
                </p>
                <p class="summary">{article.get('ai_summary', 'Summary not available')}</p>
                <a href="{article.get('source_url', '#')}" target="_blank" class="source-link">Read Original</a>
            </article>
            '''

        topics_html = ""
        for topic, articles in topics.items():
            topic_slug = self._create_slug(topic)
            topics_html += f'<li><a href="/topics/{topic_slug}.html">{topic} ({len(articles)})</a></li>'

        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{config.title}</title>
    <meta name="description" content="{config.description}">
    <link rel="stylesheet" href="/static/style.css">
    <link rel="alternate" type="application/rss+xml" title="RSS Feed" href="/feed.xml">
</head>
<body>
    <header>
        <nav>
            <h1><a href="/">{config.title}</a></h1>
            <ul>
                <li><a href="/topics/">Topics</a></li>
                <li><a href="/feed.xml">RSS</a></li>
            </ul>
        </nav>
    </header>
    
    <main>
        <section class="hero">
            <h2>{config.description}</h2>
            <p>Latest curated content from top technology sources • Generated: {context.get('generated_at', 'Unknown')}</p>
        </section>
        
        <section class="featured-articles">
            <h2>Featured Articles ({context.get('total_articles', 0)} total)</h2>
            {articles_html}
        </section>
        
        <aside class="sidebar">
            <h3>Topics</h3>
            <ul class="topics-list">
                {topics_html}
            </ul>
        </aside>
    </main>
    
    <footer>
        <p>&copy; 2025 {config.author} • Powered by AI Content Farm</p>
    </footer>
</body>
</html>'''

    def _generate_article_html(self, context: Dict[str, Any]) -> str:
        """Generate article page HTML."""
        config = context['config']
        article = context['article']
        related = context.get('related_articles', [])

        topics_list = ', '.join(article.get('topics', []))
        score = article.get('final_score', 0)
        sentiment = article.get('sentiment', 'neutral')

        related_html = ""
        for rel_article in related:
            rel_slug = self._create_slug(rel_article.get(
                'clean_title', rel_article.get('title', 'untitled')))
            related_html += f'''
            <li>
                <a href="/articles/{rel_slug}.html">{rel_article.get('clean_title', rel_article.get('title', 'Untitled'))}</a>
                <span class="score">{rel_article.get('final_score', 0):.2f}</span>
            </li>
            '''

        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{article.get('clean_title', article.get('title', 'Untitled'))} - {config.title}</title>
    <meta name="description" content="{article.get('ai_summary', 'Article summary')[:160]}">
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <header>
        <nav>
            <h1><a href="/">{config.title}</a></h1>
            <ul>
                <li><a href="/topics/">Topics</a></li>
                <li><a href="/feed.xml">RSS</a></li>
            </ul>
        </nav>
    </header>
    
    <main class="article-page">
        <article>
            <h1>{article.get('clean_title', article.get('title', 'Untitled'))}</h1>
            
            <div class="article-meta">
                <span class="score">AI Score: {score:.2f}</span> |
                <span class="sentiment sentiment-{sentiment}">{sentiment.title()}</span> |
                <span class="topics">Topics: {topics_list}</span>
            </div>
            
            <div class="article-content">
                <h2>AI Summary</h2>
                <p>{article.get('ai_summary', 'Summary not available')}</p>
                
                <div class="source-info">
                    <p><strong>Source:</strong> <a href="{article.get('source_url', '#')}" target="_blank">{article.get('source_metadata', {}).get('site_name', 'Unknown')}</a></p>
                    <a href="{article.get('source_url', '#')}" target="_blank" class="read-original-btn">Read Full Article</a>
                </div>
            </div>
        </article>
        
        <aside class="related-articles">
            <h3>Related Articles</h3>
            <ul>
                {related_html}
            </ul>
        </aside>
    </main>
    
    <footer>
        <p>&copy; 2025 {config.author} • Powered by AI Content Farm</p>
    </footer>
</body>
</html>'''

    def _generate_topics_html(self, context: Dict[str, Any]) -> str:
        """Generate topics index HTML."""
        config = context['config']
        topics = context['topics']

        topics_html = ""
        for topic, articles in sorted(topics.items()):
            topic_slug = self._create_slug(topic)
            avg_score = sum(article.get('final_score', 0)
                            for article in articles) / len(articles)
            topics_html += f'''
            <div class="topic-card">
                <h3><a href="/topics/{topic_slug}.html">{topic}</a></h3>
                <p>{len(articles)} articles • Average score: {avg_score:.2f}</p>
            </div>
            '''

        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Topics - {config.title}</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <header>
        <nav>
            <h1><a href="/">{config.title}</a></h1>
            <ul>
                <li><a href="/topics/">Topics</a></li>
                <li><a href="/feed.xml">RSS</a></li>
            </ul>
        </nav>
    </header>
    
    <main>
        <h1>All Topics</h1>
        <div class="topics-grid">
            {topics_html}
        </div>
    </main>
    
    <footer>
        <p>&copy; 2025 {config.author} • Powered by AI Content Farm</p>
    </footer>
</body>
</html>'''

    def _generate_topic_html(self, context: Dict[str, Any]) -> str:
        """Generate individual topic page HTML."""
        config = context['config']
        topic = context['topic']
        articles = context['articles']

        articles_html = ""
        for article in articles:
            slug = self._create_slug(article.get(
                'clean_title', article.get('title', 'untitled')))
            score = article.get('final_score', 0)
            sentiment = article.get('sentiment', 'neutral')

            articles_html += f'''
            <article class="article-card">
                <h3><a href="/articles/{slug}.html">{article.get('clean_title', article.get('title', 'Untitled'))}</a></h3>
                <p class="article-meta">
                    <span class="score">Score: {score:.2f}</span> | 
                    <span class="sentiment sentiment-{sentiment}">{sentiment.title()}</span>
                </p>
                <p class="summary">{article.get('ai_summary', 'Summary not available')}</p>
                <a href="{article.get('source_url', '#')}" target="_blank" class="source-link">Read Original</a>
            </article>
            '''

        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{topic} - {config.title}</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <header>
        <nav>
            <h1><a href="/">{config.title}</a></h1>
            <ul>
                <li><a href="/topics/">Topics</a></li>
                <li><a href="/feed.xml">RSS</a></li>
            </ul>
        </nav>
    </header>
    
    <main>
        <h1>{topic}</h1>
        <p>{len(articles)} articles in this topic</p>
        
        <section class="articles">
            {articles_html}
        </section>
    </main>
    
    <footer>
        <p>&copy; 2025 {config.author} • Powered by AI Content Farm</p>
    </footer>
</body>
</html>'''

    def _generate_modern_css(self) -> str:
        """Generate modern CSS for the site."""
        return '''
/* Modern CSS for AI Content Farm */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
    line-height: 1.6;
    color: #333;
    background: #f8f9fa;
}

header {
    background: #fff;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    position: sticky;
    top: 0;
    z-index: 100;
}

nav {
    max-width: 1200px;
    margin: 0 auto;
    padding: 1rem 2rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

nav h1 a {
    color: #2563eb;
    text-decoration: none;
    font-size: 1.5rem;
    font-weight: 700;
}

nav ul {
    list-style: none;
    display: flex;
    gap: 2rem;
}

nav a {
    color: #666;
    text-decoration: none;
    font-weight: 500;
    transition: color 0.2s;
}

nav a:hover {
    color: #2563eb;
}

main {
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem;
    display: grid;
    grid-template-columns: 1fr 300px;
    gap: 3rem;
}

.hero {
    grid-column: 1 / -1;
    text-align: center;
    padding: 3rem 0;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border-radius: 12px;
    margin-bottom: 2rem;
}

.hero h2 {
    font-size: 2.5rem;
    margin-bottom: 1rem;
}

.hero p {
    font-size: 1.1rem;
    opacity: 0.9;
}

.article-card {
    background: white;
    padding: 2rem;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    margin-bottom: 2rem;
    transition: transform 0.2s, box-shadow 0.2s;
}

.article-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(0,0,0,0.15);
}

.article-card h3 {
    margin-bottom: 1rem;
}

.article-card h3 a {
    color: #1a1a1a;
    text-decoration: none;
    font-size: 1.3rem;
}

.article-card h3 a:hover {
    color: #2563eb;
}

.article-meta {
    font-size: 0.9rem;
    color: #666;
    margin-bottom: 1rem;
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
}

.score {
    background: #e5f3ff;
    color: #0066cc;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-weight: 600;
}

.sentiment {
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-weight: 600;
    text-transform: capitalize;
}

.sentiment-positive {
    background: #d4edda;
    color: #155724;
}

.sentiment-negative {
    background: #f8d7da;
    color: #721c24;
}

.sentiment-neutral {
    background: #e2e3e5;
    color: #383d41;
}

.summary {
    color: #555;
    line-height: 1.7;
    margin-bottom: 1rem;
}

.source-link, .read-original-btn {
    color: #2563eb;
    text-decoration: none;
    font-weight: 500;
    display: inline-block;
    padding: 0.5rem 1rem;
    border: 2px solid #2563eb;
    border-radius: 6px;
    transition: all 0.2s;
}

.source-link:hover, .read-original-btn:hover {
    background: #2563eb;
    color: white;
}

.sidebar {
    background: white;
    padding: 2rem;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    height: fit-content;
    position: sticky;
    top: 6rem;
}

.sidebar h3 {
    margin-bottom: 1rem;
    color: #1a1a1a;
}

.topics-list {
    list-style: none;
}

.topics-list li {
    margin-bottom: 0.5rem;
}

.topics-list a {
    color: #555;
    text-decoration: none;
    padding: 0.5rem;
    display: block;
    border-radius: 4px;
    transition: background 0.2s;
}

.topics-list a:hover {
    background: #f1f5f9;
    color: #2563eb;
}

.topics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 2rem;
}

.topic-card {
    background: white;
    padding: 2rem;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    text-align: center;
    transition: transform 0.2s;
}

.topic-card:hover {
    transform: translateY(-2px);
}

.topic-card h3 a {
    color: #1a1a1a;
    text-decoration: none;
    font-size: 1.5rem;
}

.topic-card h3 a:hover {
    color: #2563eb;
}

.article-page {
    grid-template-columns: 1fr;
}

.article-page .related-articles {
    margin-top: 3rem;
    background: white;
    padding: 2rem;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.related-articles ul {
    list-style: none;
}

.related-articles li {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem 0;
    border-bottom: 1px solid #eee;
}

.related-articles li:last-child {
    border-bottom: none;
}

.related-articles a {
    color: #2563eb;
    text-decoration: none;
    flex: 1;
}

.related-articles a:hover {
    text-decoration: underline;
}

.article-content {
    background: white;
    padding: 3rem;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    line-height: 1.8;
}

.article-content h1 {
    color: #1a1a1a;
    font-size: 2.5rem;
    margin-bottom: 2rem;
    line-height: 1.2;
}

.article-content h2 {
    color: #2563eb;
    margin: 2rem 0 1rem 0;
    font-size: 1.5rem;
}

.source-info {
    background: #f8f9fa;
    padding: 1.5rem;
    border-radius: 8px;
    margin-top: 2rem;
    border-left: 4px solid #2563eb;
}

footer {
    background: #1a1a1a;
    color: white;
    text-align: center;
    padding: 2rem;
    margin-top: 4rem;
}

@media (max-width: 768px) {
    nav {
        flex-direction: column;
        gap: 1rem;
    }
    
    main {
        grid-template-columns: 1fr;
        padding: 1rem;
    }
    
    .hero h2 {
        font-size: 2rem;
    }
    
    .article-content {
        padding: 2rem;
    }
    
    .article-content h1 {
        font-size: 2rem;
    }
}
'''

# API Routes


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "Static Site Generator",
        "version": "1.0.0",
        "status": "ready",
        "endpoints": {
            "generate": "/generate",
            "preview": "/preview",
            "health": "/health"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "ssg"
    }


@app.post("/generate")
async def generate_site(request: GenerationRequest, background_tasks: BackgroundTasks):
    """Generate static site from curated content."""
    try:
        config = SiteConfig()
        generator = StaticSiteGenerator(config)

        # Run generation in background
        background_tasks.add_task(generator.generate_site)

        return {
            "status": "generation_started",
            "message": "Static site generation started",
            "preview_url": f"http://localhost:8005/preview/",
            "expected_completion": "30 seconds"
        }
    except Exception as e:
        logger.error(f"Site generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/generate/sync")
async def generate_site_sync():
    """Generate static site synchronously (for testing)."""
    try:
        config = SiteConfig()
        generator = StaticSiteGenerator(config)
        result = await generator.generate_site()

        return {
            "status": "success",
            "result": result,
            "preview_url": "http://localhost:8005/preview/"
        }
    except Exception as e:
        logger.error(f"Site generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Mount static files for preview
app.mount("/preview", StaticFiles(directory=SITE_OUTPUT_DIR,
          html=True), name="preview")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
