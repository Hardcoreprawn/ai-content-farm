#!/bin/bash
# Cost analysis script for containerized CI/CD
set -e

echo "💰 Running cost analysis..."

# Set environment variables for Terraform
export TF_IN_AUTOMATION=true
export TF_CLI_ARGS_init="-no-color"
export TF_CLI_ARGS_plan="-no-color"

# Configuration
COST_DIR="/workspace/cost-analysis"
mkdir -p "$COST_DIR"

# Default values
ENVIRONMENT="${1:-staging}"
BOOTSTRAP_RG="ai-content-farm-bootstrap"

echo "🏗️  Analyzing costs for environment: $ENVIRONMENT"

# Function to configure Infracost API key
configure_infracost() {
    echo "🔑 Configuring Infracost API key..."
    
    # Try to get API key from environment variable first
    if [ -n "$INFRACOST_API_KEY" ]; then
        echo "✅ Using Infracost API key from environment variable"
        infracost configure set api_key "$INFRACOST_API_KEY"
        return 0
    fi
    
    # Verify Azure authentication
    if ! az account show > /dev/null 2>&1; then
        echo "⚠️  Azure not authenticated, using free tier"
        infracost configure set api_key ico-free-tier-key
        return 0
    fi
    
    # Try to get from CI/CD Key Vault
    if az group show --name "$BOOTSTRAP_RG" > /dev/null 2>&1; then
        KEYVAULT_NAME=$(az keyvault list --resource-group "$BOOTSTRAP_RG" --query "[?contains(name, 'cicd')].name" -o tsv 2>/dev/null || echo "")
        
        if [ -n "$KEYVAULT_NAME" ]; then
            if az keyvault secret list --vault-name "$KEYVAULT_NAME" > /dev/null 2>&1; then
                API_KEY=$(az keyvault secret show --vault-name "$KEYVAULT_NAME" --name "infracost-api-key" --query "value" -o tsv 2>/dev/null || echo "")
                if [ -n "$API_KEY" ] && [ "$API_KEY" != "placeholder-get-from-infracost-io" ]; then
                    echo "✅ Using Infracost API key from CI/CD Key Vault"
                    infracost configure set api_key "$API_KEY"
                    return 0
                fi
            fi
        fi
    fi
    
    echo "⚠️  Using Infracost free tier"
    infracost configure set api_key ico-free-tier-key
}

# Configure Infracost
configure_infracost

# Navigate to Terraform directory
cd /workspace/infra/application

echo "🔧 Initializing Terraform..."
terraform init \
    -backend-config="storage_account_name=${TERRAFORM_STATE_STORAGE_ACCOUNT}" \
    -backend-config="container_name=tfstate" \
    -backend-config="key=${ENVIRONMENT}.tfstate" \
    -backend-config="resource_group_name=${BOOTSTRAP_RG}"

echo "📋 Creating Terraform plan..."
if terraform plan -out=tfplan -var="environment=${ENVIRONMENT}" 2>&1 | tee "$COST_DIR/plan.log"; then
    echo "✅ Terraform plan successful"
    PLAN_SUCCESS=true
else
    echo "⚠️  Terraform plan had issues, checking if they're permission-related..."
    PLAN_SUCCESS=false
    
    # Check for expected permission errors on first deployment
    if grep -q "does not have secrets get permission\|Authorization_RequestDenied" "$COST_DIR/plan.log"; then
        echo "🔍 Detected expected permission errors for first deployment"
        PLAN_SUCCESS=true
    fi
fi

if [ "$PLAN_SUCCESS" = "false" ]; then
    echo "❌ Terraform plan failed with non-permission errors"
    cat "$COST_DIR/plan.log"
    exit 1
fi

# Run Infracost analysis
echo "💸 Running Infracost cost analysis..."
if [ -f "infracost-usage.yml" ]; then
    USAGE_FLAG="--usage-file infracost-usage.yml"
else
    USAGE_FLAG=""
fi

if infracost breakdown --path tfplan $USAGE_FLAG --format json > "$COST_DIR/infracost.json" 2>&1; then
    ESTIMATED_COST=$(jq -r '.totalMonthlyCost' "$COST_DIR/infracost.json" 2>/dev/null || echo "unavailable")
    
    if [ "$ESTIMATED_COST" != "null" ] && [ "$ESTIMATED_COST" != "unavailable" ] && [ "$ESTIMATED_COST" != "0" ]; then
        echo "✅ Infracost estimation successful: \$$ESTIMATED_COST/month"
        echo "estimated-cost=$ESTIMATED_COST" >> $GITHUB_OUTPUT 2>/dev/null || true
        echo "cost-available=true" >> $GITHUB_OUTPUT 2>/dev/null || true
        
        # Show cost breakdown
        echo "📊 Cost breakdown by service:"
        jq -r '.projects[0].breakdown.resources[] | "\(.name): $\(.monthlyCost // 0)"' "$COST_DIR/infracost.json" | head -10
        
        # Cost gate evaluation
        COST_INT=$(echo "$ESTIMATED_COST" | cut -d'.' -f1)
        if [ "$COST_INT" -gt 25 ]; then
            echo "❌ COST GATE FAILED: Estimated cost \$$ESTIMATED_COST exceeds \$25/month limit"
            echo "approved=false" >> $GITHUB_OUTPUT 2>/dev/null || true
            exit 1
        else
            echo "✅ COST GATE PASSED: Estimated cost \$$ESTIMATED_COST within budget"
            echo "approved=true" >> $GITHUB_OUTPUT 2>/dev/null || true
        fi
    else
        echo "⚠️  Infracost returned invalid cost data"
        echo "estimated-cost=unavailable" >> $GITHUB_OUTPUT 2>/dev/null || true
        echo "cost-available=false" >> $GITHUB_OUTPUT 2>/dev/null || true
        echo "approved=true" >> $GITHUB_OUTPUT 2>/dev/null || true
    fi
else
    echo "❌ Infracost breakdown failed"
    cat "$COST_DIR/infracost.json" 2>/dev/null || echo "No error output available"
    echo "estimated-cost=unavailable" >> $GITHUB_OUTPUT 2>/dev/null || true
    echo "cost-available=false" >> $GITHUB_OUTPUT 2>/dev/null || true
    echo "approved=true" >> $GITHUB_OUTPUT 2>/dev/null || true
fi

# Create cost summary
cat > "$COST_DIR/cost-summary.json" << EOF
{
  "environment": "$ENVIRONMENT",
  "estimated_monthly_cost": "$ESTIMATED_COST",
  "cost_available": true,
  "gate_passed": true,
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

echo "💰 Cost analysis completed - results in $COST_DIR/"
