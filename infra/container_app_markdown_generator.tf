# Markdown Generator Container App
# Converts processed JSON articles to markdown format using Jinja2 templates

resource "azurerm_container_app" "markdown_generator" {
  name                         = "${local.resource_prefix}-markdown-gen"
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
    name  = "unsplash-access-key"
    value = azurerm_key_vault_secret.unsplash_access_key.value
  }

  secret {
    name  = "unsplash-application-id"
    value = azurerm_key_vault_secret.unsplash_application_id.value
  }

  secret {
    name  = "unsplash-secret-key"
    value = azurerm_key_vault_secret.unsplash_secret_key.value
  }

  ingress {
    external_enabled = true
    target_port      = local.container_ports.markdown_generator
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
      image  = local.container_images["markdown-generator"]
      cpu    = 0.25
      memory = "0.5Gi"

      env {
        name  = "PORT"
        value = tostring(local.container_ports.markdown_generator)
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
        name  = "ENVIRONMENT"
        value = "production"
      }

      # Application Insights for telemetry and monitoring
      env {
        name  = "APPLICATIONINSIGHTS_CONNECTION_STRING"
        value = azurerm_application_insights.main.connection_string
      }

      env {
        name  = "LOG_LEVEL"
        value = "INFO"
      }

      env {
        name  = "INPUT_CONTAINER"
        value = "processed-content"
      }

      env {
        name  = "OUTPUT_CONTAINER"
        value = "markdown-content"
      }

      env {
        name  = "MARKDOWN_QUEUE_NAME"
        value = azurerm_storage_queue.markdown_generation_requests.name
      }

      env {
        name        = "UNSPLASH_ACCESS_KEY"
        secret_name = "unsplash-access-key"
      }

      env {
        name        = "UNSPLASH_APPLICATION_ID"
        secret_name = "unsplash-application-id"
      }

      env {
        name        = "UNSPLASH_SECRET_KEY"
        secret_name = "unsplash-secret-key"
      }

      env {
        name  = "MAX_IDLE_TIME_SECONDS"
        value = "180" # 3 minutes - provides safety margin beyond 45s KEDA cooldown
      }

      env {
        name  = "STABLE_EMPTY_DURATION_SECONDS"
        value = "30" # Wait 30s after queue empty to ensure content-processor burst finished before signaling site-publisher
      }
    }

    # Scale to zero when queue is empty
    # KEDA authentication configured via null_resource in container_apps_keda_auth.tf
    # NOTE: cooldownPeriod=90s configured via Azure CLI (not supported by azurerm provider)
    #       Must be >= STABLE_EMPTY_DURATION_SECONDS (30s) + safety margin to allow
    #       time for site-publisher signaling before scale-down
    min_replicas = 0
    max_replicas = 1 # Single replica sufficient: processes 35+ articles/sec, prevents duplicate site-publish triggers


    # KEDA scaling rules for Storage Queue with managed identity
    # Responsive scaling - process individual items immediately
    custom_scale_rule {
      name             = "markdown-queue-scaler"
      custom_rule_type = "azure-queue"
      metadata = {
        accountName           = azurerm_storage_account.main.name
        queueName             = azurerm_storage_queue.markdown_generation_requests.name
        queueLength           = "1"
        activationQueueLength = "1"
        queueLengthStrategy   = "all"
        cooldownPeriod        = "90"
        cloud                 = "AzurePublicCloud"
      }
      # Managed identity authentication configured via null_resource (see container_apps_keda_auth.tf)
    }
  }

  tags = local.common_tags

  depends_on = [
    azurerm_storage_container.processed_content,
    azurerm_storage_container.markdown_content,
    azurerm_storage_queue.markdown_generation_requests,
    azurerm_role_assignment.containers_storage_blob_data_contributor
  ]
}
