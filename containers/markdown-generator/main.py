"""
Containerized Markdown Generator

This service listens for ranked content and automatically generates markdown files.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import os
import asyncio
import httpx
import logging
from datetime import datetime, timezone
from pathlib import Path
import re

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Markdown Generator API",
    description="Generates markdown from ranked content",
    version="1.0.0"
)


class MarkdownRequest(BaseModel):
    """Request to generate markdown from content."""
    content_items: List[Dict[str, Any]]
    output_dir: str = "/app/output/markdown"
    auto_notify: bool = True


class ContentWatcher:
    """Watches for new ranked content and triggers markdown generation."""

    def __init__(self):
        self.last_check = datetime.now(timezone.utc)
        self.processed_rankings = set()

    async def start_watching(self):
        """Start watching for new ranked content."""
        logger.info("Starting content watcher for ranked content")

        while True:
            try:
                await self.check_for_new_rankings()
                await asyncio.sleep(15)  # Check every 15 seconds
            except Exception as e:
                logger.error(f"Content watcher error: {e}")
                await asyncio.sleep(30)

    async def check_for_new_rankings(self):
        """Check for new rankings from the ranker service."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://content-ranker:8000/ranking/top", timeout=30.0)

                if response.status_code == 200:
                    data = response.json()
                    content_items = data.get('items', [])

                    if content_items and len(content_items) > 0:
                        # Create a hash of the content to detect changes
                        content_hash = hash(json.dumps(
                            content_items, sort_keys=True))

                        if content_hash not in self.processed_rankings:
                            logger.info(
                                f"New ranked content detected: {len(content_items)} items")
                            await self.trigger_markdown_generation(content_items)
                            self.processed_rankings.add(content_hash)

                else:
                    logger.warning(
                        f"Ranker service returned {response.status_code}")

        except Exception as e:
            logger.error(f"Failed to check for new rankings: {e}")

    async def trigger_markdown_generation(self, content_items: List[Dict[str, Any]]):
        """Generate markdown files from content items."""
        try:
            generator = MarkdownGenerator()
            result = await generator.generate_markdown_files(content_items)

            logger.info(f"Markdown generation completed: {result}")

            # Notify markdown converter
            await self.notify_markdown_ready(result)

        except Exception as e:
            logger.error(f"Failed to generate markdown: {e}")

    async def notify_markdown_ready(self, generation_result: Dict[str, Any]):
        """Notify the markdown converter that new markdown is ready."""
        try:
            notification = {
                "event": "markdown_generated",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "result": generation_result
            }

            # Try to notify markdown converter
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        "http://markdown-converter:8000/convert",
                        json={"markdown_dir": "/app/output/markdown"},
                        timeout=10.0
                    )
                logger.info("Notified markdown converter")
            except:
                logger.warning(
                    "Could not notify markdown converter (may not be running)")

        except Exception as e:
            logger.error(f"Failed to notify markdown ready: {e}")


class MarkdownGenerator:
    """Generate markdown content from pipeline results."""

    def __init__(self, output_dir: str = "/app/output/markdown"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    async def generate_markdown_files(self, content_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate markdown files from content items."""
        try:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

            # Generate individual markdown files
            markdown_files = []
            for i, item in enumerate(content_items, 1):
                markdown_content = self.generate_post_markdown(item, rank=i)

                # Create filename
                title = item.get('clean_title', item.get('title', 'untitled'))
                slug = self._create_slug(title)
                filename = f"ranked_{timestamp}_{slug}.md"
                filepath = os.path.join(self.output_dir, filename)

                # Write markdown file
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)

                markdown_files.append({
                    "file": filepath,
                    "slug": slug,
                    "title": item.get('clean_title', item.get('title', 'Untitled')),
                    "score": item.get('final_score', 0)
                })

            # Generate index file
            index_content = self.generate_index_markdown(
                content_items, timestamp)
            index_file = os.path.join(self.output_dir, "index.md")

            with open(index_file, 'w', encoding='utf-8') as f:
                f.write(index_content)

            # Generate publishing manifest
            manifest = {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "timestamp": timestamp,
                "total_posts": len(content_items),
                "posts": markdown_files,
                "index_file": index_file,
                "generator": "containerized-markdown-generator",
                "version": "1.0.0"
            }

            manifest_file = os.path.join(
                self.output_dir, "publishing_manifest.json")
            with open(manifest_file, 'w') as f:
                json.dump(manifest, f, indent=2)

            return {
                "status": "success",
                "files_generated": len(markdown_files) + 1,  # +1 for index
                "manifest_file": manifest_file,
                "output_directory": self.output_dir,
                "timestamp": timestamp
            }

        except Exception as e:
            logger.error(f"Markdown generation failed: {e}")
            raise

    def generate_post_markdown(self, item: Dict[str, Any], rank: int = 1) -> str:
        """Generate markdown for a single content item."""
        # Extract key information
        title = item.get('title', 'Untitled')
        clean_title = item.get('clean_title', title)
        source_url = item.get('source_url', '')
        content_type = item.get('content_type', 'article')

        # Get enrichment data
        ai_summary = item.get('ai_summary', 'Summary not available')
        topics = item.get('topics', [])
        sentiment = item.get('sentiment', 'neutral')

        # Get scoring data
        final_score = item.get('final_score', 0)
        engagement_score = item.get('engagement_score', 0)

        # Get source metadata
        source_metadata = item.get('source_metadata', {})
        site_name = source_metadata.get('site_name', 'Unknown Source')
        published_at = item.get(
            'published_at', datetime.now(timezone.utc).isoformat())

        # Create slug from title
        slug = self._create_slug(clean_title)

        # Generate frontmatter
        frontmatter = f"""---
title: "{clean_title}"
slug: "{slug}"
date: "{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
excerpt: "{ai_summary[:150]}..."
featured: {str(final_score > 0.8).lower()}
tags: {json.dumps(topics)}
categories: ["AI Curated", "Technology"]
source:
  name: "{site_name}"
  url: "{source_url}"
metadata:
  rank: {rank}
  ai_score: {final_score:.3f}
  engagement_score: {engagement_score:.3f}
  sentiment: "{sentiment}"
  content_type: "{content_type}"
  generated_at: "{datetime.now(timezone.utc).isoformat()}"
---"""

        # Generate content body
        body = f"""# {clean_title}

## Summary

{ai_summary}

## Key Information

**Topics:** {', '.join(topics)}

**Sentiment:** {sentiment.title()}

## Source

This content was curated from [{site_name}]({source_url}).

**Read the full article:** [{source_url}]({source_url})

---

*This post was generated by AI Content Farm - an automated content curation system.*"""

        return f"{frontmatter}\n\n{body}"

    def generate_index_markdown(self, content_items: List[Dict[str, Any]], timestamp: str) -> str:
        """Generate an index markdown file listing all articles."""

        frontmatter = f"""---
title: "AI Curated Content Index"
date: "{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
type: "index"
generated_at: "{datetime.now(timezone.utc).isoformat()}"
total_articles: {len(content_items)}
---"""

        # Create article listings
        article_list = ""
        for i, item in enumerate(content_items, 1):
            title = item.get('clean_title', item.get('title', 'Untitled'))
            slug = self._create_slug(title)
            score = item.get('final_score', 0)
            topics = ', '.join(item.get('topics', []))

            article_list += f"""
### {i}. [{title}]({slug}.html)

**Score:** {score:.3f} | **Topics:** {topics}

{item.get('ai_summary', 'Summary not available')[:200]}...

"""

        body = f"""# AI Curated Content Index

Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}  
Total Articles: {len(content_items)}

## Featured Articles
{article_list}

---

*Content curated and generated by AI Content Farm*"""

        return f"{frontmatter}\n\n{body}"

    def _create_slug(self, title: str) -> str:
        """Create URL-friendly slug from title."""
        slug = title.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[-\s]+', '-', slug)
        return slug.strip('-')[:50]  # Limit length


# Global content watcher
content_watcher = ContentWatcher()


@app.on_event("startup")
async def startup_event():
    """Start the content watcher when the app starts."""
    asyncio.create_task(content_watcher.start_watching())


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Markdown Generator",
        "version": "1.0.0",
        "status": "watching",
        "processed_rankings": len(content_watcher.processed_rankings),
        "last_check": content_watcher.last_check.isoformat()
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "markdown-generator"
    }


@app.post("/generate")
async def generate_markdown(request: MarkdownRequest):
    """Manually trigger markdown generation."""
    try:
        generator = MarkdownGenerator(request.output_dir)
        result = await generator.generate_markdown_files(request.content_items)

        if request.auto_notify:
            await content_watcher.notify_markdown_ready(result)

        return {
            "status": "success",
            "result": result
        }

    except Exception as e:
        logger.error(f"Manual markdown generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status")
async def get_status():
    """Get detailed status of the markdown generator."""
    try:
        # Check ranker availability
        ranker_available = False
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://content-ranker:8000/health", timeout=5.0)
                ranker_available = response.status_code == 200
        except:
            pass

        # Count markdown files
        markdown_files = 0
        if os.path.exists("/app/output/markdown"):
            markdown_files = len(
                list(Path("/app/output/markdown").glob("*.md")))

        return {
            "service": "markdown-generator",
            "status": "running",
            "content_watcher": {
                "watching": True,
                "processed_rankings": len(content_watcher.processed_rankings),
                "last_check": content_watcher.last_check.isoformat()
            },
            "ranker_service": {
                "available": ranker_available,
                "url": "http://content-ranker:8000"
            },
            "file_statistics": {
                "markdown_files": markdown_files
            }
        }

    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
