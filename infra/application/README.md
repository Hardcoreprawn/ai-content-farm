# Application Infrastructure

This module creates the main application infrastructure for the AI Content Farm project, including Function Apps, Key Vault, storage, and monitoring resources.

## Purpose

The application module deploys the core infrastructure needed to run the AI Content Farm:
- Azure Function Apps for content processing
- Key Vault for secrets management
- Storage accounts for data persistence
- Application Insights and Log Analytics for monitoring
- Cost monitoring and alerting

## Prerequisites

1. **Bootstrap module must be deployed first** - This module depends on resources created by the bootstrap module
2. Azure CLI authenticated: `az login`
3. Terraform >= 1.3.0 installed

## Resources Created

### Core Application Resources
- `azurerm_resource_group.main` - Resource group for all app resources
- `azurerm_linux_function_app.main` - Function App for content processing
- `azurerm_service_plan.main` - App Service Plan (Consumption tier)
- `azurerm_storage_account.main` - Storage for Function App and content data
- `azurerm_storage_container.topics` - Container for hot topics data

### Security & Secrets Management
- `azurerm_key_vault.main` - Key Vault for secrets
- `azurerm_key_vault_access_policy.*` - Access policies for different identities
- `azurerm_key_vault_secret.*` - Application secrets (Reddit API, Infracost API)

### Monitoring & Observability
- `azurerm_log_analytics_workspace.main` - Log Analytics workspace
- `azurerm_application_insights.main` - Application Insights
- `azurerm_monitor_diagnostic_setting.key_vault` - Key Vault diagnostics
- `azurerm_monitor_action_group.cost_alerts` - Cost alerting

### Identity & Access Management
- `azurerm_role_assignment.*` - RBAC assignments for Function App and admin access

## Deployment

### 1. Initialize with Remote State

First, get the backend configuration from the bootstrap module outputs:

```bash
cd ../bootstrap/
terraform output terraform_backend_config
```

Then initialize the application module:

```bash
cd ../application/
terraform init \
  -backend-config="storage_account_name=<from_bootstrap_output>" \
  -backend-config="container_name=tfstate" \
  -backend-config="key=staging.tfstate" \
  -backend-config="resource_group_name=ai-content-farm-bootstrap"
```

### 2. Configure Variables

Copy and customize the variables file:

```bash
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your specific values
```

Or use environment-specific tfvars files:
- `staging.tfvars` - Staging environment configuration
- `production.tfvars` - Production environment configuration

### 3. Plan and Deploy

```bash
# For staging
terraform plan -var-file="staging.tfvars"
terraform apply -var-file="staging.tfvars"

# For production
terraform plan -var-file="production.tfvars"
terraform apply -var-file="production.tfvars"
```

## Configuration

### Required Variables

- `environment` - Environment name (staging/production)
- `admin_user_object_id` - Object ID of the admin user for storage access

### Optional Variables

- `reddit_client_id` - Reddit API client ID
- `reddit_client_secret` - Reddit API client secret
- `reddit_user_agent` - Reddit API user agent string
- `infracost_api_key` - Infracost API key for cost estimation
- `cost_alert_email` - Email for cost alerts

## Outputs

- `function_app_name` - Name of the deployed Function App
- `resource_group_name` - Name of the resource group
- `key_vault_name` - Name of the Key Vault
- `storage_account_name` - Name of the storage account

## Environment Management

This module supports multiple environments using:
- Different tfvars files (`staging.tfvars`, `production.tfvars`)
- Separate remote state files per environment
- Environment-specific resource naming

## Security Features

- Key Vault for secrets management with access policies
- Managed identities for Function Apps
- RBAC assignments following principle of least privilege
- Diagnostic logging enabled
- HTTPS-only enforcement
- Network security configurations

## Monitoring & Observability

- Application Insights for application monitoring
- Log Analytics workspace for centralized logging
- Key Vault diagnostic settings
- Cost monitoring and alerting
- Health checks and availability monitoring
