#!/bin/bash
#
# Import Existing Container Apps into Terraform State
#
# This script imports all existing Container Apps that are defined in Terraform
# but not yet in the state.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(dirname "$SCRIPT_DIR")/infra"

# Subscription ID
SUBSCRIPTION_ID="6b924609-f8c6-4bd2-a873-2b8f55596f67"

# Resource Group
RESOURCE_GROUP="ai-content-prod-rg"

# List of Container Apps to import (Terraform resource name -> Azure Container App name)
declare -A CONTAINER_APPS=(
    ["azurerm_container_app.content_collector"]="ai-content-prod-collector"
    ["azurerm_container_app.content_processor"]="ai-content-prod-processor"
    ["azurerm_container_app.site_generator"]="ai-content-prod-site-generator"
)

echo "Importing Container Apps into Terraform state..."
echo "Resource Group: $RESOURCE_GROUP"
echo ""

cd "$INFRA_DIR"

for terraform_resource in "${!CONTAINER_APPS[@]}"; do
    container_app_name="${CONTAINER_APPS[$terraform_resource]}"

    # Construct the full Azure resource ID
    container_app_id="/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.App/containerApps/$container_app_name"

    echo "Importing $terraform_resource -> $container_app_id"
    terraform import "$terraform_resource" "$container_app_id" || {
        echo "Warning: Failed to import $terraform_resource. It might already be in state."
    }
    echo ""
done

echo "Container Apps import complete! Running terraform plan to verify..."
terraform plan -var="image_tag=a0e9ee6980f5457c103894ae4965db2e856fbeb4" -var="image_fallback_strategy=latest"
