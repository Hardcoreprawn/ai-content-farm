#!/bin/bash
set -e

# Azure Container Apps Deployment Script for AI Content Farm
# Multi-Tier Container Strategy Support

echo "🚀 Starting Azure Container Apps deployment with multi-tier strategy..."

# Configuration
RESOURCE_GROUP="ai-content-farm-core-rg"
LOCATION="UK South"
CONTAINER_APP_ENV="ai-content-farm-core-env"
# Note: Using GitHub Container Registry (GHCR) instead of ACR for cost efficiency

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

# Return to repo root for multi-tier builds
cd ..

echo "🏗️ Building and pushing multi-tier base images to GitHub Container Registry..."

# Note: Actual deployment is handled by GitHub Actions CI/CD pipeline
# This script is retained for reference and manual testing only

# Step 1: Build and push base images (required for all services)
echo "Building foundation base image..."
docker build -f containers/base/Dockerfile.multitier -t ai-content-farm-base:foundation --target foundation .
docker tag ai-content-farm-base:foundation $ACR_LOGIN_SERVER/ai-content-farm-base:foundation
docker push $ACR_LOGIN_SERVER/ai-content-farm-base:foundation

echo "Building common-deps base image..."
docker build -f containers/base/Dockerfile.multitier -t ai-content-farm-base:common-deps --target common-deps .
docker tag ai-content-farm-base:common-deps $ACR_LOGIN_SERVER/ai-content-farm-base:common-deps
docker push $ACR_LOGIN_SERVER/ai-content-farm-base:common-deps

echo "Building web-services base image..."
docker build -f containers/base/Dockerfile.multitier -t ai-content-farm-base:web-services --target web-services .
docker tag ai-content-farm-base:web-services $ACR_LOGIN_SERVER/ai-content-farm-base:web-services
docker push $ACR_LOGIN_SERVER/ai-content-farm-base:web-services

echo "Building data-processing base image..."
docker build -f containers/base/Dockerfile.multitier -t ai-content-farm-base:data-processing --target data-processing .
docker tag ai-content-farm-base:data-processing $ACR_LOGIN_SERVER/ai-content-farm-base:data-processing
docker push $ACR_LOGIN_SERVER/ai-content-farm-base:data-processing

echo "Building scheduler base image..."
docker build -f containers/base/Dockerfile.multitier -t ai-content-farm-base:scheduler --target scheduler .
docker tag ai-content-farm-base:scheduler $ACR_LOGIN_SERVER/ai-content-farm-base:scheduler
docker push $ACR_LOGIN_SERVER/ai-content-farm-base:scheduler

echo "✅ All base images pushed to ACR"

# Step 2: Build and push service containers
echo "🏗️ Building and pushing service containers..."

# Define containers to deploy (skip base directory)
CONTAINERS=("content-generator" "content-enricher" "content-processor" "content-ranker" "markdown-generator" "site-generator" "content-collector" "collector-scheduler")

for container in "${CONTAINERS[@]}"; do
    echo "Building and pushing $container..."

    # Build from repo root with correct context for multi-tier strategy
    docker build -f containers/$container/Dockerfile -t $container:latest .

    # Tag for ACR
    docker tag $container:latest $ACR_LOGIN_SERVER/$container:latest

    # Push to ACR
    docker push $ACR_LOGIN_SERVER/$container:latest

    echo "✅ $container pushed to ACR"
done

echo "✅ All service containers pushed to ACR"

# Step 3: Update Container Apps (for now just content-generator, expand later)
echo "🔄 Updating Container Apps..."
az containerapp update \
    --name "ai-content-farm-core-content-generator" \
    --resource-group $RESOURCE_GROUP \
    --image $ACR_LOGIN_SERVER/content-generator:latest

echo "✅ Container Apps updated"

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
