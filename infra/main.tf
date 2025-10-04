data "azurerm_client_config" "current" {}

# Data sources for core Key Vault to sync Reddit credentials
# This automatically syncs Reddit API credentials from the core Key Vault to the prod Key Vault
# eliminating manual credential management and preventing formatting issues
data "azurerm_key_vault" "core" {
  name                = "ai-content-farm-core-kv"
  resource_group_name = "ai-content-farm-core-rg"
}

data "azurerm_key_vault_secret" "core_reddit_client_id" {
  name         = "reddit-client-id"
  key_vault_id = data.azurerm_key_vault.core.id
}

data "azurerm_key_vault_secret" "core_reddit_client_secret" {
  name         = "reddit-client-secret"
  key_vault_id = data.azurerm_key_vault.core.id
}

data "azurerm_key_vault_secret" "core_reddit_user_agent" {
  name         = "reddit-user-agent"
  key_vault_id = data.azurerm_key_vault.core.id
}

resource "random_string" "suffix" {
  length  = 6
  upper   = false
  special = false
}

resource "azurerm_resource_group" "main" {
  name     = "${local.resource_prefix}-rg"
  location = var.location

  tags = local.common_tags
}


# Key Vault
resource "azurerm_key_vault" "main" {
  # checkov:skip=CKV2_AZURE_32: Private endpoint not required for this use case
  # checkov:skip=CKV_AZURE_109,CKV_AZURE_189: Network access "Allow" required for dynamic GitHub Actions IPs and Container Apps - security enforced via RBAC
  # nosemgrep: terraform.azure.security.keyvault.keyvault-specify-network-acl.keyvault-specify-network-acl
  name     = "${local.clean_prefix}kv${random_string.suffix.result}"
  location = azurerm_resource_group.main.location

  resource_group_name        = azurerm_resource_group.main.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  purge_protection_enabled   = true
  soft_delete_retention_days = 7

  # Network ACLs: Allow all networks, security enforced via identity-based access control
  # Security Strategy:
  # 1. GitHub Actions IPs change frequently and are unpredictable
  # 2. Container Apps consumption mode has no fixed egress IPs
  # 3. Identity-based access control (managed identity + RBAC) provides security
  # 4. Alternative would require expensive dedicated compute environment
  network_acls {
    default_action = "Allow" # Allow all networks - security enforced via identity and RBAC
    bypass         = "AzureServices"
    # No IP restrictions: GitHub Actions and Container Apps have dynamic IPs
    # Security provided by:
    # - Managed identity authentication
    # - RBAC access policies (Get/List secrets only for apps)
    # - disabled local auth (no key-based access)
  }

  tags = local.common_tags

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
  value           = data.azurerm_key_vault_secret.core_reddit_client_id.value
  key_vault_id    = azurerm_key_vault.main.id
  content_type    = "text/plain"
  expiration_date = timeadd(timestamp(), "8760h") # 1 year expiration for security compliance

  # Automatically sync from core Key Vault - don't ignore value changes
  lifecycle {
    ignore_changes = [not_before_date, expiration_date]
  }

  tags = merge(local.common_tags, {
    Purpose    = "reddit-api-access"
    SyncSource = "ai-content-farm-core-kv"
  })

  depends_on = [
    azurerm_key_vault_access_policy.developer_user,
    azurerm_key_vault_access_policy.github_actions_user
  ]
}

resource "azurerm_key_vault_secret" "reddit_client_secret" {
  name            = "reddit-client-secret"
  value           = data.azurerm_key_vault_secret.core_reddit_client_secret.value
  key_vault_id    = azurerm_key_vault.main.id
  content_type    = "text/plain"
  expiration_date = timeadd(timestamp(), "8760h") # 1 year expiration for security compliance

  # Automatically sync from core Key Vault - don't ignore value changes
  lifecycle {
    ignore_changes = [not_before_date, expiration_date]
  }

  depends_on = [
    azurerm_key_vault_access_policy.developer_user,
    azurerm_key_vault_access_policy.github_actions_user
  ]

  tags = merge(local.common_tags, {
    Purpose    = "reddit-api-access"
    SyncSource = "ai-content-farm-core-kv"
  })
}

resource "azurerm_key_vault_secret" "reddit_user_agent" {
  # checkov:skip=CKV_AZURE_41: Secret expiration not set as this is an external API credential managed outside Terraform
  # nosemgrep: terraform.azure.security.keyvault.keyvault-ensure-secret-expires.keyvault-ensure-secret-expires
  name         = "reddit-user-agent"
  value        = data.azurerm_key_vault_secret.core_reddit_user_agent.value
  key_vault_id = azurerm_key_vault.main.id
  content_type = "text/plain"

  # Automatically sync from core Key Vault - don't ignore value changes
  lifecycle {
    ignore_changes = [not_before_date, expiration_date]
  }

  tags = merge(local.common_tags, {
    Purpose    = "reddit-api-access"
    SyncSource = "ai-content-farm-core-kv"
  })

  depends_on = [
    azurerm_key_vault_access_policy.developer_user,
    azurerm_key_vault_access_policy.github_actions_user
  ]
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
    ignore_changes = [not_before_date, value, expiration_date]
  }

  depends_on = [
    azurerm_key_vault_access_policy.developer_user,
    azurerm_key_vault_access_policy.github_actions_user
  ]

  tags = merge(local.common_tags, {
    Purpose = "cost-estimation"
  })
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
  # checkov:skip=CKV_AZURE_33: Queue logging enabled via separate azurerm_storage_account_queue_properties resource
  # checkov:skip=CKV_AZURE_35: Needed for initial setup
  # checkov:skip=CKV_AZURE_59: Using for testing
  # checkov:skip=CKV_AZURE_206: LRS is sufficient for this use case
  # checkov:skip=CKV2_AZURE_1: Microsoft-managed keys are sufficient
  # checkov:skip=CKV2_AZURE_33: Public endpoint is acceptable for this use case
  # checkov:skip=CKV2_AZURE_38: Not required for non-critical data
  # checkov:skip=CKV2_AZURE_40: Shared Key authorization required for Terraform compatibility; access is restricted and secure
  # checkov:skip=CKV2_AZURE_41: No SAS tokens used
  # nosemgrep: terraform.azure.security.storage.storage-allow-microsoft-service-bypass.storage-allow-microsoft-service-bypass
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
    # Developer access from static IP for storage management
    ip_rules                   = [var.developer_ip]
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

# Enable Storage Analytics logging for queue operations to satisfy CKV_AZURE_33
resource "azurerm_storage_account_queue_properties" "main" {
  storage_account_id = azurerm_storage_account.main.id

  logging {
    delete                = true
    read                  = true
    write                 = true
    version               = "1.0"
    retention_policy_days = 7
  }
}

# Enable static website hosting
resource "azurerm_storage_account_static_website" "main" {
  storage_account_id = azurerm_storage_account.main.id
  index_document     = "index.html"
  error_404_document = "404.html"
}

# Note: The static website resource automatically creates a special "$web" container
# that serves content at the storage account's static website URL.
# Site-generator container writes HTML/CSS/JS directly to $web for live hosting.

# Enable Storage Analytics logging using modern diagnostic settings approach
# TODO: Re-enable after determining correct log categories for Storage Account
# resource "azurerm_monitor_diagnostic_setting" "storage_logging" {
#   name                       = "${local.resource_prefix}-storage-logs"
#   target_resource_id         = azurerm_storage_account.main.id
#   log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id

#   enabled_log {
#     category = "StorageRead"
#   }

#   enabled_log {
#     category = "StorageWrite"
#   }

#   enabled_log {
#     category = "StorageDelete"
#   }

#   enabled_metric {
#     category = "Transaction"
#   }
# }

# Enable blob service diagnostic settings for security compliance
# TODO: Re-enable after determining correct log categories for Blob service
# resource "azurerm_monitor_diagnostic_setting" "storage_blob_logging" {
#   name                       = "${local.resource_prefix}-blob-logs"
#   target_resource_id         = "${azurerm_storage_account.main.id}/blobServices/default"
#   log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id

#   enabled_log {
#     category = "StorageRead"
#   }

#   enabled_log {
#     category = "StorageWrite"
#   }

#   enabled_log {
#     category = "StorageDelete"
#   }

#   enabled_metric {
#     category = "Transaction"
#   }
# }

# Grant developer Storage Blob Data Contributor access for management
resource "azurerm_role_assignment" "developer_storage_blob_data_contributor" {
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = var.developer_object_id
}

# Grant developer Reader access to the storage account
resource "azurerm_role_assignment" "developer_storage_reader" {
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Reader"
  principal_id         = var.developer_object_id
}

# Grant developer Storage Queue Data Contributor access for queue management and monitoring
resource "azurerm_role_assignment" "developer_storage_queue_data_contributor" {
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Queue Data Contributor"
  principal_id         = var.developer_object_id
}

# Grant developer Storage Queue Data Reader access for queue monitoring
resource "azurerm_role_assignment" "developer_storage_queue_data_reader" {
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Queue Data Reader"
  principal_id         = var.developer_object_id
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

# Container for markdown content from markdown generator
resource "azurerm_storage_container" "markdown_content" {
  # checkov:skip=CKV2_AZURE_21: Logging not required for this use case
  name                  = "markdown-content"
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

# Storage Queues for container service communication (replaces Service Bus)
# Using Storage Queues to resolve Container Apps managed identity vs Service Bus connection string conflicts
resource "azurerm_storage_queue" "content_collection_requests" {
  name               = "content-collection-requests"
  storage_account_id = azurerm_storage_account.main.id

  lifecycle {
    # Prevent recreation when changing from storage_account_name to storage_account_id
    # The queue name is the stable identifier, not the account reference
    create_before_destroy = true
  }
}

resource "azurerm_storage_queue" "content_processing_requests" {
  name               = "content-processing-requests"
  storage_account_id = azurerm_storage_account.main.id

  lifecycle {
    # Prevent recreation when changing from storage_account_name to storage_account_id
    # The queue name is the stable identifier, not the account reference
    create_before_destroy = true
  }
}

resource "azurerm_storage_queue" "site_generation_requests" {
  name               = "site-generation-requests"
  storage_account_id = azurerm_storage_account.main.id

  lifecycle {
    # Prevent recreation when changing from storage_account_name to storage_account_id
    # The queue name is the stable identifier, not the account reference
    create_before_destroy = true
  }
}

# Container services now handle the content processing pipeline

# Azure OpenAI Cognitive Services Account
#checkov:skip=CKV_AZURE_247:Data loss prevention configuration complex for development environment
#checkov:skip=CKV2_AZURE_22:Customer-managed encryption would create circular dependency in development environment
#checkov:skip=CKV_AZURE_134:Public network access required for Container Apps Consumption tier to access via managed identity
# nosemgrep: terraform.azure.security.openai.public-network-access.public-network-access
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

  # Network access restrictions: Allow all networks, security via identity-based access control
  # checkov:skip=CKV_AZURE_134: Public network access required for Container Apps and GitHub Actions
  # nosemgrep: terraform.azure.security.openai.public-network-access.public-network-access
  # Security Strategy:
  # 1. GitHub Actions runner IPs are dynamic and unpredictable
  # 2. Container Apps consumption mode has no fixed egress IPs
  # 3. Security enforced via managed identity + RBAC (no local auth)
  # 4. Alternative requires expensive dedicated compute resources
  network_acls {
    default_action = "Allow" # Allow all networks - security via managed identity and RBAC
    # No IP restrictions: Dynamic IPs from GitHub Actions and Container Apps
    # Security provided by:
    # - System-assigned managed identity
    # - RBAC role assignments
    # - Disabled local authentication (local_auth_enabled = false)
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

  # Prevent expiration date churn
  lifecycle {
    ignore_changes = [expiration_date]
  }

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

  # Prevent expiration date churn
  lifecycle {
    ignore_changes = [expiration_date]
  }

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

  # Prevent expiration date churn
  lifecycle {
    ignore_changes = [expiration_date]
  }

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

# Container for collection templates used by content-collector service
resource "azurerm_storage_container" "collection_templates" {
  # checkov:skip=CKV2_AZURE_21: Logging not required for this use case
  name                  = "collection-templates"
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "private"
}

# Collection Templates - Upload collection templates to dedicated blob storage container for dynamic loading
resource "azurerm_storage_blob" "collection_template_default" {
  name                   = "default.json"
  storage_account_name   = azurerm_storage_account.main.name
  storage_container_name = azurerm_storage_container.collection_templates.name
  type                   = "Block"
  source                 = "${path.module}/../collection-templates/default.json"
  content_type           = "application/json"
}

resource "azurerm_storage_blob" "collection_template_tech_news" {
  name                   = "tech-news.json"
  storage_account_name   = azurerm_storage_account.main.name
  storage_container_name = azurerm_storage_container.collection_templates.name
  type                   = "Block"
  source                 = "${path.module}/../collection-templates/tech-news.json"
  content_type           = "application/json"
}

resource "azurerm_storage_blob" "collection_template_tech_rss" {
  name                   = "tech-rss.json"
  storage_account_name   = azurerm_storage_account.main.name
  storage_container_name = azurerm_storage_container.collection_templates.name
  type                   = "Block"
  source                 = "${path.module}/../collection-templates/tech-rss.json"
  content_type           = "application/json"
}

resource "azurerm_storage_blob" "collection_template_discovery" {
  name                   = "discovery.json"
  storage_account_name   = azurerm_storage_account.main.name
  storage_container_name = azurerm_storage_container.collection_templates.name
  type                   = "Block"
  source                 = "${path.module}/../collection-templates/discovery.json"
  content_type           = "application/json"
}

resource "azurerm_storage_blob" "collection_template_web_overlap_test" {
  name                   = "web-overlap-test.json"
  storage_account_name   = azurerm_storage_account.main.name
  storage_container_name = azurerm_storage_container.collection_templates.name
  type                   = "Block"
  source                 = "${path.module}/../collection-templates/web-overlap-test.json"
  content_type           = "application/json"
}

# Container Configuration Files - Upload container-specific configuration to enable blob-based config management
resource "azurerm_storage_blob" "content_processor_containers_config" {
  name                   = "config/content-processor-containers.json"
  storage_account_name   = azurerm_storage_account.main.name
  storage_container_name = azurerm_storage_container.collection_templates.name
  type                   = "Block"
  source                 = "${path.module}/../container-config/content-processor-containers.json"
  content_type           = "application/json"
}

resource "azurerm_storage_blob" "content_processor_processing_config" {
  name                   = "config/content-processor-processing.json"
  storage_account_name   = azurerm_storage_account.main.name
  storage_container_name = azurerm_storage_container.collection_templates.name
  type                   = "Block"
  source                 = "${path.module}/../container-config/content-processor-processing.json"
  content_type           = "application/json"
}

resource "azurerm_storage_blob" "content_collector_containers_config" {
  name                   = "config/content-collector-containers.json"
  storage_account_name   = azurerm_storage_account.main.name
  storage_container_name = azurerm_storage_container.collection_templates.name
  type                   = "Block"
  source                 = "${path.module}/../container-config/content-collector-containers.json"
  content_type           = "application/json"
}

resource "azurerm_storage_blob" "content_collector_processing_config" {
  name                   = "config/content-collector-processing.json"
  storage_account_name   = azurerm_storage_account.main.name
  storage_container_name = azurerm_storage_container.collection_templates.name
  type                   = "Block"
  source                 = "${path.module}/../container-config/content-collector-processing.json"
  content_type           = "application/json"
}

# Resource lock to prevent accidental deletion
# Created LAST to avoid blocking infrastructure updates during deployment
# Note: Temporarily disabled during deployment to allow resource cleanup
/*
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

    # Storage containers (only active ones remain)
    azurerm_storage_container.collected_content,
    azurerm_storage_container.processed_content,
    azurerm_storage_container.markdown_content,
    azurerm_storage_container.pipeline_logs,
    azurerm_storage_container.prompts,
    azurerm_storage_container.collection_templates,

    # Key Vault secrets and policies
    azurerm_key_vault_secret.openai_endpoint,
    azurerm_key_vault_access_policy.developer_user,
    azurerm_key_vault_access_policy.github_actions_user
  ]
}
*/

# Force infrastructure deployment trigger
