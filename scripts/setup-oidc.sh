#!/bin/bash

# Setup OIDC Authentication for GitHub Actions
# This script configures Azure Managed Identity with Federated Identity Credentials

set -e

REPO_OWNER="Hardcoreprawn"
REPO_NAME="ai-content-farm"

echo "🔐 GitHub Actions OIDC Setup"
echo "============================"
echo ""

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI not found. Please install Azure CLI first."
    exit 1
fi

if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI not found. Please install GitHub CLI first."
    exit 1
fi

if ! command -v terraform &> /dev/null; then
    echo "❌ Terraform not found. Please install Terraform first."
    exit 1
fi

echo "✅ All prerequisites found"
echo ""

# Check Azure login
echo "🔑 Checking Azure authentication..."
if ! az account show &> /dev/null; then
    echo "❌ Not logged into Azure. Please run 'az login' first."
    exit 1
fi

SUBSCRIPTION_ID=$(az account show --query "id" -o tsv)
TENANT_ID=$(az account show --query "tenantId" -o tsv)
echo "✅ Logged into Azure"
echo "   Subscription: $SUBSCRIPTION_ID"
echo "   Tenant: $TENANT_ID"
echo ""

# Check GitHub login
echo "📱 Checking GitHub authentication..."
if ! gh auth status &> /dev/null; then
    echo "❌ Not logged into GitHub. Please run 'gh auth login' first."
    exit 1
fi
echo "✅ Logged into GitHub"
echo ""

# Deploy infrastructure with managed identity
echo "🏗️  Deploying infrastructure with managed identity..."
cd infra

if [ ! -f ".terraform/terraform.tfstate" ]; then
    echo "   Initializing Terraform..."
    terraform init
fi

echo "   Planning deployment..."
terraform plan -out=tfplan

echo "   Applying infrastructure changes..."
terraform apply tfplan

echo "✅ Infrastructure deployed"
echo ""

# Get outputs from Terraform
echo "📤 Getting Terraform outputs..."
CLIENT_ID=$(terraform output -raw github_actions_client_id)
TENANT_ID=$(terraform output -raw tenant_id)
SUBSCRIPTION_ID=$(terraform output -raw subscription_id)

if [ -z "$CLIENT_ID" ]; then
    echo "❌ Failed to get client ID from Terraform output"
    exit 1
fi

echo "✅ Retrieved values:"
echo "   Client ID: $CLIENT_ID"
echo "   Tenant ID: $TENANT_ID"
echo "   Subscription ID: $SUBSCRIPTION_ID"
echo ""

# Set GitHub repository variables
echo "🔧 Setting GitHub repository variables..."

gh variable set AZURE_CLIENT_ID --body "$CLIENT_ID" --repo "$REPO_OWNER/$REPO_NAME"
gh variable set AZURE_TENANT_ID --body "$TENANT_ID" --repo "$REPO_OWNER/$REPO_NAME"
gh variable set AZURE_SUBSCRIPTION_ID --body "$SUBSCRIPTION_ID" --repo "$REPO_OWNER/$REPO_NAME"

echo "✅ GitHub variables configured"
echo ""

# Clean up any old secrets
echo "🧹 Cleaning up legacy secrets..."

# List of legacy secrets to remove
LEGACY_SECRETS=(
    "ARM_CLIENT_ID"
    "ARM_CLIENT_SECRET" 
    "ARM_SUBSCRIPTION_ID"
    "ARM_TENANT_ID"
    "AZURE_CREDENTIALS"
    "AZURE_CLIENT_SECRET"
)

for secret in "${LEGACY_SECRETS[@]}"; do
    if gh secret list --repo "$REPO_OWNER/$REPO_NAME" | grep -q "$secret"; then
        echo "   Removing legacy secret: $secret"
        gh secret delete "$secret" --repo "$REPO_OWNER/$REPO_NAME" || true
    fi
done

echo "✅ Legacy secrets cleaned up"
echo ""

# Verify configuration
echo "🔍 Verifying configuration..."

echo "   Repository variables:"
gh variable list --repo "$REPO_OWNER/$REPO_NAME" | grep "AZURE_"

echo ""
echo "   Managed Identity in Azure:"
az identity show --name "ai-content-farm-core-github-actions" --resource-group "ai-content-farm-core-rg" --query "{name:name, clientId:clientId, principalId:principalId}" -o table

echo ""
echo "   Federated Identity Credentials:"
az identity federated-credential list --name "ai-content-farm-core-github-actions" --resource-group "ai-content-farm-core-rg" --query "[].{name:name, subject:subject}" -o table

echo ""
echo "🎉 OIDC Setup Complete!"
echo "======================"
echo ""
echo "✅ **Zero secrets stored**: No credentials in GitHub or anywhere else"
echo "✅ **Automatic rotation**: Tokens refresh every 15 minutes"  
echo "✅ **Secure by default**: Federated identity with scoped access"
echo "✅ **Production ready**: Modern Azure/GitHub best practices"
echo ""
echo "🚀 **Next Steps:**"
echo "1. Test the pipeline by pushing to main or develop branch"
echo "2. Monitor workflow for successful OIDC authentication"
echo "3. Verify deployment completes without any stored credentials"
echo ""
echo "🔗 **Documentation:**"
echo "- GitHub OIDC Guide: docs/GITHUB_SECRETS_SETUP.md" 
echo "- Managed Identity: infra/container_apps.tf"
echo "- Workflow config: .github/workflows/cicd-pipeline.yml"
echo ""
echo "💡 **Troubleshooting:**"
echo "If authentication fails, check:"
echo "- Repository name matches: $REPO_OWNER/$REPO_NAME"
echo "- Branch names are correct (main/develop)"
echo "- Managed identity has proper role assignments"
