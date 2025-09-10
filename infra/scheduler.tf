# Azure Scheduler Infrastructure - Simplified Architecture
# Note: Scheduling now handled externally (GitHub Actions, cron, etc.)
# Storage tables maintained for configuration and analytics
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

# Store scheduler configuration in blob storage for external schedulers
resource "azurerm_storage_container" "scheduler_config" {
  name                  = "scheduler-config"
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "private"
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

  lifecycle {
    ignore_changes = [
      time_period[0].start_date,
      time_period[0].end_date
    ]
  }
}

# Output scheduler information for reference
output "scheduler_info" {
  description = "Information about the simplified scheduler infrastructure"
  value = {
    external_scheduling = "Use GitHub Actions or external cron to trigger content-collector"
    manual_trigger_url  = local.scheduler_config.content_collector_url

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
