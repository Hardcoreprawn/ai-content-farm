#!/bin/bash
#
# Import Existing Key Vault Secrets into Terraform State
#
# This script imports all existing Key Vault secrets that are defined in Terraform
# but not yet in the state.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(dirname "$SCRIPT_DIR")/infra"

# Key Vault name (from current deployment)
KEY_VAULT_NAME="aicontentprodkvkwakpx"

# Subscription ID
SUBSCRIPTION_ID="6b924609-f8c6-4bd2-a873-2b8f55596f67"

# Resource Group
RESOURCE_GROUP="ai-content-prod-rg"

# List of secrets to import (Terraform resource name -> Azure secret name)
declare -A SECRETS=(
    ["azurerm_key_vault_secret.infracost_api_key"]="infracost-api-key"
    ["azurerm_key_vault_secret.openai_chat_model"]="azure-openai-chat-model"
    ["azurerm_key_vault_secret.openai_embedding_model"]="azure-openai-embedding-model"
    ["azurerm_key_vault_secret.openai_endpoint"]="azure-openai-endpoint"
    ["azurerm_key_vault_secret.reddit_client_id"]="reddit-client-id"
    ["azurerm_key_vault_secret.reddit_client_secret"]="reddit-client-secret"
    ["azurerm_key_vault_secret.reddit_user_agent"]="reddit-user-agent"
)

echo "Importing Key Vault secrets into Terraform state..."
echo "Key Vault: $KEY_VAULT_NAME"
echo "Resource Group: $RESOURCE_GROUP"
echo ""

cd "$INFRA_DIR"

for terraform_resource in "${!SECRETS[@]}"; do
    azure_secret_name="${SECRETS[$terraform_resource]}"

    # Get the secret ID - we need the current version
    echo "Getting secret version for: $azure_secret_name"
    secret_id=$(az keyvault secret show --vault-name "$KEY_VAULT_NAME" --name "$azure_secret_name" --query "id" -o tsv)

    if [[ -n "$secret_id" ]]; then
        echo "Importing $terraform_resource -> $secret_id"
        terraform import "$terraform_resource" "$secret_id" || {
            echo "Warning: Failed to import $terraform_resource. It might already be in state."
        }
        echo ""
    else
        echo "Error: Could not find secret $azure_secret_name in Key Vault"
        exit 1
    fi
done

echo "Import complete! Running terraform plan to verify..."
terraform plan -var="image_tag=a0e9ee6980f5457c103894ae4965db2e856fbeb4" -var="image_fallback_strategy=latest"
