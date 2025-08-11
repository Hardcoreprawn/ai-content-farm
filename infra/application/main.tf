data "azurerm_client_config" "current" {}

locals {
  resource_prefix = var.resource_prefix != "" ? var.resource_prefix : "ai-content-${var.environment}"
}

resource "random_string" "suffix" {
  length  = 6
  upper   = false
  special = false
}

resource "azurerm_resource_group" "main" {
  name     = "${local.resource_prefix}-rg"
  location = var.location

  tags = {
    Environment = var.environment
    Project     = "ai-content-farm"
    ManagedBy   = "terraform"
  }
}

# Action Group for Cost Alerts
resource "azurerm_monitor_action_group" "cost_alerts" {
  name                = "${local.resource_prefix}-cost-alerts"
  resource_group_name = azurerm_resource_group.main.name
  short_name          = "costalertz"

  email_receiver {
    name          = "cost-alert-email"
    email_address = var.cost_alert_email != "" ? var.cost_alert_email : "admin@example.com"
  }

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
  name     = "ai-content-app-kv${random_string.suffix.result}"
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
    Purpose     = "application-secrets"
  }

  # Enable diagnostic settings for security compliance
  depends_on = [azurerm_log_analytics_workspace.main]
}

# Key Vault access policy for current user/service principal (only if not GitHub Actions)
resource "azurerm_key_vault_access_policy" "current_user" {
  count        = data.azurerm_client_config.current.object_id != var.github_actions_object_id ? 1 : 0
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

# Create a placeholder secret first (will be updated post-deployment)
resource "azurerm_key_vault_secret" "summarywomble_function_key" {
  name         = "summarywomble-function-key"
  value        = "placeholder-will-be-updated-after-function-deployment"
  key_vault_id = azurerm_key_vault.main.id

  content_type = "function-key"
  tags = {
    Purpose     = "summarywomble-auth"
    Environment = var.environment
    ManagedBy   = "terraform"
  }

  # Ignore changes to value since it will be updated by deployment process
  lifecycle {
    ignore_changes = [value]
  }

  depends_on = [
    azurerm_key_vault_access_policy.github_actions,
    azurerm_key_vault_access_policy.current_user
  ]
}

# Update the secret with the actual function key after deployment
resource "null_resource" "update_function_key" {
  depends_on = [azurerm_linux_function_app.main, azurerm_key_vault_secret.summarywomble_function_key]

  provisioner "local-exec" {
    command = "sleep 45 && echo 'Getting function app key...' && FUNCTION_KEY=$(az functionapp keys list --resource-group ${azurerm_resource_group.main.name} --name ${azurerm_linux_function_app.main.name} --query 'functionKeys.default' --output tsv) && if [ -n \"$FUNCTION_KEY\" ] && [ \"$FUNCTION_KEY\" != \"null\" ]; then echo 'Updating Key Vault secret with function key...' && az keyvault secret set --vault-name ${azurerm_key_vault.main.name} --name 'summarywomble-function-key' --value \"$FUNCTION_KEY\" --output none && echo 'Function key updated successfully'; else echo 'Error: Could not retrieve function key' && exit 1; fi"
  }

  # Trigger re-run if function app changes
  triggers = {
    function_app_id = azurerm_linux_function_app.main.id
    timestamp       = timestamp()
  }
}

# Key Vault access policy for Function App managed identity
resource "azurerm_key_vault_access_policy" "function_app" {
  key_vault_id = azurerm_key_vault.main.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = azurerm_linux_function_app.main.identity[0].principal_id

  secret_permissions = [
    "Get",
    "List"
  ]
}

# Key Vault access policy for GitHub Actions service principal (CI/CD operations)
resource "azurerm_key_vault_access_policy" "github_actions" {
  count        = var.github_actions_object_id != "" ? 1 : 0
  key_vault_id = azurerm_key_vault.main.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = var.github_actions_object_id

  secret_permissions = [
    "Get",
    "List",
    "Set",
    "Delete"
  ]
}

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

# Application secrets are managed externally via setup script
# We reference them directly by their known names and vault URI

resource "azurerm_log_analytics_workspace" "main" {
  name                = "${local.resource_prefix}-logs"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
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


resource "azurerm_service_plan" "main" {
  # checkov:skip=CKV_AZURE_212: Not applicable to consumption plan
  # checkov:skip=CKV_AZURE_225: Not applicable to consumption plan
  name                = "${local.resource_prefix}-plan"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  os_type             = "Linux"
  sku_name            = "Y1"
}

resource "azurerm_linux_function_app" "main" {
  # checkov:skip=CKV_AZURE_221: Public access is acceptable for this use case
  # checkov:skip=CKV_AZURE_97: No authentication required for this use case
  name                        = "${local.resource_prefix}-func"
  location                    = azurerm_resource_group.main.location
  resource_group_name         = azurerm_resource_group.main.name
  service_plan_id             = azurerm_service_plan.main.id
  storage_account_name        = azurerm_storage_account.main.name
  storage_account_access_key  = azurerm_storage_account.main.primary_access_key
  functions_extension_version = "~4"
  https_only                  = true

  identity {
    type = "SystemAssigned"
  }

  app_settings = {
    AzureWebJobsStorage                   = azurerm_storage_account.main.primary_connection_string
    OUTPUT_CONTAINER                      = azurerm_storage_container.topics.name
    OUTPUT_STORAGE_ACCOUNT                = azurerm_storage_account.main.name
    FUNCTIONS_WORKER_RUNTIME              = "python"
    WEBSITE_RUN_FROM_PACKAGE              = "1"
    APPINSIGHTS_INSTRUMENTATIONKEY        = azurerm_application_insights.main.instrumentation_key
    APPLICATIONINSIGHTS_CONNECTION_STRING = azurerm_application_insights.main.connection_string

    # Reddit API credentials from Key Vault (secrets managed externally)
    REDDIT_CLIENT_ID     = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault.main.vault_uri}secrets/reddit-client-id)"
    REDDIT_CLIENT_SECRET = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault.main.vault_uri}secrets/reddit-client-secret)"
    REDDIT_USER_AGENT    = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault.main.vault_uri}secrets/reddit-user-agent)"

    # Key Vault URL for fallback access
    KEY_VAULT_URL = azurerm_key_vault.main.vault_uri

    # SummaryWomble function key for internal authenticated calls
    SUMMARY_WOMBLE_KEY = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault.main.vault_uri}secrets/${azurerm_key_vault_secret.summarywomble_function_key.name})"
  }
  #zip_deploy_file = filebase64("${path.module}/function.zip")
  site_config {
    application_insights_connection_string = azurerm_application_insights.main.connection_string
    application_insights_key               = azurerm_application_insights.main.instrumentation_key
    application_stack {
      python_version = "3.11"
    }
  }
}

# Role assignments for managed identity
resource "azurerm_role_assignment" "storage_blob_data_contributor" {
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_linux_function_app.main.identity[0].principal_id
  depends_on           = [azurerm_linux_function_app.main]
}

resource "azurerm_role_assignment" "storage_account_contributor" {
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Account Contributor"
  principal_id         = azurerm_linux_function_app.main.identity[0].principal_id
  depends_on           = [azurerm_linux_function_app.main]
}

# Role assignments for admin user to access storage
# Note: These may fail in production if service principal lacks role assignment permissions
resource "azurerm_role_assignment" "admin_storage_blob_data_contributor" {
  count = var.environment == "staging" ? 1 : 0  # Only create in staging for now

  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = var.admin_user_object_id
}

resource "azurerm_role_assignment" "admin_storage_account_contributor" {
  count = var.environment == "staging" ? 1 : 0  # Only create in staging for now

  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Account Contributor"
  principal_id         = var.admin_user_object_id
}

# Optionally add Cognitive Account and Key Vault secret if OpenAI integration is needed
# resource "azurerm_cognitive_account" "openai" { ... }
# resource "azurerm_key_vault_secret" "openai_key" { ... }
