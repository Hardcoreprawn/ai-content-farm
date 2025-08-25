# Remote backend configuration for Terraform state
# This configuration stores state remotely in Azure Storage for team collaboration.
# Only the production environment persists - staging environments are ephemeral.
# OIDC authentication configured and ready for production deployment.
# Cost analysis action fixed for proper docker mounting.

terraform {
  backend "azurerm" {
    # Storage account and container for state storage
    storage_account_name = "aicontentfarmtfstate"
    container_name       = "tfstate"

    # Production state file (only persistent environment)
    key = "terraform-production.tfstate"

    # Authentication using Azure CLI credentials locally
    # and managed identity/OIDC in GitHub Actions
    use_azuread_auth = true
  }
}

# Note: Ephemeral PR environments will use separate state files
# with dynamic naming (e.g., terraform-pr-123.tfstate) and automatic cleanup.
# Only the production environment persists.
