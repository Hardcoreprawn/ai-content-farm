#!/bin/bash
# AI Content Farm - Commit Message Validation Hook
# This script validates commit messages for format and content

commit_msg_file="$1"
commit_msg=$(cat "$commit_msg_file")

echo "🔍 Validating commit message..."

# Check for emojis/unicode characters
if echo "$commit_msg" | grep -P '[^\x00-\x7F]' > /dev/null; then
    echo ""
    echo "❌ COMMIT REJECTED: Message contains emojis or non-ASCII characters!"
    echo ""
    echo "🚫 Problematic characters found in:"
    echo "\"$commit_msg\""
    echo ""
    echo "✅ Please use clean ASCII text only for better compatibility with:"
    echo "   - CI/CD systems"
    echo "   - Git tools and automation"
    echo "   - Cross-platform development"
    echo "   - Log parsing and analysis"
    echo ""
    echo "💡 Example of good commit messages:"
    echo "   fix: resolve container build matrix failures"
    echo "   feat: add BuildKit cache mounts for faster builds"
    echo "   docs: update deployment guide with new requirements"
    echo "   refactor: optimize dependency resolution strategy"
    echo ""
    exit 1
fi

# Check message length (first line should be <= 72 characters)
first_line=$(echo "$commit_msg" | head -n1)
if [ ${#first_line} -gt 72 ]; then
    echo ""
    echo "⚠️  WARNING: First line is ${#first_line} characters (recommended: ≤72)"
    echo "   Long commit messages may be truncated in git logs and UIs"
    echo ""
    echo "Current first line:"
    echo "\"$first_line\""
    echo ""
    # Don't block, just warn for length
fi

# Check for conventional commit format (recommended)
if echo "$commit_msg" | grep -qE '^(feat|fix|docs|style|refactor|test|chore|ci|perf|build)(\(.+\))?: .+'; then
    echo "✅ Conventional commit format detected"
else
    echo ""
    echo "💡 TIP: Consider using conventional commit format:"
    echo "   type(scope): description"
    echo ""
    echo "   Types: feat, fix, docs, style, refactor, test, chore, ci, perf, build"
    echo "   Example: feat(containers): add BuildKit cache mounts"
    echo ""
    # Don't block, just suggest
fi

# Check for common problematic patterns
if echo "$commit_msg" | grep -qiE '^(wip|fixup|squash|temp|tmp|test)'; then
    echo ""
    echo "⚠️  WARNING: Commit message starts with temporary keyword"
    echo "   Consider using a more descriptive message for production commits"
    echo ""
fi

# All checks passed
echo "✅ Commit message validation passed!"
exit 0
