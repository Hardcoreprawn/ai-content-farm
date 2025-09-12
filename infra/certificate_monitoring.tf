# Certificate Lifecycle Monitoring and Alerting
# Implements Azure Monitor integration for certificate expiration and mTLS health

# Action Group for certificate alerts
resource "azurerm_monitor_action_group" "certificate_alerts" {
  name                = "${var.resource_prefix}-cert-alerts"
  resource_group_name = azurerm_resource_group.main.name
  short_name          = "cert-alert"

  # Email notification
  email_receiver {
    name          = "certificate-admin"
    email_address = var.certificate_email != "" ? var.certificate_email : "admin@jablab.dev"
  }

  # Webhook for automated renewal (optional)
  webhook_receiver {
    name        = "certificate-renewal-webhook"
    service_uri = "https://api.jablab.dev/webhooks/certificate-renewal"
  }

  tags = local.common_tags
}

# Certificate Expiration Alert
resource "azurerm_monitor_metric_alert" "certificate_expiration" {
  name                = "${var.resource_prefix}-cert-expiration"
  resource_group_name = azurerm_resource_group.main.name
  scopes              = [azurerm_key_vault.main.id]
  description         = "Alert when certificates are expiring within 30 days"
  severity            = 2
  frequency           = "PT1H"
  window_size         = "PT1H"

  criteria {
    metric_namespace = "Microsoft.KeyVault/vaults"
    metric_name      = "CertificateNearExpiry"
    aggregation      = "Total"
    operator         = "GreaterThan"
    threshold        = 0
  }

  action {
    action_group_id = azurerm_monitor_action_group.certificate_alerts.id
  }

  tags = local.common_tags
}

# mTLS Handshake Failure Alert
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "mtls_handshake_failures" {
  name                = "${var.resource_prefix}-mtls-failures"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location

  evaluation_frequency = "PT5M"
  window_duration      = "PT5M"
  scopes               = [azurerm_log_analytics_workspace.main.id]
  severity             = 2

  criteria {
    query = <<-QUERY
      ContainerAppConsoleLogs_CL
      | where Log_s contains "TLS handshake failed" or Log_s contains "certificate verification failed"
      | where TimeGenerated >= ago(5m)
      | summarize count() by bin(TimeGenerated, 1m)
      | where count_ > 5
    QUERY

    time_aggregation_method = "Count"
    threshold               = 5
    operator                = "GreaterThan"
    resource_id_column      = "_ResourceId"
    metric_measure_column   = "count_"

    failing_periods {
      minimum_failing_periods_to_trigger_alert = 1
      number_of_evaluation_periods             = 1
    }
  }

  action {
    action_groups = [azurerm_monitor_action_group.certificate_alerts.id]
  }

  description = "Alert when mTLS handshake failures exceed threshold"
  enabled     = var.enable_mtls

  tags = local.common_tags
}

# Container App Health Monitoring
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "container_health" {
  name                = "${var.resource_prefix}-container-health"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location

  evaluation_frequency = "PT5M"
  window_duration      = "PT10M"
  scopes               = [azurerm_log_analytics_workspace.main.id]
  severity             = 3

  criteria {
    query = <<-QUERY
      ContainerAppSystemLogs_CL
      | where ContainerAppName_s in ("content-collector", "content-processor", "site-generator")
      | where Reason_s == "FailedToStart" or Reason_s == "CrashLoopBackOff"
      | where TimeGenerated >= ago(10m)
      | summarize count() by ContainerAppName_s
      | where count_ > 0
    QUERY

    time_aggregation_method = "Count"
    threshold               = 0
    operator                = "GreaterThan"
    resource_id_column      = "_ResourceId"
    metric_measure_column   = "count_"

    failing_periods {
      minimum_failing_periods_to_trigger_alert = 1
      number_of_evaluation_periods             = 1
    }
  }

  action {
    action_groups = [azurerm_monitor_action_group.certificate_alerts.id]
  }

  description = "Alert when containers fail to start or crash repeatedly"
  enabled     = true

  tags = local.common_tags
}

# Certificate Renewal Workbook
resource "azurerm_application_insights_workbook" "certificate_dashboard" {
  name                = uuidv5("x500", "${var.resource_prefix}-cert-dashboard") # Generate UUID for workbook name
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  display_name        = "Certificate Management Dashboard"

  data_json = jsonencode({
    version = "Notebook/1.0"
    items = [
      {
        type = 3
        content = {
          version = "KqlItem/1.0"
          query   = "AzureDiagnostics | where ResourceProvider == \"MICROSOFT.KEYVAULT\" | where OperationName == \"CertificateGet\" | summarize count() by bin(TimeGenerated, 1h) | render timechart"
          size    = 0
          title   = "Certificate Access Patterns"
          timeContext = {
            durationMs = 86400000
          }
          queryType    = 0
          resourceType = "microsoft.operationalinsights/workspaces"
        }
      },
      {
        type = 3
        content = {
          version = "KqlItem/1.0"
          query   = "ContainerAppConsoleLogs_CL | where Log_s contains \"Dapr\" and Log_s contains \"mTLS\" | summarize count() by bin(TimeGenerated, 1h) | render timechart"
          size    = 0
          title   = "mTLS Activity"
          timeContext = {
            durationMs = 86400000
          }
          queryType    = 0
          resourceType = "microsoft.operationalinsights/workspaces"
        }
      }
    ]
  })

  tags = local.common_tags
}

# Cost Alert for Certificate Management
resource "azurerm_consumption_budget_resource_group" "certificate_cost_budget" {
  name              = "${var.resource_prefix}-cert-budget"
  resource_group_id = azurerm_resource_group.main.id

  amount     = 100
  time_grain = "Monthly"

  time_period {
    start_date = formatdate("YYYY-MM-01'T'00:00:00Z", timestamp())
    end_date   = formatdate("YYYY-MM-01'T'00:00:00Z", timeadd(timestamp(), "8760h")) # 1 year
  }

  notification {
    enabled        = true
    threshold      = 80
    operator       = "GreaterThan"
    threshold_type = "Actual"

    contact_emails = [
      var.certificate_email != "" ? var.certificate_email : "admin@jablab.dev"
    ]
  }

  notification {
    enabled        = true
    threshold      = 100
    operator       = "GreaterThan"
    threshold_type = "Forecasted"

    contact_emails = [
      var.certificate_email != "" ? var.certificate_email : "admin@jablab.dev"
    ]
  }

  filter {
    dimension {
      name = "ResourceId"
      values = [
        azurerm_key_vault.main.id
        # Note: External jablab.dev DNS zone not included in budget tracking
      ]
    }
  }
}

# Log Analytics queries for certificate monitoring
resource "azurerm_log_analytics_saved_search" "certificate_renewal_history" {
  name                       = "CertificateRenewalHistory"
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  category                   = "Certificate Management"
  display_name               = "Certificate Renewal History"

  query = <<-EOT
    AzureDiagnostics
    | where ResourceType == "VAULTS"
    | where OperationName in ("CertificateCreate", "CertificateImport", "CertificateUpdate")
    | extend CertificateName = tostring(parse_json(properties_s).certificateName)
    | project TimeGenerated, Resource, OperationName, CertificateName, CallerIpAddress, identity_claim_upn_s
    | order by TimeGenerated desc
  EOT

  tags = local.common_tags
}

resource "azurerm_log_analytics_saved_search" "mtls_communication_health" {
  name                       = "MtlsCommunicationHealth"
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  category                   = "mTLS Monitoring"
  display_name               = "mTLS Communication Health"

  query = <<-EOT
    ContainerAppConsoleLogs_CL
    | where Log_s contains "dapr"
    | where Log_s contains "mTLS" or Log_s contains "certificate" or Log_s contains "TLS"
    | extend LogLevel = case(
        Log_s contains "error" or Log_s contains "ERROR", "Error",
        Log_s contains "warn" or Log_s contains "WARN", "Warning",
        Log_s contains "info" or Log_s contains "INFO", "Info",
        "Debug"
    )
    | project TimeGenerated, ContainerAppName_s, LogLevel, Log_s
    | order by TimeGenerated desc
  EOT

  tags = local.common_tags
}
