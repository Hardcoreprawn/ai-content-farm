variable "location" {
  description = "Azure region to deploy resources."
  default     = "westeurope"
}

# Test 5: Full pipeline test - comprehensive change (2025-08-12T11:10:30Z)

variable "subscription_id" {
  description = "The Azure Subscription ID to use. Leave blank to use the default from Azure CLI context."
  type        = string
  default     = "6b924609-f8c6-4bd2-a873-2b8f55596f67"
}

variable "environment" {
  description = "Environment name (staging, production)"
  type        = string
  default     = "staging"
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "Environment must be staging or production."
  }
}

variable "github_repository" {
  description = "GitHub repository in the format owner/repo"
  type        = string
  default     = "Hardcoreprawn/ai-content-farm"
}

variable "resource_prefix" {
  description = "Prefix for all resource names. If empty, defaults to 'ai-content-{environment}'"
  type        = string
  default     = ""
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

variable "cost_alert_email" {
  description = "Email address for cost alerts and budget notifications"
  type        = string
  default     = ""
  sensitive   = false
}

variable "admin_user_object_id" {
  description = "Azure AD Object ID of the admin user who should have storage access"
  type        = string
  default     = "e96077a7-82ec-4be0-86d5-ac85fdec6312"
}

variable "github_actions_client_id" {
  description = "GitHub Actions Azure Client ID (from bootstrap output)"
  type        = string
  default     = ""
}

variable "github_actions_object_id" {
  description = "GitHub Actions service principal object ID for Key Vault access"
  type        = string
  default     = ""
}

variable "function_package_url" {
  description = "URL to function deployment package in blob storage"
  type        = string
  default     = ""
}

variable "function_package_path" {
  description = "Local path to function deployment zip file"
  type        = string
  default     = ""
}
