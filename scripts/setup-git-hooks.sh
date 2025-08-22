#!/bin/bash
# Setup Git hooks for AI Content Farm development

echo "🔧 Setting up Git hooks for AI Content Farm..."

# Make sure scripts directory exists
mkdir -p scripts

# Make the pre-commit hook executable
chmod +x scripts/pre-commit-hook.sh

# Copy to Git hooks directory
cp scripts/pre-commit-hook.sh .git/hooks/pre-commit

echo "✅ Pre-commit hook installed!"
echo ""
echo "This hook will automatically:"
echo "  - Lint workflow files when .github/ files change"
echo "  - Run security scans on workflow changes"
echo "  - Prevent commits with workflow syntax errors"
echo ""
echo "To disable temporarily: git commit --no-verify"
