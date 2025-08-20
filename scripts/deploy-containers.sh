#!/bin/bash
set -e

# Azure Container Apps Deployment Script for AI Content Farm

echo "🚀 Starting Azure Container Apps deployment..."

# Configuration
RESOURCE_GROUP="ai-content-farm-core-rg"
LOCATION="UK South"
ACR_NAME="aicontentfarm76ko2hacr"
CONTAINER_APP_ENV="ai-content-farm-core-env"

# Check if logged into Azure
if ! az account show &>/dev/null; then
    echo "❌ Not logged into Azure. Please run 'az login' first."
    exit 1
fi

echo "✅ Azure CLI authenticated"

# Get current subscription
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
echo "📋 Using subscription: $SUBSCRIPTION_ID"

# Apply Terraform to create container infrastructure
echo "📦 Applying Terraform infrastructure..."
cd infra

# Initialize Terraform if needed
if [ ! -d ".terraform" ]; then
    terraform init
fi

# Plan and apply
terraform plan -var="environment=production" -out=tfplan
terraform apply tfplan

echo "✅ Infrastructure deployed"

# Get ACR login server
ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --resource-group $RESOURCE_GROUP --query loginServer -o tsv)
echo "📋 ACR Login Server: $ACR_LOGIN_SERVER"

# Login to ACR
echo "🔐 Logging into Azure Container Registry..."
az acr login --name $ACR_NAME

# Build and push content generator container
echo "🏗️ Building and pushing content generator container..."
cd ../containers/content-generator

# Build the container image
docker build -t content-generator:latest .

# Tag for ACR
docker tag content-generator:latest $ACR_LOGIN_SERVER/content-generator:latest

# Push to ACR
docker push $ACR_LOGIN_SERVER/content-generator:latest

echo "✅ Container image pushed to ACR"

# Update container app with new image
echo "🔄 Updating Container App..."
az containerapp update \
    --name "ai-content-farm-core-content-generator" \
    --resource-group $RESOURCE_GROUP \
    --image $ACR_LOGIN_SERVER/content-generator:latest

echo "✅ Container App updated"

# Show deployment status
echo "📊 Deployment Status:"
az containerapp show \
    --name "ai-content-farm-core-content-generator" \
    --resource-group $RESOURCE_GROUP \
    --query "{name:name,status:properties.provisioningState,fqdn:properties.configuration.ingress.fqdn}" \
    -o table

echo "🎉 Deployment complete!"
echo ""
echo "🌐 Container App URL:"
az containerapp show \
    --name "ai-content-farm-core-content-generator" \
    --resource-group $RESOURCE_GROUP \
    --query "properties.configuration.ingress.fqdn" \
    -o tsv

echo ""
echo "📋 To monitor logs:"
echo "az containerapp logs show --name ai-content-farm-core-content-generator --resource-group $RESOURCE_GROUP --follow"
