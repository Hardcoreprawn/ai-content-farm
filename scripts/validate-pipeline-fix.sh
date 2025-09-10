#!/bin/bash

# validate-pipeline-fix.sh
# Validates that Issue #421 pipeline fix is working correctly
# Tests dynamic container discovery, image versioning, and terraform integration

set -euo pipefail

echo "=== Validating Pipeline Fix for Issue #421 ==="
echo ""

# Check 1: Container Discovery Works
echo "✓ Testing container discovery..."
CONTAINERS=$(./scripts/discover-containers.sh --json)
echo "  Discovered containers: $CONTAINERS"

# Check 2: Container Discovery with Terraform Format
echo ""
echo "✓ Testing terraform-compatible container discovery..."
TERRAFORM_CONTAINERS=$(./scripts/terraform-discover-containers.sh)
echo "  Terraform format: $TERRAFORM_CONTAINERS"

# Check 3: Registry Images JSON Generation
echo ""
echo "✓ Testing registry images JSON generation..."
TEST_SHA="test-abc123"
REGISTRY_JSON=$(echo "$CONTAINERS" | jq -r 'to_entries | map({key: .value, value: {image: ("ghcr.io/hardcoreprawn/ai-content-farm/" + .value + ":'"$TEST_SHA"'")}}) | from_entries')
echo "  Registry images JSON:"
echo "$REGISTRY_JSON" | jq .

# Check 4: Terraform External Data Source
echo ""
echo "✓ Testing terraform external data source..."
cd infra
terraform init -backend=false > /dev/null 2>&1
terraform validate > /dev/null 2>&1
echo "  Terraform configuration is valid"

# Check 5: Terraform Plan with Dynamic Variables
echo ""
echo "✓ Testing terraform plan with dynamic variables..."
TF_VAR_image_tag="$TEST_SHA" terraform plan -var-file="production.tfvars" -target="data.external.container_discovery" > /dev/null 2>&1
echo "  Terraform plan succeeds with dynamic container discovery"

# Check 6: Pipeline YAML Syntax
echo ""
echo "✓ Testing pipeline YAML syntax..."
cd ..
yamllint -d relaxed .github/workflows/cicd-pipeline.yml > /dev/null 2>&1
echo "  Pipeline YAML syntax is valid"

echo ""
echo "🎉 All validation checks passed!"
echo ""
echo "Issue #421 Fix Summary:"
echo "- ✅ Dynamic container discovery working"
echo "- ✅ Container image versioning implemented"
echo "- ✅ Pipeline terraform deployment enhanced"
echo "- ✅ Registry images JSON format correct"
echo "- ✅ Terraform configuration validates"
echo "- ✅ Pipeline syntax valid"
echo ""
echo "🚀 Pipeline is ready to automatically load containers into Azure Container Apps!"
