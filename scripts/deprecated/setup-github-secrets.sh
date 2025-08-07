#!/bin/bash

# Setup GitHub Secrets for Azure Authentication
# This script helps set up the minimal required secrets for Azure Key Vault integration

set -e

echo "🔐 GitHub Secrets Setup for Azure Key Vault Integration"
echo "====================================================="
echo ""
echo "This script will help you set up the minimal GitHub secrets required"
echo "for Azure authentication. All application secrets will be stored in"
echo "Azure Key Vault for better security."
echo ""

# Check if gh CLI is authenticated
if ! gh auth status >/dev/null 2>&1; then
    echo "❌ GitHub CLI not authenticated. Please run 'gh auth login' first."
    exit 1
fi

echo "✅ GitHub CLI authenticated"
echo ""

# Function to set secret with validation
set_secret() {
    local secret_name="$1"
    local description="$2"
    
    echo "Setting up: $secret_name"
    echo "Description: $description"
    echo ""
    
    # Prompt for secret value
    read -s -p "Enter value for $secret_name: " secret_value
    echo ""
    
    if [ -z "$secret_value" ]; then
        echo "⚠️  Empty value provided. Skipping $secret_name"
        echo ""
        return
    fi
    
    # Set the secret
    if echo "$secret_value" | gh secret set "$secret_name"; then
        echo "✅ Successfully set $secret_name"
    else
        echo "❌ Failed to set $secret_name"
    fi
    echo ""
}

echo "🚀 Setting up Azure authentication secrets..."
echo ""
echo "🔍 Authentication Architecture:"
echo "   - GitHub Actions: Uses Service Principal for deployment"
echo "   - Function Apps: Use System-Assigned Managed Identity for runtime"
echo "   - Key Vault Access: Functions access via Managed Identity (no secrets needed)"
echo ""
echo "You'll need these values from your Azure Service Principal for GitHub Actions."
echo "This is separate from the Function App's Managed Identity which is created automatically."
echo ""
echo "If you don't have a Service Principal, create one with:"
echo "  az ad sp create-for-rbac --name 'ai-content-farm-github' --role contributor --scopes /subscriptions/YOUR_SUBSCRIPTION_ID"
echo ""

# Set each required secret
set_secret "ARM_CLIENT_ID" "Azure Service Principal Client ID (Application ID)"
set_secret "ARM_CLIENT_SECRET" "Azure Service Principal Client Secret"
set_secret "ARM_SUBSCRIPTION_ID" "Azure Subscription ID"
set_secret "ARM_TENANT_ID" "Azure Tenant ID"

echo "🔍 Creating AZURE_CREDENTIALS JSON..."
echo "This is a combined JSON format that some GitHub Actions require."
echo ""

# Prompt for AZURE_CREDENTIALS JSON format
echo "Please provide the AZURE_CREDENTIALS JSON (full service principal JSON):"
echo "Example format:"
echo '{'
echo '  "clientId": "your-client-id",'
echo '  "clientSecret": "your-client-secret",'
echo '  "subscriptionId": "your-subscription-id",'
echo '  "tenantId": "your-tenant-id"'
echo '}'
echo ""

read -s -p "Enter AZURE_CREDENTIALS JSON: " azure_credentials
echo ""

if [ -n "$azure_credentials" ]; then
    if echo "$azure_credentials" | gh secret set "AZURE_CREDENTIALS"; then
        echo "✅ Successfully set AZURE_CREDENTIALS"
    else
        echo "❌ Failed to set AZURE_CREDENTIALS"
    fi
else
    echo "⚠️  Skipping AZURE_CREDENTIALS"
fi

echo ""
echo "🎉 GitHub Secrets Setup Complete!"
echo ""
echo "📋 Summary of secrets that should now be configured:"
gh secret list

echo ""
echo "🔐 Security Note:"
echo "   - These secrets are for GitHub Actions deployment authentication only"
echo "   - Function Apps use System-Assigned Managed Identity at runtime"
echo "   - Application secrets (Reddit API, etc.) are stored in Azure Key Vault"
echo "   - Functions access Key Vault secrets via Managed Identity (no hardcoded credentials)"
echo ""
echo "🚀 Next Steps:"
echo "   1. Verify all secrets are set correctly above"
echo "   2. Push a change to trigger staging deployment"
echo "   3. Monitor GitHub Actions for deployment progress"
echo "   4. Configure application secrets in Azure Key Vault after deployment"
echo ""
