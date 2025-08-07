variable "location" {
  description = "Azure region to deploy bootstrap resources"
  type        = string
  default     = "westeurope"
}

variable "subscription_id" {
  description = "Azure subscription ID"
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
  description = "GitHub repository in format owner/repo"
  type        = string
  default     = "Hardcoreprawn/ai-content-farm"
}
