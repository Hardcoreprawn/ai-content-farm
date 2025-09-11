# Outputs
# Force deployment after Azure Functions removal - 2025-09-11

output "resource_group_name" {
  description = "Name of the Azure resource group"
  value       = azurerm_resource_group.main.name
}

output "resource_prefix" {
  description = "Resource prefix used for naming resources"
  value       = var.resource_prefix
}

# Function App outputs removed - container services don't need these

output "storage_account_name" {
  value = azurerm_storage_account.main.name
}

output "storage_container_name" {
  value = azurerm_storage_container.topics.name
}

output "storage_collected_content_container_name" {
  value = azurerm_storage_container.collected_content.name
}

output "storage_processed_content_container_name" {
  value = azurerm_storage_container.processed_content.name
}

output "storage_enriched_content_container_name" {
  value = azurerm_storage_container.enriched_content.name
}

output "storage_ranked_content_container_name" {
  value = azurerm_storage_container.ranked_content.name
}

output "storage_markdown_content_container_name" {
  value = azurerm_storage_container.markdown_content.name
}

output "storage_static_sites_container_name" {
  value = azurerm_storage_container.static_sites.name
}

output "storage_pipeline_logs_container_name" {
  value = azurerm_storage_container.pipeline_logs.name
}

output "storage_pricing_cache_container_name" {
  value = azurerm_storage_container.pricing_cache.name
}

output "key_vault_name" {
  value = azurerm_key_vault.main.name
}

output "key_vault_id" {
  value = azurerm_key_vault.main.id
}

output "application_insights_name" {
  value = azurerm_application_insights.main.name
}

output "application_insights_app_id" {
  value = azurerm_application_insights.main.app_id
}

output "log_analytics_workspace_name" {
  value = azurerm_log_analytics_workspace.main.name
}

# GitHub Actions OIDC Identity outputs
output "github_actions_client_id" {
  description = "Client ID for GitHub Actions managed identity (use for OIDC authentication)"
  value       = azurerm_user_assigned_identity.github_actions.client_id
}

output "github_actions_principal_id" {
  description = "Principal ID for GitHub Actions managed identity"
  value       = azurerm_user_assigned_identity.github_actions.principal_id
}

output "tenant_id" {
  description = "Azure tenant ID for OIDC authentication"
  value       = data.azurerm_client_config.current.tenant_id
}

output "subscription_id" {
  description = "Azure subscription ID for OIDC authentication"
  value       = data.azurerm_client_config.current.subscription_id
}

# Resource Group output
# Container Apps Environment outputs
output "container_apps_environment_name" {
  description = "Name of the Container Apps Environment"
  value       = azurerm_container_app_environment.main.name
}

output "container_apps_environment_id" {
  description = "ID of the Container Apps Environment"
  value       = azurerm_container_app_environment.main.id
}

output "storage_prompts_container_name" {
  value = azurerm_storage_container.prompts.name
}

# Content Processor Container App outputs
output "content_processor_url" {
  description = "URL of the Content Processor Container App"
  value       = "https://${azurerm_container_app.content_processor.latest_revision_fqdn}"
}

output "content_processor_name" {
  description = "Name of the Content Processor Container App"
  value       = azurerm_container_app.content_processor.name
}

# Site Generator Container App outputs
output "site_generator_url" {
  description = "URL of the Site Generator Container App"
  value       = "https://${azurerm_container_app.site_generator.latest_revision_fqdn}"
}

output "site_generator_name" {
  description = "Name of the Site Generator Container App"
  value       = azurerm_container_app.site_generator.name
}

# Static Web App outputs
output "static_web_app_url" {
  description = "Default URL of the Static Web App"
  value       = "https://${azurerm_static_web_app.jablab.default_host_name}"
}

output "static_web_app_custom_domain" {
  description = "Custom domain URL for jablab.com"
  value       = "https://jablab.com"
}

output "static_web_app_name" {
  description = "Name of the Static Web App"
  value       = azurerm_static_web_app.jablab.name
}

# Function App outputs removed - Functions infrastructure cleaned up
# Static site generation now handled by site-generator container

# DNS Zone outputs
output "dns_zone_name_servers" {
  description = "Name servers for jablab.com DNS zone"
  value       = azurerm_dns_zone.jablab.name_servers
}

# Pipeline Functions outputs removed - using container-based approach instead

output "scheduler_storage_tables" {
  description = "Storage table names for scheduler configuration"
  value = {
    topic_configurations = azurerm_storage_table.topic_configurations.name
    execution_history    = azurerm_storage_table.execution_history.name
    source_analytics     = azurerm_storage_table.source_analytics.name
  }
}

output "scheduler_storage_containers" {
  description = "Storage container names for scheduler logs and analytics"
  value = {
    scheduler_logs  = azurerm_storage_container.scheduler_logs.name
    analytics_cache = azurerm_storage_container.analytics_cache.name
  }
}
