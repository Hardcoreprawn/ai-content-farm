# Certificate Renewal Automation using Azure Container Instances
# Implements scheduled certificate renewal for mTLS infrastructure

# Container Instance for Certificate Renewal
resource "azurerm_container_group" "certificate_renewal" {
  count = var.enable_mtls ? 1 : 0

  name                = "${var.resource_prefix}-cert-renewal"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name
  ip_address_type     = "None"
  os_type             = "Linux"
  restart_policy      = "Never"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.cert_manager.id]
  }

  container {
    name   = "certificate-renewal"
    image  = "mcr.microsoft.com/azure-cli:latest"
    cpu    = 0.5
    memory = 1.0

    environment_variables = {
      RESOURCE_GROUP  = azurerm_resource_group.main.name
      KEY_VAULT_NAME  = azurerm_key_vault.main.name
      DNS_ZONE        = "jablab.dev"
      STORAGE_ACCOUNT = azurerm_storage_account.main.name
      AZURE_CLIENT_ID = azurerm_user_assigned_identity.cert_manager.client_id
    }

    # Mount the certificate management script
    volume {
      name       = "scripts"
      mount_path = "/scripts"
      secret = {
        "certificate-management.sh" = base64encode(file("${path.module}/../scripts/certificate-management.sh"))
      }
    }

    commands = [
      "/bin/bash",
      "-c",
      "chmod +x /scripts/certificate-management.sh && /scripts/certificate-management.sh renew"
    ]
  }

  tags = merge(local.common_tags, {
    Purpose = "certificate-renewal"
    Service = "automation"
  })

  depends_on = [
    azurerm_user_assigned_identity.cert_manager,
    azurerm_role_assignment.cert_manager_dns_contributor,
    azurerm_key_vault_access_policy.cert_manager
  ]
}

# Logic App for Certificate Renewal Scheduling
resource "azurerm_logic_app_workflow" "certificate_renewal_scheduler" {
  count = var.enable_mtls ? 1 : 0

  name                = "${var.resource_prefix}-cert-scheduler"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.cert_manager.id]
  }

  tags = merge(local.common_tags, {
    Purpose = "certificate-renewal-scheduling"
    Service = "automation"
  })
}

# Logic App Workflow Definition
resource "azurerm_resource_group_template_deployment" "certificate_renewal_workflow" {
  count = var.enable_mtls ? 1 : 0

  name                = "${var.resource_prefix}-cert-workflow"
  resource_group_name = azurerm_resource_group.main.name
  deployment_mode     = "Incremental"

  template_content = jsonencode({
    "$schema"      = "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#"
    contentVersion = "1.0.0.0"
    parameters     = {}
    variables      = {}
    resources = [
      {
        type       = "Microsoft.Logic/workflows"
        apiVersion = "2019-05-01"
        name       = azurerm_logic_app_workflow.certificate_renewal_scheduler[0].name
        location   = var.location
        properties = {
          definition = {
            "$schema"      = "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#"
            contentVersion = "1.0.0.0"
            parameters     = {}
            triggers = {
              "Recurrence" = {
                type = "Recurrence"
                recurrence = {
                  frequency = "Day"
                  interval  = 1
                  schedule = {
                    hours   = [2] # Run at 2 AM daily
                    minutes = [0]
                  }
                }
              }
            }
            actions = {
              "Check_Certificate_Expiration" = {
                type = "Http"
                inputs = {
                  method = "POST"
                  uri    = "https://management.azure.com/subscriptions/${data.azurerm_client_config.current.subscription_id}/resourceGroups/${azurerm_resource_group.main.name}/providers/Microsoft.ContainerInstance/containerGroups/${azurerm_container_group.certificate_renewal[0].name}/start"
                  headers = {
                    "Content-Type" = "application/json"
                  }
                  authentication = {
                    type     = "ManagedServiceIdentity"
                    identity = azurerm_user_assigned_identity.cert_manager.id
                  }
                }
              }
              "Send_Notification" = {
                type = "Http"
                inputs = {
                  method = "POST"
                  uri    = "https://api.jablab.dev/webhooks/certificate-renewal-completed"
                  headers = {
                    "Content-Type" = "application/json"
                  }
                  body = {
                    message        = "Certificate renewal check completed"
                    timestamp      = "@{utcNow()}"
                    resource_group = azurerm_resource_group.main.name
                  }
                }
                runAfter = {
                  "Check_Certificate_Expiration" = ["Succeeded"]
                }
              }
            }
          }
        }
      }
    ]
  })

  depends_on = [
    azurerm_logic_app_workflow.certificate_renewal_scheduler[0],
    azurerm_container_group.certificate_renewal[0]
  ]
}

# Role assignment for Logic App to start Container Instances
resource "azurerm_role_assignment" "logic_app_container_contributor" {
  count = var.enable_mtls ? 1 : 0

  scope                = azurerm_resource_group.main.id
  role_definition_name = "Contributor"
  principal_id         = azurerm_user_assigned_identity.cert_manager.principal_id
}

# Key Vault secret for certificate renewal status
resource "azurerm_key_vault_secret" "certificate_renewal_status" {
  count = var.enable_mtls ? 1 : 0

  name = "certificate-renewal-status"
  value = jsonencode({
    last_check   = timestamp()
    status       = "initialized"
    next_renewal = formatdate("YYYY-MM-DD", timeadd(timestamp(), "720h")) # 30 days
  })
  key_vault_id = azurerm_key_vault.main.id
  content_type = "application/json"

  lifecycle {
    ignore_changes = [value] # Will be updated by renewal automation
  }

  tags = merge(local.common_tags, {
    Purpose = "certificate-renewal-tracking"
  })

  depends_on = [
    azurerm_key_vault_access_policy.cert_manager
  ]
}

# Application Insights for certificate renewal monitoring
resource "azurerm_application_insights" "certificate_renewal" {
  count = var.enable_mtls ? 1 : 0

  name                = "${var.resource_prefix}-cert-renewal-insights"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "other"

  tags = merge(local.common_tags, {
    Purpose = "certificate-renewal-monitoring"
  })
}

# Custom metric for certificate renewal success rate
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "certificate_renewal_success" {
  count = var.enable_mtls ? 1 : 0

  name                = "${var.resource_prefix}-cert-renewal-success"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location

  evaluation_frequency = "P1D" # Daily evaluation
  window_duration      = "P1D" # 1 day window
  scopes               = [azurerm_application_insights.certificate_renewal[0].id]
  severity             = 2

  criteria {
    query = <<-QUERY
      traces
      | where message contains "Certificate renewal"
      | where message contains "success" or message contains "failed"
      | extend RenewalStatus = case(message contains "success", "Success", "Failed")
      | summarize SuccessCount = countif(RenewalStatus == "Success"), FailedCount = countif(RenewalStatus == "Failed")
      | extend SuccessRate = (SuccessCount * 100.0) / (SuccessCount + FailedCount)
      | where SuccessRate < 90
    QUERY

    time_aggregation_method = "Count"
    threshold               = 1
    operator                = "GreaterThanOrEqual"
    resource_id_column      = "_ResourceId"

    failing_periods {
      minimum_failing_periods_to_trigger_alert = 1
      number_of_evaluation_periods             = 1
    }
  }

  action {
    action_groups = [azurerm_monitor_action_group.certificate_alerts.id]
  }

  description = "Alert when certificate renewal success rate drops below 90%"
  enabled     = true

  tags = local.common_tags

  depends_on = [
    azurerm_application_insights.certificate_renewal[0],
    azurerm_monitor_action_group.certificate_alerts
  ]
}
