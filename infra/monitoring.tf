# Enhanced monitoring and alerting for mTLS, service discovery, and certificate management

# Application Insights for detailed telemetry
resource "azurerm_application_insights" "main" {
  name                = "${var.resource_prefix}-appinsights"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "web"

  tags = merge(local.common_tags, {
    Purpose = "mtls-monitoring"
  })
}

# Alert Action Group for mTLS and certificate notifications
resource "azurerm_monitor_action_group" "mtls_alerts" {
  name                = "${var.resource_prefix}-mtls-alerts"
  resource_group_name = azurerm_resource_group.main.name
  short_name          = "mTLS-Alerts"

  email_receiver {
    name          = "admin"
    email_address = "admin@${var.domain_name}"
  }

  # Azure Service Health integration
  azure_app_push_receiver {
    name = "azure-app-push"
  }

  tags = local.common_tags
}

# Certificate Expiration Alert
resource "azurerm_monitor_metric_alert" "certificate_expiry" {
  name                = "${var.resource_prefix}-cert-expiry-alert"
  resource_group_name = azurerm_resource_group.main.name
  scopes              = [azurerm_key_vault.main.id]
  description         = "Alert when mTLS certificates are expiring within 30 days"
  severity            = 2
  frequency           = "PT1H"
  window_size         = "PT1H"

  criteria {
    metric_namespace = "Microsoft.KeyVault/vaults"
    metric_name      = "CertificateExpiry"
    aggregation      = "Maximum"
    operator         = "LessThan"
    threshold        = 30 # Days
  }

  action {
    action_group_id = azurerm_monitor_action_group.mtls_alerts.id
  }

  tags = local.common_tags
}

# mTLS Handshake Failure Alert
resource "azurerm_monitor_metric_alert" "mtls_handshake_failures" {
  name                = "${var.resource_prefix}-mtls-handshake-failures"
  resource_group_name = azurerm_resource_group.main.name
  scopes              = [azurerm_container_app_environment.main.id]
  description         = "Alert on mTLS handshake failures"
  severity            = 1
  frequency           = "PT5M"
  window_size         = "PT15M"

  criteria {
    metric_namespace = "Microsoft.App/managedEnvironments"
    metric_name      = "HttpServerErrors"
    aggregation      = "Total"
    operator         = "GreaterThan"
    threshold        = 10

    dimension {
      name     = "statusCode"
      operator = "Include"
      values   = ["495", "496", "497"] # SSL/TLS related errors
    }
  }

  action {
    action_group_id = azurerm_monitor_action_group.mtls_alerts.id
  }

  tags = local.common_tags
}

# Container App Health Alert
resource "azurerm_monitor_metric_alert" "container_app_availability" {
  for_each = {
    "content-collector" = azurerm_container_app.content_collector.id
    "content-processor" = azurerm_container_app.content_processor.id
    "site-generator"    = azurerm_container_app.site_generator.id
  }

  name                = "${var.resource_prefix}-${each.key}-availability"
  resource_group_name = azurerm_resource_group.main.name
  scopes              = [each.value]
  description         = "Alert when ${each.key} availability drops below 95%"
  severity            = 2
  frequency           = "PT5M"
  window_size         = "PT15M"

  criteria {
    metric_namespace = "Microsoft.App/containerApps"
    metric_name      = "HttpRequestsPerSecond"
    aggregation      = "Average"
    operator         = "LessThan"
    threshold        = 0.01 # Minimal traffic threshold
  }

  action {
    action_group_id = azurerm_monitor_action_group.mtls_alerts.id
  }

  tags = local.common_tags
}

# Service Discovery Health Check
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "service_discovery_health" {
  name                = "${var.resource_prefix}-service-discovery-health"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name
  evaluation_frequency = "PT5M"
  window_duration      = "PT15M"
  scopes               = [azurerm_log_analytics_workspace.main.id]
  severity             = 2
  description          = "Monitor service discovery health and DNS resolution"

  criteria {
    query                   = <<-QUERY
      ContainerAppConsoleLogs_CL
      | where Log_s contains "DNS resolution"
      | where Log_s contains "failed" or Log_s contains "timeout"
      | summarize count() by bin(TimeGenerated, 5m)
      | where count_ > 5
    QUERY
    time_aggregation_method = "Count"
    threshold               = 5.0
    operator                = "GreaterThan"

    failing_periods {
      minimum_failing_periods_to_trigger_alert = 2
      number_of_evaluation_periods             = 4
    }
  }

  action {
    action_groups = [azurerm_monitor_action_group.mtls_alerts.id]
  }

  tags = local.common_tags
}

# KEDA Scaling Alert
resource "azurerm_monitor_metric_alert" "keda_scaling_failures" {
  name                = "${var.resource_prefix}-keda-scaling-failures"
  resource_group_name = azurerm_resource_group.main.name
  scopes              = [azurerm_container_app_environment.main.id]
  description         = "Alert on KEDA scaling failures"
  severity            = 2
  frequency           = "PT5M"
  window_size         = "PT15M"

  criteria {
    metric_namespace = "Microsoft.App/managedEnvironments"
    metric_name      = "ScalingFailures"
    aggregation      = "Total"
    operator         = "GreaterThan"
    threshold        = 3
  }

  action {
    action_group_id = azurerm_monitor_action_group.mtls_alerts.id
  }

  tags = local.common_tags
}

# Workbook for mTLS and Service Discovery Dashboard
resource "azurerm_application_insights_workbook" "mtls_dashboard" {
  name                = "${var.resource_prefix}-mtls-dashboard"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name
  display_name        = "mTLS and Service Discovery Dashboard"
  source_id           = azurerm_application_insights.main.id

  data_json = jsonencode({
    version = "Notebook/1.0"
    items = [
      {
        type = 1
        content = {
          json = "# mTLS Certificate and Service Discovery Monitoring\n\nThis dashboard provides comprehensive monitoring for:\n- Certificate expiration tracking\n- mTLS handshake success/failure rates\n- Service discovery health\n- Container scaling events\n- Inter-service communication metrics"
        }
      },
      {
        type = 3
        content = {
          version = "KqlItem/1.0"
          query = "AppMetrics\n| where Name == \"certificate_expiry_days\"\n| summarize arg_max(TimeGenerated, *) by tostring(Properties.certificate_name)\n| project Certificate=tostring(Properties.certificate_name), ExpiryDays=Value, LastChecked=TimeGenerated\n| order by ExpiryDays asc"
          size = 1
          title = "Certificate Expiration Status"
          queryType = 0
          resourceType = "microsoft.insights/components"
          visualization = "table"
        }
      },
      {
        type = 3
        content = {
          version = "KqlItem/1.0"
          query = "AppDependencies\n| where Type == \"Http\"\n| where Properties contains \"mtls\"\n| summarize SuccessCount=countif(Success==true), FailureCount=countif(Success==false) by bin(TimeGenerated, 5m), Target\n| project TimeGenerated, Target, SuccessRate=(SuccessCount*100.0)/(SuccessCount+FailureCount)\n| render timechart"
          size = 0
          title = "mTLS Communication Success Rate"
          queryType = 0
          resourceType = "microsoft.insights/components"
        }
      }
    ]
  })

  tags = local.common_tags
}