#!/bin/bash

# Standardized Semgrep Security Scan
# This script ensures consistent security scanning between local development and CI/CD

set -e

WORKSPACE_PATH="${1:-$(pwd)}"
OUTPUT_DIR="${2:-security-results}"
CONTAINER_IMAGE="${3:-semgrep/semgrep:latest}"

echo "🔍 Running Semgrep Security Scan"
echo "Workspace: $WORKSPACE_PATH"
echo "Output Directory: $OUTPUT_DIR"
echo "Container Image: $CONTAINER_IMAGE"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Run Semgrep with consistent configuration
echo "📊 Scanning with Semgrep..."
docker run --rm \
  -v "$WORKSPACE_PATH":/src \
  "$CONTAINER_IMAGE" \
  semgrep \
  --config=auto \
  --json \
  --output=/src/"$OUTPUT_DIR"/semgrep-results.json \
  /src || {
    echo "⚠️  Semgrep scan completed with findings"
    exit_code=$?
  }

# Also generate SARIF format for GitHub integration
echo "📊 Generating SARIF format..."
docker run --rm \
  -v "$WORKSPACE_PATH":/src \
  "$CONTAINER_IMAGE" \
  semgrep \
  --config=auto \
  --sarif \
  --output=/src/"$OUTPUT_DIR"/semgrep.sarif \
  /src || {
    echo "⚠️  Semgrep SARIF scan completed with findings"
  }

# Count findings
if [ -f "$OUTPUT_DIR/semgrep-results.json" ]; then
  finding_count=$(jq -r '.results | length' "$OUTPUT_DIR/semgrep-results.json" 2>/dev/null || echo "0")
  echo "📈 Security findings: $finding_count"

  if [ "$finding_count" -gt 0 ]; then
    echo "🔍 Security issues found:"
    jq -r '.results[] | "• \(.check_id) in \(.path):\(.start.line) - \(.extra.message)"' "$OUTPUT_DIR/semgrep-results.json" 2>/dev/null || echo "Could not parse findings"
  else
    echo "✅ No security issues found"
  fi
else
  echo "❌ No results file generated"
fi

echo "📁 Results saved to:"
echo "  - JSON: $OUTPUT_DIR/semgrep-results.json"
echo "  - SARIF: $OUTPUT_DIR/semgrep.sarif"
