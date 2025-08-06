# Backend configuration for Terraform state
# This will be populated by the bootstrap process
terraform {
  backend "azurerm" {
    # These values will be provided during terraform init
    # storage_account_name = "..."
    # container_name       = "tfstate"
    # key                  = "staging.tfstate"
    # resource_group_name  = "..."
  }
}
