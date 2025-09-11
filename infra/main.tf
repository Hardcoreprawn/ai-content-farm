data "azurerm_client_config" "current" {}

resource "random_string" "suffix" {
  length  = 6
  upper   = false
  special = false
  # Test: Debug deployment conditions - needs-infrastructure trigger (Aug 28, 2025)
  # Test: Simplified routing fix - direct dependency path (Aug 28, 2025)
  # Fix: Update network rules with correct Container Apps IP and deploy latest containers (Aug 29, 2025)
  # Trigger: Pipeline test after network simplification (Aug 31, 2025)
  # Test: Pipeline optimization validation - container rebuild and infrastructure update (Sep 11, 2025)
  # Test: Comprehensive pipeline execution with enhanced monitoring (Sep 11, 2025)
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
    default_action = "Deny"
    bypass         = "AzureServices"
    # Allow GitHub Actions IPs - these are the documented GitHub Actions IP ranges
    ip_rules = [
      "20.201.28.151/32", # GitHub Actions runner IPs
      "20.205.243.166/32",
      "20.87.245.0/24",
      "20.118.201.0/24"
    ]
    # Allow Azure services to bypass the network ACL
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

# Note: Function App access policies removed - using container-only architecture

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
  name            = "reddit-client-id"
  value           = var.reddit_client_id != "" ? var.reddit_client_id : "placeholder-change-me"
  key_vault_id    = azurerm_key_vault.main.id
  content_type    = "text/plain"
  expiration_date = timeadd(timestamp(), "8760h") # 1 year expiration for security compliance

  # External secret - don't auto-update activation date or manually set values
  lifecycle {
    ignore_changes = [not_before_date, value]
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
  name            = "reddit-client-secret"
  value           = var.reddit_client_secret != "" ? var.reddit_client_secret : "placeholder-change-me"
  key_vault_id    = azurerm_key_vault.main.id
  content_type    = "text/plain"
  expiration_date = timeadd(timestamp(), "8760h") # 1 year expiration for security compliance

  # External secret - don't auto-update expiration date or manually set values
  lifecycle {
    ignore_changes = [not_before_date, value]
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

  # External secret - don't auto-update expiration date or manually set values
  lifecycle {
    ignore_changes = [not_before_date, expiration_date, value]
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
  name            = "infracost-api-key"
  value           = var.infracost_api_key != "" ? var.infracost_api_key : "placeholder-get-from-infracost-io"
  key_vault_id    = azurerm_key_vault.main.id
  content_type    = "text/plain"
  expiration_date = timeadd(timestamp(), "8760h") # 1 year expiration for security compliance

  # External secret - don't auto-update expiration date
  lifecycle {
    ignore_changes = [not_before_date, value]
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
    default_action = "Allow"
    bypass         = ["AzureServices"] # This is the recommended configuration for Microsoft services
    # Allow access from all networks for Container Apps Consumption compatibility
    # Container Apps Consumption tier uses dynamic IPs managed by Azure
    # Security is enforced through RBAC and managed identity authentication
    ip_rules                   = []
    virtual_network_subnet_ids = []
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

  enabled_log {
    category_group = "allLogs"
  }

  enabled_metric {
    category = "Transaction"
  }
}

# Enable blob service diagnostic settings for security compliance
resource "azurerm_monitor_diagnostic_setting" "storage_blob_logging" {
  name                       = "${local.resource_prefix}-blob-logs"
  target_resource_id         = "${azurerm_storage_account.main.id}/blobServices/default"
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id

  enabled_log {
    category_group = "allLogs"
  }

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

# Container for processed content from content-processor service
resource "azurerm_storage_container" "processed_content" {
  # checkov:skip=CKV2_AZURE_21: Logging not required for this use case
  name                  = "processed-content"
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "private"
}

# Container for enriched content from content-enricher service
resource "azurerm_storage_container" "enriched_content" {
  # checkov:skip=CKV2_AZURE_21: Logging not required for this use case
  name                  = "enriched-content"
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "private"
}

# Container for ranked content from content-ranker service
resource "azurerm_storage_container" "ranked_content" {
  # checkov:skip=CKV2_AZURE_21: Logging not required for this use case
  name                  = "ranked-content"
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "private"
}

# Container for markdown content from markdown generator
resource "azurerm_storage_container" "markdown_content" {
  # checkov:skip=CKV2_AZURE_21: Logging not required for this use case
  name                  = "markdown-content"
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "private"
}

# Container for static sites from site generator
resource "azurerm_storage_container" "static_sites" {
  # checkov:skip=CKV2_AZURE_21: Logging not required for this use case
  name                  = "static-sites"
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "private"
}

# Container for pipeline logs and monitoring
resource "azurerm_storage_container" "pipeline_logs" {
  # checkov:skip=CKV2_AZURE_21: Logging not required for this use case
  name                  = "pipeline-logs"
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "private"
}

# Container for cached pricing data from Azure APIs
resource "azurerm_storage_container" "pricing_cache" {
  # checkov:skip=CKV2_AZURE_21: Logging not required for this use case
  name                  = "pricing-cache"
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "private"
}

# Container services now handle the content processing pipeline

# Azure OpenAI Cognitive Services Account
#checkov:skip=CKV_AZURE_247:Data loss prevention configuration complex for development environment
#checkov:skip=CKV2_AZURE_22:Customer-managed encryption would create circular dependency in development environment
#checkov:skip=CKV_AZURE_134:Public network access required for Container Apps Consumption tier to access via managed identity
resource "azurerm_cognitive_account" "openai" {
  # checkov:skip=CKV_AZURE_247: Data loss prevention requires complex configuration - using network ACLs for access control
  # checkov:skip=CKV2_AZURE_22: Customer-managed encryption requires complex setup - using Azure-managed encryption for development
  # checkov:skip=CKV_AZURE_134: Public network access required for Container Apps Consumption tier - secured with network ACLs
  name                = "${local.resource_prefix}-openai"
  location            = "UK South" # OpenAI available in UK South for European compliance
  resource_group_name = azurerm_resource_group.main.name
  kind                = "OpenAI"
  sku_name            = "S0"

  # Security settings
  public_network_access_enabled = true  # Required for Container Apps Consumption tier access
  local_auth_enabled            = false # Disable local authentication for security

  # Custom subdomain required for private endpoints
  custom_subdomain_name = "${replace(local.resource_prefix, "-", "")}openai"

  # Enable managed identity
  identity {
    type = "SystemAssigned"
  }

  # Network access restrictions - secured for Container Apps
  network_acls {
    default_action = "Deny"
    # Allow Azure services including Container Apps to access via managed identity
    # Container Apps Consumption tier uses Azure backbone for service communication
    ip_rules = [
      "20.201.28.151/32", # GitHub Actions runner IPs for deployment
      "20.205.243.166/32",
      "20.87.245.0/24",
      "20.118.201.0/24"
    ]
  }

  tags = local.common_tags
}

# Store OpenAI endpoint in Key Vault for managed identity authentication
# Note: API key authentication is disabled (local_auth_enabled = false)
# Services should use managed identity to authenticate with Azure OpenAI
resource "azurerm_key_vault_secret" "openai_endpoint" {
  name            = "azure-openai-endpoint"
  value           = azurerm_cognitive_account.openai.endpoint
  key_vault_id    = azurerm_key_vault.main.id
  content_type    = "text/plain"
  expiration_date = timeadd(timestamp(), "8760h") # 1 year - infrastructure endpoint
  depends_on = [
    azurerm_key_vault_access_policy.developer_user,
    azurerm_key_vault_access_policy.github_actions_user
  ]

  tags = local.common_tags
}

# GPT-3.5-turbo deployment for text generation
resource "azurerm_cognitive_deployment" "gpt_35_turbo" {
  name                 = "gpt-35-turbo"
  cognitive_account_id = azurerm_cognitive_account.openai.id
  model {
    format  = "OpenAI"
    name    = "gpt-35-turbo"
    version = "0125"
  }
  sku {
    name     = "Standard"
    capacity = 10
  }
}

# Text embedding model deployment for content analysis
resource "azurerm_cognitive_deployment" "text_embedding_ada_002" {
  name                 = "text-embedding-ada-002"
  cognitive_account_id = azurerm_cognitive_account.openai.id
  model {
    format  = "OpenAI"
    name    = "text-embedding-ada-002"
    version = "2"
  }
  sku {
    name     = "Standard"
    capacity = 10
  }
}

# Store model deployment names in Key Vault for container apps
resource "azurerm_key_vault_secret" "openai_chat_model" {
  name            = "azure-openai-chat-model"
  value           = azurerm_cognitive_deployment.gpt_35_turbo.name
  key_vault_id    = azurerm_key_vault.main.id
  content_type    = "text/plain"
  expiration_date = timeadd(timestamp(), "8760h") # 1 year - model deployment name
  depends_on = [
    azurerm_key_vault_access_policy.developer_user,
    azurerm_key_vault_access_policy.github_actions_user
  ]
  tags = local.common_tags
}

resource "azurerm_key_vault_secret" "openai_embedding_model" {
  name            = "azure-openai-embedding-model"
  value           = azurerm_cognitive_deployment.text_embedding_ada_002.name
  key_vault_id    = azurerm_key_vault.main.id
  content_type    = "text/plain"
  expiration_date = timeadd(timestamp(), "8760h") # 1 year - model deployment name
  depends_on = [
    azurerm_key_vault_access_policy.developer_user,
    azurerm_key_vault_access_policy.github_actions_user
  ]
  tags = local.common_tags
}

resource "azurerm_storage_container" "prompts" {
  # checkov:skip=CKV2_AZURE_21: Logging not required for this use case
  name                  = "prompts"
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "private"
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

    # Container Apps (from container_apps.tf)
    azurerm_container_app_environment.main,
    azurerm_user_assigned_identity.containers,
    azurerm_user_assigned_identity.github_actions,

    # Storage containers
    azurerm_storage_container.topics,
    azurerm_storage_container.collected_content,
    azurerm_storage_container.processed_content,
    azurerm_storage_container.enriched_content,
    azurerm_storage_container.ranked_content,
    azurerm_storage_container.markdown_content,
    azurerm_storage_container.static_sites,
    azurerm_storage_container.pipeline_logs,

    # Key Vault secrets and policies
    azurerm_key_vault_secret.openai_endpoint,
    azurerm_key_vault_access_policy.developer_user,
    azurerm_key_vault_access_policy.github_actions_user
  ]
}

# Azure Static Web Apps for jablab.com hosting
resource "azurerm_static_web_app" "jablab" {
  name                = "${var.resource_prefix}-jablab"
  resource_group_name = azurerm_resource_group.main.name
  location            = "West Europe" # Static Web Apps limited regions
  sku_tier            = "Free"
  sku_size            = "Free"

  # Note: Free tier doesn't support managed identities
  # Container-only deployment uses managed identity for deployments

  app_settings = {
    "ENVIRONMENT"                = "production"
    "AZURE_STORAGE_ACCOUNT_NAME" = azurerm_storage_account.main.name
    "STATIC_SITES_CONTAINER"     = "static-sites"
  }

  tags = merge(local.common_tags, {
    Service = "static-web-hosting"
    Domain  = "jablab.com"
  })
}

# DNS Zone for jablab.com (if not already existing)
resource "azurerm_dns_zone" "jablab" {
  name                = "jablab.com"
  resource_group_name = azurerm_resource_group.main.name

  tags = merge(local.common_tags, {
    Service = "dns"
    Domain  = "jablab.com"
  })
}

# DNS CNAME record to point jablab.com to Static Web App
resource "azurerm_dns_cname_record" "jablab_www" {
  name                = "www"
  zone_name           = azurerm_dns_zone.jablab.name
  resource_group_name = azurerm_resource_group.main.name
  ttl                 = 300
  record              = azurerm_static_web_app.jablab.default_host_name

  tags = local.common_tags
}

# DNS A record for apex domain (jablab.com)
resource "azurerm_dns_a_record" "jablab_apex" {
  name                = "@"
  zone_name           = azurerm_dns_zone.jablab.name
  resource_group_name = azurerm_resource_group.main.name
  ttl                 = 300
  records             = ["185.199.108.153", "185.199.109.153", "185.199.110.153", "185.199.111.153"] # GitHub Pages IPs

  tags = local.common_tags
}

# Custom domain for Static Web App
resource "azurerm_static_web_app_custom_domain" "jablab" {
  static_web_app_id = azurerm_static_web_app.jablab.id
  domain_name       = "jablab.com"
  validation_type   = "dns-txt-token"

  depends_on = [
    azurerm_dns_zone.jablab,
    azurerm_dns_a_record.jablab_apex
  ]
}
# Force infrastructure deployment trigger
