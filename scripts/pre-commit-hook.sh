#!/bin/bash
# Shared pre-commit hook for AI Content Farm
# Run this script to set up the pre-commit hook: ./scripts/setup-git-hooks.sh

# Check if any Python files are being committed
python_files=$(git diff --cached --name-only --diff-filter=AM | grep -E '\.py$')

if [ -n "$python_files" ]; then
    echo "🎨 Python files changed, checking code formatting..."
    echo "Changed files:"
    echo "$python_files" | sed 's/^/  - /'

    # Check if formatting tools are available
    if ! command -v black &> /dev/null || ! command -v isort &> /dev/null; then
        echo "📦 Installing formatting tools..."
        pip install black isort
    fi

    # Check Black formatting
    echo "Checking Black formatting..."
    if ! black --check --diff .; then
        echo ""
        echo "❌ Black formatting check failed!"
        echo "Please run 'black .' to fix formatting issues."
        echo "Then stage your fixes with 'git add' and commit again."
        exit 1
    fi

    # Check isort import sorting
    echo "Checking import sorting..."
    if ! isort --check-only --diff .; then
        echo ""
        echo "❌ Import sorting check failed!"
        echo "Please run 'isort .' to fix import sorting."
        echo "Then stage your fixes with 'git add' and commit again."
        exit 1
    fi

    echo "✅ Code formatting checks passed!"
fi

# Check if any workflow files are being committed
workflow_files=$(git diff --cached --name-only | grep -E '\.github/(workflows|actions)/')

if [ -n "$workflow_files" ]; then
    echo "🔍 Workflow files changed, running workflow linting..."
    echo "Changed files:"
    echo "$workflow_files" | sed 's/^/  - /'

    # Run workflow linting
    if ! make lint-workflows; then
        echo ""
        echo "❌ Workflow linting failed!"
        echo "Please run 'make lint-workflows' to see the issues and fix them."
        echo "Then stage your fixes with 'git add' and commit again."
        exit 1
    fi

    echo "✅ Workflow linting passed!"
fi

# Check for script injection vulnerabilities when workflow files change
if [ -n "$workflow_files" ]; then
    echo "🔒 Running security scan on workflow files..."

    if ! make scan-semgrep 2>/dev/null | grep -q "No findings"; then
        echo "⚠️  Security scan detected potential issues."
        echo "Run 'make scan-semgrep' to review security findings."
        echo "You can continue, but please review the security implications."

        # Ask user if they want to continue (in interactive mode)
        if [ -t 0 ]; then
            read -p "Continue with commit? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
        fi
    else
        echo "✅ Security scan passed!"
    fi
fi

exit 0
