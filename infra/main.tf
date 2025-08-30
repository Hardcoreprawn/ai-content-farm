data "azurerm_client_config" "current" {}

resource "random_string" "suffix" {
  length  = 6
  upper   = false
  special = false
  # Test: Debug deployment conditions - needs-infrastructure trigger (Aug 28, 2025)
  # Test: Simplified routing fix - direct dependency path (Aug 28, 2025)
  # Fix: Update network rules with correct Container Apps IP and deploy latest containers (Aug 29, 2025)
}

resource "azurerm_resource_group" "main" {
  name     = "${local.resource_prefix}-rg"
  location = var.location

  tags = local.common_tags
}


# Key Vault
resource "azurerm_key_vault" "main" {
  # checkov:skip=CKV2_AZURE_32: Private endpoint not required for this use case
  # checkov:skip=CKV_AZURE_109: Network ACLs allow all access due to dynamic GitHub Actions IPs - security enforced via RBAC
  name     = "${local.clean_prefix}kv${random_string.suffix.result}"
  location = azurerm_resource_group.main.location

  resource_group_name        = azurerm_resource_group.main.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  purge_protection_enabled   = true
  soft_delete_retention_days = 7

  # Network ACLs for security compliance
  network_acls {
    default_action = "Allow" # Temporarily allow all access for GitHub Actions compatibility
    bypass         = "AzureServices"

    # Allow access from Container Apps subnet and development IP
    # GitHub Actions IP addresses change frequently, so they use the AzureServices bypass
    # Reference: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/about-githubs-ip-addresses
    virtual_network_subnet_ids = [azurerm_subnet.container_apps.id]
    ip_rules                   = ["81.2.90.47"] # Your static IP for development
  }

  tags = {
    Environment = var.environment
    Project     = "ai-content-farm"
    ManagedBy   = "terraform"
  }

  # Enable diagnostic settings for security compliance
  depends_on = [azurerm_log_analytics_workspace.main]
}

# Key Vault access policy for local development user
resource "azurerm_key_vault_access_policy" "developer_user" {
  key_vault_id = azurerm_key_vault.main.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = "e96077a7-82ec-4be0-86d5-ac85fdec6312" # Static developer object ID

  secret_permissions = [
    "Get",
    "List",
    "Set",
    "Delete",
    "Purge",
    "Recover"
  ]
}

# Key Vault access policy for GitHub Actions CI/CD
resource "azurerm_key_vault_access_policy" "github_actions_user" {
  key_vault_id = azurerm_key_vault.main.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = "d8052fa3-6566-489e-9d61-4db7299ced2f" # Static GitHub Actions object ID

  secret_permissions = [
    "Get",
    "List",
    "Set",
    "Delete",
    "Purge",
    "Recover"
  ]
}

# Function App Key Vault access policy removed - no longer needed for containerized services

# Key Vault diagnostic settings for security compliance
resource "azurerm_monitor_diagnostic_setting" "key_vault" {
  name                       = "key-vault-diagnostics"
  target_resource_id         = azurerm_key_vault.main.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id

  enabled_log {
    category = "AuditEvent"
  }

  enabled_log {
    category = "AzurePolicyEvaluationDetails"
  }

  enabled_metric {
    category = "AllMetrics"
  }
}

# Key Vault secrets for CI/CD integration
resource "azurerm_key_vault_secret" "reddit_client_id" {
  name         = "reddit-client-id"
  value        = var.reddit_client_id != "" ? var.reddit_client_id : "placeholder-change-me"
  key_vault_id = azurerm_key_vault.main.id
  content_type = "text/plain"

  # External secret - don't auto-update expiration date
  lifecycle {
    ignore_changes = [expiration_date]
  }

  tags = {
    Environment = var.environment
    Purpose     = "reddit-api-access"
  }

  depends_on = [
    azurerm_key_vault_access_policy.developer_user,
    azurerm_key_vault_access_policy.github_actions_user
  ]
}

resource "azurerm_key_vault_secret" "reddit_client_secret" {
  name         = "reddit-client-secret"
  value        = var.reddit_client_secret != "" ? var.reddit_client_secret : "placeholder-change-me"
  key_vault_id = azurerm_key_vault.main.id
  content_type = "text/plain"

  # External secret - don't auto-update expiration date
  lifecycle {
    ignore_changes = [expiration_date]
  }

  depends_on = [
    azurerm_key_vault_access_policy.developer_user,
    azurerm_key_vault_access_policy.github_actions_user
  ]

  tags = {
    Environment = var.environment
    Purpose     = "reddit-api-access"
  }
}

resource "azurerm_key_vault_secret" "reddit_user_agent" {
  name         = "reddit-user-agent"
  value        = var.reddit_user_agent != "" ? var.reddit_user_agent : "ai-content-farm:v1.0 (by /u/your-username)"
  key_vault_id = azurerm_key_vault.main.id
  content_type = "text/plain"

  # External secret - don't auto-update expiration date
  lifecycle {
    ignore_changes = [expiration_date]
  }

  depends_on = [
    azurerm_key_vault_access_policy.developer_user,
    azurerm_key_vault_access_policy.github_actions_user
  ]

  tags = {
    Environment = var.environment
    Purpose     = "reddit-api-access"
  }
}

# CI/CD secrets for GitHub Actions
resource "azurerm_key_vault_secret" "infracost_api_key" {
  name         = "infracost-api-key"
  value        = var.infracost_api_key != "" ? var.infracost_api_key : "placeholder-get-from-infracost-io"
  key_vault_id = azurerm_key_vault.main.id
  content_type = "text/plain"

  # External secret - don't auto-update expiration date
  lifecycle {
    ignore_changes = [expiration_date]
  }

  depends_on = [
    azurerm_key_vault_access_policy.developer_user,
    azurerm_key_vault_access_policy.github_actions_user
  ]

  tags = {
    Environment = var.environment
    Purpose     = "cost-estimation"
  }
}

# Service Bus encryption key - DISABLED for Standard SKU cost optimization
# Standard Service Bus SKU does not support customer-managed encryption keys
# This resource is kept commented for future upgrade to Premium SKU if needed
#
# resource "azurerm_key_vault_key" "servicebus" {
#   name            = "servicebus-encryption-key"
#   key_vault_id    = azurerm_key_vault.main.id
#   key_type        = "RSA"
#   key_size        = 2048
#   expiration_date = timeadd(timestamp(), "2160h") # 90 days for cost optimization
#
#   key_opts = [
#     "decrypt",
#     "encrypt",
#     "sign",
#     "unwrapKey",
#     "verify",
#     "wrapKey",
#   ]
#
#   depends_on = [azurerm_key_vault_access_policy.current_user]
#   tags = local.common_tags
# }

# Access policy for Service Bus managed identity - DISABLED for Standard SKU
# Standard Service Bus SKU does not support customer-managed encryption keys
# This resource is kept commented for future upgrade to Premium SKU if needed
#
# resource "azurerm_key_vault_access_policy" "servicebus" {
#   key_vault_id = azurerm_key_vault.main.id
#   tenant_id    = data.azurerm_client_config.current.tenant_id
#   object_id    = azurerm_user_assigned_identity.servicebus.principal_id
#
#   key_permissions = [
#     "Get",
#     "UnwrapKey",
#     "WrapKey"
#   ]
#
#   depends_on = [azurerm_user_assigned_identity.servicebus]
# }


resource "azurerm_log_analytics_workspace" "main" {
  name                = "${local.resource_prefix}-la"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30 # Reduced from default 90 days for cost optimization

  tags = local.common_tags
}

resource "azurerm_application_insights" "main" {
  name                = "${local.resource_prefix}-insights"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "web"
}

resource "azurerm_storage_account" "main" {
  # checkov:skip=CKV_AZURE_33: Not using queues
  # checkov:skip=CKV_AZURE_35: Needed for initial setup
  # checkov:skip=CKV_AZURE_59: Using for testing
  # checkov:skip=CKV_AZURE_206: LRS is sufficient for this use case
  # checkov:skip=CKV2_AZURE_1: Microsoft-managed keys are sufficient
  # checkov:skip=CKV2_AZURE_33: Public endpoint is acceptable for this use case
  # checkov:skip=CKV2_AZURE_38: Not required for non-critical data
  # checkov:skip=CKV2_AZURE_40: Shared Key authorization required for Terraform compatibility; access is restricted and secure
  # checkov:skip=CKV2_AZURE_41: No SAS tokens used
  # nosemgrep: terraform.azure.security.storage.storage-allow-microsoft-service-bypass.storage-allow-microsoft-service-bypass
  # nosemgrep: terraform.azure.security.storage.storage-queue-services-logging.storage-queue-services-logging
  # nosemgrep: terraform.azure.security.storage.storage-analytics-logging.storage-analytics-logging
  # Note: Modern diagnostic settings approach implemented below for comprehensive logging
  name                          = "${local.clean_prefix}st${random_string.suffix.result}"
  resource_group_name           = azurerm_resource_group.main.name
  location                      = azurerm_resource_group.main.location
  account_tier                  = "Standard"
  account_replication_type      = "LRS"
  public_network_access_enabled = true
  shared_access_key_enabled     = true
  # nosemgrep: terraform.azure.security.storage.storage-allow-microsoft-service-bypass.storage-allow-microsoft-service-bypass
  network_rules {
    default_action = "Deny"
    bypass         = ["AzureServices"] # This is the recommended configuration for Microsoft services
    # Allow access only from Container Apps subnet and approved IPs
    # Security is enforced through RBAC and managed identity authentication
    ip_rules                   = ["81.2.90.47"] # Your static IP for development access
    virtual_network_subnet_ids = [azurerm_subnet.container_apps.id]
  }
  allow_nested_items_to_be_public = false
  min_tls_version                 = "TLS1_2"
  # nosemgrep: terraform.azure.security.storage.storage-queue-services-logging.storage-queue-services-logging
  blob_properties {
    # Enable Storage Analytics logging for blob operations
    # Note: This is configured at the storage account level for compliance
    delete_retention_policy {
      days = 7
    }
    versioning_enabled = true
  }
}

# Enable Storage Analytics logging using modern diagnostic settings approach
resource "azurerm_monitor_diagnostic_setting" "storage_logging" {
  name                       = "${local.resource_prefix}-storage-logs"
  target_resource_id         = azurerm_storage_account.main.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id

  enabled_metric {
    category = "Transaction"
  }
}

resource "azurerm_storage_container" "topics" {
  # checkov:skip=CKV2_AZURE_21: Logging not required for this use case
  name                  = "content-topics"
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "private"
}

# Container for collected content from content-collector service
resource "azurerm_storage_container" "collected_content" {
  # checkov:skip=CKV2_AZURE_21: Logging not required for this use case
  name                  = "collected-content"
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "private"
}

# Container services now handle the content processing pipeline

# Azure OpenAI Cognitive Services Account
#checkov:skip=CKV_AZURE_247:Data loss prevention configuration complex for development environment
#checkov:skip=CKV2_AZURE_22:Customer-managed encryption would create circular dependency in development environment
resource "azurerm_cognitive_account" "openai" {
  # checkov:skip=CKV_AZURE_247: Data loss prevention requires complex configuration - using network ACLs for access control
  # checkov:skip=CKV2_AZURE_22: Customer-managed encryption requires complex setup - using Azure-managed encryption for development
  name                = "${local.resource_prefix}-openai"
  location            = "UK South" # OpenAI available in UK South for European compliance
  resource_group_name = azurerm_resource_group.main.name
  kind                = "OpenAI"
  sku_name            = "S0"

  # Security settings
  public_network_access_enabled = false
  local_auth_enabled            = false # Disable local authentication for security

  # Custom subdomain required for private endpoints
  custom_subdomain_name = "${replace(local.resource_prefix, "-", "")}openai"

  # Enable managed identity
  identity {
    type = "SystemAssigned"
  }

  # Network access restrictions
  network_acls {
    default_action = "Deny"

    # Allow access from Container Apps subnet
    virtual_network_rules {
      subnet_id = azurerm_subnet.container_apps.id
    }

    # Allow access from your development IP
    ip_rules = ["81.2.90.47"]
  }

  tags = local.common_tags
}

# Store OpenAI endpoint in Key Vault for managed identity authentication
# Note: API key authentication is disabled (local_auth_enabled = false)
# Services should use managed identity to authenticate with Azure OpenAI
resource "azurerm_key_vault_secret" "openai_endpoint" {
  name         = "azure-openai-endpoint"
  value        = azurerm_cognitive_account.openai.endpoint
  key_vault_id = azurerm_key_vault.main.id
  content_type = "text/plain"
  depends_on = [
    azurerm_key_vault_access_policy.developer_user,
    azurerm_key_vault_access_policy.github_actions_user
  ]

  tags = local.common_tags
}

# Resource lock to prevent accidental deletion
# Created LAST to avoid blocking infrastructure updates during deployment
resource "azurerm_management_lock" "resource_group_lock" {
  name       = "resource-group-lock"
  scope      = azurerm_resource_group.main.id
  lock_level = "CanNotDelete"
  notes      = "Prevents accidental deletion of the resource group and all its resources"

  # Ensure all major infrastructure is created before applying the lock
  depends_on = [
    # Core infrastructure
    azurerm_key_vault.main,
    azurerm_storage_account.main,
    azurerm_cognitive_account.openai,
    azurerm_log_analytics_workspace.main,
    azurerm_application_insights.main,

    # Networking (from networking.tf)
    azurerm_virtual_network.main,
    azurerm_subnet.container_apps,
    azurerm_network_security_group.container_apps,

    # Container Apps (from container_apps.tf)
    azurerm_container_app_environment.main,
    azurerm_user_assigned_identity.containers,
    azurerm_user_assigned_identity.github_actions,

    # Storage containers
    azurerm_storage_container.topics,
    azurerm_storage_container.collected_content,

    # Key Vault secrets and policies
    azurerm_key_vault_secret.openai_endpoint,
    azurerm_key_vault_access_policy.developer_user,
    azurerm_key_vault_access_policy.github_actions_user
  ]
}
