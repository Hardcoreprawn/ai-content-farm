# Azure Container Apps infrastructure for AI Content Farm

# Local values for access control
locals {
  # Allow access from your static IP for development/monitoring
  allowed_ips = [
    "81.2.90.47/32" # Your current static IP
  ]
}

# Container Apps Environment - reusing main Log Analytics workspace for cost efficiency
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
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azurerm_user_assigned_identity.containers.principal_id

  depends_on = [azurerm_user_assigned_identity.containers]
}

# Grant container identity write access to collected-content container only
resource "azurerm_role_assignment" "containers_storage_blob_data_contributor" {
  scope                = "${azurerm_storage_account.main.id}/blobServices/default/containers/${azurerm_storage_container.collected_content.name}"
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.containers.principal_id

  depends_on = [
    azurerm_user_assigned_identity.containers,
    azurerm_storage_container.collected_content
  ]
}

# Grant container identity access to Azure OpenAI
resource "azurerm_role_assignment" "containers_cognitive_services_openai_user" {
  scope                = azurerm_cognitive_account.openai.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_user_assigned_identity.containers.principal_id

  depends_on = [azurerm_user_assigned_identity.containers]
}

# Grant GitHub Actions identity access to subscription (for deployments)
resource "azurerm_role_assignment" "github_actions_contributor" {
  scope                = "/subscriptions/${data.azurerm_client_config.current.subscription_id}"
  role_definition_name = "Contributor"
  principal_id         = azurerm_user_assigned_identity.github_actions.principal_id

  depends_on = [azurerm_user_assigned_identity.github_actions]
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

# Event Grid System Topic for Storage Account
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

# Service Bus Queue for blob events
resource "azurerm_servicebus_queue" "blob_events" {
  name         = "blob-events"
  namespace_id = azurerm_servicebus_namespace.main.id

  max_size_in_megabytes = 1024
}

# Event Grid Subscription for blob creation events
# Event Grid Subscription for blob creation events
resource "azurerm_eventgrid_system_topic_event_subscription" "blob_created" {
  name                  = "${var.resource_prefix}-blob-created"
  system_topic          = azurerm_eventgrid_system_topic.storage.name
  resource_group_name   = azurerm_resource_group.main.name
  event_delivery_schema = "EventGridSchema"

  service_bus_queue_endpoint_id = azurerm_servicebus_queue.blob_events.id

  depends_on = [azurerm_eventgrid_system_topic.storage]
}

# Site Generator Container App (Customer-facing website)
resource "azurerm_container_app" "site_generator" {
  name                         = "${var.resource_prefix}-site-gen"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.containers.id]
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
      image  = var.container_images["site-generator"]
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
        name  = "ENVIRONMENT"
        value = "production"
      }
    }

    min_replicas = 1
    max_replicas = 3
  }

  tags = local.common_tags
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
      name   = "content-collector"
      image  = var.container_images["content-collector"]
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
    }

    min_replicas = 0
    max_replicas = 2
  }

  tags = local.common_tags

  depends_on = [
    azurerm_storage_container.collected_content,
    azurerm_role_assignment.containers_storage_blob_data_contributor
  ]
}

# Content Ranker Container App
resource "azurerm_container_app" "content_ranker" {
  name                         = "${var.resource_prefix}-ranker"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.containers.id]
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
      name   = "content-ranker"
      image  = var.container_images["content-ranker"]
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
    }

    min_replicas = 0
    max_replicas = 2
  }

  tags = local.common_tags
}

# Content Generator Container App
resource "azurerm_container_app" "content_generator" {
  name                         = "${var.resource_prefix}-content-gen"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.containers.id]
  }

  template {
    container {
      name   = "content-generator"
      image  = var.container_images["content-generator"]
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
        name        = "AZURE_OPENAI_ENDPOINT"
        secret_name = "azure-openai-endpoint"
      }

      # Note: API key authentication disabled - using managed identity
      # Container should authenticate using Azure.Identity.DefaultAzureCredential

      env {
        name  = "AZURE_OPENAI_DEPLOYMENT_NAME"
        value = "gpt-4o-mini"
      }

      env {
        name  = "SERVICE_BUS_NAMESPACE"
        value = azurerm_servicebus_namespace.main.name
      }

      env {
        name  = "BLOB_EVENTS_QUEUE"
        value = azurerm_servicebus_queue.blob_events.name
      }

      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }
    }

    # Scale to zero for maximum cost savings - only runs when there's work to do
    min_replicas = 0
    max_replicas = 5
  }

  secret {
    name  = "azure-openai-endpoint"
    value = azurerm_cognitive_account.openai.endpoint
  }

  # Note: API key secret removed - using managed identity authentication

  ingress {
    allow_insecure_connections = false
    external_enabled           = true
    target_port                = 8000

    # IP restrictions for secure access
    ip_security_restriction {
      action           = "Allow"
      ip_address_range = "81.2.90.47/32"
      name             = "AllowStaticIP"
    }

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  tags = local.common_tags

  depends_on = [
    azurerm_role_assignment.containers_storage_blob_data_reader,
    azurerm_role_assignment.containers_storage_blob_data_contributor,
    azurerm_key_vault_access_policy.containers
  ]
}

# Content Enricher Container App
resource "azurerm_container_app" "content_enricher" {
  name                         = "${local.resource_prefix}-enricher"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.containers.id]
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
      name   = "content-enricher"
      image  = var.container_images["content-enricher"]
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
        name  = "CONTAINER_NAME"
        value = azurerm_storage_container.topics.name
      }
    }

    min_replicas = 1
    max_replicas = 3
  }

  tags = local.common_tags

  depends_on = [
    azurerm_role_assignment.containers_storage_blob_data_contributor
  ]
}

# Content Processor Container App
resource "azurerm_container_app" "content_processor" {
  name                         = "${local.resource_prefix}-processor"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.containers.id]
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
      image  = var.container_images["content-processor"]
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
        name  = "CONTAINER_NAME"
        value = azurerm_storage_container.topics.name
      }
    }

    min_replicas = 1
    max_replicas = 3
  }

  tags = local.common_tags

  depends_on = [
    azurerm_role_assignment.containers_storage_blob_data_contributor
  ]
}

# Markdown Generator Container App
resource "azurerm_container_app" "markdown_generator" {
  name                         = "${local.resource_prefix}-markdown-gen"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.containers.id]
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
      name   = "markdown-generator"
      image  = var.container_images["markdown-generator"]
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
        name  = "CONTAINER_NAME"
        value = azurerm_storage_container.topics.name
      }
    }

    min_replicas = 1
    max_replicas = 3
  }

  tags = local.common_tags

  depends_on = [
    azurerm_role_assignment.containers_storage_blob_data_contributor
  ]
}

# Collector Scheduler Container App
resource "azurerm_container_app" "collector_scheduler" {
  name                         = "${local.resource_prefix}-scheduler"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.containers.id]
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
      name   = "collector-scheduler"
      image  = var.container_images["collector-scheduler"]
      cpu    = 0.25
      memory = "0.5Gi"

      env {
        name  = "AZURE_CLIENT_ID"
        value = azurerm_user_assigned_identity.containers.client_id
      }

      env {
        name  = "SERVICE_BUS_NAMESPACE"
        value = azurerm_servicebus_namespace.main.name
      }

      env {
        name  = "BLOB_EVENTS_QUEUE"
        value = azurerm_servicebus_queue.blob_events.name
      }
    }

    min_replicas = 1
    max_replicas = 2
  }

  tags = local.common_tags

  depends_on = [
    azurerm_role_assignment.containers_storage_blob_data_contributor
  ]
}
