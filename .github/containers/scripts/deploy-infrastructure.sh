#!/bin/bash
# Terraform deployment script for containerized CI/CD
set -e

echo "🚀 Deploying infrastructure..."

# Configuration
ENVIRONMENT="${1:-staging}"
BOOTSTRAP_RG="ai-content-farm-bootstrap"

# Set Terraform environment variables
export TF_IN_AUTOMATION=true
export TF_CLI_ARGS_init="-no-color"
export TF_CLI_ARGS_apply="-no-color"

echo "🏗️  Deploying to environment: $ENVIRONMENT"

# Navigate to Terraform directory
cd /workspace/infra/application

echo "🔧 Initializing Terraform..."
terraform init \
    -backend-config="storage_account_name=${TERRAFORM_STATE_STORAGE_ACCOUNT}" \
    -backend-config="container_name=tfstate" \
    -backend-config="key=${ENVIRONMENT}.tfstate" \
    -backend-config="resource_group_name=${BOOTSTRAP_RG}"

echo "🚀 Applying Terraform configuration..."
terraform apply -auto-approve -var="environment=${ENVIRONMENT}"

echo "📤 Extracting outputs..."
FUNCTION_APP_NAME=$(terraform output -raw function_app_name)
RESOURCE_GROUP=$(terraform output -raw resource_group_name)

# Export to GitHub environment
echo "FUNCTION_APP_NAME=$FUNCTION_APP_NAME" >> $GITHUB_ENV 2>/dev/null || true
echo "RESOURCE_GROUP=$RESOURCE_GROUP" >> $GITHUB_ENV 2>/dev/null || true

# Also create output file for container use
cat > /workspace/terraform-outputs.env << EOF
FUNCTION_APP_NAME=$FUNCTION_APP_NAME
RESOURCE_GROUP=$RESOURCE_GROUP
ENVIRONMENT=$ENVIRONMENT
EOF

echo "✅ Infrastructure deployment completed"
echo "Function App: $FUNCTION_APP_NAME"
echo "Resource Group: $RESOURCE_GROUP"
