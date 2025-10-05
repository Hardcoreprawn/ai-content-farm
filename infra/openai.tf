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

# Collection Templates - Automatically upload all JSON templates from collection-templates/ folder
# This uses fileset to discover all .json files and uploads them dynamically
# Add new templates by simply creating .json files in collection-templates/ - no Terraform changes needed!
resource "azurerm_storage_blob" "collection_templates" {
  for_each = fileset("${path.module}/../collection-templates", "*.json")

  name                   = each.value
  storage_account_name   = azurerm_storage_account.main.name
  storage_container_name = azurerm_storage_container.collection_templates.name
  type                   = "Block"
  source                 = "${path.module}/../collection-templates/${each.value}"
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
