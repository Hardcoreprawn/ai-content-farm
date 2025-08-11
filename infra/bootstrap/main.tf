# Bootstrap infrastructure for AI Content Farm
# This creates the foundation resources needed before the main infrastructure

terraform {
  # Backend configuration for remote state (use after initial bootstrap)
  # Uncomment and run: terraform init -backend-config=backend.hcl
  # backend "azurerm" {}
  
  required_version = ">= 1.3.0"
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
  name                     = "aicontentfarm${random_string.suffix.result}"
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

# Environment-based federated identity credentials for GitHub Environments
resource "azuread_application_federated_identity_credential" "staging_environment" {
  application_id = azuread_application.github_actions.id
  display_name   = "staging-environment"
  description    = "Staging environment deployment"
  audiences      = ["api://AzureADTokenExchange"]
  issuer         = "https://token.actions.githubusercontent.com"
  subject        = "repo:${var.github_repository}:environment:staging"
}

resource "azuread_application_federated_identity_credential" "production_environment" {
  application_id = azuread_application.github_actions.id
  display_name   = "production-environment"
  description    = "Production environment deployment"
  audiences      = ["api://AzureADTokenExchange"]
  issuer         = "https://token.actions.githubusercontent.com"
  subject        = "repo:${var.github_repository}:environment:production"
}

# CI/CD Key Vault for GitHub Actions secrets (separate from application secrets)
resource "azurerm_key_vault" "cicd" {
  # checkov:skip=CKV_AZURE_189: Public access is acceptable for CI/CD use case
  # checkov:skip=CKV_AZURE_109: Firewall rules not required for CI/CD use case
  # checkov:skip=CKV2_AZURE_32: Private endpoint not required for CI/CD use case
  name                = "ai-content-cicd-kv${random_string.suffix.result}"
  location            = azurerm_resource_group.bootstrap.location
  resource_group_name = azurerm_resource_group.bootstrap.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"

  # Security settings
  purge_protection_enabled   = true
  soft_delete_retention_days = 7

  tags = {
    Purpose     = "ci-cd-secrets"
    Project     = "ai-content-farm"
    ManagedBy   = "terraform-bootstrap"
    Environment = var.environment
  }
}

# Key Vault access policy for current user/service principal (admin access)
resource "azurerm_key_vault_access_policy" "cicd_admin" {
  key_vault_id = azurerm_key_vault.cicd.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = data.azurerm_client_config.current.object_id

  secret_permissions = [
    "Get",
    "List",
    "Set",
    "Delete",
    "Purge",
    "Recover"
  ]
}

# Key Vault access policy for GitHub Actions service principal (read-only)
resource "azurerm_key_vault_access_policy" "github_actions_cicd" {
  key_vault_id = azurerm_key_vault.cicd.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = azuread_service_principal.github_actions.object_id

  secret_permissions = [
    "Get",
    "List"
  ]
}

# CI/CD secrets for GitHub Actions OIDC
resource "azurerm_key_vault_secret" "azure_client_id" {
  name            = "azure-client-id"
  value           = azuread_application.github_actions.client_id
  key_vault_id    = azurerm_key_vault.cicd.id
  content_type    = "text/plain"

  depends_on = [
    azurerm_key_vault_access_policy.cicd_admin,
    azurerm_key_vault_access_policy.github_actions_cicd
  ]

  tags = {
    Purpose     = "github-actions-oidc"
    Environment = var.environment
  }
}

resource "azurerm_key_vault_secret" "azure_tenant_id" {
  name            = "azure-tenant-id"
  value           = data.azurerm_client_config.current.tenant_id
  key_vault_id    = azurerm_key_vault.cicd.id
  content_type    = "text/plain"

  depends_on = [
    azurerm_key_vault_access_policy.cicd_admin,
    azurerm_key_vault_access_policy.github_actions_cicd
  ]

  tags = {
    Purpose     = "github-actions-oidc"
    Environment = var.environment
  }
}

resource "azurerm_key_vault_secret" "azure_subscription_id" {
  name            = "azure-subscription-id"
  value           = data.azurerm_client_config.current.subscription_id
  key_vault_id    = azurerm_key_vault.cicd.id
  content_type    = "text/plain"

  depends_on = [
    azurerm_key_vault_access_policy.cicd_admin,
    azurerm_key_vault_access_policy.github_actions_cicd
  ]

  tags = {
    Purpose     = "github-actions-oidc"
    Environment = var.environment
  }
}

# CI/CD secret: Infracost API key
resource "azurerm_key_vault_secret" "infracost_api_key" {
  name            = "infracost-api-key"
  value           = "placeholder-get-from-infracost-io"
  key_vault_id    = azurerm_key_vault.cicd.id
  content_type    = "text/plain"
  expiration_date = timeadd(timestamp(), "8760h") # 1 year from now

  depends_on = [
    azurerm_key_vault_access_policy.cicd_admin,
    azurerm_key_vault_access_policy.github_actions_cicd
  ]

  tags = {
    Purpose     = "cost-estimation"
    Environment = var.environment
  }
}

# Role assignment for the service principal at subscription level
resource "azurerm_role_assignment" "github_actions_contributor" {
  scope                = "/subscriptions/${data.azurerm_client_config.current.subscription_id}"
  role_definition_name = "Contributor"
  principal_id         = azuread_service_principal.github_actions.object_id
}

# User Access Administrator role for creating role assignments
resource "azurerm_role_assignment" "github_actions_user_access_admin" {
  scope                = "/subscriptions/${data.azurerm_client_config.current.subscription_id}"
  role_definition_name = "User Access Administrator"
  principal_id         = azuread_service_principal.github_actions.object_id
}
