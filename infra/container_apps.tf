# Azure Container Apps infrastructure for AI Content Farm

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

# SHARED Container Registry for all environments - saves $20/month vs per-environment registries
# Uses image tags to differentiate between staging/production deployments
# Tags strategy:
#   - latest = development
#   - staging-{version} = staging environment
#   - prod-{version} = production environment
#   - pr-{number}-{commit} = ephemeral PR environments
#checkov:skip=CKV_AZURE_165:Geo-replication requires Premium SKU - cost prohibitive for development
#checkov:skip=CKV_AZURE_233:Zone redundancy requires Premium SKU - cost prohibitive for development
#checkov:skip=CKV_AZURE_137:Using authentication-based security instead of network restrictions for cost efficiency
resource "azurerm_container_registry" "main" {
  # checkov:skip=CKV_AZURE_165: Geo-replication requires Premium SKU - too expensive for development
  # checkov:skip=CKV_AZURE_233: Zone redundancy requires Premium SKU - too expensive for development
  # checkov:skip=CKV_AZURE_137: Using authentication-based security instead of network restrictions for cost efficiency
  name                = "aicontentfarmacr${random_string.suffix.result}" # Shared across all environments
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  sku                 = "Basic" # Basic SKU saves $15/month per environment vs Standard
  admin_enabled       = false   # Disable admin account for security - use managed identity only

  # Enable public network access - Basic SKU has limited security options
  public_network_access_enabled = true

  # Note: Basic SKU limitations:
  # - No vulnerability scanning (security trade-off compensated by CI/CD Trivy scanning)
  # - No network restrictions (compensated by Azure AD authentication)
  # - 10GB storage limit (sufficient for multiple tagged versions)
  # - 2 webhook limit (currently using 0)

  tags = merge(local.common_tags, {
    Purpose          = "shared-multi-environment"
    CostOptimization = "consolidated-registry"
  })
}

# Note: Removing diagnostic settings as Basic SKU has limited logging capabilities

# Resource lock to prevent accidental deletion of Container Registry
resource "azurerm_management_lock" "container_registry_lock" {
  name       = "container-registry-lock"
  scope      = azurerm_container_registry.main.id
  lock_level = "CanNotDelete"
  notes      = "Prevents accidental deletion of the container registry and all stored images"
}

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

# Grant container identity access to Storage Account
resource "azurerm_role_assignment" "containers_storage_blob_data_contributor" {
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.containers.principal_id

  depends_on = [azurerm_user_assigned_identity.containers]
}

# Grant container identity access to Container Registry
resource "azurerm_role_assignment" "containers_acr_pull" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPull"
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

# Grant GitHub Actions identity access to Container Registry
resource "azurerm_role_assignment" "github_actions_acr_push" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPush"
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
resource "azurerm_eventgrid_event_subscription" "blob_created" {
  name                  = "${var.resource_prefix}-blob-created"
  scope                 = azurerm_eventgrid_system_topic.storage.id
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

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  template {
    container {
      name   = "site-generator"
      image  = "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest" # Placeholder image, updated by deployment
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

  template {
    container {
      name   = "content-collector"
      image  = "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest" # Placeholder image, updated by deployment
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
    }

    min_replicas = 0
    max_replicas = 2
  }

  tags = local.common_tags
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

  template {
    container {
      name   = "content-ranker"
      image  = "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest" # Placeholder image, updated by deployment
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
      image  = "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest" # Placeholder image, updated by deployment
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

      env {
        name        = "AZURE_OPENAI_API_KEY"
        secret_name = "azure-openai-api-key"
      }

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

  secret {
    name  = "azure-openai-api-key"
    value = azurerm_cognitive_account.openai.primary_access_key
  }

  ingress {
    allow_insecure_connections = false
    external_enabled           = true
    target_port                = 8000

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  tags = local.common_tags

  depends_on = [
    azurerm_role_assignment.containers_storage_blob_data_contributor,
    azurerm_key_vault_access_policy.containers
  ]
}
