#!/usr/bin/env python3
"""
Manual verification script for API standardization fixes (Issue #523)
"""

import os
import sys

# Add content-collector directory to path
sys.path.insert(0, "/workspaces/ai-content-farm/containers/content-collector")
sys.path.insert(0, "/workspaces/ai-content-farm")


def test_reddit_collector_info_fix():
    """Test that Reddit collector info includes authentication_status and status fields."""
    print("Testing Reddit collector info fix...")

    try:
        from containers.content_collector.source_collectors import (
            SourceCollectorFactory,
        )

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
        return False


def test_sources_endpoint_response():
    """Test that sources endpoint includes Mastodon and has consistent format."""
    print("Testing sources endpoint response...")

    try:
        from fastapi.testclient import TestClient

        from containers.content_collector.main import app

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


def test_standard_response_consistency():
    """Test that StandardResponse helper creates consistent format."""
    print("Testing StandardResponse consistency...")

    try:
        from libs.shared_models import StandardResponse, create_success_response

        # Test success response
        response = create_success_response(
            message="Test message", data={"test": "data"}, metadata={"test": "metadata"}
        )

        print(f"Success response: {response.model_dump()}")

        # Verify errors is empty list, not None
        assert response.errors == []
        assert response.errors is not None

        print("✅ StandardResponse consistency fix works correctly")
        return True

    except Exception as e:
        print(f"❌ StandardResponse test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all verification tests."""
    print("=== API Standardization Verification (Issue #523) ===\n")

    tests = [
        test_reddit_collector_info_fix,
        test_sources_endpoint_response,
        test_standard_response_consistency,
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
