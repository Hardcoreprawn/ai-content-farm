#!/usr/bin/env python3
"""
Quick verification script for image support in markdown generation.

This script tests the complete image pipeline:
1. Generate frontmatter with images
2. Render markdown template
3. Verify images appear in output
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

from markdown_generation import prepare_frontmatter
from markdown_generator import create_jinja_environment, generate_markdown_content
from models import ArticleMetadata

# Add containers to path
sys.path.insert(0, str(Path(__file__).parent / "containers" / "markdown-generator"))


def test_image_pipeline():
    """Test complete image pipeline."""
    print("🔍 Testing Image Support Pipeline")
    print("=" * 60)

    # Test 1: Frontmatter generation with images
    print("\n1️⃣  Testing frontmatter generation with images...")
    frontmatter = prepare_frontmatter(
        title="AI Breakthrough in Quantum Computing",
        source="reddit",
        original_url="https://reddit.com/r/technology/post",
        generated_at=datetime.now(timezone.utc).isoformat() + "Z",
        format="hugo",
        author="Jane Doe",
        hero_image="https://images.unsplash.com/photo-1526374965328-7f5ae4e8cfb6?w=1080&q=80",
        image_alt="Quantum computer processor with blue lights",
        image_credit="Photo by Author Name on Unsplash",
        image_color="#1a1a2e",
        tags=["quantum", "ai", "computing"],
    )

    print("✅ Frontmatter generated:")
    print(frontmatter)
    print("\n" + "-" * 60)

    # Verify frontmatter contains cover image
    if "cover:" in frontmatter and "image:" in frontmatter:
        print("✅ Cover image found in frontmatter")
    else:
        print("❌ ERROR: Cover image NOT found in frontmatter")
        return False

    if "caption:" in frontmatter:
        print("✅ Image caption found in frontmatter")
    else:
        print("❌ ERROR: Image caption NOT found in frontmatter")
        return False

    # Test 2: Template rendering with images
    print("\n2️⃣  Testing template rendering with images...")

    metadata = ArticleMetadata(
        title="AI Breakthrough in Quantum Computing",
        url="https://reddit.com/r/technology/post",
        source="reddit",
        author="Jane Doe",
        published_date=datetime.now(timezone.utc),
        tags=["quantum", "ai", "computing"],
        category="technology",
        hero_image="https://images.unsplash.com/photo-1526374965328-7f5ae4e8cfb6?w=1080&q=80",
        image_alt="Quantum computer processor with blue lights",
        image_credit="Photo by Author Name on Unsplash",
        image_color="#1a1a2e",
    )

    article_data = {
        "summary": "Scientists announce breakthrough in quantum error correction.",
        "content": "The breakthrough involves a new approach to quantum error correction...",
        "article_content": "## Introduction\n\nQuantum computers have long been hindered by error rates...",
        "key_points": [
            "Error rates reduced by 50%",
            "New quantum gate design",
            "Scalable to 1000+ qubits",
        ],
        "generated_at": datetime.now(timezone.utc).isoformat() + "Z",
        "source_metadata": {"source_url": "https://reddit.com/r/technology/post"},
    }

    # Create Jinja2 environment and generate markdown
    jinja_env = create_jinja_environment()
    markdown = generate_markdown_content(
        article_data, metadata, jinja_env, "default.md.j2"
    )

    print("✅ Markdown generated:")
    print(markdown)
    print("\n" + "-" * 60)

    # Test 3: Verify markdown structure
    print("\n3️⃣  Verifying markdown structure...")

    checks = [
        ("YAML frontmatter", "---" in markdown),
        ("Title in frontmatter", 'title: "AI Breakthrough' in markdown),
        ("Cover image in frontmatter", "cover:" in markdown and "image:" in markdown),
        ("Image alt text", "alt: Quantum computer processor" in markdown),
        ("Image credit", "caption: Photo by Author Name on Unsplash" in markdown),
        ("Summary section", "## Summary" in markdown),
        ("Content section", "## Introduction" in markdown),
        ("Key Points section", "## Key Points" in markdown),
        ("Source attribution", "**Source:**" in markdown),
    ]

    all_passed = True
    for check_name, result in checks:
        status = "✅" if result else "❌"
        print(f"{status} {check_name}")
        if not result:
            all_passed = False

    # Test 4: Test without images (graceful degradation)
    print("\n4️⃣  Testing graceful degradation (no images)...")

    metadata_no_image = ArticleMetadata(
        title="Regular Article",
        url="https://example.com/article",
        source="rss",
        tags=["tech"],
        # No image fields
    )

    article_data_no_image = {
        "summary": "An interesting article about technology.",
        "content": "Content goes here.",
        "generated_at": datetime.now(timezone.utc).isoformat() + "Z",
    }

    markdown_no_image = generate_markdown_content(
        article_data_no_image, metadata_no_image, jinja_env, "default.md.j2"
    )

    no_image_checks = [
        ("Markdown generated without images", len(markdown_no_image) > 0),
        ("Title still present", "title:" in markdown_no_image),
        ("Content still present", "## Summary" in markdown_no_image),
        ("No broken cover references", "cover:" not in markdown_no_image),
    ]

    for check_name, result in no_image_checks:
        status = "✅" if result else "❌"
        print(f"{status} {check_name}")
        if not result:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All image pipeline tests PASSED!")
        return True
    else:
        print("❌ Some tests FAILED")
        return False


if __name__ == "__main__":
    success = test_image_pipeline()
    sys.exit(0 if success else 1)
