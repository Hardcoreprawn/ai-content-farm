#!/usr/bin/env python3
"""
Headless CMS Integration Example

Demonstrates how to integrate the AI Content Farm output with popular headless CMS platforms.
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path


class HeadlessCMSPublisher:
    """Example publisher for various headless CMS platforms."""

    def __init__(self, cms_type: str = "strapi"):
        self.cms_type = cms_type.lower()
        self.supported_cms = ["strapi", "contentful", "ghost", "sanity", "netlify-cms"]

        if self.cms_type not in self.supported_cms:
            raise ValueError(
                f"Unsupported CMS: {cms_type}. Supported: {self.supported_cms}"
            )

    def prepare_for_strapi(self, manifest_file: str):
        """Prepare content for Strapi CMS."""
        print(f"🎯 Preparing content for Strapi CMS...")

        with open(manifest_file, "r") as f:
            manifest = json.load(f)

        # Create Strapi import structure
        strapi_dir = "output/cms/strapi"
        os.makedirs(strapi_dir, exist_ok=True)

        # Convert to Strapi collection format
        strapi_articles = []

        for post in manifest["posts"]:
            post_file = post["file"]

            # Read the markdown file
            with open(post_file, "r") as f:
                content = f.read()

            # Extract frontmatter and content
            if content.startswith("---"):
                parts = content.split("---", 2)
                frontmatter_text = parts[1]
                body_content = parts[2].strip()

                # Parse frontmatter (simple parsing for demo)
                frontmatter = {}
                for line in frontmatter_text.strip().split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        frontmatter[key.strip()] = value.strip().strip('"')

                # Helper function to safely get nested values
                def safe_get(data, *keys):
                    for key in keys:
                        if isinstance(data, dict) and key in data:
                            data = data[key]
                        else:
                            return None
                    return data

                # Parse complex fields safely
                source_url = ""
                ai_score = 0.0

                if "source" in frontmatter:
                    source_str = frontmatter["source"]
                    if "url:" in source_str:
                        # Extract URL from source string
                        for line in source_str.split("\n"):
                            if "url:" in line:
                                source_url = line.split(":", 1)[1].strip().strip('"')

                if "metadata" in frontmatter:
                    metadata_str = frontmatter["metadata"]
                    if "ai_score:" in metadata_str:
                        # Extract AI score from metadata string
                        for line in metadata_str.split("\n"):
                            if "ai_score:" in line:
                                try:
                                    ai_score = float(line.split(":", 1)[1].strip())
                                except (ValueError, IndexError):
                                    ai_score = 0.0

                # Create Strapi article object
                article = {
                    "title": frontmatter.get("title", "Untitled"),
                    "slug": frontmatter.get("slug", "untitled"),
                    "content": body_content,
                    "excerpt": frontmatter.get("excerpt", ""),
                    "published_at": frontmatter.get(
                        "date", datetime.now().strftime("%Y-%m-%d")
                    ),
                    "status": "published",
                    "featured": frontmatter.get("featured", "false").lower() == "true",
                    "categories": ["AI Curated", "Technology"],
                    "tags": frontmatter.get("tags", "[]"),
                    "source_url": source_url,
                    "ai_score": ai_score,
                    "content_type": "ai-curated",
                }

                strapi_articles.append(article)

        # Save Strapi import file
        strapi_import = os.path.join(strapi_dir, "ai_curated_articles.json")
        with open(strapi_import, "w") as f:
            json.dump(
                {"version": 2, "data": {"api::article.article": strapi_articles}},
                f,
                indent=2,
            )

        print(f"✅ Strapi import file created: {strapi_import}")
        return strapi_import

    def prepare_for_ghost(self, manifest_file: str):
        """Prepare content for Ghost CMS."""
        print(f"👻 Preparing content for Ghost CMS...")

        ghost_dir = "output/cms/ghost"
        os.makedirs(ghost_dir, exist_ok=True)

        # Copy markdown files for Ghost import
        with open(manifest_file, "r") as f:
            manifest = json.load(f)

        ghost_posts = []

        for post in manifest["posts"]:
            post_file = post["file"]

            # Read markdown content
            with open(post_file, "r") as f:
                content = f.read()

            # Copy to Ghost directory with proper naming
            filename = os.path.basename(post_file)
            ghost_file = os.path.join(ghost_dir, filename)

            with open(ghost_file, "w") as f:
                f.write(content)

            ghost_posts.append(ghost_file)

        # Create Ghost import instructions
        instructions = f"""
# Ghost CMS Import Instructions

1. Copy all markdown files from {ghost_dir}/ to your Ghost content directory
2. Use Ghost's built-in markdown importer or Ghost CLI:
   - `ghost import --path {ghost_dir}`
3. All posts include proper frontmatter for Ghost compatibility

Files ready for import:
{chr(10).join(f'- {os.path.basename(f)}' for f in ghost_posts)}
        """

        with open(os.path.join(ghost_dir, "IMPORT_INSTRUCTIONS.md"), "w") as f:
            f.write(instructions)

        print(f"✅ Ghost files prepared in: {ghost_dir}")
        return ghost_dir

    def prepare_for_netlify_cms(self, manifest_file: str):
        """Prepare content for Netlify CMS."""
        print(f"🌐 Preparing content for Netlify CMS...")

        netlify_dir = "output/cms/netlify"
        posts_dir = os.path.join(netlify_dir, "content/posts")
        os.makedirs(posts_dir, exist_ok=True)

        with open(manifest_file, "r") as f:
            manifest = json.load(f)

        # Copy and rename files for Netlify CMS structure
        for post in manifest["posts"]:
            post_file = post["file"]

            # Read and modify content for Netlify CMS
            with open(post_file, "r") as f:
                content = f.read()

            # Extract date from frontmatter for filename
            if "date:" in content:
                date_line = [line for line in content.split("\n") if "date:" in line][0]
                date = date_line.split(":", 1)[1].strip().strip('"')
            else:
                date = datetime.now().strftime("%Y-%m-%d")

            # Create Netlify CMS filename
            slug = os.path.basename(post_file).replace(".md", "")
            netlify_filename = f"{date}-{slug}.md"
            netlify_file = os.path.join(posts_dir, netlify_filename)

            with open(netlify_file, "w") as f:
                f.write(content)

        # Create Netlify CMS config
        config = {
            "backend": {"name": "git-gateway", "branch": "main"},
            "media_folder": "static/images",
            "public_folder": "/images",
            "collections": [
                {
                    "name": "posts",
                    "label": "AI Curated Posts",
                    "folder": "content/posts",
                    "create": True,
                    "slug": "{{year}}-{{month}}-{{day}}-{{slug}}",
                    "fields": [
                        {"label": "Title", "name": "title", "widget": "string"},
                        {"label": "Date", "name": "date", "widget": "datetime"},
                        {"label": "Summary", "name": "summary", "widget": "text"},
                        {"label": "Tags", "name": "tags", "widget": "list"},
                        {"label": "Featured", "name": "featured", "widget": "boolean"},
                        {"label": "Body", "name": "body", "widget": "markdown"},
                    ],
                }
            ],
        }

        config_file = os.path.join(netlify_dir, "admin/config.yml")
        os.makedirs(os.path.dirname(config_file), exist_ok=True)

        import yaml

        with open(config_file, "w") as f:
            yaml.dump(config, f, default_flow_style=False)

        print(f"✅ Netlify CMS structure created in: {netlify_dir}")
        return netlify_dir


def demonstrate_cms_integration():
    """Demonstrate CMS integration with the latest content."""

    print("🚀 AI Content Farm - Headless CMS Integration Demo")
    print("=" * 60)

    # Find the latest manifest
    manifest_files = list(Path("output/markdown").glob("publishing_manifest.json"))

    if not manifest_files:
        print("❌ No publishing manifest found. Run process_live_content.py first.")
        return

    # Use the manifest (there should be only one)
    manifest_file = str(manifest_files[0])
    print(f"📋 Using manifest: {manifest_file}")

    # Initialize publisher
    publisher = HeadlessCMSPublisher()

    print(f"\n🔄 Preparing content for multiple CMS platforms...")

    # Prepare for different CMS platforms
    results = {}

    try:
        # Strapi
        results["strapi"] = publisher.prepare_for_strapi(manifest_file)

        # Ghost
        publisher.cms_type = "ghost"
        results["ghost"] = publisher.prepare_for_ghost(manifest_file)

        # Netlify CMS
        publisher.cms_type = "netlify-cms"
        results["netlify"] = publisher.prepare_for_netlify_cms(manifest_file)

        print(f"\n✅ Content prepared for {len(results)} CMS platforms:")
        for cms, path in results.items():
            rel_path = path.replace("/workspaces/ai-content-farm/", "")
            print(f"   📦 {cms.title()}: {rel_path}")

        # Create summary
        summary = {
            "integration_summary": {
                "prepared_at": datetime.now().isoformat(),
                "cms_platforms": list(results.keys()),
                "total_articles": len(json.load(open(manifest_file))["posts"]),
                "ready_for_publishing": True,
            },
            "cms_outputs": results,
        }

        summary_file = "output/cms/integration_summary.json"
        os.makedirs(os.path.dirname(summary_file), exist_ok=True)

        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)

        print(f"\n📊 Integration Summary:")
        print(f"   🎯 CMS Platforms: {len(results)}")
        print(
            f"   📰 Articles Ready: {summary['integration_summary']['total_articles']}"
        )
        print(
            f"   📋 Summary File: {summary_file.replace('/workspaces/ai-content-farm/', '')}"
        )

        print(f"\n💡 Next Steps:")
        print(f"   1. Choose your preferred CMS platform")
        print(f"   2. Follow the import instructions in each CMS directory")
        print(f"   3. Set up automated publishing workflows")
        print(f"   4. Configure content scheduling and distribution")

    except Exception as e:
        print(f"❌ Error during CMS preparation: {e}")


if __name__ == "__main__":
    # Install pyyaml if needed
    try:
        import yaml
    except ImportError:
        print("Installing PyYAML for Netlify CMS config...")
        os.system("pip install PyYAML")
        import yaml

    demonstrate_cms_integration()
