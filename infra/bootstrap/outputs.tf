output "storage_account_name" {
  description = "Storage account name for Terraform state"
  value       = azurerm_storage_account.tfstate.name
}

output "container_name" {
  description = "Storage container name for Terraform state"
  value       = azurerm_storage_container.tfstate.name
}

output "resource_group_name" {
  description = "Resource group name for bootstrap resources"
  value       = azurerm_resource_group.bootstrap.name
}

output "azure_client_id" {
  description = "Azure Client ID for GitHub Actions"
  value       = azuread_application.github_actions.client_id
}

output "github_actions_object_id" {
  description = "Object ID of the GitHub Actions service principal"
  value       = azuread_service_principal.github_actions.object_id
}

output "cicd_key_vault_name" {
  description = "Name of the CI/CD Key Vault for GitHub Actions secrets"
  value       = azurerm_key_vault.cicd.name
}

output "cicd_key_vault_uri" {
  description = "URI of the CI/CD Key Vault for GitHub Actions secrets"
  value       = azurerm_key_vault.cicd.vault_uri
}

output "azure_tenant_id" {
  description = "Azure Tenant ID"
  value       = data.azurerm_client_config.current.tenant_id
}

output "azure_subscription_id" {
  description = "Azure Subscription ID"
  value       = data.azurerm_client_config.current.subscription_id
}

output "github_variables_setup" {
  description = "GitHub repository variables to set"
  value = {
    AZURE_CLIENT_ID       = azuread_application.github_actions.client_id
    AZURE_TENANT_ID       = data.azurerm_client_config.current.tenant_id
    AZURE_SUBSCRIPTION_ID = data.azurerm_client_config.current.subscription_id
  }
}

output "terraform_backend_config" {
  description = "Backend configuration for main Terraform"
  value = {
    storage_account_name = azurerm_storage_account.tfstate.name
    container_name       = azurerm_storage_container.tfstate.name
    key                  = "${var.environment}.tfstate"
    resource_group_name  = azurerm_resource_group.bootstrap.name
  }
}
