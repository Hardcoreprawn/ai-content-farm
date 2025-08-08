#!/bin/bash
# Security gate evaluation script
set -e

echo "🚪 Evaluating security gate..."

SECURITY_DIR="/workspace/security-results"
CRITICAL_COUNT=0
HIGH_COUNT=0

# Check Checkov results for critical/high findings
if [ -f "$SECURITY_DIR/checkov.json" ]; then
    CRITICAL_COUNT=$(jq '.results.failed_checks | map(select(.severity == "CRITICAL")) | length' "$SECURITY_DIR/checkov.json" 2>/dev/null || echo 0)
    HIGH_COUNT=$(jq '.results.failed_checks | map(select(.severity == "HIGH")) | length' "$SECURITY_DIR/checkov.json" 2>/dev/null || echo 0)
fi

# Check vulnerability scan results
if [ -f "$SECURITY_DIR/vulnerabilities.json" ]; then
    VULN_CRITICAL=$(jq '.matches | map(select(.vulnerability.severity == "Critical")) | length' "$SECURITY_DIR/vulnerabilities.json" 2>/dev/null || echo 0)
    VULN_HIGH=$(jq '.matches | map(select(.vulnerability.severity == "High")) | length' "$SECURITY_DIR/vulnerabilities.json" 2>/dev/null || echo 0)
    
    CRITICAL_COUNT=$((CRITICAL_COUNT + VULN_CRITICAL))
    HIGH_COUNT=$((HIGH_COUNT + VULN_HIGH))
fi

echo "📊 Security findings summary:"
echo "  Critical: $CRITICAL_COUNT"
echo "  High: $HIGH_COUNT"

# Security gate decision logic
if [ "$CRITICAL_COUNT" -gt 0 ]; then
    echo "❌ SECURITY GATE FAILED: $CRITICAL_COUNT critical security findings detected"
    echo "approved=false" >> $GITHUB_OUTPUT 2>/dev/null || true
    exit 1
elif [ "$HIGH_COUNT" -gt 10 ]; then
    echo "❌ SECURITY GATE FAILED: $HIGH_COUNT high-severity findings exceed limit (>10)"
    echo "approved=false" >> $GITHUB_OUTPUT 2>/dev/null || true
    exit 1
else
    echo "✅ SECURITY GATE PASSED: No critical findings, $HIGH_COUNT high findings"
    echo "approved=true" >> $GITHUB_OUTPUT 2>/dev/null || true
fi

# Create summary file
cat > "$SECURITY_DIR/security-summary.json" << EOF
{
  "critical_count": $CRITICAL_COUNT,
  "high_count": $HIGH_COUNT,
  "gate_passed": true,
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

echo "📄 Security summary written to $SECURITY_DIR/security-summary.json"
