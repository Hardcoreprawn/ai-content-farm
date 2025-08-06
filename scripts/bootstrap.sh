#!/bin/bash
set -e

# AI Content Farm Bootstrap Setup Script
# This script sets up the foundation infrastructure for the AI Content Farm project

echo "🚀 AI Content Farm Bootstrap Setup"
echo "=================================="
echo ""

# Check if user is logged into Azure
if ! az account show &>/dev/null; then
    echo "❌ You need to be logged into Azure CLI first"
    echo "   Run: az login"
    exit 1
fi

# Get current Azure context
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)

echo "✅ Azure context:"
echo "   Subscription: $SUBSCRIPTION_ID"
echo "   Tenant: $TENANT_ID"
echo ""

# Set environment (default to staging)
ENVIRONMENT=${1:-staging}
echo "🌍 Environment: $ENVIRONMENT"
echo ""

# Run bootstrap
echo "🔧 Step 1: Creating bootstrap infrastructure..."
cd infra/bootstrap
terraform init
terraform plan -var="environment=$ENVIRONMENT"

echo ""
read -p "🤔 Proceed with bootstrap? (y/N): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Bootstrap cancelled"
    exit 1
fi

terraform apply -var="environment=$ENVIRONMENT" -auto-approve

echo ""
echo "✅ Bootstrap infrastructure created!"
echo ""

# Get outputs for GitHub setup
echo "🔑 Step 2: GitHub Repository Variables"
echo "======================================"
echo "Set these variables in your GitHub repository:"
echo "GitHub Settings → Secrets and Variables → Actions → Variables"
echo ""

# Get the values
AZURE_CLIENT_ID=$(terraform output -raw azure_client_id)
STORAGE_ACCOUNT=$(terraform output -raw storage_account_name)

echo "AZURE_CLIENT_ID = $AZURE_CLIENT_ID"
echo "AZURE_TENANT_ID = $TENANT_ID"
echo "AZURE_SUBSCRIPTION_ID = $SUBSCRIPTION_ID"
echo "TERRAFORM_STATE_STORAGE_ACCOUNT = $STORAGE_ACCOUNT"
echo ""

# GitHub CLI setup if available
if command -v gh &> /dev/null; then
    echo "🤖 Found GitHub CLI. Setting variables automatically..."
    gh variable set AZURE_CLIENT_ID --body "$AZURE_CLIENT_ID"
    gh variable set AZURE_TENANT_ID --body "$TENANT_ID"
    gh variable set AZURE_SUBSCRIPTION_ID --body "$SUBSCRIPTION_ID"
    gh variable set TERRAFORM_STATE_STORAGE_ACCOUNT --body "$STORAGE_ACCOUNT"
    echo "✅ GitHub variables set automatically!"
else
    echo "💡 Install GitHub CLI (gh) to set variables automatically"
fi

echo ""
echo "🏗️ Step 3: Configuring main Terraform..."
cd ..
terraform init -reconfigure \
    -backend-config="storage_account_name=$STORAGE_ACCOUNT" \
    -backend-config="container_name=tfstate" \
    -backend-config="key=$ENVIRONMENT.tfstate" \
    -backend-config="resource_group_name=ai-content-farm-bootstrap"

echo ""
echo "🎉 Bootstrap Complete!"
echo "===================="
echo ""
echo "✅ What was created:"
echo "   • Azure AD Application: ai-content-farm-github-$ENVIRONMENT"
echo "   • Storage Account: $STORAGE_ACCOUNT (for Terraform state)"
echo "   • Resource Group: ai-content-farm-bootstrap"
echo "   • GitHub repository variables configured"
echo "   • Main Terraform configured for remote state"
echo ""
echo "🚀 Next steps:"
echo "   1. Run 'make apply' to deploy the main infrastructure"
echo "   2. Your GitHub Actions pipeline will now use proper OIDC and remote state"
echo "   3. All infrastructure changes will be tracked in remote state"
echo ""
