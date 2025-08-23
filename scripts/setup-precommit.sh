#!/bin/bash

# Pre-commit setup script
# This script installs and configures pre-commit hooks for the project

set -e

echo "🔧 Setting up pre-commit hooks for AI Content Farm..."

# Check if pre-commit is installed
if ! command -v pre-commit &> /dev/null; then
    echo "📦 Installing pre-commit..."
    pip install pre-commit
    echo "✅ pre-commit installed"
else
    echo "✅ pre-commit is already installed"
fi

# Install the pre-commit hooks
echo "🔗 Installing pre-commit hooks..."
pre-commit install

# Run pre-commit on all files to ensure everything is working
echo "🧪 Testing pre-commit hooks on all files..."
pre-commit run --all-files || {
    echo "⚠️  Some pre-commit checks failed."
    echo "🔧 Auto-fixing formatting issues..."
    ./scripts/code-quality.sh --fix
    echo "🔄 Running pre-commit checks again..."
    pre-commit run --all-files
}

echo ""
echo "🎉 Pre-commit hooks are now set up!"
echo ""
echo "ℹ️  What happens now:"
echo "   • Every git commit will automatically run code quality checks"
echo "   • Failed checks will prevent the commit (use --no-verify to bypass)"
echo "   • The same checks run locally as in CI/CD pipeline"
echo ""
echo "🛠️  Manual commands:"
echo "   make lint-python     # Run Python linting"
echo "   make format-python   # Auto-fix Python formatting"
echo "   pre-commit run       # Run all pre-commit hooks"
echo "   pre-commit run --all-files  # Run on all files"
echo ""
echo "📚 For more info, see: docs/PRE_COMMIT_SETUP.md"
