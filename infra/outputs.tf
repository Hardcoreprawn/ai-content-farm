# Outputs
# Trivial change to trigger infrastructure detection - 2025-08-25

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
