terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "4.37.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "3.6.0"
    }
    acme = {
      source  = "vancluever/acme"
      version = "~> 2.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }
  required_version = ">= 1.3.0"
  # Updated 2025-09-01: Testing security scanning pipeline
  # Updated 2025-09-12: Added ACME and TLS providers for PKI infrastructure
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id != "" ? var.subscription_id : null
}

provider "random" {}

# ACME provider for Let's Encrypt
provider "acme" {
  # Use Let's Encrypt staging for testing, production for real certificates
  server_url = var.environment == "production" ? "https://acme-v02.api.letsencrypt.org/directory" : "https://acme-staging-v02.api.letsencrypt.org/directory"
}
