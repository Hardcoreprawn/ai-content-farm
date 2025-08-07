#!/bin/bash

# Setup GitHub Actions with Azure Federated Identity (OIDC)
# This is the modern, secure approach using managed identity instead of service principals

set -e

echo "🔐 GitHub Actions Azure OIDC Setup"
echo "=================================="
echo ""
echo "This script sets up Federated Identity Credentials for GitHub Actions"
echo "to authenticate with Azure using OIDC tokens instead of secrets."
echo ""
echo "🔍 Benefits:"
echo "   ✅ No secrets stored in GitHub"
echo "   ✅ Automatic credential rotation"
echo "   ✅ Stronger security with OIDC"
echo "   ✅ Auditable with Azure AD logs"
echo ""

# Check if Azure CLI is available and authenticated
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI not found. Please install Azure CLI first."
    exit 1
fi

if ! az account show &> /dev/null; then
    echo "❌ Not authenticated to Azure. Please run 'az login' first."
    exit 1
fi

echo "✅ Azure CLI authenticated"
echo ""

# Get current subscription and tenant info
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)

echo "📋 Current Azure Context:"
echo "   Subscription ID: $SUBSCRIPTION_ID"
echo "   Tenant ID: $TENANT_ID"
echo ""

# Get GitHub repository info
REPO_URL=$(git remote get-url origin 2>/dev/null || echo "")
if [[ $REPO_URL == *"github.com"* ]]; then
    # Extract owner/repo from URL
    REPO_INFO=$(echo "$REPO_URL" | sed 's/.*github\.com[:/]\([^/]*\/[^/]*\)\.git.*/\1/' | sed 's/\.git$//')
    REPO_OWNER=$(echo "$REPO_INFO" | cut -d'/' -f1)
    REPO_NAME=$(echo "$REPO_INFO" | cut -d'/' -f2)
else
    read -p "Enter GitHub repository owner: " REPO_OWNER
    read -p "Enter GitHub repository name: " REPO_NAME
fi

echo "📱 GitHub Repository:"
echo "   Owner: $REPO_OWNER"
echo "   Repository: $REPO_NAME"
echo ""

# Create Azure AD Application
APP_NAME="ai-content-farm-github-oidc"
echo "🏗️  Creating Azure AD Application: $APP_NAME"

APP_ID=$(az ad app create \
    --display-name "$APP_NAME" \
    --query appId -o tsv)

echo "✅ Created Application: $APP_ID"

# Create Service Principal
echo "🔑 Creating Service Principal..."
SP_OBJECT_ID=$(az ad sp create \
    --id "$APP_ID" \
    --query id -o tsv)

echo "✅ Created Service Principal: $SP_OBJECT_ID"

# Create Federated Identity Credentials for different GitHub contexts
echo "🔗 Creating Federated Identity Credentials..."

# Main branch (production)
az ad app federated-credential create \
    --id "$APP_ID" \
    --parameters '{
        "name": "main-branch",
        "issuer": "https://token.actions.githubusercontent.com",
        "subject": "repo:'$REPO_OWNER'/'$REPO_NAME':ref:refs/heads/main",
        "description": "Main branch deployment",
        "audiences": ["api://AzureADTokenExchange"]
    }'

# Develop branch (staging)
az ad app federated-credential create \
    --id "$APP_ID" \
    --parameters '{
        "name": "develop-branch", 
        "issuer": "https://token.actions.githubusercontent.com",
        "subject": "repo:'$REPO_OWNER'/'$REPO_NAME':ref:refs/heads/develop",
        "description": "Develop branch deployment",
        "audiences": ["api://AzureADTokenExchange"]
    }'

# Pull requests
az ad app federated-credential create \
    --id "$APP_ID" \
    --parameters '{
        "name": "pull-requests",
        "issuer": "https://token.actions.githubusercontent.com", 
        "subject": "repo:'$REPO_OWNER'/'$REPO_NAME':pull_request",
        "description": "Pull request validation",
        "audiences": ["api://AzureADTokenExchange"]
    }'

echo "✅ Created Federated Identity Credentials"

# Assign Contributor role to the Service Principal
echo "🔐 Assigning Contributor role..."
az role assignment create \
    --assignee-object-id "$SP_OBJECT_ID" \
    --assignee-principal-type ServicePrincipal \
    --role "Contributor" \
    --scope "/subscriptions/$SUBSCRIPTION_ID"

echo "✅ Assigned Contributor role"

# Set GitHub repository variables (not secrets!)
echo "📝 Setting GitHub repository variables..."

if command -v gh &> /dev/null && gh auth status &> /dev/null; then
    gh variable set AZURE_CLIENT_ID --body "$APP_ID"
    gh variable set AZURE_SUBSCRIPTION_ID --body "$SUBSCRIPTION_ID" 
    gh variable set AZURE_TENANT_ID --body "$TENANT_ID"
    echo "✅ Set GitHub repository variables"
else
    echo "⚠️  GitHub CLI not available. Please set these as repository variables manually:"
    echo "   AZURE_CLIENT_ID: $APP_ID"
    echo "   AZURE_SUBSCRIPTION_ID: $SUBSCRIPTION_ID"
    echo "   AZURE_TENANT_ID: $TENANT_ID"
fi

echo ""
echo "🎉 OIDC Setup Complete!"
echo ""
echo "📋 Summary:"
echo "   Azure AD Application: $APP_ID"
echo "   Service Principal: $SP_OBJECT_ID"
echo "   Federated Credentials: 3 (main, develop, pull_request)"
echo "   Role Assignment: Contributor on subscription"
echo ""
echo "🚀 Next Steps:"
echo "   1. Update GitHub Actions workflows to use OIDC authentication"
echo "   2. Remove any existing ARM_CLIENT_SECRET from GitHub secrets"
echo "   3. Test deployment with secure OIDC authentication"
echo ""
echo "📖 Repository Variables Set:"
echo "   - AZURE_CLIENT_ID (not a secret!)"
echo "   - AZURE_SUBSCRIPTION_ID (not a secret!)"
echo "   - AZURE_TENANT_ID (not a secret!)"
echo ""
