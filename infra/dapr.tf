# Dapr Components for mTLS and Service Discovery
# These components enable secure communication between microservices

# Dapr Configuration for mTLS
resource "azurerm_container_app_environment_dapr_component" "mtls_config" {
  name                         = "mtls-config"
  container_app_environment_id = azurerm_container_app_environment.main.id
  component_type               = "configuration"
  version                      = "v1"

  metadata {
    name  = "enabled"
    value = "true"
  }

  metadata {
    name  = "mtls"
    value = "true"
  }

  metadata {
    name  = "sentryAddress"
    value = "dapr-sentry-service.dapr-system.svc.cluster.local:443"
  }

  metadata {
    name  = "controlPlaneAddress"
    value = "dapr-api.dapr-system.svc.cluster.local:80"
  }

  metadata {
    name  = "placementAddress"
    value = "dapr-placement-server.dapr-system.svc.cluster.local:50005"
  }
}

# State Store with mTLS support  
resource "azurerm_container_app_environment_dapr_component" "statestore" {
  name                         = "statestore"
  container_app_environment_id = azurerm_container_app_environment.main.id
  component_type               = "state.azure.blobstorage"
  version                      = "v1"

  metadata {
    name  = "accountName"
    value = azurerm_storage_account.main.name
  }

  metadata {
    name  = "containerName"
    value = "dapr-state"
  }

  metadata {
    name  = "azureClientId"
    value = azurerm_user_assigned_identity.containers.client_id
  }

  scopes = ["content-collector", "content-processor", "site-generator"]
}

# Pub/Sub component for inter-service communication
resource "azurerm_container_app_environment_dapr_component" "pubsub" {
  name                         = "pubsub"
  container_app_environment_id = azurerm_container_app_environment.main.id
  component_type               = "pubsub.azure.servicebus.topics"
  version                      = "v1"

  metadata {
    name  = "namespaceName"
    value = "${azurerm_servicebus_namespace.main.name}.servicebus.windows.net"
  }

  metadata {
    name  = "azureClientId"
    value = azurerm_user_assigned_identity.containers.client_id
  }

  scopes = ["content-collector", "content-processor", "site-generator"]
}

# Service Discovery component
resource "azurerm_container_app_environment_dapr_component" "service_discovery" {
  name                         = "service-discovery"
  container_app_environment_id = azurerm_container_app_environment.main.id
  component_type               = "nameresolution.mdns"
  version                      = "v1"

  metadata {
    name  = "domain"
    value = var.domain_name
  }

  scopes = ["content-collector", "content-processor", "site-generator"]
}

# Certificate Secret Store for mTLS certificates
resource "azurerm_container_app_environment_dapr_component" "certificates" {
  name                         = "certificates"
  container_app_environment_id = azurerm_container_app_environment.main.id
  component_type               = "secretstores.azure.keyvault"
  version                      = "v1"

  metadata {
    name  = "vaultName"
    value = azurerm_key_vault.main.name
  }

  metadata {
    name  = "azureClientId"
    value = azurerm_user_assigned_identity.containers.client_id
  }

  scopes = ["content-collector", "content-processor", "site-generator"]
}