#!/usr/bin/env python3
"""
Collection Template Manager Script

Easy utility for enabling/disabling content sources in collection templates.
Supports both local JSON files and Azure Blob Storage templates.

Usage:
    # List current source status
    python manage_templates.py --list

    # Enable all Reddit sources
    python manage_templates.py --enable reddit

    # Disable all RSS sources
    python manage_templates.py --disable rss

    # Enable specific source by index
    python manage_templates.py --enable-source 0

    # Show detailed template structure
    python manage_templates.py --show-template default.json
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List

# Add project libs to path
sys.path.append(str(Path(__file__).parent.parent / "libs"))

try:
    from blob_storage import BlobStorageClient

    BLOB_AVAILABLE = True
except ImportError:
    BLOB_AVAILABLE = False
    print("Warning: Blob storage not available, local mode only")


class TemplateManager:
    """Manages collection template source enable/disable operations."""

    def __init__(self, template_path: str = None, use_blob: bool = False):
        self.template_path = template_path or "collection-templates/default.json"
        self.use_blob = use_blob and BLOB_AVAILABLE
        self.blob_client = BlobStorageClient() if self.use_blob else None

    async def load_template(self) -> Dict:
        """Load template from local file or blob storage."""
        if self.use_blob:
            try:
                content = await self.blob_client.download_text(
                    container_name="prompts", blob_name=self.template_path
                )
                return json.loads(content)
            except Exception as e:
                print(f"Error loading from blob storage: {e}")
                return {}
        else:
            # Local file mode
            local_path = Path(__file__).parent.parent / self.template_path
            if local_path.exists():
                with open(local_path, "r") as f:
                    return json.load(f)
            else:
                print(f"Template file not found: {local_path}")
                return {}

    async def save_template(self, template: Dict) -> bool:
        """Save template to local file or blob storage."""
        try:
            if self.use_blob:
                await self.blob_client.upload_text(
                    container_name="prompts",
                    blob_name=self.template_path,
                    content=json.dumps(template, indent=4),
                )
                print(f"✅ Template saved to blob storage: {self.template_path}")
            else:
                # Local file mode
                local_path = Path(__file__).parent.parent / self.template_path
                local_path.parent.mkdir(parents=True, exist_ok=True)
                with open(local_path, "w") as f:
                    json.dump(template, f, indent=4)
                print(f"✅ Template saved locally: {local_path}")
            return True
        except Exception as e:
            print(f"❌ Error saving template: {e}")
            return False

    def list_sources(self, template: Dict) -> None:
        """List all sources with their enabled status."""
        sources = template.get("sources", [])

        print(f"\n📋 Template: {self.template_path}")
        print(f"🔍 Found {len(sources)} source configurations:\n")

        for i, source in enumerate(sources):
            enabled = source.get("enabled", True)
            source_type = source.get("type", "unknown")

            # Handle legacy _disabled_* format
            if any(key.startswith("_disabled_") for key in source.keys()):
                enabled = False
                source_type = "legacy-disabled"

            status_icon = "✅" if enabled else "❌"
            comment = source.get("_comment", "")

            print(f"  [{i:2d}] {status_icon} {source_type.upper()}")

            if source_type == "reddit":
                subreddits = source.get("subreddits", [])
                limit = source.get("limit", 0)
                print(f"       └─ {len(subreddits)} subreddits, limit: {limit}")

            elif source_type == "rss":
                websites = source.get("websites", [])
                limit = source.get("limit", 0)
                print(f"       └─ {len(websites)} feeds, limit: {limit}")

            if comment:
                print(f"       💬 {comment}")
            print()

    async def toggle_sources_by_type(
        self, template: Dict, source_type: str, enabled: bool
    ) -> Dict:
        """Enable or disable all sources of a specific type."""
        sources = template.get("sources", [])
        modified_count = 0

        for source in sources:
            # Handle legacy _disabled_* format by converting to new format
            if any(key.startswith("_disabled_") for key in source.keys()):
                # Find the nested source definition
                for key, value in source.items():
                    if key.startswith("_disabled_") and isinstance(value, dict):
                        if value.get("type") == source_type:
                            # Convert to new format
                            source.clear()
                            source.update(value)
                            source["enabled"] = enabled
                            modified_count += 1
                            break
            elif source.get("type") == source_type:
                source["enabled"] = enabled
                modified_count += 1

        action = "enabled" if enabled else "disabled"
        print(f"✅ {action.capitalize()} {modified_count} {source_type} sources")
        return template

    async def toggle_source_by_index(
        self, template: Dict, index: int, enabled: bool
    ) -> Dict:
        """Enable or disable a specific source by index."""
        sources = template.get("sources", [])

        if 0 <= index < len(sources):
            source = sources[index]

            # Handle legacy _disabled_* format
            if any(key.startswith("_disabled_") for key in source.keys()):
                # Convert to new format
                for key, value in source.items():
                    if key.startswith("_disabled_") and isinstance(value, dict):
                        source.clear()
                        source.update(value)
                        break

            source["enabled"] = enabled
            action = "enabled" if enabled else "disabled"
            source_type = source.get("type", "unknown")
            print(f"✅ {action.capitalize()} source {index} ({source_type})")
        else:
            print(f"❌ Invalid source index: {index} (valid range: 0-{len(sources)-1})")

        return template


async def main():
    parser = argparse.ArgumentParser(
        description="Manage collection template source enable/disable status",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --list                    # Show all sources with status
  %(prog)s --enable reddit           # Enable all Reddit sources
  %(prog)s --disable rss             # Disable all RSS sources
  %(prog)s --enable-source 0         # Enable source at index 0
  %(prog)s --disable-source 2        # Disable source at index 2
  %(prog)s --template tech.json      # Use different template file
  %(prog)s --blob --list             # Use blob storage mode
        """,
    )

    parser.add_argument(
        "--template",
        default="collection-templates/default.json",
        help="Template file path (default: collection-templates/default.json)",
    )
    parser.add_argument(
        "--blob", action="store_true", help="Use blob storage instead of local files"
    )
    parser.add_argument(
        "--list", action="store_true", help="List all sources with their status"
    )
    parser.add_argument(
        "--enable",
        metavar="TYPE",
        help="Enable all sources of specified type (reddit, rss, web)",
    )
    parser.add_argument(
        "--disable",
        metavar="TYPE",
        help="Disable all sources of specified type (reddit, rss, web)",
    )
    parser.add_argument(
        "--enable-source",
        type=int,
        metavar="INDEX",
        help="Enable source at specific index",
    )
    parser.add_argument(
        "--disable-source",
        type=int,
        metavar="INDEX",
        help="Disable source at specific index",
    )

    args = parser.parse_args()

    # Validate arguments
    if not any(
        [
            args.list,
            args.enable,
            args.disable,
            args.enable_source is not None,
            args.disable_source is not None,
        ]
    ):
        parser.print_help()
        return

    # Initialize manager
    manager = TemplateManager(template_path=args.template, use_blob=args.blob)

    # Load template
    template = await manager.load_template()
    if not template:
        print("❌ Failed to load template")
        return

    # Execute requested action
    if args.list:
        manager.list_sources(template)
        return

    # Modification actions
    modified = False

    if args.enable:
        template = await manager.toggle_sources_by_type(template, args.enable, True)
        modified = True

    if args.disable:
        template = await manager.toggle_sources_by_type(template, args.disable, False)
        modified = True

    if args.enable_source is not None:
        template = await manager.toggle_source_by_index(
            template, args.enable_source, True
        )
        modified = True

    if args.disable_source is not None:
        template = await manager.toggle_source_by_index(
            template, args.disable_source, False
        )
        modified = True

    # Save if modified
    if modified:
        await manager.save_template(template)
        print("\n📋 Updated source status:")
        manager.list_sources(template)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
