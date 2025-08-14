variable "location" {
  description = "Azure region to deploy resources."
  default     = "westeurope"
}

variable "subscription_id" {
  description = "The Azure Subscription ID to use. Leave blank to use the default from Azure CLI context."
  type        = string
  default     = "6b924609-f8c6-4bd2-a873-2b8f55596f67"
}

variable "environment" {
  description = "Environment name (staging, production, or dynamic like pr-123)"
  type        = string
  default     = "development"
  validation {
    condition     = contains(["development", "staging", "production"], var.environment) || can(regex("^pr-[0-9]+$", var.environment))
    error_message = "Environment must be development, staging, production, or pr-{number} format."
  }
}

variable "environment_name" {
  description = "Dynamic environment name for ephemeral environments (overrides environment)"
  type        = string
  default     = ""
}

variable "branch_name" {
  description = "Git branch name for ephemeral environments"
  type        = string
  default     = ""
}

variable "resource_prefix" {
  description = "Prefix for all resource names (will be dynamic for ephemeral environments)"
  type        = string
  default     = "ai-content-dev"
}

# Computed locals for dynamic naming
locals {
  # Use environment_name if provided (for ephemeral), otherwise use environment
  effective_environment = var.environment_name != "" ? var.environment_name : var.environment

  # Dynamic resource prefix based on environment
  resource_prefix = var.environment_name != "" ? "ai-content-${var.environment_name}" : var.resource_prefix

  # Tags for all resources
  common_tags = {
    Environment = local.effective_environment
    Project     = "ai-content-farm"
    ManagedBy   = "terraform"
    BranchName  = var.branch_name != "" ? var.branch_name : "main"
  }
}

# Reddit API Configuration
variable "reddit_client_id" {
  description = "Reddit API client ID (can be set via Key Vault)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "reddit_client_secret" {
  description = "Reddit API client secret (can be set via Key Vault)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "reddit_user_agent" {
  description = "Reddit API user agent string"
  type        = string
  default     = ""
}

# CI/CD Configuration
variable "infracost_api_key" {
  description = "Infracost API key for cost estimation"
  type        = string
  default     = ""
  sensitive   = true
}
