#!/bin/bash

# Azure OIDC Authentication Validation Script
# This script validates the Azure OIDC setup for GitHub Actions

set -e

echo "🔍 Azure OIDC Authentication Validation"
echo "========================================"

# Configuration
CLIENT_ID="effa0588-70ae-4781-b214-20c726f3867e"
TENANT_ID="d1790d70-c02c-4e8e-94ee-e3ccbdb19d19"
SUBSCRIPTION_ID="6b924609-f8c6-4bd2-a873-2b8f55596f67"

echo "📋 Configuration:"
echo "   Client ID: $CLIENT_ID"
echo "   Tenant ID: $TENANT_ID"
echo "   Subscription ID: $SUBSCRIPTION_ID"
echo ""

echo "🔐 Checking App Registration..."
APP_INFO=$(az ad app show --id "$CLIENT_ID" --query "{displayName:displayName, appId:appId}" -o json)
echo "   App Registration: $(echo $APP_INFO | jq -r .displayName)"
echo "   App ID: $(echo $APP_INFO | jq -r .appId)"
echo ""

echo "🌐 Checking Federated Identity Credentials..."
FED_CREDS=$(az ad app federated-credential list --id "$CLIENT_ID" --query "[].{name:name, subject:subject}" -o json)
echo "   Number of federated credentials: $(echo $FED_CREDS | jq length)"
echo $FED_CREDS | jq -r '.[] | "   - \(.name): \(.subject)"'
echo ""

echo "👤 Checking Service Principal..."
SP_INFO=$(az ad sp show --id "$CLIENT_ID" --query "{id:id, displayName:displayName}" -o json)
echo "   Service Principal: $(echo $SP_INFO | jq -r .displayName)"
echo "   Object ID: $(echo $SP_INFO | jq -r .id)"
echo ""

echo "🔑 Checking Role Assignments..."
ROLE_ASSIGNMENTS=$(az role assignment list \
  --assignee "$(echo $SP_INFO | jq -r .id)" \
  --query "[].{role:roleDefinitionName, scope:scope}" -o json)

if [ "$(echo $ROLE_ASSIGNMENTS | jq length)" -eq 0 ]; then
  echo "   ⚠️  No role assignments found directly. Checking resource groups..."

  # Check core resource group
  CORE_RG_ROLES=$(az role assignment list \
    --resource-group "ai-content-farm-core-rg" \
    --query "[?principalId=='$(echo $SP_INFO | jq -r .id)'].{role:roleDefinitionName, scope:scope}" -o json)

  echo "   Core Resource Group roles: $(echo $CORE_RG_ROLES | jq length)"
  echo $CORE_RG_ROLES | jq -r '.[] | "   - \(.role) on \(.scope | split("/") | .[-1])"'

  # Check staging resource group
  STAGING_RG_ROLES=$(az role assignment list \
    --resource-group "ai-content-staging-rg" \
    --query "[?principalId=='$(echo $SP_INFO | jq -r .id)'].{role:roleDefinitionName, scope:scope}" -o json)

  echo "   Staging Resource Group roles: $(echo $STAGING_RG_ROLES | jq length)"
  echo $STAGING_RG_ROLES | jq -r '.[] | "   - \(.role) on \(.scope | split("/") | .[-1])"'
else
  echo "   Number of role assignments: $(echo $ROLE_ASSIGNMENTS | jq length)"
  echo $ROLE_ASSIGNMENTS | jq -r '.[] | "   - \(.role) on \(.scope)"'
fi
echo ""

echo "🏗️  Checking Azure Resources..."
echo "   Resource Groups:"
az group list --query "[].{name:name, location:location}" -o table | sed 's/^/      /'

echo ""
echo "   Container Registries:"
az acr list --query "[].{name:name, resourceGroup:resourceGroup, loginServer:loginServer}" -o table | sed 's/^/      /'

echo ""
echo "   Storage Accounts (for Terraform state):"
az storage account list --query "[].{name:name, resourceGroup:resourceGroup}" -o table | sed 's/^/      /'

echo ""
echo "✅ Azure OIDC Validation Complete!"
echo ""
echo "📌 Next Steps:"
echo "   1. Test the OIDC authentication in GitHub Actions"
echo "   2. Create a small test deployment to main branch"
echo "   3. Monitor the deployment logs for authentication success"
echo "   4. Verify that no secrets are being used for Azure authentication"
echo ""
echo "🔗 GitHub Variables to verify:"
echo "   - AZURE_CLIENT_ID should be: $CLIENT_ID"
echo "   - AZURE_TENANT_ID should be: $TENANT_ID"
echo "   - AZURE_SUBSCRIPTION_ID should be: $SUBSCRIPTION_ID"
