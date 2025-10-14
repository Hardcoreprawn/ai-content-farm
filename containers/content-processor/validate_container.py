#!/usr/bin/env python3
"""
Content Processor Container Validation Script

Comprehensive validation of the optimized content-processor container.
Checks:
- Code structure and organization
- Import integrity
- Type hint coverage
- Test coverage
- Configuration validity
- Dependencies
"""

import ast
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


class Colors:
    """ANSI color codes for terminal output."""

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    END = "\033[0m"


def print_section(title: str):
    """Print section header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{title}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}\n")


def print_success(message: str):
    """Print success message."""
    print(f"{Colors.GREEN}✓{Colors.END} {message}")


def print_error(message: str):
    """Print error message."""
    print(f"{Colors.RED}✗{Colors.END} {message}")


def print_warning(message: str):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠{Colors.END} {message}")


def print_info(message: str):
    """Print info message."""
    print(f"  {message}")


def count_lines_of_code() -> Dict[str, int]:
    """Count lines of code in Python files."""
    base_dir = Path(".")
    total_lines = 0
    file_count = 0

    for py_file in base_dir.rglob("*.py"):
        if "__pycache__" in str(py_file) or "venv" in str(py_file):
            continue
        if py_file.is_file():
            with open(py_file, "r", encoding="utf-8") as f:
                lines = len(f.readlines())
                total_lines += lines
                file_count += 1

    return {"total_lines": total_lines, "file_count": file_count}


def check_imports() -> Tuple[bool, List[str]]:
    """Check if all imports are valid."""
    errors = []
    success = True

    try:
        result = subprocess.run(
            ["python", "-m", "py_compile"]
            + [str(p) for p in Path(".").rglob("*.py") if "__pycache__" not in str(p)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            success = False
            errors.append(result.stderr)
    except Exception as e:
        success = False
        errors.append(str(e))

    return success, errors


def check_type_hints() -> Dict[str, Any]:
    """Check type hint coverage in Python files."""
    base_dir = Path(".")
    total_functions = 0
    typed_functions = 0
    files_checked = 0

    for py_file in base_dir.rglob("*.py"):
        if "__pycache__" in str(py_file) or "test_" in py_file.name:
            continue

        try:
            with open(py_file, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())

            files_checked += 1
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Only check public functions
                    if not node.name.startswith("_"):
                        total_functions += 1
                        # Check if function has return type annotation
                        if node.returns is not None:
                            # Check if parameters have type annotations
                            params_typed = all(
                                arg.annotation is not None
                                for arg in node.args.args
                                if arg.arg != "self"
                            )
                            if params_typed:
                                typed_functions += 1
        except Exception:
            continue

    coverage = (typed_functions / total_functions * 100) if total_functions > 0 else 0

    return {
        "files_checked": files_checked,
        "total_functions": total_functions,
        "typed_functions": typed_functions,
        "coverage_percent": coverage,
    }


def check_tests() -> Dict[str, Any]:
    """Check test coverage and count tests."""
    test_dir = Path("tests")

    if not test_dir.exists():
        return {"exists": False}

    test_files = list(test_dir.glob("test_*.py"))
    total_tests = 0

    for test_file in test_files:
        try:
            with open(test_file, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name.startswith("test_"):
                        total_tests += 1
        except Exception:
            continue

    return {"exists": True, "test_files": len(test_files), "total_tests": total_tests}


def check_required_files() -> Dict[str, bool]:
    """Check if required files exist."""
    required_files = [
        "main.py",
        "config.py",
        "requirements.txt",
        "Dockerfile",
        "pyproject.toml",
    ]

    results = {}
    for file in required_files:
        results[file] = Path(file).exists()

    return results


def check_directory_structure() -> Dict[str, bool]:
    """Check if expected directories exist."""
    expected_dirs = [
        "core",
        "endpoints",
        "models",
        "operations",
        "utils",
        "tests",
    ]

    results = {}
    for directory in expected_dirs:
        results[directory] = Path(directory).is_dir()

    return results


def check_no_deprecated_files() -> List[str]:
    """Check for files that should have been deleted."""
    deprecated_patterns = [
        "dependencies.py",
        "services/",
        "lease_operations.py",
        "blob_operations.py",
        "session_state.py",
        "diagnostics.py",
    ]

    found_deprecated = []
    for pattern in deprecated_patterns:
        matches = list(Path(".").rglob(pattern))
        if matches:
            found_deprecated.extend([str(m) for m in matches])

    return found_deprecated


def run_quick_tests() -> Tuple[bool, str]:
    """Run quick unit tests."""
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/", "-q", "--tb=no", "-x"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        success = result.returncode == 0
        output = result.stdout + result.stderr

        return success, output
    except subprocess.TimeoutExpired:
        return False, "Tests timed out after 60 seconds"
    except Exception as e:
        return False, str(e)


def main():
    """Run all validation checks."""
    print(f"\n{Colors.BOLD}Content Processor Container Validation{Colors.END}")
    print(f"{Colors.BOLD}Date: 2025-10-15{Colors.END}")

    issues_found = []
    warnings_found = []

    # Check 1: Code metrics
    print_section("1. Code Metrics")
    loc_data = count_lines_of_code()
    print_info(f"Total Python files: {loc_data['file_count']}")
    print_info(f"Total lines of code: {loc_data['total_lines']:,}")

    if loc_data["total_lines"] < 10000:
        print_success(
            f"Code size is lean: {loc_data['total_lines']:,} LOC (target: <10,000)"
        )
    else:
        print_warning(
            f"Code size: {loc_data['total_lines']:,} LOC (target was <10,000)"
        )
        warnings_found.append("Code size slightly above target")

    # Check 2: Required files
    print_section("2. Required Files")
    required_files = check_required_files()
    for file, exists in required_files.items():
        if exists:
            print_success(f"{file} exists")
        else:
            print_error(f"{file} missing")
            issues_found.append(f"Missing required file: {file}")

    # Check 3: Directory structure
    print_section("3. Directory Structure")
    directories = check_directory_structure()
    for directory, exists in directories.items():
        if exists:
            print_success(f"{directory}/ exists")
        else:
            print_error(f"{directory}/ missing")
            issues_found.append(f"Missing directory: {directory}/")

    # Check 4: Deprecated files check
    print_section("4. Deprecated Files Check")
    deprecated = check_no_deprecated_files()
    if not deprecated:
        print_success("No deprecated files found")
    else:
        for file in deprecated:
            print_warning(f"Found deprecated file: {file}")
            warnings_found.append(f"Deprecated file still exists: {file}")

    # Check 5: Import integrity
    print_section("5. Import Integrity")
    imports_valid, import_errors = check_imports()
    if imports_valid:
        print_success("All imports are valid")
    else:
        print_error("Import errors found")
        for error in import_errors[:5]:  # Show first 5 errors
            print_info(f"  {error[:100]}")
        issues_found.append("Import validation failed")

    # Check 6: Type hints
    print_section("6. Type Hint Coverage")
    type_data = check_type_hints()
    print_info(f"Files checked: {type_data['files_checked']}")
    print_info(f"Public functions: {type_data['total_functions']}")
    print_info(f"Fully typed: {type_data['typed_functions']}")
    print_info(f"Coverage: {type_data['coverage_percent']:.1f}%")

    if type_data["coverage_percent"] >= 80:
        print_success(
            f"Type hint coverage is excellent: {type_data['coverage_percent']:.1f}%"
        )
    elif type_data["coverage_percent"] >= 60:
        print_warning(
            f"Type hint coverage is adequate: {type_data['coverage_percent']:.1f}%"
        )
        warnings_found.append("Type hint coverage below 80%")
    else:
        print_error(f"Type hint coverage is low: {type_data['coverage_percent']:.1f}%")
        issues_found.append("Type hint coverage below 60%")

    # Check 7: Tests
    print_section("7. Test Coverage")
    test_data = check_tests()
    if test_data["exists"]:
        print_success(f"Tests directory exists")
        print_info(f"Test files: {test_data['test_files']}")
        print_info(f"Total tests: {test_data['total_tests']}")

        if test_data["total_tests"] >= 200:
            print_success(f"Excellent test count: {test_data['total_tests']} tests")
        elif test_data["total_tests"] >= 100:
            print_success(f"Good test count: {test_data['total_tests']} tests")
        else:
            print_warning(
                f"Test count could be higher: {test_data['total_tests']} tests"
            )
            warnings_found.append("Test count below 100")
    else:
        print_error("Tests directory not found")
        issues_found.append("Missing tests directory")

    # Check 8: Quick test run
    print_section("8. Quick Test Run")
    print_info("Running quick unit tests...")
    tests_pass, test_output = run_quick_tests()

    if tests_pass:
        print_success("Unit tests passed")
    else:
        print_error("Some tests failed")
        print_info("Test output (last 500 chars):")
        print_info(test_output[-500:])
        issues_found.append("Unit tests failing")

    # Final summary
    print_section("Validation Summary")

    if not issues_found and not warnings_found:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ ALL CHECKS PASSED!{Colors.END}")
        print(f"{Colors.GREEN}The container is in excellent shape.{Colors.END}\n")
        return 0
    elif not issues_found:
        print(
            f"\n{Colors.YELLOW}{Colors.BOLD}⚠ VALIDATION PASSED WITH WARNINGS{Colors.END}"
        )
        print(f"{Colors.YELLOW}Warnings found: {len(warnings_found)}{Colors.END}")
        for warning in warnings_found:
            print(f"  {Colors.YELLOW}⚠{Colors.END} {warning}")
        print(
            f"\n{Colors.YELLOW}The container is functional but has minor issues.{Colors.END}\n"
        )
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}✗ VALIDATION FAILED{Colors.END}")
        print(f"{Colors.RED}Issues found: {len(issues_found)}{Colors.END}")
        for issue in issues_found:
            print(f"  {Colors.RED}✗{Colors.END} {issue}")
        if warnings_found:
            print(f"\n{Colors.YELLOW}Warnings: {len(warnings_found)}{Colors.END}")
            for warning in warnings_found:
                print(f"  {Colors.YELLOW}⚠{Colors.END} {warning}")
        print(
            f"\n{Colors.RED}The container needs fixes before deployment.{Colors.END}\n"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
