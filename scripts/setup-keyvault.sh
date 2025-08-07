#!/bin/bash

# Key Vault Setup Script for AI Content Farm
# This script sets up secrets in both the CI/CD and Application Key Vaults

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT=${1:-staging}
BOOTSTRAP_RG="ai-content-farm-bootstrap"
APPLICATION_RG="ai-content-${ENVIRONMENT}-rg"

echo -e "${BLUE}🔐 Key Vault Setup for AI Content Farm${NC}"
echo -e "Environment: ${YELLOW}${ENVIRONMENT}${NC}"
echo ""

# Function to discover key vault names
discover_vaults() {
    echo -e "${BLUE}🔍 Discovering Key Vaults...${NC}"
    
    # Find CI/CD vault in bootstrap resource group
    CICD_VAULT=$(az keyvault list --resource-group "${BOOTSTRAP_RG}" --query "[0].name" -o tsv 2>/dev/null || echo "")
    
    # Find Application vault in application resource group  
    APP_VAULT=$(az keyvault list --resource-group "${APPLICATION_RG}" --query "[0].name" -o tsv 2>/dev/null || echo "")
    
    if [[ -z "$CICD_VAULT" ]]; then
        echo -e "${RED}❌ CI/CD Key Vault not found in ${BOOTSTRAP_RG}${NC}"
        echo "Please run 'make bootstrap' first to create the bootstrap infrastructure."
        exit 1
    fi
    
    if [[ -z "$APP_VAULT" ]]; then
        echo -e "${RED}❌ Application Key Vault not found in ${APPLICATION_RG}${NC}"
        echo "Please run 'make deploy' first to create the application infrastructure."
        exit 1
    fi
    
    echo -e "${GREEN}✅ Found CI/CD Key Vault: ${CICD_VAULT}${NC}"
    echo -e "${GREEN}✅ Found Application Key Vault: ${APP_VAULT}${NC}"
}

# Function to set a secret with confirmation
set_secret() {
    local vault_name=$1
    local secret_name=$2
    local description=$3
    local is_sensitive=${4:-true}
    
    echo ""
    echo -e "${YELLOW}Setting: ${secret_name}${NC}"
    echo -e "Description: ${description}"
    echo -e "Vault: ${vault_name}"
    
    if [[ "$is_sensitive" == "true" ]]; then
        read -s -p "Enter value (hidden): " secret_value
        echo ""
    else
        read -p "Enter value: " secret_value
    fi
    
    if [[ -n "$secret_value" ]]; then
        az keyvault secret set \
            --vault-name "$vault_name" \
            --name "$secret_name" \
            --value "$secret_value" \
            --output none
        echo -e "${GREEN}✅ Secret '${secret_name}' set successfully${NC}"
    else
        echo -e "${YELLOW}⚠️  Skipping empty secret '${secret_name}'${NC}"
    fi
}

# Function to setup CI/CD secrets
setup_cicd_secrets() {
    echo ""
    echo -e "${BLUE}🚀 Setting up CI/CD secrets in ${CICD_VAULT}${NC}"
    
    # GitHub Actions OIDC identifiers (not secrets since we use federated credentials)
    set_secret "$CICD_VAULT" "azure-client-id" "Azure Service Principal Client ID for GitHub Actions OIDC" false
    set_secret "$CICD_VAULT" "azure-tenant-id" "Azure Tenant ID for GitHub Actions OIDC" false
    set_secret "$CICD_VAULT" "azure-subscription-id" "Azure Subscription ID for GitHub Actions OIDC" false
    
    # Optional: Update Infracost API key if you have one
    echo ""
    echo -e "${YELLOW}Infracost API key already exists with placeholder. Update it? (y/N)${NC}"
    read -p "Update Infracost key: " update_infracost
    if [[ "$update_infracost" == "y" ]]; then
        set_secret "$CICD_VAULT" "infracost-api-key" "Infracost API key for cost estimation"
    fi
}

# Function to setup application secrets
setup_application_secrets() {
    echo ""
    echo -e "${BLUE}🚀 Setting up Application secrets in ${APP_VAULT}${NC}"
    
    # Only the Reddit API credentials that are actually used by the functions
    echo -e "${YELLOW}Setting up Reddit API credentials (required for functions to work)${NC}"
    set_secret "$APP_VAULT" "reddit-client-id" "Reddit API Client ID"
    set_secret "$APP_VAULT" "reddit-client-secret" "Reddit API Client Secret" 
    set_secret "$APP_VAULT" "reddit-user-agent" "Reddit API User Agent" false
    
    echo ""
    echo -e "${GREEN}✅ Application secrets configured!${NC}"
    echo -e "${YELLOW}Note: Storage and Application Insights are automatically configured by Terraform.${NC}"
}

# Main execution
main() {
    # Check Azure CLI login
    if ! az account show >/dev/null 2>&1; then
        echo -e "${RED}❌ Please run 'az login' first${NC}"
        exit 1
    fi
    
    # Discover vaults
    discover_vaults
    
    echo ""
    echo -e "${YELLOW}What would you like to set up?${NC}"
    echo "1) CI/CD secrets only"
    echo "2) Application secrets only"  
    echo "3) Both CI/CD and Application secrets"
    echo "4) Exit"
    
    read -p "Choose an option (1-4): " choice
    
    case $choice in
        1)
            setup_cicd_secrets
            ;;
        2)
            setup_application_secrets
            ;;
        3)
            setup_cicd_secrets
            setup_application_secrets
            ;;
        4)
            echo -e "${BLUE}👋 Exiting...${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Invalid choice${NC}"
            exit 1
            ;;
    esac
    
    echo ""
    echo -e "${GREEN}🎉 Key Vault setup completed successfully!${NC}"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "• Update your function app settings to reference these Key Vault secrets"
    echo "• Test your application to ensure secrets are accessible"
    echo "• Consider setting up secret rotation policies"
}

# Run main function
main "$@"
