variable "location" {
  description = "Azure region to deploy bootstrap resources"
  type        = string
  default     = "westeurope"
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
