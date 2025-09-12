# KEDA + Dapr Integration for Event-Driven Scaling
# Replaces Service Bus with direct mTLS communication while keeping scale-to-zero

# KEDA Dapr State Store Scaler (replaces Service Bus queues)
resource "azurerm_container_app_environment_dapr_component" "keda_state_store" {
  count                        = var.enable_mtls ? 1 : 0
  name                         = "keda-work-queue"
  container_app_environment_id = azurerm_container_app_environment.main.id
  component_type               = "state.azure.cosmosdb"
  version                      = "v1"

  metadata {
    name  = "url"
    value = azurerm_cosmosdb_account.keda_state[0].endpoint
  }

  metadata {
    name  = "database"
    value = azurerm_cosmosdb_sql_database.keda_state[0].name
  }

  metadata {
    name  = "collection"
    value = azurerm_cosmosdb_sql_container.work_queue[0].name
  }

  secret {
    name  = "masterkey"
    value = azurerm_cosmosdb_account.keda_state[0].primary_key
  }

  scopes = [
    "content-collector-dapr",
    "content-processor-dapr",
    "site-generator-dapr"
  ]
}

# Cosmos DB for KEDA work queue state (ultra-budget optimized)
resource "azurerm_cosmosdb_account" "keda_state" {
  count               = var.enable_mtls ? 1 : 0
  name                = "${local.clean_prefix}kedastate${random_string.suffix.result}"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"

  # Ultra-budget optimization
  consistency_policy {
    consistency_level = "Session" # Cheapest option
  }

  geo_location {
    location          = var.location
    failover_priority = 0
  }

  tags = local.common_tags
}

resource "azurerm_cosmosdb_sql_database" "keda_state" {
  count               = var.enable_mtls ? 1 : 0
  name                = "keda-workqueue"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.keda_state[0].name

  # Ultra-budget: Use serverless (pay-per-request)
  # No throughput specified = serverless mode
}

resource "azurerm_cosmosdb_sql_container" "work_queue" {
  count               = var.enable_mtls ? 1 : 0
  name                = "work-items"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.keda_state[0].name
  database_name       = azurerm_cosmosdb_sql_database.keda_state[0].name
  partition_key_paths = ["/service_name"]

  # TTL for automatic cleanup
  default_ttl = 3600 # 1 hour

  indexing_policy {
    indexing_mode = "consistent"

    included_path {
      path = "/*"
    }
  }
}

# KEDA HTTP Add-on for direct HTTP scaling (alternative approach)
resource "azurerm_container_app_environment_dapr_component" "keda_http_scaler" {
  count                        = var.enable_mtls ? 1 : 0
  name                         = "keda-http-scaler"
  container_app_environment_id = azurerm_container_app_environment.main.id
  component_type               = "bindings.http"
  version                      = "v1"

  metadata {
    name  = "url"
    value = "http://keda-add-on-http-interceptor-proxy.keda.svc.cluster.local:8080"
  }

  scopes = [
    "content-collector-dapr",
    "content-processor-dapr",
    "site-generator-dapr"
  ]
}

# Enhanced Container Apps with KEDA + Dapr scaling
resource "azurerm_container_app" "content_collector_keda_dapr" {
  count                        = var.enable_mtls ? 1 : 0
  name                         = "${var.resource_prefix}-collector-keda" # Shortened to fit 32 char limit
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.containers.id]
  }

  # mTLS certificates
  # TLS certificates (only when PKI is enabled)
  dynamic "secret" {
    for_each = var.enable_pki ? [1] : []
    content {
      name  = "tls-certificate"
      value = azurerm_key_vault_certificate.service_certificates["content-collector"].certificate_data
    }
  }

  dynamic "secret" {
    for_each = var.enable_pki ? [1] : []
    content {
      name  = "tls-private-key"
      value = azurerm_key_vault_secret.service_private_keys["content-collector"].value
    }
  }

  # Reddit API secrets
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

  # Dapr configuration with mTLS
  dapr {
    app_id       = "content-collector-dapr"
    app_port     = 8000
    app_protocol = "http"
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "http2" # Use HTTP/2 for better performance

    # Public access for webhook triggers
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

      # Enhanced environment configuration
      env {
        name  = "AZURE_CLIENT_ID"
        value = azurerm_user_assigned_identity.containers.client_id
      }

      env {
        name  = "AZURE_STORAGE_ACCOUNT_NAME"
        value = azurerm_storage_account.main.name
      }

      # Dapr + mTLS configuration
      env {
        name  = "DAPR_HTTP_PORT"
        value = "3500"
      }

      env {
        name  = "DAPR_GRPC_PORT"
        value = "50001"
      }

      env {
        name  = "DAPR_MTLS_ENABLED"
        value = "true"
      }

      env {
        name        = "DAPR_TRUST_ANCHORS" # pragma: allowlist secret
        secret_name = "tls-certificate"    # pragma: allowlist secret
      }

      # Service discovery
      env {
        name  = "CONTENT_PROCESSOR_SERVICE"
        value = "content-processor-dapr"
      }

      env {
        name  = "SITE_GENERATOR_SERVICE"
        value = "site-generator-dapr"
      }

      # Reddit API configuration
      env {
        name        = "REDDIT_CLIENT_ID"
        secret_name = "reddit-client-id" # pragma: allowlist secret
      }

      env {
        name        = "REDDIT_CLIENT_SECRET" # pragma: allowlist secret
        secret_name = "reddit-client-secret" # pragma: allowlist secret
      }

      env {
        name        = "REDDIT_USER_AGENT"
        secret_name = "reddit-user-agent" # pragma: allowlist secret
      }

      env {
        name  = "ENVIRONMENT"
        value = "production"
      }

      # KEDA work queue configuration
      env {
        name  = "KEDA_STATE_STORE"
        value = "keda-work-queue"
      }

      env {
        name  = "WORK_QUEUE_NAME"
        value = "content-collection-requests"
      }
    }

    min_replicas = 0 # Scale to zero!
    max_replicas = 3

    # KEDA HTTP scaler (scales based on incoming HTTP requests)
    http_scale_rule {
      name                = "http-requests-scaler"
      concurrent_requests = 1
    }

    # KEDA HTTP scaler - fallback to Service Bus queue for now
    azure_queue_scale_rule {
      name         = "servicebus-queue-scaler"
      queue_length = 1
      queue_name   = "content-collection-requests"

      authentication {
        secret_name       = "azure-servicebus-connection-string" # pragma: allowlist secret
        trigger_parameter = "connection"
      }
    }
  }

  tags = local.common_tags

  depends_on = [
    azurerm_container_app_environment_dapr_component.mtls_configuration,
    azurerm_container_app_environment_dapr_component.keda_state_store
  ]
}

# Work Queue Management Service (replaces Service Bus message sending)
resource "azurerm_container_app" "work_queue_manager" {
  count                        = var.enable_mtls ? 1 : 0
  name                         = "${var.resource_prefix}-queue-mgr"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.containers.id]
  }

  # Minimal always-on service for work queue management
  template {
    container {
      name   = "work-queue-manager"
      image  = "mcr.microsoft.com/dapr/daprd:1.12.0" # Lightweight Dapr sidecar
      cpu    = 0.25
      memory = "0.5Gi"

      env {
        name  = "DAPR_HTTP_PORT"
        value = "3500"
      }

      env {
        name  = "KEDA_STATE_STORE"
        value = "keda-work-queue"
      }
    }

    min_replicas = 1 # Always on for work queue management
    max_replicas = 1
  }

  dapr {
    app_id = "work-queue-manager"
    # No app_port needed for Dapr sidecar-only container
  }

  tags = local.common_tags
}

# Output the new endpoints
output "keda_dapr_endpoints" {
  description = "KEDA + Dapr service endpoints"
  value = var.enable_mtls ? {
    content_collector  = azurerm_container_app.content_collector_keda_dapr[0].latest_revision_fqdn
    work_queue_manager = azurerm_container_app.work_queue_manager[0].latest_revision_fqdn
    cosmos_db_endpoint = azurerm_cosmosdb_account.keda_state[0].endpoint
  } : null
}
