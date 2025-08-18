#!/bin/bash
"""
Local Development Environment Setup

This script helps configure local development to use Azure Key Vault
for secrets while using Azurite for storage emulation.
"""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔧 AI Content Farm - Local Development Setup${NC}"
echo "=============================================="

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}📝 Creating .env file for local development...${NC}"
    touch .env
fi

echo -e "\n${BLUE}🔑 Azure Key Vault Configuration${NC}"
echo "For local development, you can connect to your Azure Key Vault in the cloud"
echo "while using Azurite for storage emulation."
echo ""

# Function to prompt for input with default
prompt_with_default() {
    local prompt="$1"
    local default="$2"
    local var_name="$3"
    
    if [ -n "$default" ]; then
        read -p "$prompt [$default]: " input
        value="${input:-$default}"
    else
        read -p "$prompt: " value
    fi
    
    # Update or add to .env file
    if grep -q "^$var_name=" .env; then
        # Update existing line
        sed -i "s|^$var_name=.*|$var_name=$value|" .env
    else
        # Add new line
        echo "$var_name=$value" >> .env
    fi
}

# Get current values from .env if they exist
current_kv_url=$(grep "^AZURE_KEY_VAULT_URL=" .env 2>/dev/null | cut -d'=' -f2- || echo "")
current_client_id=$(grep "^AZURE_CLIENT_ID=" .env 2>/dev/null | cut -d'=' -f2- || echo "")
current_tenant_id=$(grep "^AZURE_TENANT_ID=" .env 2>/dev/null | cut -d'=' -f2- || echo "")

echo "1. Azure Key Vault URL (e.g., https://your-keyvault.vault.azure.net/)"
prompt_with_default "   Enter Key Vault URL" "$current_kv_url" "AZURE_KEY_VAULT_URL"

echo ""
echo "2. Azure Authentication (for Key Vault access)"
echo "   You can use either:"
echo "   - Service Principal (Client ID + Client Secret)"
echo "   - Azure CLI login (az login)"
echo "   - Managed Identity (in Azure environments)"
echo ""

read -p "Do you want to configure Service Principal authentication? (y/n): " use_sp
if [[ $use_sp =~ ^[Yy]$ ]]; then
    prompt_with_default "   Azure Client ID (Service Principal)" "$current_client_id" "AZURE_CLIENT_ID"
    
    echo "   Azure Client Secret (Service Principal)"
    read -s -p "   Enter Client Secret (hidden): " client_secret
    echo ""
    
    if [ -n "$client_secret" ]; then
        if grep -q "^AZURE_CLIENT_SECRET=" .env; then
            sed -i "s|^AZURE_CLIENT_SECRET=.*|AZURE_CLIENT_SECRET=$client_secret|" .env
        else
            echo "AZURE_CLIENT_SECRET=$client_secret" >> .env
        fi
    fi
    
    prompt_with_default "   Azure Tenant ID" "$current_tenant_id" "AZURE_TENANT_ID"
else
    echo -e "${YELLOW}💡 Make sure you're logged in with Azure CLI: ${NC}az login"
fi

echo ""
echo -e "${BLUE}📱 Reddit API Configuration${NC}"
echo "You can either:"
echo "1. Store Reddit credentials in Azure Key Vault (recommended)"
echo "2. Use local environment variables as fallback"
echo ""

read -p "Do you want to set local Reddit credentials as fallback? (y/n): " use_reddit_env
if [[ $use_reddit_env =~ ^[Yy]$ ]]; then
    current_reddit_id=$(grep "^REDDIT_CLIENT_ID=" .env 2>/dev/null | cut -d'=' -f2- || echo "")
    current_reddit_agent=$(grep "^REDDIT_USER_AGENT=" .env 2>/dev/null | cut -d'=' -f2- || echo "ai-content-farm-local/1.0")
    
    prompt_with_default "   Reddit Client ID" "$current_reddit_id" "REDDIT_CLIENT_ID"
    
    echo "   Reddit Client Secret"
    read -s -p "   Enter Reddit Client Secret (hidden): " reddit_secret
    echo ""
    
    if [ -n "$reddit_secret" ]; then
        if grep -q "^REDDIT_CLIENT_SECRET=" .env; then
            sed -i "s|^REDDIT_CLIENT_SECRET=.*|REDDIT_CLIENT_SECRET=$reddit_secret|" .env
        else
            echo "REDDIT_CLIENT_SECRET=$reddit_secret" >> .env
        fi
    fi
    
    prompt_with_default "   Reddit User Agent" "$current_reddit_agent" "REDDIT_USER_AGENT"
fi

echo ""
echo -e "${GREEN}✅ Configuration saved to .env file${NC}"
echo ""
echo -e "${BLUE}🐳 Docker Compose Configuration${NC}"
echo "The docker-compose.yml will automatically load these environment variables."
echo ""
echo -e "${YELLOW}📋 Next Steps:${NC}"
echo "1. Make sure your Key Vault contains these secrets:"
echo "   - reddit-client-id"
echo "   - reddit-client-secret"
echo "   - reddit-user-agent (optional)"
echo ""
echo "2. If using Service Principal, ensure it has Key Vault access:"
echo "   - Key Vault Secrets User role (or custom policy)"
echo ""
echo "3. Start the services:"
echo "   docker-compose up -d"
echo ""
echo "4. Test the configuration:"
echo "   curl http://localhost:8001/health | jq '.environment_info.key_vault'"
echo ""
echo -e "${GREEN}🎉 Local development environment configured!${NC}"
