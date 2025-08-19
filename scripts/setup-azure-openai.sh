#!/bin/bash
# Azure OpenAI Service Setup Script
# Creates Azure OpenAI service and documents the configuration for Terraform

set -e  # Exit on any error

# Configuration
SUBSCRIPTION_ID=${AZURE_SUBSCRIPTION_ID:-$(az account show --query id -o tsv)}
RESOURCE_GROUP="ai-content-farm-rg"
LOCATION="eastus"
OPENAI_SERVICE_NAME="ai-content-farm-openai-$(date +%s | tail -c 5)"  # Unique suffix
DEPLOYMENT_NAME="gpt-35-turbo"
MODEL_NAME="gpt-35-turbo"
MODEL_VERSION="0613"

echo "🚀 Setting up Azure OpenAI Service for AI Content Farm"
echo "=================================================="
echo "Subscription: $SUBSCRIPTION_ID"
echo "Resource Group: $RESOURCE_GROUP"
echo "Location: $LOCATION"
echo "Service Name: $OPENAI_SERVICE_NAME"
echo ""

# Check if logged in
echo "🔐 Checking Azure CLI authentication..."
if ! az account show > /dev/null 2>&1; then
    echo "❌ Not logged in to Azure. Please run: az login"
    exit 1
fi

echo "✅ Authenticated as: $(az account show --query user.name -o tsv)"

# Create resource group if it doesn't exist
echo "📁 Creating resource group..."
az group create \
    --name "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --output table

# Check if OpenAI service is available in the region
echo "🔍 Checking OpenAI service availability in $LOCATION..."
AVAILABLE=$(az cognitiveservices account list-kinds --location "$LOCATION" --query "[?contains(kind, 'OpenAI')]" -o tsv)
if [ -z "$AVAILABLE" ]; then
    echo "⚠️ OpenAI service not available in $LOCATION. Trying eastus..."
    LOCATION="eastus"
fi

# Create Azure OpenAI service
echo "🧠 Creating Azure OpenAI service..."
az cognitiveservices account create \
    --name "$OPENAI_SERVICE_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --kind OpenAI \
    --sku S0 \
    --custom-domain "$OPENAI_SERVICE_NAME" \
    --output table

# Wait for service to be ready
echo "⏳ Waiting for service to be ready..."
sleep 30

# Deploy GPT-3.5-turbo model
echo "🤖 Deploying GPT-3.5-turbo model..."
az cognitiveservices account deployment create \
    --name "$OPENAI_SERVICE_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --deployment-name "$DEPLOYMENT_NAME" \
    --model-name "$MODEL_NAME" \
    --model-version "$MODEL_VERSION" \
    --model-format OpenAI \
    --sku-capacity 10 \
    --sku-name Standard \
    --output table

# Get credentials
echo "🔑 Retrieving service credentials..."
ENDPOINT=$(az cognitiveservices account show \
    --name "$OPENAI_SERVICE_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.endpoint" \
    --output tsv)

API_KEY=$(az cognitiveservices account keys list \
    --name "$OPENAI_SERVICE_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "key1" \
    --output tsv)

# Output configuration
echo ""
echo "✅ Azure OpenAI Service Setup Complete!"
echo "======================================="
echo "Service Name: $OPENAI_SERVICE_NAME"
echo "Resource Group: $RESOURCE_GROUP"
echo "Location: $LOCATION"
echo "Endpoint: $ENDPOINT"
echo "Deployment: $DEPLOYMENT_NAME"
echo ""

# Create environment file
ENV_FILE="azure-openai.env"
cat > "$ENV_FILE" << EOF
# Azure OpenAI Service Configuration
# Generated on $(date)
AZURE_OPENAI_ENDPOINT=$ENDPOINT
AZURE_OPENAI_API_KEY=$API_KEY
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT_NAME=$DEPLOYMENT_NAME
AZURE_OPENAI_SERVICE_NAME=$OPENAI_SERVICE_NAME
AZURE_RESOURCE_GROUP=$RESOURCE_GROUP
EOF

echo "💾 Configuration saved to: $ENV_FILE"
echo "📝 Add these to your .env file:"
echo ""
cat "$ENV_FILE"

# Create Terraform documentation
TERRAFORM_DOC="azure-openai-terraform.md"
cat > "$TERRAFORM_DOC" << EOF
# Azure OpenAI Terraform Configuration

## Created Resources

\`\`\`hcl
resource "azurerm_cognitive_account" "openai" {
  name                = "$OPENAI_SERVICE_NAME"
  location            = "$LOCATION"
  resource_group_name = "$RESOURCE_GROUP"
  kind                = "OpenAI"
  sku_name           = "S0"
  
  custom_subdomain_name = "$OPENAI_SERVICE_NAME"
  
  tags = {
    Environment = "production"
    Project     = "ai-content-farm"
    Component   = "ai-services"
  }
}

resource "azurerm_cognitive_deployment" "gpt35_turbo" {
  name                 = "$DEPLOYMENT_NAME"
  cognitive_account_id = azurerm_cognitive_account.openai.id
  
  model {
    format  = "OpenAI"
    name    = "$MODEL_NAME"
    version = "$MODEL_VERSION"
  }
  
  scale {
    type     = "Standard"
    capacity = 10
  }
}
\`\`\`

## Outputs

\`\`\`hcl
output "openai_endpoint" {
  value = azurerm_cognitive_account.openai.endpoint
}

output "openai_primary_key" {
  value     = azurerm_cognitive_account.openai.primary_access_key
  sensitive = true
}

output "openai_deployment_name" {
  value = azurerm_cognitive_deployment.gpt35_turbo.name
}
\`\`\`

## Key Vault Integration

\`\`\`hcl
resource "azurerm_key_vault_secret" "openai_key" {
  name         = "azure-openai-api-key"
  value        = azurerm_cognitive_account.openai.primary_access_key
  key_vault_id = azurerm_key_vault.main.id
}
\`\`\`
EOF

echo "📖 Terraform documentation saved to: $TERRAFORM_DOC"

# Test the service
echo "🧪 Testing Azure OpenAI service..."
python3 - << EOF
import openai
import os
import asyncio

async def test_azure_openai():
    client = openai.AsyncAzureOpenAI(
        azure_endpoint="$ENDPOINT",
        api_key="$API_KEY",
        api_version="2024-02-15-preview"
    )
    
    try:
        response = await client.chat.completions.create(
            model="$DEPLOYMENT_NAME",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'Azure OpenAI is working!' in exactly 5 words."}
            ],
            max_tokens=20
        )
        print("✅ Test successful:", response.choices[0].message.content.strip())
        return True
    except Exception as e:
        print("❌ Test failed:", str(e))
        return False
    finally:
        await client.close()

# Run test
result = asyncio.run(test_azure_openai())
if result:
    print("🎉 Azure OpenAI service is ready for content generation!")
else:
    print("⚠️ Service created but test failed. Check configuration.")
EOF

echo ""
echo "🎯 Next Steps:"
echo "1. Copy configuration to .env file"
echo "2. Run: docker-compose up content-generator"
echo "3. Test: curl http://localhost:8008/health"
echo "4. Generate content with proper Azure OpenAI integration"
