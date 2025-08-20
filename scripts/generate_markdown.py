#!/usr/bin/env python3
"""
Markdown Generator for AI Content Farm

Converts pipeline output into markdown format suitable for headless CMS publishing.
"""

import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List


class MarkdownGenerator:
    """Generate markdown content from pipeline results."""

    def __init__(self, output_dir: str = "output/markdown"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_post_markdown(self, item: Dict[str, Any], rank: int = 1) -> str:
        """Generate markdown for a single content item."""

        # Extract key information
        title = item.get("title", "Untitled")
        clean_title = item.get("clean_title", title)
        source_url = item.get("source_url", "")
        content_type = item.get("content_type", "article")

        # Get enrichment data
        ai_summary = item.get("ai_summary", "Summary not available")
        topics = item.get("topics", [])
        sentiment = item.get("sentiment", "neutral")

        # Get scoring data
        final_score = item.get("final_score", 0)
        engagement_score = item.get("engagement_score", 0)

        # Get source metadata
        source_metadata = item.get("source_metadata", {})
        site_name = source_metadata.get("site_name", "Unknown Source")
        published_at = item.get("published_at", datetime.now(timezone.utc).isoformat())

        # Create slug from title
        slug = self._create_slug(clean_title)

        # Generate frontmatter
        frontmatter = self._generate_frontmatter(
            title=clean_title,
            slug=slug,
            summary=ai_summary,
            topics=topics,
            sentiment=sentiment,
            source_url=source_url,
            source_name=site_name,
            published_at=published_at,
            score=final_score,
            rank=rank,
            content_type=content_type,
        )

        # Generate main content
        content = self._generate_content(item)

        return f"{frontmatter}\n\n{content}"

    def _create_slug(self, title: str) -> str:
        """Create URL-safe slug from title."""
        # Convert to lowercase and replace spaces with hyphens
        slug = title.lower()
        # Remove special characters, keep only alphanumeric and hyphens
        slug = re.sub(r"[^a-z0-9\s-]", "", slug)
        # Replace spaces with hyphens
        slug = re.sub(r"\s+", "-", slug)
        # Remove multiple consecutive hyphens
        slug = re.sub(r"-+", "-", slug)
        # Remove leading/trailing hyphens
        slug = slug.strip("-")
        # Limit length
        return slug[:50]

    def _generate_frontmatter(self, **kwargs) -> str:
        """Generate YAML frontmatter for the post."""

        # Parse published date
        try:
            pub_date = datetime.fromisoformat(
                kwargs["published_at"].replace("Z", "+00:00")
            )
            date_str = pub_date.strftime("%Y-%m-%d")
            time_str = pub_date.strftime("%H:%M:%S")
        except:
            date_str = datetime.now().strftime("%Y-%m-%d")
            time_str = datetime.now().strftime("%H:%M:%S")

        frontmatter = f"""---
title: "{kwargs['title']}"
slug: "{kwargs['slug']}"
date: "{date_str}"
time: "{time_str}"
summary: "{kwargs['summary'][:200]}..."
excerpt: "{kwargs['summary'][:150]}..."
tags: {json.dumps(kwargs['topics'][:5])}
categories: ["tech", "ai-curated"]
sentiment: "{kwargs['sentiment']}"
source:
  name: "{kwargs['source_name']}"
  url: "{kwargs['source_url']}"
metadata:
  ai_score: {kwargs['score']:.3f}
  rank: {kwargs['rank']}
  content_type: "{kwargs['content_type']}"
  generated_at: "{datetime.now(timezone.utc).isoformat()}"
published: true
featured: {str(kwargs['rank'] <= 3).lower()}
---"""

        return frontmatter

    def _generate_content(self, item: Dict[str, Any]) -> str:
        """Generate the main markdown content."""

        title = item.get("clean_title", "Untitled")
        ai_summary = item.get("ai_summary", "Summary not available")
        source_url = item.get("source_url", "")
        source_metadata = item.get("source_metadata", {})
        site_name = source_metadata.get("site_name", "Unknown Source")

        # Get additional content if available
        original_content = item.get("content", "")
        topics = item.get("topics", [])
        sentiment = item.get("sentiment", "neutral")

        content = f"""# {title}

## Summary

{ai_summary}

## Key Information

"""

        if topics:
            content += f"**Topics:** {', '.join(topics[:5])}\n\n"

        content += f"**Sentiment:** {sentiment.title()}\n\n"

        if original_content and len(original_content.strip()) > 0:
            content += f"""## Original Content

{original_content[:500]}{"..." if len(original_content) > 500 else ""}

"""

        content += f"""## Source

This content was curated from [{site_name}]({source_url}).

**Read the full article:** [{source_url}]({source_url})

---

*This post was generated by AI Content Farm - an automated content curation system.*
"""

        return content

    def generate_index_markdown(
        self, items: List[Dict[str, Any]], title: str = "AI Curated Tech News"
    ) -> str:
        """Generate an index/summary markdown file."""

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        content = f"""---
title: "{title}"
date: "{datetime.now().strftime('%Y-%m-%d')}"
type: "index"
generated_at: "{datetime.now(timezone.utc).isoformat()}"
total_items: {len(items)}
---

# {title}

*Generated on {timestamp}*

## Featured Stories ({len(items)} articles)

"""

        for i, item in enumerate(items, 1):
            title = item.get("clean_title", "Untitled")
            slug = self._create_slug(title)
            ai_summary = item.get("ai_summary", "No summary available")
            source_metadata = item.get("source_metadata", {})
            site_name = source_metadata.get("site_name", "Unknown")
            score = item.get("final_score", 0)

            content += f"""### {i}. [{title}](./{slug}.md)

**Source:** {site_name} | **AI Score:** {score:.3f}

{ai_summary[:150]}...

---

"""

        content += f"""
## About This Curation

This index contains {len(items)} articles automatically curated and ranked by our AI content pipeline. Articles are sourced from leading technology publications and processed through:

- **Content Processing**: Normalization and cleaning
- **AI Enrichment**: Summary generation and topic classification  
- **Smart Ranking**: Multi-factor scoring based on relevance and quality

*Last updated: {timestamp}*
"""

        return content

    def process_pipeline_output(
        self, pipeline_file: str, output_prefix: str = None
    ) -> Dict[str, str]:
        """Process a complete pipeline output file and generate markdown files."""

        # Load pipeline output
        with open(pipeline_file, "r") as f:
            data = json.load(f)

        ranked_items = data.get("ranked_items", [])
        metadata = data.get("metadata", {})

        if not ranked_items:
            raise ValueError("No ranked items found in pipeline output")

        # Generate timestamp for filenames if no prefix provided
        if output_prefix is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_prefix = f"curated_{timestamp}"

        generated_files = {}

        # Generate individual post markdown files
        for i, item in enumerate(ranked_items, 1):
            title = item.get("clean_title", f"Article {i}")
            slug = self._create_slug(title)

            markdown_content = self.generate_post_markdown(item, rank=i)

            # Save individual post
            post_filename = f"{output_prefix}_{slug}.md"
            post_path = os.path.join(self.output_dir, post_filename)

            with open(post_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)

            generated_files[f"post_{i}"] = post_path

        # Generate index file
        index_content = self.generate_index_markdown(
            ranked_items,
            title=f"AI Curated Tech News - {datetime.now().strftime('%B %d, %Y')}",
        )

        index_filename = f"{output_prefix}_index.md"
        index_path = os.path.join(self.output_dir, index_filename)

        with open(index_path, "w", encoding="utf-8") as f:
            f.write(index_content)

        generated_files["index"] = index_path

        return generated_files


def main():
    """Main function to process the latest pipeline output."""

    # Find the latest web pipeline test file
    output_dir = "/workspaces/ai-content-farm/output"
    files = [
        f
        for f in os.listdir(output_dir)
        if f.startswith("web_pipeline_test_") and f.endswith(".json")
    ]

    if not files:
        print("❌ No pipeline output files found")
        return

    # Get the latest file
    latest_file = sorted(files)[-1]
    file_path = os.path.join(output_dir, latest_file)

    print(f"📄 Processing pipeline output: {latest_file}")

    # Generate markdown
    generator = MarkdownGenerator()

    try:
        generated_files = generator.process_pipeline_output(file_path)

        print(f"\n✅ Generated {len(generated_files)} markdown files:")
        for file_type, file_path in generated_files.items():
            rel_path = os.path.relpath(file_path, "/workspaces/ai-content-farm")
            print(f"   📝 {file_type}: {rel_path}")

        print(f"\n🚀 Ready for headless CMS publishing!")
        print(f"📁 Markdown files location: output/markdown/")

        # Show sample of index file
        if "index" in generated_files:
            with open(generated_files["index"], "r") as f:
                preview = f.read()[:500]
            print(f"\n📖 Index file preview:")
            print("---")
            print(preview + "...")
            print("---")

    except Exception as e:
        print(f"❌ Error generating markdown: {e}")


if __name__ == "__main__":
    main()
