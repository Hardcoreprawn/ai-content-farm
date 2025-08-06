# Outputs

output "function_app_name" {
  value = azurerm_linux_function_app.main.name
}

output "function_app_default_hostname" {
  value = azurerm_linux_function_app.main.default_hostname
}

output "storage_account_name" {
  value = azurerm_storage_account.main.name
}

output "storage_container_name" {
  value = azurerm_storage_container.topics.name
}

output "resource_group_name" {
  value = azurerm_resource_group.main.name
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

# GitHub Actions OIDC Configuration
output "github_actions_client_id" {
  description = "Client ID for GitHub Actions OIDC"
  value       = data.azuread_application.github_actions.client_id
}

output "github_actions_tenant_id" {
  description = "Tenant ID for GitHub Actions OIDC"
  value       = data.azurerm_client_config.current.tenant_id
}

output "github_actions_subscription_id" {
  description = "Subscription ID for GitHub Actions OIDC"
  value       = data.azurerm_client_config.current.subscription_id
}

output "github_variables_setup_command" {
  description = "Command to set GitHub repository variables"
  value       = <<EOT
Run these commands to set up GitHub repository variables:
gh variable set AZURE_CLIENT_ID --body "${data.azuread_application.github_actions.client_id}"
gh variable set AZURE_TENANT_ID --body "${data.azurerm_client_config.current.tenant_id}"
gh variable set AZURE_SUBSCRIPTION_ID --body "${data.azurerm_client_config.current.subscription_id}"
EOT
}

output "application_insights_app_id" {
  value = azurerm_application_insights.main.app_id
}

output "log_analytics_workspace_name" {
  value = azurerm_log_analytics_workspace.main.name
}
