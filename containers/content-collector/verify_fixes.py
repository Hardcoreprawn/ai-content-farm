#!/usr/bin/env python3
"""
Manual verification script for content-collector specific fixes
"""

import os
import sys

# Add current directory and parent for proper imports
sys.path.insert(0, ".")
sys.path.insert(0, "../..")


def test_reddit_collector_info_fix():
    """Test that Reddit collector info includes authentication_status and status fields."""
    print("Testing Reddit collector info fix...")

    try:
        from source_collectors import SourceCollectorFactory

        info = SourceCollectorFactory.get_reddit_collector_info()
        print(f"Reddit collector info: {info}")

        # Check for new fields
        assert "authentication_status" in info, "Missing authentication_status field"
        assert "status" in info, "Missing status field"

        # Verify values are correct
        assert info["authentication_status"] in ["authenticated", "unauthenticated"]
        assert info["status"] in ["available", "limited"]

        print("✅ Reddit collector info fix works correctly")
        return True

    except Exception as e:
        print(f"❌ Reddit collector info test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_sources_endpoint_response():
    """Test that sources endpoint includes Mastodon and has consistent format."""
    print("Testing sources endpoint response...")

    try:
        from fastapi.testclient import TestClient
        from main import app

        client = TestClient(app)
        response = client.get("/sources")

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = response.json()
        print(f"Sources response structure: {list(data.keys())}")

        # Check response format consistency
        assert "status" in data
        assert "message" in data
        assert "data" in data
        assert "errors" in data
        assert "metadata" in data

        # Verify errors is empty list, not null
        assert data["errors"] == []
        assert data["errors"] is not None

        # Check for Mastodon in sources
        sources = data["data"]["sources"]
        print(f"Available sources: {list(sources.keys())}")

        assert "mastodon" in sources, "Mastodon source not found"

        mastodon = sources["mastodon"]
        assert mastodon["type"] == "mastodon"
        assert "Mastodon" in mastodon["description"]

        print("✅ Sources endpoint fix works correctly")
        return True

    except Exception as e:
        print(f"❌ Sources endpoint test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run verification tests."""
    print("=== Content-Collector API Fixes Verification ===\n")

    tests = [
        test_reddit_collector_info_fix,
        test_sources_endpoint_response,
    ]

    results = []
    for test in tests:
        results.append(test())
        print()

    print("=== Summary ===")
    passed = sum(results)
    total = len(results)
    print(f"Tests passed: {passed}/{total}")

    if passed == total:
        print("🎉 All fixes working correctly!")
        return 0
    else:
        print("⚠️  Some fixes need attention")
        return 1


if __name__ == "__main__":
    sys.exit(main())
