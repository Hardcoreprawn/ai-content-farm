# Azure Logic App Scheduler Infrastructure
# Cost-optimized scheduler for dynamic content collection
# Pipeline test: triggering infrastructure deployment

# Logic App for content collection scheduling
resource "azurerm_logic_app_workflow" "content_scheduler" {
  name                = "${var.resource_prefix}-scheduler"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name

  # Use system-assigned managed identity for authentication
  identity {
    type = "SystemAssigned"
  }

  tags = merge(local.common_tags, {
    Purpose    = "content-collection-scheduler"
    CostCenter = "scheduler"
  })
}

# Logic App Action - Workflow Definition
resource "azurerm_logic_app_action_http" "call_content_collector" {
  name         = "Call_Content_Collector"
  logic_app_id = azurerm_logic_app_workflow.content_scheduler.id
  method       = "POST"
  uri          = "https://${azurerm_container_app.content_collector.latest_revision_fqdn}/api/collect"

  headers = {
    "Content-Type" = "application/json"
  }

  body = jsonencode({
    source = "reddit"
    topics = ["technology", "programming", "science"]
  })
}

# Logic App Trigger - Recurrence
resource "azurerm_logic_app_trigger_recurrence" "content_collection_schedule" {
  name         = "Recurrence"
  logic_app_id = azurerm_logic_app_workflow.content_scheduler.id
  frequency    = "Hour"
  interval     = 6
  time_zone    = "UTC"
}

# Storage tables for scheduler configuration and analytics
resource "azurerm_storage_table" "topic_configurations" {
  name                 = "topicconfigurations"
  storage_account_name = azurerm_storage_account.main.name
}

resource "azurerm_storage_table" "execution_history" {
  name                 = "executionhistory"
  storage_account_name = azurerm_storage_account.main.name
}

resource "azurerm_storage_table" "source_analytics" {
  name                 = "sourceanalytics"
  storage_account_name = azurerm_storage_account.main.name
}

# Grant Logic App permission to call Container Apps
resource "azurerm_role_assignment" "scheduler_container_apps_reader" {
  scope                = azurerm_resource_group.main.id
  role_definition_name = "Reader"
  principal_id         = azurerm_logic_app_workflow.content_scheduler.identity[0].principal_id
}

# Grant Logic App permission to manage storage tables
resource "azurerm_role_assignment" "scheduler_storage_table_contributor" {
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Table Data Contributor"
  principal_id         = azurerm_logic_app_workflow.content_scheduler.identity[0].principal_id
}

# Grant Logic App permission to access Key Vault for any needed secrets
resource "azurerm_key_vault_access_policy" "scheduler" {
  key_vault_id = azurerm_key_vault.main.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = azurerm_logic_app_workflow.content_scheduler.identity[0].principal_id

  secret_permissions = [
    "Get",
    "List"
  ]
}

# Container App URLs for scheduler to call
# These will be used in Logic App workflow to call content services
locals {
  scheduler_config = {
    content_collector_url = "https://${azurerm_container_app.content_collector.latest_revision_fqdn}"
    content_processor_url = "https://${azurerm_container_app.content_processor.latest_revision_fqdn}"

    # Topic configurations for Phase 1 MVP
    initial_topics = {
      technology = {
        display_name = "Technology"
        schedule = {
          frequency_hours = 4
          priority        = "high"
        }
        sources = {
          reddit = {
            subreddits = ["technology", "programming", "MachineLearning", "artificial"]
            limit      = 20
            sort       = "hot"
          }
        }
        criteria = {
          min_score        = 50
          min_comments     = 10
          include_keywords = ["AI", "machine learning", "automation", "tech"]
        }
      }
      programming = {
        display_name = "Programming"
        schedule = {
          frequency_hours = 6
          priority        = "medium"
        }
        sources = {
          reddit = {
            subreddits = ["programming", "webdev", "javascript", "python"]
            limit      = 15
            sort       = "hot"
          }
        }
        criteria = {
          min_score        = 30
          min_comments     = 5
          include_keywords = ["code", "development", "framework", "library"]
        }
      }
      science = {
        display_name = "Science"
        schedule = {
          frequency_hours = 8
          priority        = "medium"
        }
        sources = {
          reddit = {
            subreddits = ["science", "Futurology", "datascience"]
            limit      = 15
            sort       = "hot"
          }
        }
        criteria = {
          min_score        = 40
          min_comments     = 8
          include_keywords = ["research", "study", "discovery", "innovation"]
        }
      }
    }
  }
}

# Store scheduler configuration in Key Vault for Logic App access
resource "azurerm_key_vault_secret" "scheduler_config" {
  name         = "scheduler-config-v2"
  value        = jsonencode(local.scheduler_config)
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [azurerm_key_vault_access_policy.scheduler]

  tags = merge(local.common_tags, {
    Purpose = "scheduler-configuration"
  })
}

# Budget alert for scheduler costs
resource "azurerm_consumption_budget_resource_group" "scheduler_budget" {
  name              = "${var.resource_prefix}-scheduler-budget"
  resource_group_id = azurerm_resource_group.main.id

  amount     = 5 # $5/month budget for scheduler components
  time_grain = "Monthly"

  time_period {
    start_date = formatdate("YYYY-MM-01'T'00:00:00'Z'", timestamp())
  }

  notification {
    enabled   = true
    threshold = 80 # Alert at 80% of budget ($4)
    operator  = "GreaterThan"

    contact_emails = [
      "admin@example.com" # TODO: Replace with actual notification email
    ]
  }

  notification {
    enabled   = true
    threshold = 100 # Alert at 100% of budget ($5)
    operator  = "GreaterThan"

    contact_emails = [
      "admin@example.com" # TODO: Replace with actual notification email
    ]
  }
}

# Output scheduler information for reference
output "scheduler_info" {
  description = "Information about the deployed scheduler infrastructure"
  value = {
    logic_app_name                = azurerm_logic_app_workflow.content_scheduler.name
    logic_app_id                  = azurerm_logic_app_workflow.content_scheduler.id
    managed_identity_principal_id = azurerm_logic_app_workflow.content_scheduler.identity[0].principal_id

    storage_tables = {
      topic_configurations = azurerm_storage_table.topic_configurations.name
      execution_history    = azurerm_storage_table.execution_history.name
      source_analytics     = azurerm_storage_table.source_analytics.name
    }

    content_collector_url = local.scheduler_config.content_collector_url
    content_processor_url = local.scheduler_config.content_processor_url

    budget_name   = azurerm_consumption_budget_resource_group.scheduler_budget.name
    budget_amount = azurerm_consumption_budget_resource_group.scheduler_budget.amount
  }

  sensitive = false
}

# Create blob container for scheduler logs
resource "azurerm_storage_container" "scheduler_logs" {
  name                  = "scheduler-logs"
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "private"
}

# Create blob container for analytics cache
resource "azurerm_storage_container" "analytics_cache" {
  name                  = "analytics-cache"
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "private"
}
