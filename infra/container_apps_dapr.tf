# Dapr Configuration Updates for Container Apps
# This file contains Dapr sidecar configuration for existing Container Apps

# Update Content Collector with Dapr
resource "azurerm_container_app" "content_collector_dapr" {
  count = var.enable_mtls ? 1 : 0

  name                         = "${var.resource_prefix}-collector-dapr"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.containers.id]
  }

  # Dapr configuration for mTLS
  dapr {
    app_id       = "content-collector"
    app_port     = 8000
    app_protocol = "http"
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

  secret {
    name  = "azure-servicebus-connection-string"
    value = azurerm_servicebus_namespace.main.default_primary_connection_string
  }

  # TLS certificate from Key Vault
  secret {
    name  = "tls-certificate"
    value = azurerm_key_vault_secret.dapr_trust_root.value
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "http" # Fixed: Use HTTP instead of HTTPS for basic deployment

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
        name        = "REDDIT_CLIENT_ID" # pragma: allowlist secret
        secret_name = "reddit-client-id" # pragma: allowlist secret
      }

      env {
        name        = "REDDIT_CLIENT_SECRET" # pragma: allowlist secret
        secret_name = "reddit-client-secret" # pragma: allowlist secret
      }

      env {
        name        = "REDDIT_USER_AGENT" # pragma: allowlist secret
        secret_name = "reddit-user-agent" # pragma: allowlist secret
      }

      env {
        name  = "ENVIRONMENT"
        value = "production"
      }

      # Dapr configuration
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

      # Service Bus configuration
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

    # KEDA scaling rules
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
    azurerm_container_app_environment_dapr_component.mtls_configuration,
    azurerm_key_vault_secret.dapr_trust_root
    # azurerm_dns_a_record.service_api - temporarily removed due to provider bug
  ]
}

# Update Content Processor with Dapr
resource "azurerm_container_app" "content_processor_dapr" {
  count = var.enable_mtls ? 1 : 0

  name                         = "${var.resource_prefix}-processor-dapr"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.containers.id]
  }

  # Dapr configuration for mTLS
  dapr {
    app_id       = "content-processor"
    app_port     = 8000
    app_protocol = "http"
  }

  secret {
    name  = "openai-chat-model"
    value = azurerm_key_vault_secret.openai_chat_model.value
  }

  secret {
    name  = "openai-embedding-model"
    value = azurerm_key_vault_secret.openai_embedding_model.value
  }

  secret {
    name  = "azure-servicebus-connection-string"
    value = azurerm_servicebus_namespace.main.default_primary_connection_string
  }

  secret {
    name  = "tls-certificate"
    value = azurerm_key_vault_secret.dapr_trust_root.value
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "http" # Fixed: Use HTTP instead of HTTPS for basic deployment

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

      # Dapr configuration
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

      # Service Bus configuration
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
    azurerm_container_app_environment_dapr_component.mtls_configuration,
    azurerm_key_vault_secret.dapr_trust_root,
    azurerm_cognitive_account.openai
  ]
}

# Update Site Generator with Dapr
resource "azurerm_container_app" "site_generator_dapr" {
  count = var.enable_mtls ? 1 : 0

  name                         = "${var.resource_prefix}-site-gen-dapr" # Shortened name to fit 32 char limit
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.containers.id]
  }

  # Dapr configuration for mTLS
  dapr {
    app_id       = "site-generator"
    app_port     = 8000
    app_protocol = "http"
  }

  secret {
    name  = "azure-servicebus-connection-string"
    value = azurerm_servicebus_namespace.main.default_primary_connection_string
  }

  secret {
    name  = "tls-certificate"
    value = azurerm_key_vault_secret.dapr_trust_root.value
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
        name  = "ENVIRONMENT"
        value = "production"
      }

      # Dapr configuration
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

      # Service Bus configuration
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
    azurerm_container_app_environment_dapr_component.mtls_configuration,
    azurerm_key_vault_secret.dapr_trust_root
  ]
}
