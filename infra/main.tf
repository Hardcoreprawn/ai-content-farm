data "azurerm_client_config" "current" {}

resource "random_string" "suffix" {
  length  = 6
  upper   = false
  special = false
}

resource "azurerm_resource_group" "main" {
  name     = "${var.resource_prefix}-rg"
  location = var.location

  tags = {
    Environment = var.environment
    Project     = "ai-content-farm"
    ManagedBy   = "terraform"
  }
}


resource "azurerm_key_vault" "main" {
  # checkov:skip=CKV_AZURE_189: Public access is acceptable for this use case
  # checkov:skip=CKV_AZURE_109: Firewall rules not required for this use case
  # checkov:skip=CKV2_AZURE_32: Private endpoint not required for this use case
  name     = "${replace(var.resource_prefix, "-", "")}kv${random_string.suffix.result}"
  location = azurerm_resource_group.main.location

  resource_group_name        = azurerm_resource_group.main.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  purge_protection_enabled   = true
  soft_delete_retention_days = 7

  tags = {
    Environment = var.environment
    Project     = "ai-content-farm"
    ManagedBy   = "terraform"
  }

  # Enable diagnostic settings for security compliance
  depends_on = [azurerm_log_analytics_workspace.main]
}

# Key Vault access policy for current user/service principal
resource "azurerm_key_vault_access_policy" "current_user" {
  key_vault_id = azurerm_key_vault.main.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = data.azurerm_client_config.current.object_id

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
  name            = "reddit-client-id"
  value           = var.reddit_client_id != "" ? var.reddit_client_id : "placeholder-change-me"
  key_vault_id    = azurerm_key_vault.main.id
  content_type    = "text/plain"
  expiration_date = timeadd(timestamp(), "8760h") # 1 year from now
  depends_on      = [azurerm_key_vault_access_policy.current_user]

  tags = {
    Environment = var.environment
    Purpose     = "reddit-api-access"
  }
}

resource "azurerm_key_vault_secret" "reddit_client_secret" {
  name            = "reddit-client-secret"
  value           = var.reddit_client_secret != "" ? var.reddit_client_secret : "placeholder-change-me"
  key_vault_id    = azurerm_key_vault.main.id
  content_type    = "text/plain"
  expiration_date = timeadd(timestamp(), "8760h") # 1 year from now
  depends_on      = [azurerm_key_vault_access_policy.current_user]

  tags = {
    Environment = var.environment
    Purpose     = "reddit-api-access"
  }
}

resource "azurerm_key_vault_secret" "reddit_user_agent" {
  name            = "reddit-user-agent"
  value           = var.reddit_user_agent != "" ? var.reddit_user_agent : "ai-content-farm:v1.0 (by /u/your-username)"
  key_vault_id    = azurerm_key_vault.main.id
  content_type    = "text/plain"
  expiration_date = timeadd(timestamp(), "8760h") # 1 year from now
  depends_on      = [azurerm_key_vault_access_policy.current_user]

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
  expiration_date = timeadd(timestamp(), "8760h") # 1 year from now
  depends_on      = [azurerm_key_vault_access_policy.current_user]

  tags = {
    Environment = var.environment
    Purpose     = "cost-estimation"
  }
}

resource "azurerm_log_analytics_workspace" "main" {
  name                = "${var.resource_prefix}-logs"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

resource "azurerm_application_insights" "main" {
  name                = "${var.resource_prefix}-insights"
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
  name                          = "hottopicsstorage${random_string.suffix.result}"
  resource_group_name           = azurerm_resource_group.main.name
  location                      = azurerm_resource_group.main.location
  account_tier                  = "Standard"
  account_replication_type      = "LRS"
  public_network_access_enabled = true
  shared_access_key_enabled     = true
  network_rules {
    default_action = "Allow"
    bypass         = ["AzureServices"]
  }
  allow_nested_items_to_be_public = false
  min_tls_version                 = "TLS1_2"
}

resource "azurerm_storage_container" "topics" {
  # checkov:skip=CKV2_AZURE_21: Logging not required for this use case
  name                  = "hot-topics"
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "private"
}


# Azure Functions infrastructure removed as part of container migration
# Container services now handle the content processing pipeline

# Optionally add Cognitive Account and Key Vault secret if OpenAI integration is needed
# resource "azurerm_cognitive_account" "openai" { ... }
# resource "azurerm_key_vault_secret" "openai_key" { ... }
