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
    # Try to get Infracost API key from Key Vault
    if [ -z "$INFRACOST_API_KEY" ]; then
        echo "🔑 Checking for Infracost API key in Azure Key Vault..."
        KEYVAULT_NAME=$(az keyvault list --resource-group "ai-content-dev-rg" --query "[0].name" -o tsv 2>/dev/null || echo "")
        if [ -n "$KEYVAULT_NAME" ]; then
            export INFRACOST_API_KEY=$(az keyvault secret show --vault-name "$KEYVAULT_NAME" --name "infracost-api-key" --query "value" -o tsv 2>/dev/null || echo "")
            if [ -n "$INFRACOST_API_KEY" ] && [ "$INFRACOST_API_KEY" != "placeholder-get-from-infracost-io" ]; then
                echo "✅ Using Infracost API key from Key Vault"
                infracost configure set api_key "$INFRACOST_API_KEY"
            else
                echo "⚠️  No valid Infracost API key in Key Vault. Get one from https://infracost.io"
                echo "   Then run: make setup-keyvault to store it"
            fi
        else
            echo "⚠️  Key Vault not found. Deploy infrastructure first or set INFRACOST_API_KEY manually"
        fi
    fi
    
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
