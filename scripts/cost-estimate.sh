#!/bin/bash

# Script to run Infracost locally with our usage model
# Usage: ./scripts/cost-estimate.sh

set -e

cd "$(dirname "$0")/../infra"

echo "🏗️  Initializing Terraform..."
terraform init > /dev/null

echo "📋 Creating Terraform plan..."
terraform plan -out=tfplan > /dev/null

echo "💰 Running Infracost with usage model..."
if command -v infracost &> /dev/null; then
    echo ""
    echo "📊 Monthly Cost Estimate:"
    echo "========================"
    infracost breakdown --path tfplan --usage-file infracost-usage.yml --show-skipped
    
    echo ""
    echo "💡 Cost breakdown saved to: infracost-report.json"
    infracost breakdown --path tfplan --usage-file infracost-usage.yml --format json > infracost-report.json
    
    echo ""
    echo "🎯 Key metrics:"
    TOTAL_COST=$(jq -r '.totalMonthlyCost' infracost-report.json)
    echo "  • Total monthly cost: \$$TOTAL_COST"
    echo "  • Annual cost estimate: \$$(echo "$TOTAL_COST * 12" | bc -l | cut -d'.' -f1)"
    
    echo ""
    echo "🚦 Pipeline gates:"
    COST_INT=$(echo "$TOTAL_COST" | cut -d'.' -f1)
    if [ "$COST_INT" -gt 15 ]; then
        echo "  • Status: ❌ FAIL - Exceeds \$15/month limit"
    elif [ "$COST_INT" -gt 5 ]; then
        echo "  • Status: ⚠️  WARN - Exceeds \$5/month (requires approval)"
    else
        echo "  • Status: ✅ PASS - Within \$5/month budget"
    fi
    
else
    echo "❌ Infracost not installed. Install with:"
    echo "curl -fsSL https://raw.githubusercontent.com/infracost/infracost/master/scripts/install.sh | sh"
fi

# Clean up
rm -f tfplan
