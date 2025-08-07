terraform {
  backend "azurerm" {
    # Backend configuration is provided via -backend-config flag
    # Use backend-staging.hcl or backend-production.hcl
  }
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "4.37.0"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.47"
    }
    random = {
      source  = "hashicorp/random"
      version = "3.6.0"
    }
  }
  required_version = ">= 1.3.0"
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy    = true
      recover_soft_deleted_key_vaults = true
    }
  }
  subscription_id = var.subscription_id
}

provider "azuread" {}

provider "random" {}