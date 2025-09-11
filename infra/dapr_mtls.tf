# Dapr mTLS Configuration for Azure Container Apps
# Implements mutual TLS for secure inter-service communication

# Dapr Configuration for mTLS
resource "azurerm_container_app_environment_dapr_component" "mtls_configuration" {
  name                         = "mtls-config"
  container_app_environment_id = azurerm_container_app_environment.main.id
  component_type               = "configuration"
  version                      = "v1"

  metadata {
    name  = "enableMTLS"
    value = var.enable_mtls ? "true" : "false"
  }

  metadata {
    name  = "allowedOrigins"
    value = "https://*.${azurerm_dns_zone.jablab.name}"
  }

  metadata {
    name  = "defaultAction"
    value = "allow"
  }

  # Certificate configuration from Key Vault
  metadata {
    name  = "certificateStore"
    value = "keyvault"
  }

  metadata {
    name  = "keyVaultName"
    value = azurerm_key_vault.main.name
  }

  # Scope to all services in the environment
  scopes = ["*"]

  depends_on = [
    azurerm_key_vault.main,
    azurerm_container_app_environment.main
  ]
}

# Dapr Access Control Configuration
resource "azurerm_container_app_environment_dapr_component" "access_control" {
  name                         = "access-control"
  container_app_environment_id = azurerm_container_app_environment.main.id
  component_type               = "middleware.http.oauth2"
  version                      = "v1"

  metadata {
    name  = "enableAccessControl"
    value = "true"
  }

  metadata {
    name  = "defaultAction"
    value = "deny"
  }

  metadata {
    name  = "trustDomain"
    value = azurerm_dns_zone.jablab.name
  }

  # Service-specific access policies
  metadata {
    name = "policies"
    value = jsonencode([
      {
        "appId" : "content-collector",
        "defaultAction" : "allow",
        "trustDomain" : azurerm_dns_zone.jablab.name,
        "namespace" : "default"
      },
      {
        "appId" : "content-processor",
        "defaultAction" : "allow",
        "trustDomain" : azurerm_dns_zone.jablab.name,
        "namespace" : "default"
      },
      {
        "appId" : "site-generator",
        "defaultAction" : "allow",
        "trustDomain" : azurerm_dns_zone.jablab.name,
        "namespace" : "default"
      }
    ])
  }

  scopes = ["*"]

  depends_on = [
    azurerm_container_app_environment.main
  ]
}

# Service-to-Service mTLS policy configuration
resource "azurerm_container_app_environment_dapr_component" "service_mesh_policy" {
  name                         = "service-mesh-policy"
  container_app_environment_id = azurerm_container_app_environment.main.id
  component_type               = "middleware.http.ratelimit"
  version                      = "v1"

  metadata {
    name  = "enableServiceMesh"
    value = "true"
  }

  metadata {
    name  = "mtlsMode"
    value = "strict"
  }

  metadata {
    name  = "certificateLifetime"
    value = "24h"
  }

  metadata {
    name  = "certificateRenewalThreshold"
    value = "6h"
  }

  # Certificate rotation configuration
  metadata {
    name  = "autoRotateCertificates"
    value = "true"
  }

  metadata {
    name  = "certificateProvider"
    value = "keyvault"
  }

  scopes = ["content-collector", "content-processor", "site-generator"]

  depends_on = [
    azurerm_key_vault.main
  ]
}

# Key Vault secret for Dapr mTLS trust root certificate
resource "azurerm_key_vault_secret" "dapr_trust_root" {
  name         = "dapr-trust-root-cert"
  value        = "placeholder-will-be-updated-by-certificate-automation"
  key_vault_id = azurerm_key_vault.main.id
  content_type = "application/x-pem-file"

  lifecycle {
    ignore_changes = [value] # Will be managed by certificate automation
  }

  tags = merge(local.common_tags, {
    Purpose = "dapr-mtls-trust-root"
    Service = "service-mesh"
  })

  depends_on = [
    azurerm_key_vault_access_policy.cert_manager
  ]
}

# Dapr Sidecar configuration for Container Apps
locals {
  dapr_sidecar_config = {
    enabled            = var.enable_mtls
    app_id             = null # Will be set per container app
    app_port           = 8000
    app_protocol       = "http"
    enable_api_logging = true
    log_level          = "info"

    # mTLS Configuration
    mtls = {
      enabled           = var.enable_mtls
      workload_cert_ttl = "24h"
      allow_insecure    = false
      trust_domain      = azurerm_dns_zone.jablab.name
    }

    # Service discovery
    name_resolution = {
      component = "mdns"
      version   = "v1"
      configuration = {
        addresses = ["api.${azurerm_dns_zone.jablab.name}:443"]
      }
    }
  }
}

# Update Container Apps with Dapr sidecar configuration
# This will be applied to existing container apps in container_apps.tf