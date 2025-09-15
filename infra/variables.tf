variable "location" {
  description = "Azure region to deploy resources."
  default     = "uksouth"
}

# Updated: Enhanced CI/CD pipeline with unified build reporting - Aug 22, 2025
# Phase 1 validation: Trigger terraform run after requirements fixes - Sep 9, 2025
# Pipeline Fix Test: Issue #421 dynamic container discovery - Sep 10, 2025
variable "subscription_id" {
  description = "The Azure Subscription ID to use. Leave blank to use the default from Azure CLI context."
  type        = string
  default     = "6b924609-f8c6-4bd2-a873-2b8f55596f67"
}

variable "environment" {
  description = "Environment name (production only - dev/staging handled via container revisions)"
  type        = string
  default     = "production"
  validation {
    condition     = var.environment == "production"
    error_message = "Only production environment supported. Use container revisions for dev/staging."
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

variable "test_feature_flag" {
  description = "Test feature flag for smart deployment validation and container image fallback testing - updated Sept 3rd"
  type        = bool
  default     = false
}

# Image tag for all containers (commit hash or version)
variable "image_tag" {
  description = "Image tag for all containers - should be commit hash for production deployments"
  type        = string
  default     = "latest"
}

# Container image configuration for deployments
variable "container_images" {
  description = "Map of container names to their full registry URLs with tags - can be overridden with specific image references"
  type        = map(string)
  default     = {} # Will be populated by locals with dynamic image_tag
}

# Computed locals for dynamic naming
locals {
  # Use environment_name if provided (for ephemeral), otherwise use environment
  effective_environment = var.environment_name != "" ? var.environment_name : var.environment

  # Dynamic resource prefix based on environment
  resource_prefix = var.environment_name != "" ? "ai-content-${var.environment_name}" : var.resource_prefix

  # Container images are now dynamically discovered in container_discovery.tf
  # This local is kept for backwards compatibility but will use discovered containers

  # Clean prefix for resources that don't allow hyphens (Key Vault, Storage Account)
  clean_prefix = replace(local.resource_prefix, "-", "")

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

# Certificate Management Configuration
variable "certificate_email" {
  description = "Email address for Let's Encrypt certificate notifications"
  type        = string
  default     = "admin@jablab.dev"
}

# mTLS variables removed - DAPR infrastructure deprecated in favor of scale-to-zero architecture

variable "enable_pki" {
  description = "Enable PKI infrastructure and certificate management"
  type        = bool
  default     = false
}

variable "primary_domain" {
  description = "Primary domain for certificates (jablab.dev or jablab.com)"
  type        = string
  default     = "jablab.dev"
}

variable "certificate_services" {
  description = "List of services that need certificates"
  type        = list(string)
  default = [
    "content-collector",
    "content-processor",
    "site-generator"
  ]
}

variable "certificate_domains" {
  description = "Additional domains to include in certificates"
  type        = list(string)
  default     = ["jablab.dev"]
}

variable "dns_zones_resource_group" {
  description = "Resource group containing existing DNS zones (empty = use main resource group)"
  type        = string
  default     = ""
}

variable "jablab_dev_resource_group" {
  description = "Resource group for jablab.dev DNS zone"
  type        = string
  default     = "jabr_personal"
}

# User access configuration
variable "developer_email" {
  description = "Developer email for blob storage access"
  type        = string
  default     = "j.brewster_outlook.com#EXT#@jbrewster.onmicrosoft.com"
}

variable "developer_object_id" {
  description = "Developer Azure AD object ID for blob storage access"
  type        = string
  default     = "e96077a7-82ec-4be0-86d5-ac85fdec6312"
}

variable "developer_ip" {
  description = "Developer static IP for storage account access"
  type        = string
  default     = "81.2.90.47"
}
