#!/bin/bash
# Function app deployment script for containerized CI/CD
set -e

echo "📦 Deploying Azure Function App..."

# Load environment variables from infrastructure deployment
if [ -f "/workspace/terraform-outputs.env" ]; then
    source /workspace/terraform-outputs.env
fi

# Validate required variables
if [ -z "$FUNCTION_APP_NAME" ] || [ -z "$RESOURCE_GROUP" ]; then
    echo "❌ Missing required environment variables: FUNCTION_APP_NAME, RESOURCE_GROUP"
    exit 1
fi

echo "📱 Deploying to Function App: $FUNCTION_APP_NAME"
echo "📍 Resource Group: $RESOURCE_GROUP"

# Navigate to functions directory
cd /workspace/functions

# Create deployment package
echo "📦 Creating deployment package..."
zip -r ../function-app.zip . -x "*.pyc" "*/__pycache__/*" ".python_packages/*" "*.log"

# Deploy using Azure CLI
echo "🚀 Deploying function package..."
az functionapp deployment source config-zip \
    --resource-group "$RESOURCE_GROUP" \
    --name "$FUNCTION_APP_NAME" \
    --src ../function-app.zip

echo "✅ Function app deployment completed"

# Wait for deployment to be ready and test
echo "⏳ Waiting for function app to be ready..."
for i in {1..12}; do  # 2 minutes max
    if curl -s "https://${FUNCTION_APP_NAME}.azurewebsites.net" > /dev/null; then
        echo "✅ Function app is responding"
        break
    fi
    echo "Attempt $i/12: Function app not ready yet, waiting 10 seconds..."
    sleep 10
done

echo "🔗 Function app URL: https://${FUNCTION_APP_NAME}.azurewebsites.net"
