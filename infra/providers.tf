terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "4.37.0"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.0"
    }

    random = {
      source  = "hashicorp/random"
      version = "3.6.0"
    }
    external = {
      source  = "hashicorp/external"
      version = "~> 2.3"
    }
  }
  required_version = ">= 1.3.0"
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id != "" ? var.subscription_id : null
}

provider "azuread" {}

provider "random" {}
