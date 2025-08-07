#!/bin/bash

# Remove old Key Vault secret resources from Terraform state
# These are now managed externally via the setup script

set -e

echo "🧹 Cleaning up Terraform state - removing externally managed Key Vault secrets"
echo "This script removes the old secret resources from state since they're now managed externally"
echo ""

cd infra/application

# Configure backend for remote state  
terraform init -backend-config="storage_account_name=aicontentfarm76ko2h" \
              -backend-config="container_name=tfstate" \
              -backend-config="key=staging.tfstate" \
              -backend-config="resource_group_name=ai-content-farm-bootstrap"

echo "📋 Current state resources related to reddit secrets:"
terraform state list | grep reddit || echo "No reddit secrets found in state"

echo ""
echo "🗑️  Removing reddit secret resources from state..."

# Remove the old secret resources from state (they'll continue to exist in Azure, just not managed by Terraform)
terraform state rm azurerm_key_vault_secret.reddit_client_id || echo "reddit_client_id not in state"
terraform state rm azurerm_key_vault_secret.reddit_client_secret || echo "reddit_client_secret not in state" 
terraform state rm azurerm_key_vault_secret.reddit_user_agent || echo "reddit_user_agent not in state"

echo ""
echo "✅ State cleanup completed!"
echo "The secrets still exist in Azure Key Vault but are no longer managed by Terraform."
echo "They are now managed externally via the setup script and referenced by the Function App."
