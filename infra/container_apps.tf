# Azure Container Apps infrastructure for AI Content Farm

# Container Apps Environment
resource "azurerm_container_app_environment" "main" {
  name                = "${var.resource_prefix}-env"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name

  tags = local.common_tags
}

# Log Analytics Workspace for Container Apps
resource "azurerm_log_analytics_workspace" "container_apps" {
  name                = "${var.resource_prefix}-ca-logs"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = local.common_tags
}

# Container Registry for storing container images
#checkov:skip=CKV_AZURE_165:Geo-replication requires Premium SKU - cost prohibitive for development
#checkov:skip=CKV_AZURE_233:Zone redundancy requires Premium SKU - cost prohibitive for development  
resource "azurerm_container_registry" "main" {
  # checkov:skip=CKV_AZURE_165: Geo-replication requires Premium SKU - too expensive for development
  # checkov:skip=CKV_AZURE_233: Zone redundancy requires Premium SKU - too expensive for development
  name                = "${replace(var.resource_prefix, "-", "")}acr"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  sku                 = "Standard" # Upgraded from Basic for security features
  admin_enabled       = false      # Disable admin account for security

  # Enable public network access restrictions
  public_network_access_enabled = false

  # Enable dedicated data endpoints
  data_endpoint_enabled = true

  # Zone redundancy (requires Premium SKU in production)
  zone_redundancy_enabled = false # Would need Premium SKU

  # Retention policy for untagged manifests
  retention_policy_in_days = 7

  # Trust policy for content trust
  trust_policy_enabled = true

  # Enable vulnerability scanning (requires Standard or Premium)
  quarantine_policy_enabled = true

  tags = local.common_tags
}

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

# Managed Identity for Service Bus encryption
resource "azurerm_user_assigned_identity" "servicebus" {
  name                = "${var.resource_prefix}-servicebus-identity"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name

  tags = local.common_tags
}

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
  name                = "${var.resource_prefix}-sb"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "Premium" # Upgraded for security features

  # Security configurations
  public_network_access_enabled = false
  local_auth_enabled            = false # Disable local authentication
  minimum_tls_version           = "1.2" # Use latest TLS

  # Enable managed identity
  identity {
    type = "SystemAssigned"
  }

  depends_on = [
    azurerm_key_vault_access_policy.servicebus,
    azurerm_key_vault_key.servicebus
  ]

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

# Content Generator Container App
resource "azurerm_container_app" "content_generator" {
  name                         = "${var.resource_prefix}-content-generator"
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
      image  = "${azurerm_container_registry.main.login_server}/content-generator:latest"
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
