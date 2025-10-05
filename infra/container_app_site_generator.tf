resource "azurerm_container_app" "site_generator" {
  name                         = "${local.resource_prefix}-site-generator"
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
        value = "$web"
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

      # Disable auto-shutdown for site-generator (needs to stay up for HTTP endpoints)
      # Container will stay alive during KEDA cooldown period (300s) for debugging
      env {
        name  = "DISABLE_AUTO_SHUTDOWN"
        value = "true"
      }
    }

    # Scale to zero when queue is empty (KEDA cooldown handles HTTP availability)
    # KEDA authentication configured via null_resource in container_apps_keda_auth.tf
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
      # Managed identity authentication configured via null_resource (see container_apps_keda_auth.tf)
    }
  }

  tags = local.common_tags

  depends_on = [
    azurerm_storage_container.collected_content,
    azurerm_role_assignment.containers_storage_blob_data_contributor
  ]
}
