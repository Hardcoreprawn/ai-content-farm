# Bootstrap infrastructure for AI Content Farm
# This creates the foundation resources needed before the main infrastructure

terraform {
  required_version = ">= 1.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy    = true
      recover_soft_deleted_key_vaults = true
    }
  }
}

provider "azuread" {}

# Get current Azure configuration
data "azurerm_client_config" "current" {}

# Resource group for bootstrap resources (Terraform state, Azure AD app)
resource "azurerm_resource_group" "bootstrap" {
  name     = "ai-content-farm-bootstrap"
  location = var.location

  tags = {
    Purpose   = "terraform-state-and-bootstrap"
    Project   = "ai-content-farm"
    ManagedBy = "terraform-bootstrap"
  }
}

# Storage account for Terraform remote state
resource "azurerm_storage_account" "tfstate" {
  name                     = "aicontentfarmtfstate${random_string.suffix.result}"
  resource_group_name      = azurerm_resource_group.bootstrap.name
  location                 = azurerm_resource_group.bootstrap.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"

  blob_properties {
    versioning_enabled = true
  }

  tags = {
    Purpose   = "terraform-state"
    Project   = "ai-content-farm"
    ManagedBy = "terraform-bootstrap"
  }
}

# Storage container for Terraform state
resource "azurerm_storage_container" "tfstate" {
  name                  = "tfstate"
  storage_account_id    = azurerm_storage_account.tfstate.id
  container_access_type = "private"
}

# Random suffix for unique naming
resource "random_string" "suffix" {
  length  = 6
  upper   = false
  special = false
}

# Azure AD Application for GitHub Actions OIDC
resource "azuread_application" "github_actions" {
  display_name = "ai-content-farm-github-${var.environment}"
  description  = "GitHub Actions OIDC application for ${var.environment} environment"

  # Required API permissions for Terraform operations
  required_resource_access {
    resource_app_id = "00000003-0000-0000-c000-000000000000" # Microsoft Graph

    resource_access {
      id   = "9a5d68dd-52b0-4cc2-bd40-abcf44ac3a30" # Application.ReadWrite.All
      type = "Role"
    }
  }

  tags = ["github-actions", "oidc", var.environment]
}

# Service Principal for the Azure AD Application
resource "azuread_service_principal" "github_actions" {
  client_id = azuread_application.github_actions.client_id
  
  tags = ["github-actions", "oidc", var.environment]
}

# Federated Identity Credentials for GitHub Actions OIDC
resource "azuread_application_federated_identity_credential" "main_branch" {
  application_id = azuread_application.github_actions.id
  display_name   = "main-branch"
  description    = "Main branch deployment"
  audiences      = ["api://AzureADTokenExchange"]
  issuer         = "https://token.actions.githubusercontent.com"
  subject        = "repo:${var.github_repository}:ref:refs/heads/main"
}

resource "azuread_application_federated_identity_credential" "develop_branch" {
  application_id = azuread_application.github_actions.id
  display_name   = "develop-branch"
  description    = "Develop branch deployment"
  audiences      = ["api://AzureADTokenExchange"]
  issuer         = "https://token.actions.githubusercontent.com"
  subject        = "repo:${var.github_repository}:ref:refs/heads/develop"
}

resource "azuread_application_federated_identity_credential" "pull_requests" {
  application_id = azuread_application.github_actions.id
  display_name   = "pull-requests"
  description    = "Pull request validation"
  audiences      = ["api://AzureADTokenExchange"]
  issuer         = "https://token.actions.githubusercontent.com"
  subject        = "repo:${var.github_repository}:pull_request"
}

# Role assignment for the service principal at subscription level
resource "azurerm_role_assignment" "github_actions_contributor" {
  scope                = "/subscriptions/${data.azurerm_client_config.current.subscription_id}"
  role_definition_name = "Contributor"
  principal_id         = azuread_service_principal.github_actions.object_id
}
