# Site Publisher Container App
# Builds static websites from markdown content using Hugo

resource "azurerm_container_app" "site_publisher" {
  name                         = "${local.resource_prefix}-site-publisher"
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

  ingress {
    external_enabled = true
    target_port      = local.container_ports.site_publisher
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
      name   = "site-publisher"
      image  = local.container_images["site-publisher"]
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "PORT"
        value = tostring(local.container_ports.site_publisher)
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

      env {
        name  = "LOG_LEVEL"
        value = "INFO"
      }

      env {
        name  = "MARKDOWN_CONTAINER"
        value = "markdown-content"
      }

      env {
        name  = "OUTPUT_CONTAINER"
        value = "$web"
      }

      env {
        name  = "BACKUP_CONTAINER"
        value = "web-backup"
      }

      env {
        name  = "QUEUE_NAME"
        value = "site-publishing-requests"
      }

      env {
        name  = "HUGO_BASE_URL"
        value = azurerm_storage_account_static_website.main.index_document != null ? azurerm_storage_account.main.primary_web_endpoint : "https://example.com"
      }
    }

    # Scale to zero when queue is empty
    # KEDA authentication configured via null_resource in container_apps_keda_auth.tf
    min_replicas = 0
    max_replicas = 2 # Hugo builds are CPU/memory intensive, limit concurrency

    # KEDA scaling rules for Storage Queue with managed identity
    # Build site when markdown generation completes
    custom_scale_rule {
      name             = "site-publish-queue-scaler"
      custom_rule_type = "azure-queue"
      metadata = {
        queueName   = azurerm_storage_queue.site_publishing_requests.name
        accountName = azurerm_storage_account.main.name
        queueLength = "1" # Build immediately when triggered
        cloud       = "AzurePublicCloud"
      }
      # Managed identity authentication configured via null_resource (see container_apps_keda_auth.tf)
    }
  }

  tags = local.common_tags

  depends_on = [
    azurerm_storage_container.markdown_content,
    azurerm_storage_account_static_website.main,
    azurerm_storage_queue.site_publishing_requests,
    azurerm_role_assignment.containers_storage_blob_data_contributor
  ]
}
