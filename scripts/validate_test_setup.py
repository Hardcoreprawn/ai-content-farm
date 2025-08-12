#!/usr/bin/env python3
"""
Test Structure Validation Script
Validates that the testing framework setup is complete and working correctly.
"""

import os
import sys
from pathlib import Path

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
ENDC = '\033[0m'


def print_status(message, status):
    """Print a status message with color coding."""
    color = GREEN if status == "✅" else RED if status == "❌" else YELLOW
    print(f"{status} {color}{message}{ENDC}")


def check_file_exists(file_path, description):
    """Check if a file exists and print status."""
    exists = os.path.exists(file_path)
    print_status(f"{description}: {file_path}", "✅" if exists else "❌")
    return exists


def check_function_tests():
    """Check that all Azure Functions have test files."""
    functions_dir = Path("functions")
    function_dirs = [d for d in functions_dir.iterdir() if d.is_dir(
    ) and not d.name.startswith("__") and not d.name.startswith(".")]

    print(f"\n{BLUE}Checking Azure Function Test Files:{ENDC}")
    all_good = True

    for func_dir in function_dirs:
        # Convert CamelCase to snake_case for test file naming
        test_file_name = ""
        for i, char in enumerate(func_dir.name):
            if i > 0 and char.isupper():
                test_file_name += "_"
            test_file_name += char.lower()

        test_file = func_dir / f"test_{test_file_name}.py"
        conftest_file = func_dir / "conftest.py"

        has_test = test_file.exists()
        has_conftest = conftest_file.exists()

        print_status(f"{func_dir.name} test file", "✅" if has_test else "❌")
        print_status(f"{func_dir.name} conftest.py",
                     "✅" if has_conftest else "❌")

        if not (has_test and has_conftest):
            all_good = False

    return all_good


def main():
    """Main validation function."""
    print(f"{BLUE}🧪 Testing Framework Validation{ENDC}")
    print("=" * 50)

    # Core configuration files
    print(f"\n{BLUE}Core Configuration Files:{ENDC}")
    core_files = [
        ("pytest.ini", "pytest configuration"),
        ("tests/conftest.py", "shared test fixtures"),
        (".github/workflows/test.yml", "GitHub Actions workflow"),
        ("scripts/run_tests.py", "test validation script")
    ]

    all_core_good = True
    for file_path, desc in core_files:
        if not check_file_exists(file_path, desc):
            all_core_good = False

    # Function-specific tests
    functions_good = check_function_tests()

    # Makefile targets
    print(f"\n{BLUE}Makefile Test Targets:{ENDC}")
    makefile_content = ""
    try:
        with open("Makefile", "r") as f:
            makefile_content = f.read()
    except FileNotFoundError:
        print_status("Makefile not found", "❌")
        return False

    test_targets = [
        "test-setup",
        "test-unit",
        "test-integration",
        "test-functions-local",
        "test-coverage",
        "test-watch"
    ]

    makefile_good = True
    for target in test_targets:
        if f"{target}:" in makefile_content:
            print_status(f"Makefile target: {target}", "✅")
        else:
            print_status(f"Makefile target: {target}", "❌")
            makefile_good = False

    # Overall status
    print(f"\n{BLUE}Overall Status:{ENDC}")
    print("=" * 50)

    if all_core_good and functions_good and makefile_good:
        print_status("Testing framework setup complete", "✅")
        print(f"\n{GREEN}✨ All systems operational!{ENDC}")
        print(f"{GREEN}Ready for development with comprehensive testing.{ENDC}")
        return True
    else:
        print_status("Testing framework setup incomplete", "❌")
        print(f"\n{RED}⚠️  Some components are missing or misconfigured.{ENDC}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
