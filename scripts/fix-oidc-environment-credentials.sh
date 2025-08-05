#!/bin/bash

# Fix OIDC Federated Identity Credentials for Environment-based Deployments
# Run this script tomorrow to fix the staging deployment issue

echo "🔧 Fixing OIDC federated identity credentials for environment deployments..."

# Get the Azure AD application
APP_ID=$(az ad app list --display-name "ai-content-github-actions" --query "[0].appId" -o tsv)
APP_OBJECT_ID=$(az ad app show --id $APP_ID --query "id" -o tsv)

if [ -z "$APP_ID" ]; then
  echo "❌ Azure AD application not found"
  exit 1
fi

echo "✅ Found Azure AD application: $APP_ID"

# Add federated identity credential for staging environment
echo "📝 Adding federated identity credential for staging environment..."
az ad app federated-credential create \
  --id $APP_OBJECT_ID \
  --parameters '{
    "name": "staging-environment",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:Hardcoreprawn/ai-content-farm:environment:staging",
    "description": "Staging environment deployment",
    "audiences": ["api://AzureADTokenExchange"]
  }'

# Add federated identity credential for production environment  
echo "📝 Adding federated identity credential for production environment..."
az ad app federated-credential create \
  --id $APP_OBJECT_ID \
  --parameters '{
    "name": "production-environment", 
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:Hardcoreprawn/ai-content-farm:environment:production",
    "description": "Production environment deployment",
    "audiences": ["api://AzureADTokenExchange"]
  }'

echo "✅ Federated identity credentials added successfully!"
echo ""
echo "🚀 Now you can re-run the pipeline and staging deployment should work."
echo ""
echo "To test, run:"
echo "  gh workflow run \"Consolidated CI/CD Pipeline\""
echo "  # Or push a commit to the develop branch"
