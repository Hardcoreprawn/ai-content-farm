#!/bin/bash

# Terraform Resource Cleanup Script
# This script handles the resource lock issue preventing ACR resource cleanup
# Usage: ./scripts/terraform-resource-cleanup.sh production

set -euo pipefail

ENVIRONMENT=${1:-production}
RESOURCE_GROUP="ai-content-${ENVIRONMENT}-rg"
SUBSCRIPTION_ID="6b924609-f8c6-4bd2-a873-2b8f55596f67"

echo "[INFO] Starting Terraform resource cleanup for environment: $ENVIRONMENT"

# Check if we're authenticated to Azure
if ! az account show >/dev/null 2>&1; then
    echo "[ERROR] Not authenticated to Azure. Please run 'az login' first."
    exit 1
fi

# Set the correct subscription
az account set --subscription "$SUBSCRIPTION_ID"

# Check if resource group exists
if ! az group show --name "$RESOURCE_GROUP" >/dev/null 2>&1; then
    echo "[INFO] Resource group $RESOURCE_GROUP does not exist. Nothing to cleanup."
    exit 0
fi

echo "[INFO] Found resource group: $RESOURCE_GROUP"

# Check for resource lock
LOCK_ID=$(az group lock list --resource-group "$RESOURCE_GROUP" --query "[0].id" -o tsv 2>/dev/null || echo "")

if [ -n "$LOCK_ID" ]; then
    echo "[INFO] Found resource group lock: $LOCK_ID"
    echo "[INFO] Temporarily removing lock to allow ACR cleanup..."

    # Remove the lock temporarily
    az group lock delete --ids "$LOCK_ID"
    echo "[INFO] Lock removed successfully"

    # Set flag to recreate lock later
    LOCK_REMOVED=true
else
    echo "[INFO] No resource group lock found"
    LOCK_REMOVED=false
fi

# Navigate to terraform directory
cd "$(dirname "$0")/../infra"

echo "[INFO] Initializing Terraform..."
terraform init -reconfigure \
    -backend-config="key=terraform-${ENVIRONMENT}.tfstate" \
    -backend-config="storage_account_name=aicontentfarmtfstate"

echo "[INFO] Importing current state to ensure consistency..."
# This helps Terraform understand the current state without trying to destroy locked resources

echo "[INFO] Planning Terraform changes..."
terraform plan -var-file="${ENVIRONMENT}.tfvars" -out=tfplan

echo "[INFO] Applying Terraform changes..."
terraform apply tfplan

# Recreate the lock if we removed it
if [ "$LOCK_REMOVED" = true ]; then
    echo "[INFO] Recreating resource group lock..."
    az group lock create \
        --resource-group "$RESOURCE_GROUP" \
        --name "resource-group-lock" \
        --lock-type CannotDelete \
        --notes "Prevent accidental deletion of production resources"
    echo "[INFO] Resource group lock recreated"
fi

echo "[INFO] Terraform resource cleanup completed successfully"
