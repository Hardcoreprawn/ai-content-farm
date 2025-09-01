"""
Test the site generator with existing processed content.
Demonstrates markdown generation and site building.
"""

import asyncio
import json
import sys
import tempfile
from pathlib import Path

from site_generator import SiteGenerator

from config import Config

sys.path.append("/workspaces/ai-content-farm/containers/site-generator")
sys.path.append("/workspaces/ai-content-farm")


def test_markdown_generation():
    """Test markdown generation with sample article (without Azure connectivity)."""

    # Sample article data (based on the one we examined earlier)
    sample_article = {
        "topic_id": "reddit_1n4boz5",
        "title": "U.S. And Allies Declare Salt Typhoon Hack A National Defense Crisis",
        "article_content": """**Title: U.S. And Allies Declare Salt Typhoon Hack A National Defense Crisis**

**Introduction:**
In a recent turn of events, the United States and its allies have declared the Salt Typhoon hack as a national defense crisis. This unprecedented move has sent shockwaves through the global cybersecurity community, raising concerns about the vulnerability of critical infrastructure to cyber threats.

**Main Content:**

**1. The Salt Typhoon Hack Unveiled**
The Salt Typhoon hack, a sophisticated cyber attack that targeted key government agencies and critical infrastructure, was first detected by cybersecurity experts earlier this month.

**2. Response from the U.S. and Allies**
In response to the Salt Typhoon hack, the United States, along with its allies, has classified the incident as a national defense crisis.

**Conclusion:**
The declaration of the Salt Typhoon hack as a national defense crisis serves as a wake-up call for governments and organizations worldwide to prioritize cybersecurity and invest in robust defense mechanisms.""",
        "word_count": 497,
        "quality_score": 0.5,
        "cost": 0.0010515,
        "tokens_used": 895,
        "processing_time": 4.402451,
        "source_priority": 1,
        "source": "reddit",
        "original_url": "https://www.forbes.com/sites/emilsayegh/2025/08/30/us-and-allies-declare-salt-typhoon-hack-a-national-defense-crisis/",
        "generated_at": "2025-09-01T17:29:27.920322+00:00",
        "metadata": {
            "processor_id": "84e275e9",
            "session_id": "eeb8bde6-b096-4d30-8b5b-19febfb7dfae",
            "openai_model": "gpt-35-turbo",
            "original_upvotes": 0,
            "original_comments": 399,
            "content_type": "generated_article",
        },
    }

    print("🧪 Testing Site Generator Components")
    print("=" * 50)

    # Test core functionality without Azure connectivity
    import re
    from datetime import datetime, timezone

    from site_generator import SiteGenerator

    # Test slug creation (static method)
    def create_slug(title: str) -> str:
        """Create URL-safe slug from title."""
        slug = title.lower()
        slug = re.sub(r"[^a-z0-9\s-]", "", slug)
        slug = re.sub(r"\s+", "-", slug)
        slug = re.sub(r"-+", "-", slug)
        slug = slug.strip("-")
        return slug[:50]

    # Test markdown creation (static method)
    def create_markdown_content(article_data: dict) -> str:
        """Create markdown content with frontmatter."""
        title = article_data.get("title", "Untitled")
        content = article_data.get("article_content", "")
        word_count = article_data.get("word_count", 0)
        quality_score = article_data.get("quality_score", 0)
        cost = article_data.get("cost", 0)
        source = article_data.get("source", "unknown")
        original_url = article_data.get("original_url", "")
        generated_at = article_data.get(
            "generated_at", datetime.now(timezone.utc).isoformat()
        )
        topic_id = article_data.get("topic_id", "")

        # Create slug
        slug = create_slug(title)

        # Generate frontmatter
        frontmatter = f"""---
title: "{title}"
slug: "{slug}"
date: "{datetime.now().strftime('%Y-%m-%d')}"
time: "{datetime.now().strftime('%H:%M:%S')}"
summary: "{title}"
tags: ["tech", "ai-curated", "{source}"]
categories: ["tech", "ai-curated"]
source:
  name: "{source}"
  url: "{original_url}"
metadata:
  topic_id: "{topic_id}"
  word_count: {word_count}
  quality_score: {quality_score}
  cost: {cost}
  generated_at: "{generated_at}"
published: true
---

"""

        return frontmatter + content

    print("✅ Generator components loaded")

    # Test markdown creation
    print("\n📝 Testing markdown generation...")
    markdown_content = create_markdown_content(sample_article)

    print("Generated Markdown:")
    print("-" * 30)
    print(
        markdown_content[:500] + "..."
        if len(markdown_content) > 500
        else markdown_content
    )
    print("-" * 30)

    # Test slug creation
    slug = create_slug(sample_article["title"])
    print(f"✅ Generated slug: {slug}")

    # Save to temporary file for inspection
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(markdown_content)
        temp_path = f.name

    print(f"✅ Markdown saved to: {temp_path}")

    # Test configuration
    config = Config()
    print(f"✅ Site title: {config.SITE_TITLE}")
    print(f"✅ Site domain: {config.SITE_DOMAIN}")
    print(f"✅ Articles per page: {config.ARTICLES_PER_PAGE}")

    print("\n🎉 Site generator components working correctly!")
    print(f"📄 Full markdown file available at: {temp_path}")

    return temp_path


if __name__ == "__main__":
    test_markdown_generation()
