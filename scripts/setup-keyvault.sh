#!/bin/bash

# Key Vault Setup Script for AI Content Farm
# This script helps configure secrets in Azure Key Vault

set -e

echo "🔐 AI Content Farm - Key Vault Setup"
echo "===================================="

# Check if Azure CLI is installed and logged in
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI is not installed. Please install it first."
    exit 1
fi

# Check if logged in to Azure
if ! az account show &> /dev/null; then
    echo "❌ Not logged in to Azure. Please run 'az login' first."
    exit 1
fi

# Get current subscription
SUBSCRIPTION=$(az account show --query "name" -o tsv)
echo "📋 Current subscription: $SUBSCRIPTION"

# Environment selection
echo ""
echo "Select environment:"
echo "1) Development (ai-content-dev)"
echo "2) Staging (ai-content-staging)"  
echo "3) Production (ai-content-prod)"
read -p "Enter choice (1-3): " ENV_CHOICE

case $ENV_CHOICE in
    1)
        ENVIRONMENT="development"
        RESOURCE_PREFIX="ai-content-dev"
        ;;
    2)
        ENVIRONMENT="staging"
        RESOURCE_PREFIX="ai-content-staging"
        ;;
    3)
        ENVIRONMENT="production"
        RESOURCE_PREFIX="ai-content-prod"
        ;;
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

echo "Selected environment: $ENVIRONMENT"

# Find Key Vault
RESOURCE_GROUP="${RESOURCE_PREFIX}-rg"
echo "🔍 Looking for Key Vault in resource group: $RESOURCE_GROUP"

KEYVAULT_NAME=$(az keyvault list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv 2>/dev/null || echo "")

if [ -z "$KEYVAULT_NAME" ]; then
    echo "❌ Key Vault not found in resource group $RESOURCE_GROUP"
    echo "   Please deploy the infrastructure first with 'make apply'"
    exit 1
fi

echo "✅ Found Key Vault: $KEYVAULT_NAME"

# Configure Reddit API secrets
echo ""
echo "🤖 Reddit API Configuration"
echo "=========================="

read -p "Enter Reddit Client ID (or press Enter to skip): " REDDIT_CLIENT_ID
if [ -n "$REDDIT_CLIENT_ID" ]; then
    echo "Setting reddit-client-id..."
    az keyvault secret set --vault-name "$KEYVAULT_NAME" --name "reddit-client-id" --value "$REDDIT_CLIENT_ID" > /dev/null
    echo "✅ Reddit Client ID stored"
fi

read -s -p "Enter Reddit Client Secret (or press Enter to skip): " REDDIT_CLIENT_SECRET
echo ""
if [ -n "$REDDIT_CLIENT_SECRET" ]; then
    echo "Setting reddit-client-secret..."
    az keyvault secret set --vault-name "$KEYVAULT_NAME" --name "reddit-client-secret" --value "$REDDIT_CLIENT_SECRET" > /dev/null
    echo "✅ Reddit Client Secret stored"
fi

read -p "Enter Reddit User Agent [ai-content-farm:v1.0 (by /u/your-username)]: " REDDIT_USER_AGENT
REDDIT_USER_AGENT=${REDDIT_USER_AGENT:-"ai-content-farm:v1.0 (by /u/your-username)"}
echo "Setting reddit-user-agent..."
az keyvault secret set --vault-name "$KEYVAULT_NAME" --name "reddit-user-agent" --value "$REDDIT_USER_AGENT" > /dev/null
echo "✅ Reddit User Agent stored"

# Configure Infracost API key
echo ""
echo "💰 Infracost Configuration"
echo "========================"

read -s -p "Enter Infracost API Key (get from https://infracost.io): " INFRACOST_API_KEY
echo ""
if [ -n "$INFRACOST_API_KEY" ]; then
    echo "Setting infracost-api-key..."
    az keyvault secret set --vault-name "$KEYVAULT_NAME" --name "infracost-api-key" --value "$INFRACOST_API_KEY" > /dev/null
    echo "✅ Infracost API Key stored"
else
    echo "⚠️  Infracost API key not provided. Cost estimation will be limited."
fi

# Verify stored secrets
echo ""
echo "🔍 Verifying stored secrets..."
echo "=============================="

SECRETS=$(az keyvault secret list --vault-name "$KEYVAULT_NAME" --query "[].name" -o tsv | grep -E "(reddit|infracost)" || echo "")

if [ -n "$SECRETS" ]; then
    echo "✅ Secrets found in Key Vault:"
    for secret in $SECRETS; do
        echo "   - $secret"
    done
else
    echo "⚠️  No secrets found. Please check the configuration."
fi

# GitHub Actions Configuration
echo ""
echo "🚀 GitHub Actions Configuration"
echo "==============================="
echo ""
echo "For GitHub Actions to work, you still need these secrets in GitHub:"
echo ""
echo "Required GitHub Repository Secrets:"
echo "   ARM_CLIENT_ID=<service-principal-client-id>"
echo "   ARM_CLIENT_SECRET=<service-principal-secret>"
echo "   ARM_SUBSCRIPTION_ID=$(az account show --query "id" -o tsv)"
echo "   ARM_TENANT_ID=$(az account show --query "tenantId" -o tsv)"
echo "   AZURE_CREDENTIALS=<service-principal-json>"
echo ""
echo "Optional GitHub Repository Secrets (fallback):"
echo "   INFRACOST_API_KEY=<your-infracost-key> (if not in Key Vault)"
echo ""
echo "To create a service principal for GitHub Actions:"
echo "   az ad sp create-for-rbac --name \"ai-content-farm-cicd\" \\"
echo "     --role contributor \\"
echo "     --scopes /subscriptions/$(az account show --query "id" -o tsv) \\"
echo "     --sdk-auth"
echo ""
echo "✅ Key Vault setup complete for $ENVIRONMENT environment!"
echo "🔐 Key Vault: $KEYVAULT_NAME"
echo "📋 Resource Group: $RESOURCE_GROUP"
