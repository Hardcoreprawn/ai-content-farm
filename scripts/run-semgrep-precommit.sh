#!/bin/bash
# Semgrep pre-commit hook - blocks commits with security issues
# This script runs semgrep and blocks commits if ERROR-level issues are found

set -e

echo "🔒 Running Semgrep security scan (pre-commit)..."

# Create temporary directory for results
TEMP_DIR=$(mktemp -d)
SEMGREP_RESULTS="$TEMP_DIR/semgrep-precommit.json"

# Run semgrep in Docker (if available)
if command -v docker >/dev/null 2>&1; then
    echo "📋 Running Semgrep scan..."

    # Run semgrep with the project's configuration
    docker run --rm \
        -v "$(pwd):/src" \
        -v "$TEMP_DIR:/tmp/results" \
        semgrep/semgrep:latest \
        --config=auto \
        --config=/src/config/.semgrep.yml \
        --json \
        --output=/tmp/results/semgrep-precommit.json \
        /src || true

    # Check if results file exists and has content
    if [ -f "$SEMGREP_RESULTS" ] && [ -s "$SEMGREP_RESULTS" ]; then
        # Count issues by severity
        error_count=$(jq '[.results[] | select(.extra.severity == "ERROR")] | length' "$SEMGREP_RESULTS" 2>/dev/null || echo "0")
        warning_count=$(jq '[.results[] | select(.extra.severity == "WARNING")] | length' "$SEMGREP_RESULTS" 2>/dev/null || echo "0")
        info_count=$(jq '[.results[] | select(.extra.severity == "INFO")] | length' "$SEMGREP_RESULTS" 2>/dev/null || echo "0")

        echo "📊 Semgrep Results:"
        echo "   Errors: $error_count"
        echo "   Warnings: $warning_count"
        echo "   Info: $info_count"

        # Block commit if ERROR-level issues found
        if [ "$error_count" -gt 0 ]; then
            echo ""
            echo "❌ COMMIT BLOCKED: Semgrep found $error_count ERROR-level security issue(s)"
            echo ""
            echo "🔍 Error details:"
            jq -r '.results[] | select(.extra.severity == "ERROR") | "   - " + .extra.message + " (" + .path + ":" + (.start.line | tostring) + ")"' "$SEMGREP_RESULTS" 2>/dev/null || echo "   (Unable to parse error details)"
            echo ""
            echo "💡 To fix:"
            echo "   1. Review and fix the security issues above"
            echo "   2. If issues are acceptable, add '# nosemgrep: rule-id' comments"
            echo "   3. Run 'git commit' again"
            echo ""
            echo "📖 For more details:"
            echo "   cat security-results/semgrep-results.json | jq '.results[] | select(.extra.severity == \"ERROR\")'"

            # Clean up
            rm -rf "$TEMP_DIR"
            exit 1
        fi

        # Warn about non-blocking issues
        if [ "$warning_count" -gt 0 ] || [ "$info_count" -gt 0 ]; then
            echo ""
            echo "⚠️  Semgrep found $warning_count warnings and $info_count info items"
            echo "   These don't block the commit but should be reviewed"
            echo "   Run 'make security-python' to see full results"
        fi

        echo "✅ No blocking security issues found"
    else
        echo "✅ Semgrep scan completed (no issues found)"
    fi
else
    echo "⚠️  Docker not available - skipping Semgrep scan"
    echo "   Install Docker to enable security scanning"
fi

# Clean up
rm -rf "$TEMP_DIR"

echo "🔒 Pre-commit security scan completed"
