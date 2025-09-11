# Cost monitoring and budget alerts

# Budget for the entire resource group
resource "azurerm_consumption_budget_resource_group" "main" {
  name              = "${var.resource_prefix}-budget"
  resource_group_id = azurerm_resource_group.main.id

  amount     = 55 # Increased budget for pipeline testing (Sep 11, 2025) - was $50
  time_grain = "Monthly"

  time_period {
    start_date = "2025-08-01T00:00:00Z"
    end_date   = "2030-12-31T00:00:00Z"
  }

  filter {
    dimension {
      name = "ResourceGroupName"
      values = [
        azurerm_resource_group.main.name,
      ]
    }
  }

  notification {
    enabled   = true
    threshold = 50 # Alert at 50% of budget
    operator  = "GreaterThan"

    contact_emails = [
      "hardcoreprawn@duck.com" # Placeholder - replace with actual admin email
    ]
  }

  notification {
    enabled   = true
    threshold = 90 # Critical alert at 90% of budget
    operator  = "GreaterThan"

    contact_emails = [
      "admin@example.com" # Placeholder - replace with actual admin email
    ]
  }
}

# Monitor Azure OpenAI usage specifically
resource "azurerm_monitor_action_group" "cost_alerts" {
  name                = "${var.resource_prefix}-cost-alerts"
  resource_group_name = azurerm_resource_group.main.name
  short_name          = "costAlert"

  email_receiver {
    name          = "admin"
    email_address = "admin@example.com" # Replace with your email
  }
}

# Alert for high Azure OpenAI costs
resource "azurerm_monitor_metric_alert" "openai_cost" {
  name                = "${var.resource_prefix}-openai-cost-alert"
  resource_group_name = azurerm_resource_group.main.name
  scopes              = [azurerm_cognitive_account.openai.id]
  description         = "Alert when OpenAI costs exceed threshold"
  severity            = 2

  criteria {
    metric_namespace = "Microsoft.CognitiveServices/accounts"
    metric_name      = "TotalCalls"
    aggregation      = "Total"
    operator         = "GreaterThan"
    threshold        = 10000 # Alert after 10k API calls
  }

  window_size = "PT5M"
  frequency   = "PT1M"

  action {
    action_group_id = azurerm_monitor_action_group.cost_alerts.id
  }

  tags = local.common_tags
}
