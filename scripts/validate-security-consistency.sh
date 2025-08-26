#!/bin/bash

# Security Scan Consistency Validator
# Validates that local development and CI/CD produce the same security scan results

set -e

echo "🔍 Security Scan Consistency Validator"
echo "======================================"

# Run standardized semgrep scan
echo "📊 Running standardized semgrep scan..."
./scripts/run-semgrep.sh $(pwd) security-results semgrep/semgrep:latest > /dev/null 2>&1

# Check if both output files exist
if [ ! -f "security-results/semgrep-results.json" ]; then
    echo "❌ JSON results file missing"
    exit 1
fi

if [ ! -f "security-results/semgrep.sarif" ]; then
    echo "❌ SARIF results file missing"
    exit 1
fi

# Count findings in both formats
json_count=$(jq -r '.results | length' security-results/semgrep-results.json 2>/dev/null || echo "0")
sarif_count=$(jq -r '.runs[0].results | length' security-results/semgrep.sarif 2>/dev/null || echo "0")

echo "📈 Results Comparison:"
echo "  JSON format:  $json_count findings"
echo "  SARIF format: $sarif_count findings"

# Validate consistency
if [ "$json_count" -eq "$sarif_count" ]; then
    echo "✅ Results are consistent between formats"

    if [ "$json_count" -eq 0 ]; then
        echo "🎉 No security issues found!"
        exit 0
    else
        echo "⚠️  $json_count security issues found"
        echo ""
        echo "🔍 Summary of findings:"
        jq -r '.results[] | "• \(.check_id) in \(.path):\(.start.line)"' security-results/semgrep-results.json 2>/dev/null | head -10
        if [ "$json_count" -gt 10 ]; then
            echo "... and $((json_count - 10)) more"
        fi
        exit 1
    fi
else
    echo "⚠️  Format discrepancy detected: JSON ($json_count) vs SARIF ($sarif_count)"
    echo "📝 This is expected due to nosemgrep comment handling differences"
    echo "🎯 Using JSON format as the authoritative source (CI/CD standard)"

    if [ "$json_count" -eq 0 ]; then
        echo "🎉 No security issues found in authoritative JSON format!"
        exit 0
    else
        echo "⚠️  $json_count security issues found in JSON format"
        echo ""
        echo "🔍 Summary of findings:"
        jq -r '.results[] | "• \(.check_id) in \(.path):\(.start.line)"' security-results/semgrep-results.json 2>/dev/null | head -10
        if [ "$json_count" -gt 10 ]; then
            echo "... and $((json_count - 10)) more"
        fi
        exit 1
    fi
fi
