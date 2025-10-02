#!/usr/bin/env bash
set -euo pipefail

# Configure KEDA Managed Identity Authentication for Azure Container Apps
# This script configures KEDA scale rules to use workload identity (managed identity)
# for authenticating to Azure Storage Queues.
#
# CONTEXT: The azurerm Terraform provider doesn't support configuring workload identity
# for KEDA scale rules. This must be done via Azure CLI after Terraform creates the
# container apps. This script should be run:
# 1. After initial Terraform deployment
# 2. After any Terraform changes to container app scale rules
# 3. Via null_resource local-exec provisioner (future enhancement)
#
# Reference: This configuration worked on Sept 19, 2025 before being wiped by subsequent
# Terraform applies.

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
RESOURCE_GROUP="${RESOURCE_GROUP:-ai-content-prod-rg}"
MANAGED_IDENTITY_NAME="${MANAGED_IDENTITY_NAME:-ai-content-prod-containers-identity}"
STORAGE_ACCOUNT_NAME="${STORAGE_ACCOUNT_NAME:-aicontentprodstkwakpx}"

echo -e "${GREEN}=== Configuring KEDA Managed Identity Authentication ===${NC}"
echo "Resource Group: ${RESOURCE_GROUP}"
echo "Managed Identity: ${MANAGED_IDENTITY_NAME}"
echo "Storage Account: ${STORAGE_ACCOUNT_NAME}"
echo

# Get managed identity client ID
echo -e "${YELLOW}Fetching managed identity client ID...${NC}"
CLIENT_ID=$(az identity show \
  --name "${MANAGED_IDENTITY_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query clientId \
  --output tsv)

if [ -z "${CLIENT_ID}" ]; then
  echo -e "${RED}ERROR: Could not fetch managed identity client ID${NC}"
  exit 1
fi

echo -e "${GREEN}✓ Managed Identity Client ID: ${CLIENT_ID}${NC}"
echo

# Configure content-processor KEDA scale rule
echo -e "${YELLOW}Configuring KEDA auth for content-processor...${NC}"
az containerapp update \
  --name ai-content-prod-processor \
  --resource-group "${RESOURCE_GROUP}" \
  --scale-rule-name storage-queue-scaler \
  --scale-rule-type azure-queue \
  --scale-rule-metadata \
    accountName="${STORAGE_ACCOUNT_NAME}" \
    queueName=content-processing-requests \
    queueLength=1 \
    cloud=AzurePublicCloud \
  --scale-rule-auth workloadIdentity="${CLIENT_ID}" \
  --output none

echo -e "${GREEN}✓ Configured content-processor KEDA authentication${NC}"

# Configure site-generator KEDA scale rule
echo -e "${YELLOW}Configuring KEDA auth for site-generator...${NC}"
az containerapp update \
  --name ai-content-prod-site-generator \
  --resource-group "${RESOURCE_GROUP}" \
  --scale-rule-name storage-queue-scaler \
  --scale-rule-type azure-queue \
  --scale-rule-metadata \
    accountName="${STORAGE_ACCOUNT_NAME}" \
    queueName=site-generation-requests \
    queueLength=1 \
    cloud=AzurePublicCloud \
  --scale-rule-auth workloadIdentity="${CLIENT_ID}" \
  --output none

echo -e "${GREEN}✓ Configured site-generator KEDA authentication${NC}"
echo

# Verify configuration
echo -e "${YELLOW}Verifying KEDA configuration...${NC}"
PROCESSOR_CONFIG=$(az containerapp show \
  --name ai-content-prod-processor \
  --resource-group "${RESOURCE_GROUP}" \
  --query "properties.template.scale.rules[?name=='storage-queue-scaler']" \
  --output json)

SITE_GEN_CONFIG=$(az containerapp show \
  --name ai-content-prod-site-generator \
  --resource-group "${RESOURCE_GROUP}" \
  --query "properties.template.scale.rules[?name=='storage-queue-scaler']" \
  --output json)

echo "Processor Scale Rule:"
echo "${PROCESSOR_CONFIG}" | jq '.'
echo
echo "Site Generator Scale Rule:"
echo "${SITE_GEN_CONFIG}" | jq '.'
echo

echo -e "${GREEN}=== KEDA Authentication Configuration Complete ===${NC}"
echo
echo -e "${YELLOW}NOTE: This configuration will be wiped out by the next 'terraform apply'${NC}"
echo -e "${YELLOW}TODO: Integrate this script into Terraform using null_resource or azapi provider${NC}"
