resource "azurerm_container_app" "content_collector" {
  name                         = "${local.resource_prefix}-collector"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  lifecycle {
    ignore_changes = [template[0].container[0].image]
  }

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

  # Storage Queue configuration (replaces Service Bus for Container Apps compatibility)
  # Storage Queues support managed identity authentication with KEDA scaling
  # This resolves authentication conflicts between managed identity and connection strings

  ingress {
    external_enabled = true
    target_port      = local.container_ports.collector
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
        name  = "PORT"
        value = tostring(local.container_ports.collector)
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

      # Storage Queue configuration for wake-up pattern
      env {
        name  = "STORAGE_QUEUE_NAME"
        value = azurerm_storage_queue.content_collection_requests.name
      }

      # Enable KEDA cron triggering for scheduled collections
      env {
        name  = "KEDA_CRON_TRIGGER"
        value = "true"
      }
    }

    # Scale based on CRON schedule (0->1 at start time, 1->0 after end time)
    # NOTE: cooldownPeriod=45s configured via Azure CLI (not supported by azurerm provider)
    min_replicas = 0
    max_replicas = 1 # Single collection run sufficient

    # KEDA cron scaler for regular content collection
    # Triggers collection 3 times per day to reduce API load while maintaining fresh content
    custom_scale_rule {
      name             = "cron-scaler"
      custom_rule_type = "cron"
      metadata = {
        timezone        = "UTC"
        start           = "0 0,8,16 * * *"  # Every 8 hours: 00:00, 08:00, 16:00 UTC
        end             = "30 0,8,16 * * *" # Maximum 30 minutes window (container auto-shuts down when done, typically 2-5 min)
        desiredReplicas = "1"
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
