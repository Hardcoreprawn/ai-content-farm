#!/usr/bin/env python3
"""
Simple test script for content-processor.
Validates imports and basic endpoints work.
"""

import os
import sys

# Add repo root to Python path for libs imports
sys.path.insert(0, "/workspaces/ai-content-farm")


def test_imports():
    """Test that all imports work correctly."""
    print("Testing imports...")
    try:
        # Add content-processor directory to path
        sys.path.insert(0, "/workspaces/ai-content-farm/containers/content-processor")

        # Clear any cached modules
        if "main" in sys.modules:
            del sys.modules["main"]

        import main

        app = main.app
        print("✅ Main app import successful")

        from libs.shared_models import StandardResponse

        print("✅ Shared models import successful")

        from libs.standard_endpoints import create_standard_health_endpoint

        print("✅ Standard endpoints import successful")

        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_app_routes():
    """Test that app has expected routes."""
    print("\nTesting app routes...")
    try:
        # Add content-processor directory to path
        sys.path.insert(0, "/workspaces/ai-content-farm/containers/content-processor")

        # Clear any cached modules
        if "main" in sys.modules:
            del sys.modules["main"]

        import main

        app = main.app

        routes = {}
        for route in app.routes:
            if hasattr(route, "path") and hasattr(route, "methods"):
                routes[route.path] = route.methods

        expected_routes = ["/health", "/status", "/docs", "/", "/process"]

        for expected in expected_routes:
            if expected in routes:
                print(f"✅ {expected} endpoint found")
            else:
                print(f"❌ {expected} endpoint missing")
                return False

        return True
    except Exception as e:
        print(f"❌ Route test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("Content Processor Validation Test")
    print("=" * 40)

    success = True
    success &= test_imports()
    success &= test_app_routes()

    print("\n" + "=" * 40)
    if success:
        print("✅ All tests passed! Content processor is ready.")
        sys.exit(0)
    else:
        print("❌ Some tests failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
