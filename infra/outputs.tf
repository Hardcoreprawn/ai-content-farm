# Outputs

# Container outputs (to be added when container infrastructure is deployed)
# output "container_app_name" {
#   value = azurerm_container_app.main.name
# }
#
# output "container_app_hostname" {
#   value = azurerm_container_app.main.fqdn
# }

output "storage_account_name" {
  value = azurerm_storage_account.main.name
}

output "storage_container_name" {
  value = azurerm_storage_container.topics.name
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
