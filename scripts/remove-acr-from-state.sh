#!/bin/bash

# Manual ACR Resource State Cleanup Script
# This script removes legacy ACR resources from Terraform state to prevent deletion attempts
# Usage: ./scripts/remove-acr-from-state.sh production

set -euo pipefail

ENVIRONMENT=${1:-production}
STORAGE_ACCOUNT="aicontentfarmtfstate"
STATE_FILE="terraform-${ENVIRONMENT}.tfstate"

echo "[INFO] Removing legacy ACR resources from Terraform state for environment: $ENVIRONMENT"

# Check if we're authenticated to Azure
if ! az account show >/dev/null 2>&1; then
    echo "[ERROR] Not authenticated to Azure. Please run 'az login' first."
    exit 1
fi

# Navigate to terraform directory
cd "$(dirname "$0")/../infra"

echo "[INFO] Initializing Terraform..."
terraform init -reconfigure \
    -backend-config="key=${STATE_FILE}" \
    -backend-config="storage_account_name=${STORAGE_ACCOUNT}"

echo "[INFO] Checking for legacy ACR resources in state..."

# List of ACR-related resources to remove from state
ACR_RESOURCES=(
    "azurerm_container_registry.main"
    "azurerm_role_assignment.containers_acr_pull"
    "azurerm_role_assignment.github_actions_acr_push"
)

for resource in "${ACR_RESOURCES[@]}"; do
    if terraform state list | grep -q "^${resource}$"; then
        echo "[INFO] Removing $resource from Terraform state..."
        terraform state rm "$resource" || echo "[WARN] Failed to remove $resource (may not exist)"
    else
        echo "[INFO] Resource $resource not found in state (already removed or never existed)"
    fi
done

echo "[INFO] Legacy ACR resource cleanup completed"
echo "[INFO] Next deployment should proceed without ACR deletion attempts"
