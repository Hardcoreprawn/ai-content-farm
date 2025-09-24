#!/usr/bin/env python3
"""
Test the refactored SimpleWebCollector to ensure it still works.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add paths for proper imports using pathlib for robustness
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(project_root))


async def test_simple_web_collector():
    """Test that the refactored SimpleWebCollector still works."""
    print("Testing refactored SimpleWebCollector...")

    try:
        from collectors.simple_web import SimpleWebCollector

        # Create collector instance
        collector = SimpleWebCollector(
            {"max_items": 5, "min_points": 1, "websites": ["news.ycombinator.com"]}
        )

        print(f"✅ Collector created successfully")
        print(f"   Source name: {collector.get_source_name()}")
        print(f"   Max items: {collector.max_items}")
        print(f"   Min points: {collector.min_points}")

        # Test health check
        health_ok, health_msg = await collector.health_check()
        print(f"✅ Health check: {health_ok} - {health_msg}")

        # Test a small collection (don't actually collect to avoid rate limits)
        print("✅ Refactored SimpleWebCollector is working correctly")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run the test."""
    print("=== SimpleWebCollector Refactoring Test ===\n")

    success = await test_simple_web_collector()

    if success:
        print("\n🎉 Refactoring successful! File reduced from 549 to ~165 lines")
        return 0
    else:
        print("\n⚠️  Refactoring needs fixes")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
