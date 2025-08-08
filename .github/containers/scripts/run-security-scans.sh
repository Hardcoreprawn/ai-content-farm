#!/bin/bash
# Security scanning script for containerized CI/CD
set -e

echo "🔍 Running comprehensive security scans..."

# Create output directory
mkdir -p /workspace/security-results

# Function to run scan with error handling
run_scan() {
    local tool=$1
    local cmd=$2
    local output_file=$3
    
    echo "Running $tool..."
    if eval "$cmd" 2>&1 | tee "/workspace/security-results/${tool}.log"; then
        echo "✅ $tool completed successfully"
        return 0
    else
        echo "⚠️  $tool completed with warnings/errors (non-blocking)"
        return 1
    fi
}

# Run Checkov on infrastructure
run_scan "checkov-infra" \
    "checkov -d /workspace/infra --quiet --compact --output json --output-file-path /workspace/security-results/checkov.json" \
    "checkov.json"

# Run Checkov on functions
run_scan "checkov-functions" \
    "checkov -d /workspace/functions --quiet --compact --output json --output-file-path /workspace/security-results/checkov-functions.json" \
    "checkov-functions.json"

# Run TFSec
cd /workspace/infra/application
run_scan "tfsec" \
    "tfsec . --format json --out /workspace/security-results/tfsec.json --soft-fail" \
    "tfsec.json"
cd /workspace

# Run Terrascan
cd /workspace/infra/application
run_scan "terrascan" \
    "terrascan scan -i terraform --output json > /workspace/security-results/terrascan.json" \
    "terrascan.json"
cd /workspace

# Generate SBOM
run_scan "syft-sbom" \
    "syft /workspace/functions -o json=/workspace/security-results/sbom.json" \
    "sbom.json"

# Run vulnerability scan on generated SBOM
if [ -f "/workspace/security-results/sbom.json" ]; then
    run_scan "grype-vulns" \
        "grype sbom:/workspace/security-results/sbom.json -o json > /workspace/security-results/vulnerabilities.json" \
        "vulnerabilities.json"
fi

echo "🔍 Security scans completed - results in /workspace/security-results/"
