#!/usr/bin/env python3
"""
Integration test: Generate markdown from real Azure content.
This connects to the actual processed content and creates markdown.
"""

import json
import os
import sys
import tempfile
from datetime import datetime, timezone

from libs.blob_storage import BlobStorageClient

# Test with our real Azure environment
os.environ["AZURE_STORAGE_CONNECTION_STRING"] = (
    "DefaultEndpointsProtocol=https;AccountName=aicontentprodst8y5ne5;AccountKey=fake;EndpointSuffix=core.windows.net"
)

sys.path.append("/workspaces/ai-content-farm")


def test_real_content_to_markdown():
    """Test converting real processed content to markdown."""

    print("🔗 Testing with Real Azure Content")
    print("=" * 50)

    # Get the article we examined earlier
    article_filename = "20250901_172932_reddit_1n4boz5.json"

    try:
        # Use Azure CLI auth instead of connection string
        blob_client = BlobStorageClient()

        print(f"📥 Downloading article: {article_filename}")

        # Download the content using Azure CLI auth
        from azure.identity import AzureCliCredential
        from azure.storage.blob import BlobServiceClient

        credential = AzureCliCredential()
        service_client = BlobServiceClient(
            account_url="https://aicontentprodst8y5ne5.blob.core.windows.net",
            credential=credential,
        )

        container_client = service_client.get_container_client("processed-content")
        blob_client = container_client.get_blob_client(article_filename)

        content = blob_client.download_blob().readall().decode("utf-8")
        article_data = json.loads(content)

        print("✅ Article downloaded successfully")
        print(f"📰 Title: {article_data['title']}")
        print(f"📊 Word count: {article_data['word_count']}")
        print(f"💰 Cost: ${article_data['cost']}")

        # Generate markdown using our generator functions
        markdown_content = create_markdown_from_real_content(article_data)

        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"/tmp/jablab_article_{timestamp}.md"

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        print(f"✅ Markdown generated: {output_path}")
        print("\n📄 Generated Markdown Preview:")
        print("-" * 40)
        print(
            markdown_content[:600] + "..."
            if len(markdown_content) > 600
            else markdown_content
        )
        print("-" * 40)

        # Also create an HTML preview
        html_content = create_html_preview(article_data, markdown_content)
        html_path = f"/tmp/jablab_article_{timestamp}.html"

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"✅ HTML preview generated: {html_path}")

        return output_path, html_path

    except Exception as e:
        print(f"❌ Error: {e}")
        return None, None


def create_markdown_from_real_content(article_data):
    """Create markdown content from real article data."""

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
    import re

    def create_slug(title: str) -> str:
        slug = title.lower()
        slug = re.sub(r"[^a-z0-9\s-]", "", slug)
        slug = re.sub(r"\s+", "-", slug)
        slug = re.sub(r"-+", "-", slug)
        slug = slug.strip("-")
        return slug[:50]

    slug = create_slug(title)

    # Enhanced frontmatter for JAMStack
    frontmatter = f"""---
title: "{title}"
slug: "{slug}"
date: "{datetime.now().strftime('%Y-%m-%d')}"
time: "{datetime.now().strftime('%H:%M:%S')}"
summary: "{title[:150]}..."
excerpt: "{title[:100]}..."
tags: ["tech", "ai-curated", "{source}", "cybersecurity", "news"]
categories: ["tech", "ai-curated"]
layout: "article"
source:
  name: "{source}"
  url: "{original_url}"
  domain: "{original_url.split('/')[2] if '://' in original_url else 'unknown'}"
seo:
  description: "{title}"
  keywords: "cybersecurity, technology news, AI curated, {source}"
metadata:
  topic_id: "{topic_id}"
  word_count: {word_count}
  quality_score: {quality_score}
  generation_cost: {cost}
  generated_at: "{generated_at}"
  reading_time: "{max(1, word_count // 200)} min read"
  ai_model: "gpt-35-turbo"
published: true
featured: {quality_score > 0.7}
priority: {int(quality_score * 10)}
---

"""

    return frontmatter + content


def create_html_preview(article_data, markdown_content):
    """Create a simple HTML preview of the article."""

    title = article_data.get("title", "Untitled")

    # Simple markdown to HTML conversion
    content_html = markdown_content.split("---", 2)[2].strip()
    content_html = content_html.replace("**", "<strong>").replace("**", "</strong>")
    content_html = content_html.replace("\n\n", "</p><p>")
    content_html = f"<p>{content_html}</p>"

    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - JabLab Tech News</title>
    <style>
        body {{
            font-family: system-ui, -apple-system, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
            line-height: 1.6;
            color: #1e293b;
        }}
        h1 {{ color: #2563eb; margin-bottom: 1rem; }}
        .meta {{
            background: #f8fafc;
            padding: 1rem;
            border-radius: 8px;
            margin: 1rem 0;
            font-size: 0.9rem;
            color: #64748b;
        }}
        .content {{ font-size: 1.1rem; margin: 2rem 0; }}
        .footer {{
            border-top: 1px solid #e2e8f0;
            padding-top: 1rem;
            margin-top: 2rem;
            font-size: 0.9rem;
            color: #64748b;
        }}
        strong {{ color: #1e293b; }}
    </style>
</head>
<body>
    <header>
        <h1>{title}</h1>
        <div class="meta">
            <strong>Source:</strong> {article_data.get('source', 'Unknown')}<br>
            <strong>Word Count:</strong> {article_data.get('word_count', 0)} words<br>
            <strong>Quality Score:</strong> {int(article_data.get('quality_score', 0) * 100)}%<br>
            <strong>Generation Cost:</strong> ${article_data.get('cost', 0):.6f}<br>
            <strong>Generated:</strong> {article_data.get('generated_at', 'Unknown')}
        </div>
    </header>

    <main class="content">
        {content_html}
    </main>

    <footer class="footer">
        <p><strong>About this article:</strong> This content was automatically generated by AI Content Farm using GPT-3.5-turbo.
        It represents an AI interpretation of technology news and should be verified against original sources.</p>
        <p><strong>Original Source:</strong> <a href="{article_data.get('original_url', '#')}" target="_blank">{article_data.get('original_url', 'Not available')}</a></p>
    </footer>
</body>
</html>"""

    return html_template


if __name__ == "__main__":
    markdown_path, html_path = test_real_content_to_markdown()

    if markdown_path and html_path:
        print(f"\n🎉 Success! Files generated:")
        print(f"📝 Markdown: {markdown_path}")
        print(f"🌐 HTML Preview: {html_path}")
        print(f"\n💡 You can open the HTML file in a browser to see how it looks!")
    else:
        print("\n❌ Generation failed")
