# Azure Container Apps infrastructure for AI Content Farm

# Container Apps Environment - reusing main Log Analytics workspace for cost efficiency
# Using Consumption plan without VNet integration for simplicity and cost optimization
resource "azurerm_container_app_environment" "main" {
  name                       = "${local.resource_prefix}-env"
  location                   = var.location
  resource_group_name        = azurerm_resource_group.main.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id # Reuse main workspace

  tags = local.common_tags
}

# Log Analytics Workspace consolidated with main workspace for cost efficiency
# Using azurerm_log_analytics_workspace.main from main.tf

# Managed Identity for containers
resource "azurerm_user_assigned_identity" "containers" {
  name                = "${local.resource_prefix}-containers-identity"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name

  tags = local.common_tags
}

# Managed Identity for GitHub Actions CI/CD
resource "azurerm_user_assigned_identity" "github_actions" {
  name                = "${local.resource_prefix}-github-actions"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name

  tags = merge(local.common_tags, {
    Purpose = "github-actions-oidc"
  })
}

# Federated Identity Credential for GitHub Actions (main branch)
resource "azurerm_federated_identity_credential" "github_main" {
  name                = "github-main-branch"
  resource_group_name = azurerm_resource_group.main.name
  audience            = ["api://AzureADTokenExchange"]
  issuer              = "https://token.actions.githubusercontent.com"
  parent_id           = azurerm_user_assigned_identity.github_actions.id
  subject             = "repo:Hardcoreprawn/ai-content-farm:ref:refs/heads/main"
}

# Federated Identity Credential for GitHub Actions (develop branch)
resource "azurerm_federated_identity_credential" "github_develop" {
  name                = "github-develop-branch"
  resource_group_name = azurerm_resource_group.main.name
  audience            = ["api://AzureADTokenExchange"]
  issuer              = "https://token.actions.githubusercontent.com"
  parent_id           = azurerm_user_assigned_identity.github_actions.id
  subject             = "repo:Hardcoreprawn/ai-content-farm:ref:refs/heads/develop"
}

# Federated Identity Credential for GitHub Actions (pull requests)
resource "azurerm_federated_identity_credential" "github_pr" {
  name                = "github-pull-requests"
  resource_group_name = azurerm_resource_group.main.name
  audience            = ["api://AzureADTokenExchange"]
  issuer              = "https://token.actions.githubusercontent.com"
  parent_id           = azurerm_user_assigned_identity.github_actions.id
  subject             = "repo:Hardcoreprawn/ai-content-farm:pull_request"
}

# Managed Identity for Service Bus encryption - DISABLED for Standard SKU cost optimization
# Standard Service Bus SKU uses Azure-managed encryption and doesn't support customer-managed keys
# This resource is kept commented for future upgrade to Premium SKU if needed
#
# resource "azurerm_user_assigned_identity" "servicebus" {
#   name                = "${local.resource_prefix}-servicebus-identity"
#   location            = var.location
#   resource_group_name = azurerm_resource_group.main.name
#   tags = local.common_tags
# }

# Grant container identity access to Key Vault
resource "azurerm_key_vault_access_policy" "containers" {
  key_vault_id = azurerm_key_vault.main.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = azurerm_user_assigned_identity.containers.principal_id

  secret_permissions = [
    "Get",
    "List"
  ]

  depends_on = [azurerm_user_assigned_identity.containers]
}

# Grant container identity read access to Storage Account (for listing containers)
resource "azurerm_role_assignment" "containers_storage_blob_data_reader" {
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Reader"
  principal_id         = azurerm_user_assigned_identity.containers.principal_id
}

# Grant container identity write access to collected-content container only
resource "azurerm_role_assignment" "containers_storage_blob_data_contributor" {
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.containers.principal_id
}

# Grant container identity access to Key Vault secrets
resource "azurerm_role_assignment" "containers_key_vault_secrets_user" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.containers.principal_id
}

# Grant container identity access to Azure OpenAI
resource "azurerm_role_assignment" "containers_cognitive_services_openai_user" {
  scope                = azurerm_cognitive_account.openai.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_user_assigned_identity.containers.principal_id
}

# Grant container identity access to Storage Queues (replaces Service Bus)
resource "azurerm_role_assignment" "containers_storage_queue_data_contributor" {
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Queue Data Contributor"
  principal_id         = azurerm_user_assigned_identity.containers.principal_id
}

# Grant GitHub Actions identity access to subscription (for deployments)
resource "azurerm_role_assignment" "github_actions_contributor" {
  scope                = "/subscriptions/${data.azurerm_client_config.current.subscription_id}"
  role_definition_name = "Contributor"
  principal_id         = azurerm_user_assigned_identity.github_actions.principal_id
}

# Grant GitHub Actions identity access to Key Vault
resource "azurerm_key_vault_access_policy" "github_actions" {
  key_vault_id = azurerm_key_vault.main.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = azurerm_user_assigned_identity.github_actions.principal_id

  secret_permissions = [
    "Get",
    "List",
    "Set",
    "Delete",
    "Purge",
    "Recover"
  ]

  depends_on = [azurerm_user_assigned_identity.github_actions]
}

# Storage Queue configuration replaces Service Bus for better Container Apps integration
# Storage Queues support managed identity authentication with KEDA scaling
# This resolves the authentication conflict between managed identity and connection strings

# Content Collector Container App
