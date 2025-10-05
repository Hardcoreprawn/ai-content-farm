# Data sources and shared configuration
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
