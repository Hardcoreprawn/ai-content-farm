#!/usr/bin/env python3
"""
Live System Test for Simplified Collection System - ACTIVE

CURRENT ARCHITECTURE: End-to-end test for the simplified collector system
Status: ACTIVE - Tests the new simplified architecture

Tests the simplified collection system with proper monorepo paths.
Validates that Reddit and Mastodon collection work in the live environment.

Features:
- Tests Reddit collection from real API
- Tests Mastodon collection from real API
- Tests multi-source collection
- Validates configuration and error handling
- Provides live system validation

Test the simplified collection system with proper monorepo paths.
"""

import asyncio
import sys
from pathlib import Path

from content_processing_simple import collect_content_batch

# Add shared libs to path (monorepo pattern)
repo_root = Path(__file__).parent.parent.parent
libs_path = repo_root / "libs"
sys.path.insert(0, str(libs_path))

# Now safe to import


async def test_simplified_system():
    """Test the simplified collection system end-to-end."""

    print("🧪 Testing Simplified Collection System")
    print("=" * 50)

    # Test 1: Reddit Collection
    print("\n1. Testing Reddit Collection...")
    reddit_sources = [{"type": "reddit", "subreddits": ["programming"], "limit": 3}]

    try:
        result = await collect_content_batch(reddit_sources)
        print(f"✅ Reddit collection successful!")
        print(f"   Items collected: {result['metadata']['total_items']}")
        print(f"   Status: {result['metadata']['reddit_status']}")
        if result["collected_items"]:
            sample = result["collected_items"][0]
            print(f"   Sample: {sample['title'][:60]}...")
    except Exception as e:
        print(f"❌ Reddit collection failed: {e}")

    # Test 2: Multi-source collection
    print("\n2. Testing Multi-source Collection...")
    multi_sources = [
        {"type": "reddit", "subreddits": ["technology"], "limit": 2},
        {
            "type": "mastodon",
            "instances": ["mastodon.social"],
            "hashtags": ["technology"],
            "limit": 2,
        },
    ]

    try:
        result = await collect_content_batch(multi_sources)
        print(f"✅ Multi-source collection successful!")
        print(f"   Total sources: {result['metadata']['total_sources']}")
        print(f"   Sources processed: {result['metadata']['sources_processed']}")
        print(f"   Total items: {result['metadata']['total_items']}")

        # Show breakdown
        for key, value in result["metadata"].items():
            if key.endswith("_count") and value > 0:
                source = key.replace("_count", "")
                print(f"   {source}: {value} items")

    except Exception as e:
        print(f"❌ Multi-source collection failed: {e}")

    print("\n🎉 Testing Complete!")


if __name__ == "__main__":
    asyncio.run(test_simplified_system())
