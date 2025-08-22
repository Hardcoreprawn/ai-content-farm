#!/bin/bash
# Shared pre-commit hook for AI Content Farm
# Run this script to set up the pre-commit hook: ./scripts/setup-git-hooks.sh

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
