# Monitoring Dashboards & Saved Queries
# Provides Application Insights monitoring dashboards and KQL queries

# Log Analytics Saved Queries Pack for monitoring
resource "azurerm_log_analytics_query_pack" "performance_queries" {
  name                = "${local.resource_prefix}-perf-queries"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  tags = merge(
    local.common_tags,
    {
      category = "Performance Monitoring"
    }
  )
}

# Query: Performance Score Trends
resource "azurerm_log_analytics_query_pack_query" "performance_score_trends" {
  query_pack_id = azurerm_log_analytics_query_pack.performance_queries.id
  display_name  = "Performance Score Trends"
  body          = "customEvents\n| where name == 'PagePerformance'\n| extend score = todouble(customDimensions.performanceScore)\n| summarize AvgScore = avg(score) by bin(timestamp, 1h)\n| render timechart"
  categories    = ["monitor"]
}

# Query: Core Web Vitals Overview
resource "azurerm_log_analytics_query_pack_query" "web_vitals_overview" {
  query_pack_id = azurerm_log_analytics_query_pack.performance_queries.id
  display_name  = "Core Web Vitals Overview (Last 24h)"
  body          = "customMetrics\n| where name in ('LargestContentfulPaint', 'CumulativeLayoutShift', 'TimeToFirstByte', 'FirstContentfulPaint')\n| summarize Avg = avg(value) by name\n| render table"
  categories    = ["monitor"]
}

# Query: Resource Performance by Type
resource "azurerm_log_analytics_query_pack_query" "resource_performance" {
  query_pack_id = azurerm_log_analytics_query_pack.performance_queries.id
  display_name  = "Resource Loading Performance"
  body          = "customEvents\n| where name startswith 'ResourceLoading'\n| extend resourceType = extract('ResourceLoading_(.+)', 1, name)\n| summarize Count = sum(todouble(customDimensions.count)), AvgTime = avg(todouble(customDimensions.avgTime)) by resourceType\n| order by AvgTime desc"
  categories    = ["applications"]
}

# Query: User Interaction Heatmap
resource "azurerm_log_analytics_query_pack_query" "user_interactions" {
  query_pack_id = azurerm_log_analytics_query_pack.performance_queries.id
  display_name  = "User Interactions Summary"
  body          = "customEvents\n| where name startswith 'UserAction'\n| summarize count() by name, bin(timestamp, 1h)\n| render timechart"
  categories    = ["applications"]
}

# Query: Performance Score Distribution
resource "azurerm_log_analytics_query_pack_query" "performance_distribution" {
  query_pack_id = azurerm_log_analytics_query_pack.performance_queries.id
  display_name  = "Performance Score Distribution"
  body          = "customEvents\n| where name == 'PagePerformance'\n| extend score = todouble(customDimensions.performanceScore)\n| extend category = case(score >= 90, 'Excellent', score >= 75, 'Good', score >= 50, 'Needs Improvement', 'Poor')\n| summarize count() by category"
  categories    = ["monitor"]
}

# Pipeline Monitoring Queries
resource "azurerm_log_analytics_query_pack" "pipeline_queries" {
  name                = "${local.resource_prefix}-pipeline-queries"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  tags = merge(
    local.common_tags,
    {
      category = "Pipeline Monitoring"
    }
  )
}

# Query: Container App Errors
resource "azurerm_log_analytics_query_pack_query" "container_errors" {
  query_pack_id = azurerm_log_analytics_query_pack.pipeline_queries.id
  display_name  = "Container App Errors (Last 24h)"
  body          = "exceptions\n| summarize count() by cloud_RoleName, exceptionType\n| order by count_ desc"
  categories    = ["security"]
}

# Query: Processing Success Rate
resource "azurerm_log_analytics_query_pack_query" "processing_success_rate" {
  query_pack_id = azurerm_log_analytics_query_pack.pipeline_queries.id
  display_name  = "Processing Success Rate"
  body          = "customEvents\n| where name contains 'process'\n| extend success = name contains 'Success' or name contains 'Complete'\n| summarize Total = count(), Successful = sum(success) by bin(timestamp, 1h)\n| extend SuccessRate = todouble(Successful) / Total * 100\n| render timechart"
  categories    = ["monitor"]
}

# Query: Queue Depth Monitoring
resource "azurerm_log_analytics_query_pack_query" "queue_depth" {
  query_pack_id = azurerm_log_analytics_query_pack.pipeline_queries.id
  display_name  = "Storage Queue Depth"
  body          = "AzureMetrics\n| where ResourceProvider == 'MICROSOFT.STORAGE'\n| where MetricName == 'ApproximateMessageCount'\n| summarize AvgDepth = avg(Total), MaxDepth = max(Total) by bin(TimeGenerated, 15m), Resource\n| render timechart"
  categories    = ["resources"]
}

# Query: Container App Replicas Over Time
resource "azurerm_log_analytics_query_pack_query" "replica_scaling" {
  query_pack_id = azurerm_log_analytics_query_pack.pipeline_queries.id
  display_name  = "KEDA Scaling Activity"
  body          = "AzureMetrics\n| where ResourceProvider == 'MICROSOFT.APP'\n| where MetricName == 'ReplcaCount'\n| summarize AvgReplicas = avg(Total) by bin(TimeGenerated, 1h), Resource\n| render timechart"
  categories    = ["monitor"]
}

# Outputs for dashboard access
output "appinsights_analytics_url" {
  description = "URL to Application Insights Logs Analytics for querying"
  value       = "https://portal.azure.com/#@${data.azurerm_client_config.current.tenant_id}/resource${azurerm_application_insights.main.id}/logs"
}

output "appinsights_dashboards_url" {
  description = "URL to create and manage dashboards"
  value       = "https://portal.azure.com/#@${data.azurerm_client_config.current.tenant_id}/resource${azurerm_application_insights.main.id}/overview"
}

output "performance_queries_pack_id" {
  description = "Performance monitoring queries pack ID"
  value       = azurerm_log_analytics_query_pack.performance_queries.id
}

output "pipeline_queries_pack_id" {
  description = "Pipeline monitoring queries pack ID"
  value       = azurerm_log_analytics_query_pack.pipeline_queries.id
}
