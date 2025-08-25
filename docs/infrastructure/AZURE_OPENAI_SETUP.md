# Azure OpenAI Service Setup Guide

This guide shows how to set up Azure OpenAI Service for the AI Content Farm content generation pipeline.

## 🎯 Why Azure OpenAI Service?

✅ **Better for Azure hosting**: Integrated with Azure infrastructure
✅ **Enterprise compliance**: GDPR, SOC, ISO certifications
✅ **Cost management**: Better billing integration and controls
✅ **Data residency**: Keep data in your Azure region
✅ **Network security**: Private endpoints and VNet integration
✅ **Monitoring**: Azure Monitor integration

## 📋 Prerequisites

- Azure subscription
- Azure CLI installed (or use Azure Cloud Shell)
- Contributor access to Azure subscription

## 🚀 Setup Steps

### 1. Create Azure OpenAI Resource

```bash
# Set variables
RESOURCE_GROUP="ai-content-farm-rg"
LOCATION="eastus"  # or your preferred region
OPENAI_SERVICE_NAME="ai-content-farm-openai"

# Create resource group (if needed)
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create Azure OpenAI service
az cognitiveservices account create \
  --name $OPENAI_SERVICE_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --kind OpenAI \
  --sku S0 \
  --custom-domain $OPENAI_SERVICE_NAME
```

### 2. Deploy GPT Models

```bash
# Deploy GPT-3.5-turbo for cost-effective content generation
az cognitiveservices account deployment create \
  --name $OPENAI_SERVICE_NAME \
  --resource-group $RESOURCE_GROUP \
  --deployment-name "gpt-35-turbo" \
  --model-name "gpt-35-turbo" \
  --model-version "0613" \
  --model-format OpenAI \
  --sku-capacity 10 \
  --sku-name Standard

# Optional: Deploy GPT-4 for higher quality (more expensive)
az cognitiveservices account deployment create \
  --name $OPENAI_SERVICE_NAME \
  --resource-group $RESOURCE_GROUP \
  --deployment-name "gpt-4" \
  --model-name "gpt-4" \
  --model-version "0613" \
  --model-format OpenAI \
  --sku-capacity 5 \
  --sku-name Standard
```

### 3. Get Credentials

```bash
# Get the endpoint URL
ENDPOINT=$(az cognitiveservices account show \
  --name $OPENAI_SERVICE_NAME \
  --resource-group $RESOURCE_GROUP \
  --query "properties.endpoint" \
  --output tsv)

# Get the API key
API_KEY=$(az cognitiveservices account keys list \
  --name $OPENAI_SERVICE_NAME \
  --resource-group $RESOURCE_GROUP \
  --query "key1" \
  --output tsv)

echo "Azure OpenAI Endpoint: $ENDPOINT"
echo "Azure OpenAI API Key: $API_KEY"
```

### 4. Update Environment Variables

Add to your `.env` file:

```bash
# Azure OpenAI Service Configuration
AZURE_OPENAI_ENDPOINT=https://your-service-name.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-35-turbo
```

## 💰 Cost Optimization

### Model Selection
- **GPT-3.5-turbo**: ~$0.0015/1K tokens (cost-effective for tl;dr articles)
- **GPT-4**: ~$0.03/1K tokens (premium quality for important content)

### Usage Estimates
- **TL;DR article**: ~400 tokens = $0.0006 with GPT-3.5
- **Blog article**: ~1200 tokens = $0.0018 with GPT-3.5
- **Daily processing**: 50 tl;dr articles = ~$0.03/day

### Cost Controls
```bash
# Set spending limit (optional)
az cognitiveservices account update \
  --name $OPENAI_SERVICE_NAME \
  --resource-group $RESOURCE_GROUP \
  --tags "budget=monthly-50-usd"
```

## 🔐 Security Best Practices

### 1. Use Managed Identity (Production)
```bash
# Enable system-assigned managed identity
az cognitiveservices account identity assign \
  --name $OPENAI_SERVICE_NAME \
  --resource-group $RESOURCE_GROUP
```

### 2. Network Security
```bash
# Restrict to specific IP ranges (optional)
az cognitiveservices account network-rule add \
  --name $OPENAI_SERVICE_NAME \
  --resource-group $RESOURCE_GROUP \
  --ip-address "YOUR_IP_RANGE"
```

### 3. Key Vault Integration
```bash
# Store API key in Azure Key Vault
az keyvault secret set \
  --vault-name "your-keyvault" \
  --name "azure-openai-api-key" \
  --value "$API_KEY"
```

## 🧪 Testing the Integration

1. **Update environment variables** in your `.env` file
2. **Build and start** the content generator:
   ```bash
   docker-compose up content-generator
   ```
3. **Test the health endpoint**:
   ```bash
   curl http://localhost:8008/health
   ```
4. **Check service status**:
   ```bash
   curl http://localhost:8008/status
   ```

## 📊 Monitoring & Alerting

### Azure Monitor Integration
- **Request metrics**: Track API calls and response times
- **Error rates**: Monitor failed requests
- **Cost tracking**: Daily/monthly spend alerts

### Log Analytics
```bash
# Enable diagnostic settings
az monitor diagnostic-settings create \
  --name "openai-logs" \
  --resource "/subscriptions/.../resourceGroups/$RESOURCE_GROUP/providers/Microsoft.CognitiveServices/accounts/$OPENAI_SERVICE_NAME" \
  --logs '[{"category":"Audit","enabled":true},{"category":"RequestResponse","enabled":true}]' \
  --metrics '[{"category":"AllMetrics","enabled":true}]' \
  --workspace "/subscriptions/.../resourceGroups/$RESOURCE_GROUP/providers/Microsoft.OperationalInsights/workspaces/your-workspace"
```

## 🔄 Production Deployment

For production, consider:
- **Private endpoints** for network isolation
- **Managed identity** instead of API keys
- **Auto-scaling** based on demand
- **Multi-region deployment** for high availability
- **Content filtering** for safety and compliance

## ⚡ Quick Start (Minimal Setup)

If you just want to test quickly:

1. **Create the service** via Azure Portal:
   - Go to "Create a resource" → "AI + Machine Learning" → "OpenAI"
   - Choose your subscription, resource group, and region
   - Create the resource

2. **Deploy a model**:
   - Go to your OpenAI resource → "Model deployments"
   - Deploy "gpt-35-turbo" with default settings

3. **Get credentials**:
   - Go to "Keys and Endpoint"
   - Copy the endpoint URL and key

4. **Update .env** and run docker-compose!

---

**Cost estimate**: ~$1-5/month for moderate usage (50-100 articles/day)
