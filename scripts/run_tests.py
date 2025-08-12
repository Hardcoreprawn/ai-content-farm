#!/usr/bin/env python3
"""
Test runner script for AI Content Farm functions.

Provides utilities for running tests locally and validating the testing setup.
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path
import json


def find_test_files():
    """Find all test files in the project"""
    test_files = []

    # Find tests in functions directory (co-located tests)
    functions_dir = Path(__file__).parent.parent / 'functions'
    if functions_dir.exists():
        for test_file in functions_dir.rglob('test_*.py'):
            test_files.append(str(test_file))

    # Find tests in tests directory (centralized tests)
    tests_dir = Path(__file__).parent.parent / 'tests'
    if tests_dir.exists():
        for test_file in tests_dir.rglob('test_*.py'):
            test_files.append(str(test_file))

    return sorted(test_files)


def validate_test_structure():
    """Validate that all functions have tests"""
    functions_dir = Path(__file__).parent.parent / 'functions'
    if not functions_dir.exists():
        print("❌ Functions directory not found")
        return False

    functions = [d for d in functions_dir.iterdir()
                 if d.is_dir() and not d.name.startswith('.') and d.name != '__pycache__']

    missing_tests = []
    for func_dir in functions:
        # Look for any test file in the function directory
        test_files = list(func_dir.glob('test_*.py'))
        if not test_files:
            missing_tests.append(func_dir.name)

    if missing_tests:
        print(f"❌ Missing tests for functions: {', '.join(missing_tests)}")
        return False

    print(f"✅ All {len(functions)} functions have test files")
    return True


def run_pytest(args=None):
    """Run pytest with appropriate arguments"""
    cmd = ['python', '-m', 'pytest']

    if args:
        cmd.extend(args)
    else:
        # Default arguments
        cmd.extend([
            '--tb=short',
            '--maxfail=3',
            '-v'
        ])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error running pytest: {e}")
        return False


def check_dependencies():
    """Check that required test dependencies are installed"""
    required_packages = [
        'pytest',
        'pytest-cov',
        'pytest-html',
        'requests'
    ]

    missing = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing.append(package)

    if missing:
        print(f"❌ Missing test dependencies: {', '.join(missing)}")
        print("Run: pip install " + " ".join(missing))
        return False

    print("✅ All test dependencies are installed")
    return True


def create_test_report():
    """Create a comprehensive test report"""
    print("📊 Generating test report...")

    cmd = [
        'python', '-m', 'pytest',
        '--html=test-report.html',
        '--self-contained-html',
        '--junitxml=test-results.xml',
        '--cov=functions',
        '--cov-report=html',
        '--cov-report=term-missing'
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout)

        if result.returncode == 0:
            print("✅ Test report generated successfully")
            print("📄 HTML report: test-report.html")
            print("📄 Coverage report: htmlcov/index.html")
            print("📄 JUnit XML: test-results.xml")
        else:
            print("❌ Test report generation failed")
            print(result.stderr)

        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error generating test report: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Test runner for AI Content Farm')
    parser.add_argument('--validate', action='store_true',
                        help='Validate test structure')
    parser.add_argument('--check-deps', action='store_true',
                        help='Check test dependencies')
    parser.add_argument('--unit', action='store_true',
                        help='Run unit tests only')
    parser.add_argument('--integration', action='store_true',
                        help='Run integration tests only')
    parser.add_argument('--function', action='store_true',
                        help='Run function tests only')
    parser.add_argument('--coverage', action='store_true',
                        help='Run tests with coverage')
    parser.add_argument('--report', action='store_true',
                        help='Generate comprehensive test report')
    parser.add_argument('--list', action='store_true',
                        help='List all test files')

    args = parser.parse_args()

    if args.list:
        test_files = find_test_files()
        print(f"Found {len(test_files)} test files:")
        for test_file in test_files:
            print(f"  {test_file}")
        return

    if args.validate:
        if not validate_test_structure():
            sys.exit(1)
        return

    if args.check_deps:
        if not check_dependencies():
            sys.exit(1)
        return

    if args.report:
        if not create_test_report():
            sys.exit(1)
        return

    # Run tests
    pytest_args = []

    if args.unit:
        pytest_args.extend(['-m', 'unit'])
    elif args.integration:
        pytest_args.extend(['-m', 'integration'])
    elif args.function:
        pytest_args.extend(['-m', 'function'])

    if args.coverage:
        pytest_args.extend(['--cov=functions', '--cov-report=term-missing'])

    # Check dependencies first
    if not check_dependencies():
        sys.exit(1)

    # Validate structure
    if not validate_test_structure():
        print("⚠️  Test structure validation failed, but continuing with tests...")

    # Run tests
    success = run_pytest(pytest_args)

    if not success:
        sys.exit(1)


if __name__ == '__main__':
    main()
