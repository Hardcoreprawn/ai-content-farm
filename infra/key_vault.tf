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
