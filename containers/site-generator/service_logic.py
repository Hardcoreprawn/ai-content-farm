#!/usr/bin/env python3
"""
Site Generator business logic implementation
"""

import asyncio
import logging
import json
import tempfile
import shutil
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from jinja2 import Environment, FileSystemLoader, Template

from libs.blob_storage import BlobStorageClient, BlobContainers, get_timestamped_blob_name
from models import GenerationRequest, GenerationStatus, GenerationStatusResponse, ContentItem, SiteMetadata
from config import get_config

logger = logging.getLogger(__name__)


class SiteProcessor:
    """Core business logic for Site Generator."""

    def __init__(self):
        self.config = get_config()
        self.blob_client = BlobStorageClient()
        self.is_running = False
        self.watch_task = None
        self.generation_status: Dict[str, Dict[str, Any]] = {}

        # Initialize Jinja2 environment
        self.setup_templates()

    def setup_templates(self):
        """Setup Jinja2 templates for site generation."""
        # Create templates directory if it doesn't exist
        template_dir = "/app/templates"
        os.makedirs(template_dir, exist_ok=True)

        # Create default templates if they don't exist
        self.create_default_templates(template_dir)

        # Initialize Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=True
        )

    def create_default_templates(self, template_dir: str):
        """Create default HTML templates."""
        # Base template
        base_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}{{ site_metadata.title }}{% endblock %}</title>
    <meta name="description" content="{{ site_metadata.description }}">
    <style>
        /* Modern CSS styling */
        :root {
            --primary-color: #2563eb;
            --secondary-color: #64748b;
            --background-color: #f8fafc;
            --card-background: #ffffff;
            --text-color: #1e293b;
            --border-color: #e2e8f0;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            line-height: 1.6;
            color: var(--text-color);
            background-color: var(--background-color);
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
        }
        
        header {
            background: var(--card-background);
            border-bottom: 1px solid var(--border-color);
            padding: 20px 0;
            margin-bottom: 40px;
        }
        
        .header-content {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .logo {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--primary-color);
            text-decoration: none;
        }
        
        .subtitle {
            color: var(--secondary-color);
            font-size: 0.9rem;
            margin-top: 4px;
        }
        
        .article-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
            gap: 30px;
            margin-bottom: 60px;
        }
        
        .article-card {
            background: var(--card-background);
            border-radius: 12px;
            border: 1px solid var(--border-color);
            padding: 24px;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .article-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        }
        
        .article-title {
            font-size: 1.25rem;
            font-weight: 600;
            margin-bottom: 12px;
            line-height: 1.4;
        }
        
        .article-title a {
            color: var(--text-color);
            text-decoration: none;
        }
        
        .article-title a:hover {
            color: var(--primary-color);
        }
        
        .article-meta {
            color: var(--secondary-color);
            font-size: 0.85rem;
            margin-bottom: 16px;
            display: flex;
            gap: 16px;
        }
        
        .article-summary {
            color: var(--text-color);
            line-height: 1.6;
            margin-bottom: 16px;
        }
        
        .article-tags {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }
        
        .tag {
            background: var(--primary-color);
            color: white;
            padding: 4px 12px;
            border-radius: 16px;
            font-size: 0.75rem;
            font-weight: 500;
        }
        
        footer {
            background: var(--card-background);
            border-top: 1px solid var(--border-color);
            padding: 40px 0;
            text-align: center;
            color: var(--secondary-color);
            margin-top: 60px;
        }
        
        @media (max-width: 768px) {
            .article-grid {
                grid-template-columns: 1fr;
            }
            
            .header-content {
                flex-direction: column;
                text-align: center;
                gap: 8px;
            }
        }
    </style>
</head>
<body>
    <header>
        <div class="container">
            <div class="header-content">
                <div>
                    <a href="/" class="logo">{{ site_metadata.title }}</a>
                    <div class="subtitle">{{ site_metadata.description }}</div>
                </div>
                <div style="font-size: 0.85rem; color: var(--secondary-color);">
                    Updated {{ site_metadata.generation_date.strftime('%B %d, %Y') }}
                </div>
            </div>
        </div>
    </header>
    
    <main class="container">
        {% block content %}{% endblock %}
    </main>
    
    <footer>
        <div class="container">
            <p>Generated by AI Content Farm • {{ site_metadata.total_articles }} articles • {{ site_metadata.content_sources|join(', ') }}</p>
        </div>
    </footer>
</body>
</html>"""

        # Index template
        index_template = """{% extends "base.html" %}

{% block content %}
<div class="article-grid">
    {% for article in articles %}
    <article class="article-card">
        <h2 class="article-title">
            <a href="{{ article.url }}" target="_blank" rel="noopener noreferrer">
                {{ article.title }}
            </a>
        </h2>
        
        <div class="article-meta">
            <span>{{ article.source|title }}</span>
            {% if article.published_date %}
            <span>{{ article.published_date.strftime('%B %d, %Y') }}</span>
            {% endif %}
            {% if article.score %}
            <span>Score: {{ "%.1f"|format(article.score) }}</span>
            {% endif %}
        </div>
        
        <div class="article-summary">
            {{ article.summary }}
        </div>
        
        {% if article.tags %}
        <div class="article-tags">
            {% for tag in article.tags[:3] %}
            <span class="tag">{{ tag }}</span>
            {% endfor %}
        </div>
        {% endif %}
    </article>
    {% endfor %}
</div>
{% endblock %}"""

        # Write templates to files
        with open(f"{template_dir}/base.html", "w") as f:
            f.write(base_template)

        with open(f"{template_dir}/index.html", "w") as f:
            f.write(index_template)

        logger.info(f"Created default templates in {template_dir}")

    async def start(self):
        """Start background processing."""
        if not self.is_running:
            self.is_running = True
            self.watch_task = asyncio.create_task(
                self._watch_for_new_content())
            logger.info("Site processor started")

    async def stop(self):
        """Stop background processing."""
        self.is_running = False
        if self.watch_task:
            self.watch_task.cancel()
            try:
                await self.watch_task
            except asyncio.CancelledError:
                pass
        logger.info("Site processor stopped")

    async def _watch_for_new_content(self):
        """Watch for new ranked content to automatically generate sites."""
        while self.is_running:
            try:
                # Check for new ranked content blobs
                new_blobs = await self._find_new_ranked_content()

                for blob_info in new_blobs:
                    # Auto-generate site for new content
                    site_id = f"auto_{blob_info['name'].replace('.json', '')}_{datetime.now(timezone.utc).strftime('%H%M%S')}"
                    await self.generate_site(
                        site_id=site_id,
                        request=GenerationRequest(
                            content_source=blob_info['name'])
                    )
                    logger.info(
                        f"Auto-generated site {site_id} for new content")

                await asyncio.sleep(30)  # Check every 30 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in content watcher: {e}")
                await asyncio.sleep(60)  # Wait longer on error

    async def _find_new_ranked_content(self) -> List[Dict[str, Any]]:
        """Find new ranked content that hasn't been processed into sites yet."""
        try:
            # List recent ranked content blobs
            blobs = self.blob_client.list_blobs("ranked-content")

            # Filter for recent blobs (last hour)
            recent_threshold = datetime.now(timezone.utc).timestamp() - 3600
            new_blobs = []

            for blob in blobs:
                blob_time = blob.get('last_modified', datetime.min)
                if hasattr(blob_time, 'timestamp'):
                    if blob_time.timestamp() > recent_threshold:
                        new_blobs.append({
                            'name': blob['name'],
                            'last_modified': blob_time
                        })

            return new_blobs[:5]  # Limit to 5 most recent

        except Exception as e:
            logger.error(f"Error finding new ranked content: {e}")
            return []

    async def generate_site(self, site_id: str, request: GenerationRequest):
        """Generate a complete static site."""
        try:
            # Update status
            self.generation_status[site_id] = {
                "status": GenerationStatus.PROCESSING,
                "progress": 0,
                "current_step": "Initializing",
                "start_time": datetime.now(timezone.utc)
            }

            # Step 1: Load content
            self._update_status(site_id, 10, "Loading content")
            articles = await self._load_content(request.content_source)

            # Step 2: Process and filter articles
            self._update_status(site_id, 30, "Processing articles")
            processed_articles = self._process_articles(
                articles, request.max_articles)

            # Step 3: Generate HTML
            self._update_status(site_id, 60, "Generating HTML")
            site_html = await self._generate_html(processed_articles, request, site_id)

            # Step 4: Upload to blob storage
            self._update_status(site_id, 90, "Uploading to storage")
            await self._upload_site(site_id, site_html)

            # Step 5: Complete
            self._update_status(site_id, 100, "Completed",
                                GenerationStatus.COMPLETED)

            logger.info(f"Site generation completed for {site_id}")

        except Exception as e:
            logger.error(f"Site generation failed for {site_id}: {e}")
            self.generation_status[site_id] = {
                "status": GenerationStatus.FAILED,
                "error_message": str(e),
                "completion_time": datetime.now(timezone.utc)
            }

    def _update_status(self, site_id: str, progress: int, step: str, status: GenerationStatus = GenerationStatus.PROCESSING):
        """Update generation status."""
        self.generation_status[site_id].update({
            "status": status,
            "progress": progress,
            "current_step": step
        })

        if status == GenerationStatus.COMPLETED:
            self.generation_status[site_id]["completion_time"] = datetime.now(
                timezone.utc)

    async def _load_content(self, content_source: str) -> List[Dict[str, Any]]:
        """Load content from blob storage."""
        try:
            if content_source == "ranked":
                # Find most recent ranked content
                blobs = self.blob_client.list_blobs("ranked-content")
                if not blobs:
                    raise ValueError("No ranked content available")

                # Get most recent blob (blobs are dictionaries with name and metadata)
                latest_blob = max(blobs, key=lambda x: x.get(
                    'last_modified', datetime.min))
                blob_name = latest_blob['name']
            else:
                blob_name = content_source

            # Download content
            content_data = self.blob_client.download_json(
                "ranked-content", blob_name)

            if isinstance(content_data, dict) and 'items' in content_data:
                return content_data['items']
            elif isinstance(content_data, list):
                return content_data
            else:
                raise ValueError("Invalid content format")

        except Exception as e:
            logger.error(f"Failed to load content from {content_source}: {e}")
            # Return empty list as fallback
            return []

    def _process_articles(self, articles: List[Dict[str, Any]], max_articles: int) -> List[ContentItem]:
        """Process and convert articles to ContentItem objects."""
        processed = []

        for article_data in articles[:max_articles]:
            try:
                # Create ContentItem from article data
                article = ContentItem(
                    title=article_data.get('title', 'Untitled'),
                    url=article_data.get('url', '#'),
                    summary=article_data.get('summary', article_data.get(
                        'description', 'No summary available')),
                    content=article_data.get('content'),
                    author=article_data.get('author'),
                    published_date=self._parse_date(
                        article_data.get('published_date')),
                    tags=article_data.get('tags', []),
                    score=article_data.get('score'),
                    source=article_data.get('source', 'unknown')
                )
                processed.append(article)

            except Exception as e:
                logger.warning(f"Failed to process article: {e}")
                continue

        return processed

    def _parse_date(self, date_str: Any) -> Optional[datetime]:
        """Parse date string to datetime object."""
        if not date_str:
            return None

        if isinstance(date_str, datetime):
            return date_str

        try:
            # Try ISO format first
            return datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
        except:
            return None

    async def _generate_html(self, articles: List[ContentItem], request: GenerationRequest, site_id: str) -> str:
        """Generate HTML for the site."""
        try:
            # Create site metadata
            site_metadata = SiteMetadata(
                title=request.site_title or self.config.site_title,
                description=request.site_description or self.config.site_description,
                generation_date=datetime.now(timezone.utc),
                theme=request.theme.value,
                total_articles=len(articles),
                content_sources=list(
                    set(article.source for article in articles)),
                version=self.config.version
            )

            # Render HTML using Jinja2
            template = self.jinja_env.get_template('index.html')
            html_content = template.render(
                articles=articles,
                site_metadata=site_metadata,
                site_id=site_id
            )

            return html_content

        except Exception as e:
            logger.error(f"HTML generation failed: {e}")
            raise

    async def _upload_site(self, site_id: str, html_content: str):
        """Upload generated site to blob storage."""
        try:
            # Upload index.html
            self.blob_client.upload_text(
                "published-sites",
                f"{site_id}/index.html",
                html_content
            )

            # Create a simple manifest
            manifest = {
                "site_id": site_id,
                "generation_date": datetime.now(timezone.utc).isoformat(),
                "files": ["index.html"],
                "theme": "modern"
            }

            self.blob_client.upload_json(
                "published-sites",
                f"{site_id}/manifest.json",
                manifest
            )

            logger.info(f"Site {site_id} uploaded successfully")

        except Exception as e:
            logger.error(f"Failed to upload site {site_id}: {e}")
            raise

    async def get_generation_status(self, site_id: str) -> GenerationStatusResponse:
        """Get the status of a site generation."""
        if site_id not in self.generation_status:
            raise ValueError(f"Site generation {site_id} not found")

        status_data = self.generation_status[site_id]

        return GenerationStatusResponse(
            site_id=site_id,
            status=status_data["status"],
            progress_percentage=status_data.get("progress", 0),
            current_step=status_data.get("current_step", "Unknown"),
            error_message=status_data.get("error_message"),
            completion_time=status_data.get("completion_time")
        )

    async def list_available_sites(self) -> List[Dict[str, Any]]:
        """List all available generated sites."""
        try:
            sites = []
            blobs = self.blob_client.list_blobs("published-sites")

            # Group blobs by site_id (directory)
            site_dirs = set()
            for blob in blobs:
                blob_name = blob.get('name', '')
                if '/' in blob_name:
                    site_id = blob_name.split('/')[0]
                    site_dirs.add(site_id)

            # Get info for each site
            for site_id in site_dirs:
                try:
                    # Try to get manifest
                    manifest = self.blob_client.download_json(
                        "published-sites",
                        f"{site_id}/manifest.json"
                    )

                    sites.append({
                        "site_id": site_id,
                        "generation_date": manifest.get("generation_date"),
                        "preview_url": f"/preview/{site_id}",
                        "theme": manifest.get("theme", "unknown")
                    })

                except Exception as e:
                    logger.warning(
                        f"Could not get manifest for site {site_id}: {e}")
                    # Add basic info without manifest
                    sites.append({
                        "site_id": site_id,
                        "preview_url": f"/preview/{site_id}",
                        "status": "manifest_missing"
                    })

            return sorted(sites, key=lambda x: x.get("generation_date", ""), reverse=True)

        except Exception as e:
            logger.error(f"Failed to list sites: {e}")
            return []
