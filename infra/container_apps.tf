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

# Event Grid System Topic for Storage Account - used by Azure Functions for pipeline automation
resource "azurerm_eventgrid_system_topic" "storage" {
  name                   = "${local.resource_prefix}-storage-events"
  location               = var.location
  resource_group_name    = azurerm_resource_group.main.name
  source_arm_resource_id = azurerm_storage_account.main.id
  topic_type             = "Microsoft.Storage.StorageAccounts"

  tags = local.common_tags
}

# Storage Queue configuration replaces Service Bus for better Container Apps integration
# Storage Queues support managed identity authentication with KEDA scaling
# This resolves the authentication conflict between managed identity and connection strings

# Content Collector Container App
resource "azurerm_container_app" "content_collector" {
  name                         = "${local.resource_prefix}-collector"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  lifecycle {
    ignore_changes = [template[0].container[0].image]
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.containers.id]
  }

  secret {
    name  = "reddit-client-id"
    value = azurerm_key_vault_secret.reddit_client_id.value
  }

  secret {
    name  = "reddit-client-secret"
    value = azurerm_key_vault_secret.reddit_client_secret.value
  }

  secret {
    name  = "reddit-user-agent"
    value = azurerm_key_vault_secret.reddit_user_agent.value
  }

  # Storage Queue configuration (replaces Service Bus for Container Apps compatibility)
  # Storage Queues support managed identity authentication with KEDA scaling
  # This resolves authentication conflicts between managed identity and connection strings

  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "http"

    # No IP restrictions - allowing Azure Logic Apps to access
    # TODO: Consider adding Azure service tag restrictions for production security

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  template {
    container {
      name   = "content-collector"
      image  = local.container_images["content-collector"]
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "AZURE_CLIENT_ID"
        value = azurerm_user_assigned_identity.containers.client_id
      }

      env {
        name  = "AZURE_STORAGE_ACCOUNT_NAME"
        value = azurerm_storage_account.main.name
      }

      env {
        name        = "REDDIT_CLIENT_ID"
        secret_name = "reddit-client-id"
      }

      env {
        name        = "REDDIT_CLIENT_SECRET"
        secret_name = "reddit-client-secret"
      }

      env {
        name        = "REDDIT_USER_AGENT"
        secret_name = "reddit-user-agent" # pragma: allowlist secret
      }

      env {
        name  = "ENVIRONMENT"
        value = "production"
      }

      # Storage Queue configuration for wake-up pattern
      env {
        name  = "STORAGE_QUEUE_NAME"
        value = azurerm_storage_queue.content_collection_requests.name
      }

      # Enable KEDA cron triggering for scheduled collections
      env {
        name  = "KEDA_CRON_TRIGGER"
        value = "true"
      }

      # Disable auto-shutdown for debugging (set to false for production efficiency)
      env {
        name  = "DISABLE_AUTO_SHUTDOWN"
        value = "true"
      }
    }

    min_replicas = 0
    max_replicas = 2

    # KEDA cron scaler for regular content collection
    # Triggers collection 3 times per day to reduce API load while maintaining fresh content
    custom_scale_rule {
      name             = "cron-scaler"
      custom_rule_type = "cron"
      metadata = {
        timezone        = "UTC"
        start           = "0 0,8,16 * * *"  # Every 8 hours: 00:00, 08:00, 16:00 UTC
        end             = "10 0,8,16 * * *" # Stop scaling after 10 minutes
        desiredReplicas = "1"
      }
    }
  }

  tags = local.common_tags

  depends_on = [
    azurerm_storage_container.collected_content,
    azurerm_role_assignment.containers_storage_blob_data_contributor
  ]
}

# Content Processor Container App
resource "azurerm_container_app" "content_processor" {
  name                         = "${local.resource_prefix}-processor"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  lifecycle {
    ignore_changes = [template[0].container[0].image]
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.containers.id]
  }

  secret {
    name  = "openai-chat-model"
    value = azurerm_key_vault_secret.openai_chat_model.value
  }

  secret {
    name  = "openai-embedding-model"
    value = azurerm_key_vault_secret.openai_embedding_model.value
  }

  # Storage Queue configuration (replaces Service Bus)

  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "http"

    # IP restrictions for secure access
    ip_security_restriction {
      action           = "Allow"
      ip_address_range = "81.2.90.47/32"
      name             = "AllowStaticIP"
    }

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  template {
    container {
      name   = "content-processor"
      image  = local.container_images["content-processor"]
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "AZURE_CLIENT_ID"
        value = azurerm_user_assigned_identity.containers.client_id
      }

      env {
        name  = "AZURE_STORAGE_ACCOUNT_NAME"
        value = azurerm_storage_account.main.name
      }

      env {
        name  = "AZURE_TENANT_ID"
        value = data.azurerm_client_config.current.tenant_id
      }

      env {
        name  = "AZURE_SUBSCRIPTION_ID"
        value = data.azurerm_client_config.current.subscription_id
      }

      env {
        name  = "AZURE_OPENAI_ENDPOINT"
        value = azurerm_cognitive_account.openai.endpoint
      }

      env {
        name        = "AZURE_OPENAI_CHAT_MODEL"
        secret_name = "openai-chat-model" # pragma: allowlist secret
      }

      env {
        name        = "AZURE_OPENAI_EMBEDDING_MODEL"
        secret_name = "openai-embedding-model" # pragma: allowlist secret
      }

      env {
        name  = "ENVIRONMENT"
        value = "production"
      }

      # Storage Queue configuration for wake-up pattern
      env {
        name  = "STORAGE_QUEUE_NAME"
        value = azurerm_storage_queue.content_processing_requests.name
      }

      # Disable auto-shutdown for debugging (set to false for production efficiency)
      env {
        name  = "DISABLE_AUTO_SHUTDOWN"
        value = "true"
      }
    }

    min_replicas = 0
    max_replicas = 3

    # KEDA scaling rules for Storage Queue messages with managed identity
    # Updated for individual item processing (responsive scaling)
    custom_scale_rule {
      name             = "storage-queue-scaler"
      custom_rule_type = "azure-queue"
      metadata = {
        queueName   = azurerm_storage_queue.content_processing_requests.name
        accountName = azurerm_storage_account.main.name
        queueLength = "1" # Scale immediately when individual items arrive
        cloud       = "AzurePublicCloud"
      }
      # Using managed identity - no authentication block needed
      # The container's managed identity will be used automatically
    }
  }

  tags = local.common_tags

  depends_on = [
    azurerm_storage_container.collected_content,
    azurerm_role_assignment.containers_storage_blob_data_contributor,
    azurerm_cognitive_account.openai
  ]
}

# Site Generator Container App
resource "azurerm_container_app" "site_generator" {
  name                         = "${local.resource_prefix}-site-generator"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  lifecycle {
    ignore_changes = [template[0].container[0].image]
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.containers.id]
  }

  # Storage Queue configuration (replaces Service Bus)

  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "http"

    # IP restrictions for secure access
    ip_security_restriction {
      action           = "Allow"
      ip_address_range = "81.2.90.47/32"
      name             = "AllowStaticIP"
    }

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  template {
    container {
      name   = "site-generator"
      image  = local.container_images["site-generator"]
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "AZURE_CLIENT_ID"
        value = azurerm_user_assigned_identity.containers.client_id
      }

      env {
        name  = "AZURE_STORAGE_ACCOUNT_NAME"
        value = azurerm_storage_account.main.name
      }

      env {
        name  = "AZURE_STORAGE_ACCOUNT_URL"
        value = azurerm_storage_account.main.primary_blob_endpoint
      }

      env {
        name  = "SITE_TITLE"
        value = "JabLab Tech News"
      }

      env {
        name  = "SITE_DESCRIPTION"
        value = "AI-curated technology news and insights"
      }

      env {
        name  = "SITE_DOMAIN"
        value = "jablab.dev"
      }

      env {
        name  = "SITE_URL"
        value = "https://jablab.dev"
      }

      env {
        name  = "PROCESSED_CONTENT_CONTAINER"
        value = "processed-content"
      }

      env {
        name  = "MARKDOWN_CONTENT_CONTAINER"
        value = "markdown-content"
      }

      env {
        name  = "STATIC_SITES_CONTAINER"
        value = "static-sites"
      }

      env {
        name  = "ENVIRONMENT"
        value = "production"
      }

      # Storage Queue configuration for wake-up pattern
      env {
        name  = "STORAGE_QUEUE_NAME"
        value = azurerm_storage_queue.site_generation_requests.name
      }

      # Disable auto-shutdown for debugging (set to false for production efficiency)
      env {
        name  = "DISABLE_AUTO_SHUTDOWN"
        value = "true"
      }
    }

    min_replicas = 0
    max_replicas = 2

    # KEDA scaling rules for Storage Queue messages with managed identity
    # Site generator handles generation requests for processed content
    custom_scale_rule {
      name             = "storage-queue-scaler"
      custom_rule_type = "azure-queue"
      metadata = {
        queueName   = azurerm_storage_queue.site_generation_requests.name
        accountName = azurerm_storage_account.main.name
        queueLength = "1" # Process generation requests immediately
        cloud       = "AzurePublicCloud"
      }
      # Using managed identity - no authentication block needed
      # The container's managed identity will be used automatically
    }
  }

  tags = local.common_tags

  depends_on = [
    azurerm_storage_container.collected_content,
    azurerm_role_assignment.containers_storage_blob_data_contributor
  ]
}
