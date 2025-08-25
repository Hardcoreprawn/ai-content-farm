#!/bin/bash
# Setup Git hooks for AI Content Farm development

echo "🔧 Setting up Git hooks for AI Content Farm..."

# Make sure scripts directory exists
mkdir -p scripts

# Make the hooks executable
chmod +x scripts/pre-commit-hook.sh
chmod +x scripts/commit-msg-hook.sh

# Copy to Git hooks directory
cp scripts/pre-commit-hook.sh .git/hooks/pre-commit
cp scripts/commit-msg-hook.sh .git/hooks/commit-msg

echo "✅ Git hooks installed!"
echo ""
echo "Pre-commit hook will:"
echo "  - Check Python code formatting (Black) and import sorting (isort)"
echo "  - Lint workflow files when .github/ files change"
echo "  - Run security scans on workflow changes"
echo "  - Prevent commits with formatting or workflow syntax errors"
echo ""
echo "Commit-msg hook will:"
echo "  - Block emojis and non-ASCII characters in commit messages"
echo "  - Warn about long commit messages (>72 chars)"
echo "  - Suggest conventional commit format"
echo "  - Detect temporary/WIP commit messages"
echo ""
echo "To bypass hooks temporarily: git commit --no-verify"
echo "To bypass just commit-msg: git commit --no-verify"
