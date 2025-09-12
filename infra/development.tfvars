# Development environment configuration for PKI testing
environment     = "development"
resource_prefix = "ai-content-dev"

# PKI Configuration
enable_pki        = true
primary_domain    = "jablab.dev"
certificate_email = "dev@jablab.dev"

# Services that need certificates
certificate_services = [
  "content-collector",
  "content-processor",
  "site-generator"
]

# DNS Configuration
jablab_dev_resource_group = "jabr_personal"

# KEDA and mTLS integration
enable_keda = true
enable_mtls = true

# Development-specific settings
location          = "uksouth"
test_feature_flag = true
