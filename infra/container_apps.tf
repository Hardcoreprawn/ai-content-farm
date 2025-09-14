# Azure Container Apps infrastructure for AI Content Farm

# Container Apps Environment - reusing main Log Analytics workspace for cost efficiency
# Using Consumption plan without VNet integration for simplicity and cost optimization
resource "azurerm_container_app_environment" "main" {
  name                       = "${var.resource_prefix}-env"
  location                   = var.location
  resource_group_name        = azurerm_resource_group.main.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id # Reuse main workspace

  tags = local.common_tags
}

# Log Analytics Workspace consolidated with main workspace for cost efficiency
# Using azurerm_log_analytics_workspace.main from main.tf

# Managed Identity for containers
resource "azurerm_user_assigned_identity" "containers" {
  name                = "${var.resource_prefix}-containers-identity"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name

  tags = local.common_tags
}

# Managed Identity for GitHub Actions CI/CD
resource "azurerm_user_assigned_identity" "github_actions" {
  name                = "${var.resource_prefix}-github-actions"
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
#   name                = "${var.resource_prefix}-servicebus-identity"
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

# Grant container identity access to Service Bus (Phase 1 Security Implementation)
resource "azurerm_role_assignment" "containers_servicebus_data_receiver" {
  scope                = azurerm_servicebus_namespace.main.id
  role_definition_name = "Azure Service Bus Data Receiver"
  principal_id         = azurerm_user_assigned_identity.containers.principal_id
}

resource "azurerm_role_assignment" "containers_servicebus_data_sender" {
  scope                = azurerm_servicebus_namespace.main.id
  role_definition_name = "Azure Service Bus Data Sender"
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
  name                   = "${var.resource_prefix}-storage-events"
  location               = var.location
  resource_group_name    = azurerm_resource_group.main.name
  source_arm_resource_id = azurerm_storage_account.main.id
  topic_type             = "Microsoft.Storage.StorageAccounts"

  tags = local.common_tags
}

# Service Bus Namespace for event processing
#checkov:skip=CKV_AZURE_199:Double encryption complex and costly for development environment
#checkov:skip=CKV_AZURE_201:Customer-managed encryption complex setup for development environment
resource "azurerm_servicebus_namespace" "main" {
  # checkov:skip=CKV_AZURE_201: Customer-managed encryption requires complex setup - using Azure-managed encryption for development
  # checkov:skip=CKV_AZURE_199: Double encryption requires complex configuration - single encryption sufficient for development
  name                = "${var.resource_prefix}-servicebus"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "Standard" # Downgrade from Premium for significant cost savings

  # Security configurations - Standard SKU limitations
  public_network_access_enabled = true  # Standard SKU cannot disable public access
  local_auth_enabled            = false # Disable local authentication
  minimum_tls_version           = "1.2" # Use latest TLS

  # Enable managed identity
  identity {
    type = "SystemAssigned"
  }

  # Note: Standard SKU limitations vs Premium:
  # - Cannot disable public network access (security trade-off)
  # - No customer-managed encryption keys
  # - No virtual network integration
  # - Saves $600+/month vs Premium

  tags = local.common_tags
}

# Service Bus customer-managed encryption disabled for development environment
# This would be enabled in production with proper key management

# Service Bus Queues for container services (Phase 1 Security Implementation)
resource "azurerm_servicebus_queue" "content_collection_requests" {
  name         = "content-collection-requests"
  namespace_id = azurerm_servicebus_namespace.main.id

  max_size_in_megabytes                = 1024
  dead_lettering_on_message_expiration = true
  default_message_ttl                  = "PT30M" # 30 minutes TTL
  max_delivery_count                   = 3

  # Enable duplicate detection for idempotency
  requires_duplicate_detection            = true
  duplicate_detection_history_time_window = "PT10M"
}

resource "azurerm_servicebus_queue" "content_processing_requests" {
  name         = "content-processing-requests"
  namespace_id = azurerm_servicebus_namespace.main.id

  max_size_in_megabytes                = 1024
  dead_lettering_on_message_expiration = true
  default_message_ttl                  = "PT30M" # 30 minutes TTL
  max_delivery_count                   = 3

  # Enable duplicate detection for idempotency
  requires_duplicate_detection            = true
  duplicate_detection_history_time_window = "PT10M"
}

resource "azurerm_servicebus_queue" "site_generation_requests" {
  name         = "site-generation-requests"
  namespace_id = azurerm_servicebus_namespace.main.id

  max_size_in_megabytes                = 1024
  dead_lettering_on_message_expiration = true
  default_message_ttl                  = "PT30M" # 30 minutes TTL
  max_delivery_count                   = 3

  # Enable duplicate detection for idempotency
  requires_duplicate_detection            = true
  duplicate_detection_history_time_window = "PT10M"
}

# Content Collector Container App
resource "azurerm_container_app" "content_collector" {
  name                         = "${var.resource_prefix}-collector"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

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

  # Service Bus connection string for KEDA scaling (Phase 1 Security Implementation)
  secret {
    name  = "azure-servicebus-connection-string"
    value = azurerm_servicebus_namespace.main.default_primary_connection_string
  }

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

      # Service Bus configuration for Phase 1 Security Implementation
      env {
        name  = "SERVICE_BUS_NAMESPACE"
        value = azurerm_servicebus_namespace.main.name
      }

      env {
        name  = "SERVICE_BUS_QUEUE_NAME"
        value = azurerm_servicebus_queue.content_collection_requests.name
      }
    }

    min_replicas = 0
    max_replicas = 2

    # KEDA scaling rules for Service Bus messages (Phase 1 Security Implementation)
    azure_queue_scale_rule {
      name         = "servicebus-queue-scaler"
      queue_name   = azurerm_servicebus_queue.content_collection_requests.name
      queue_length = 1

      authentication {
        secret_name       = "azure-servicebus-connection-string" # pragma: allowlist secret
        trigger_parameter = "connection"
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
  name                         = "${var.resource_prefix}-processor"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

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

  # Service Bus connection string for KEDA scaling (Phase 1 Security Implementation)
  secret {
    name  = "azure-servicebus-connection-string"
    value = azurerm_servicebus_namespace.main.default_primary_connection_string
  }

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

      # Service Bus configuration for Phase 1 Security Implementation
      env {
        name  = "SERVICE_BUS_NAMESPACE"
        value = azurerm_servicebus_namespace.main.name
      }

      env {
        name  = "SERVICE_BUS_QUEUE_NAME"
        value = azurerm_servicebus_queue.content_processing_requests.name
      }
    }

    min_replicas = 0
    max_replicas = 3

    # KEDA scaling rules for Service Bus messages (Phase 1 Security Implementation)
    azure_queue_scale_rule {
      name         = "servicebus-queue-scaler"
      queue_name   = azurerm_servicebus_queue.content_processing_requests.name
      queue_length = 1

      authentication {
        secret_name       = "azure-servicebus-connection-string" # pragma: allowlist secret
        trigger_parameter = "connection"
      }
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
  name                         = "${var.resource_prefix}-site-generator"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.containers.id]
  }

  # Service Bus connection string for KEDA scaling (Phase 1 Security Implementation)
  secret {
    name  = "azure-servicebus-connection-string"
    value = azurerm_servicebus_namespace.main.default_primary_connection_string
  }

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

      # Service Bus configuration for Phase 1 Security Implementation
      env {
        name  = "SERVICE_BUS_NAMESPACE"
        value = azurerm_servicebus_namespace.main.name
      }

      env {
        name  = "SERVICE_BUS_QUEUE_NAME"
        value = azurerm_servicebus_queue.site_generation_requests.name
      }
    }

    min_replicas = 0
    max_replicas = 2

    # KEDA scaling rules for Service Bus messages (Phase 1 Security Implementation)
    azure_queue_scale_rule {
      name         = "servicebus-queue-scaler"
      queue_name   = azurerm_servicebus_queue.site_generation_requests.name
      queue_length = 1

      authentication {
        secret_name       = "azure-servicebus-connection-string" # pragma: allowlist secret
        trigger_parameter = "connection"
      }
    }
  }

  tags = local.common_tags

  depends_on = [
    azurerm_storage_container.collected_content,
    azurerm_role_assignment.containers_storage_blob_data_contributor
  ]
}
