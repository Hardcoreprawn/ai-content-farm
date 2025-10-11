resource "azurerm_container_app" "content_processor" {
  name                         = "${local.resource_prefix}-processor"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  lifecycle {
    # Ignore authentication changes - managed by null_resource in container_apps_keda_auth.tf
    ignore_changes = [
      template[0].custom_scale_rule[0].authentication,
      template[0].container[0].image
    ]
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
    target_port      = local.container_ports.processor
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
        name  = "PORT"
        value = tostring(local.container_ports.processor)
      }
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

      # Output queue for triggering markdown generation
      env {
        name  = "MARKDOWN_QUEUE_NAME"
        value = azurerm_storage_queue.markdown_generation_requests.name
      }
    }

    # Scale to zero when queue is empty
    # KEDA authentication configured via null_resource in container_apps_keda_auth.tf
    min_replicas = 0
    max_replicas = 3

    # KEDA scaling rules for Storage Queue messages with managed identity
    # Updated for individual item processing (responsive scaling)
    custom_scale_rule {
      name             = "storage-queue-scaler"
      custom_rule_type = "azure-queue"
      metadata = {
        queueName             = azurerm_storage_queue.content_processing_requests.name
        accountName           = azurerm_storage_account.main.name
        queueLength           = "80" # Target messages per replica (80 messages = 1 replica, 160 = 2 replicas, etc.)
        activationQueueLength = "1"  # Minimum queue length to activate scaling (0->1 transition)
        cloud                 = "AzurePublicCloud"
      }
      # Managed identity authentication configured via null_resource (see container_apps_keda_auth.tf)
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
