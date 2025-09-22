#!/usr/bin/env python3
"""
Easy Test Runner for Content-Collector - ACTIVE

CURRENT ARCHITECTURE: Simple test runner for the simplified collector system
Status: ACTIVE - Replaces complex test patterns

Handles all the path setup and provides a simple interface for running tests.
Supports both unit tests and live system validation.

Features:
- Automatic monorepo path setup
- Runs unit and integration tests
- Optional live system testing
- Clean output formatting
- Simple command-line interface

Easy test runner for content-collector.

Handles all the path setup and provides a simple interface for running tests.
"""

import subprocess
import sys
from pathlib import Path

# Setup paths for monorepo


def setup_paths():
    """Add shared libs to Python path."""
    repo_root = Path(__file__).parent.parent.parent
    libs_path = repo_root / "libs"
    if str(libs_path) not in sys.path:
        sys.path.insert(0, str(libs_path))


def run_tests():
    """Run all tests with proper setup."""

    print("🧪 Content Collector Test Runner")
    print("=" * 40)

    # Test files to run
    test_files = [
        "tests/test_simplified_collectors.py",
        "tests/test_integration_simple.py",
    ]

    # Run each test file
    for test_file in test_files:
        print(f"\n📋 Running {test_file}...")

        cmd = [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"]

        result = subprocess.run(cmd, cwd=Path(__file__).parent)

        if result.returncode == 0:
            print(f"✅ {test_file} passed!")
        else:
            print(f"❌ {test_file} failed!")
            return False

    print("\n🎉 All tests passed!")
    return True


def run_live_test():
    """Run live system test."""
    print("\n🚀 Running live system test...")
    cmd = [sys.executable, "test_simplified_system.py"]
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    return result.returncode == 0


if __name__ == "__main__":
    setup_paths()

    import argparse

    parser = argparse.ArgumentParser(description="Content Collector Test Runner")
    parser.add_argument("--live", action="store_true", help="Run live system test")
    parser.add_argument(
        "--all", action="store_true", help="Run all tests including live"
    )
    args = parser.parse_args()

    if args.live:
        success = run_live_test()
    elif args.all:
        success = run_tests() and run_live_test()
    else:
        success = run_tests()

    sys.exit(0 if success else 1)
