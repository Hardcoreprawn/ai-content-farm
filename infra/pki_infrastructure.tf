# Azure PKI Infrastructure for mTLS
# Manages Let's Encrypt certificates via ACME and stores them in Azure Key Vault
# Integrates with existing infrastructure in main.tf

# Import existing DNS Zones (don't create new ones)
data "azurerm_dns_zone" "jablab_dev" {
  count               = var.enable_pki ? 1 : 0
  name                = "jablab.dev"
  resource_group_name = var.jablab_dev_resource_group
}

# Key Vault for certificate storage (extends existing Key Vault)
resource "azurerm_key_vault_access_policy" "pki_certificates" {
  count        = var.enable_pki ? 1 : 0
  key_vault_id = azurerm_key_vault.main.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = data.azurerm_client_config.current.object_id

  certificate_permissions = [
    "Backup", "Create", "Delete", "DeleteIssuers", "Get", "GetIssuers",
    "Import", "List", "ListIssuers", "ManageContacts", "ManageIssuers",
    "Purge", "Recover", "Restore", "SetIssuers", "Update"
  ]

  key_permissions = [
    "Backup", "Create", "Decrypt", "Delete", "Encrypt", "Get", "Import",
    "List", "Purge", "Recover", "Restore", "Sign", "UnwrapKey", "Update",
    "Verify", "WrapKey"
  ]

  secret_permissions = [
    "Backup", "Delete", "Get", "List", "Purge", "Recover", "Restore", "Set"
  ]
}

# Access policy for Container Apps managed identity
resource "azurerm_key_vault_access_policy" "containers_pki" {
  count        = var.enable_pki ? 1 : 0
  key_vault_id = azurerm_key_vault.main.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = azurerm_user_assigned_identity.containers.principal_id

  certificate_permissions = [
    "Get", "List"
  ]

  secret_permissions = [
    "Get", "List"
  ]
}

# Storage account for ACME challenge files (if needed for HTTP-01 challenges)
resource "azurerm_storage_account" "acme_challenges" {
  count                    = var.enable_pki ? 1 : 0
  name                     = "${local.clean_prefix}acme${random_string.suffix.result}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  # Using DNS-01 challenges, so no static website needed

  tags = local.common_tags
}

# Private key for ACME account
resource "tls_private_key" "acme_account" {
  count     = var.enable_pki ? 1 : 0
  algorithm = "RSA"
  rsa_bits  = 4096
}

# ACME registration
resource "acme_registration" "account" {
  count           = var.enable_pki ? 1 : 0
  account_key_pem = tls_private_key.acme_account[0].private_key_pem
  email_address   = var.certificate_email
}

# DNS Challenge provider configuration for Azure DNS
locals {
  pki_dns_challenge_config = var.enable_pki ? {
    provider = "azuredns"
    config = {
      AZURE_CLIENT_ID       = data.azurerm_client_config.current.client_id
      AZURE_SUBSCRIPTION_ID = data.azurerm_client_config.current.subscription_id
      AZURE_TENANT_ID       = data.azurerm_client_config.current.tenant_id
      AZURE_RESOURCE_GROUP  = azurerm_resource_group.main.name
    }
    } : {
    provider = "none"
    config   = {}
  }
}

# Generate certificates for each service
resource "tls_private_key" "service_keys" {
  for_each  = var.enable_pki ? toset(var.certificate_services) : []
  algorithm = "RSA"
  rsa_bits  = 2048
}

resource "acme_certificate" "service_certificates" {
  for_each                = var.enable_pki ? toset(var.certificate_services) : []
  account_key_pem         = acme_registration.account[0].account_key_pem
  certificate_request_pem = tls_cert_request.service_csr[each.key].cert_request_pem
  min_days_remaining      = 30

  dns_challenge {
    provider = "azuredns"
    config = {
      AZURE_CLIENT_ID       = data.azurerm_client_config.current.client_id
      AZURE_SUBSCRIPTION_ID = data.azurerm_client_config.current.subscription_id
      AZURE_TENANT_ID       = data.azurerm_client_config.current.tenant_id
      AZURE_RESOURCE_GROUP  = azurerm_resource_group.main.name
    }
  }

  depends_on = [data.azurerm_dns_zone.jablab_dev]
}

# Certificate signing requests for each service
resource "tls_cert_request" "service_csr" {
  for_each        = var.enable_pki ? toset(var.certificate_services) : []
  private_key_pem = tls_private_key.service_keys[each.key].private_key_pem

  subject {
    common_name  = "${each.key}.jablab.dev"
    organization = "AI Content Farm"
  }

  dns_names = [
    "${each.key}.jablab.dev"
  ]
}

# Store certificates in existing Key Vault
resource "azurerm_key_vault_certificate" "service_certificates" {
  for_each     = var.enable_pki ? toset(var.certificate_services) : []
  name         = "${each.key}-certificate"
  key_vault_id = azurerm_key_vault.main.id

  certificate {
    contents = acme_certificate.service_certificates[each.key].certificate_pem
    password = ""
  }

  certificate_policy {
    issuer_parameters {
      name = "Unknown"
    }

    key_properties {
      exportable = true
      key_size   = 2048
      key_type   = "RSA"
      reuse_key  = false
    }

    secret_properties {
      content_type = "application/x-pkcs12"
    }
  }

  tags = local.common_tags

  depends_on = [azurerm_key_vault_access_policy.pki_certificates]
}

# Store private keys as secrets in existing Key Vault
resource "azurerm_key_vault_secret" "service_private_keys" {
  for_each     = var.enable_pki ? toset(var.certificate_services) : []
  name         = "${each.key}-private-key"
  value        = tls_private_key.service_keys[each.key].private_key_pem
  key_vault_id = azurerm_key_vault.main.id

  tags = local.common_tags

  depends_on = [azurerm_key_vault_access_policy.pki_certificates]
}

# DNS A records for services
resource "azurerm_dns_a_record" "service_records_dev" {
  for_each            = var.enable_pki ? toset(var.certificate_services) : []
  name                = each.key
  zone_name           = data.azurerm_dns_zone.jablab_dev[0].name
  resource_group_name = data.azurerm_dns_zone.jablab_dev[0].resource_group_name
  ttl                 = 300

  # This will point to the Container Apps environment ingress IP
  # You'll need to update this with the actual IP after Container Apps deployment
  records = ["20.108.146.58"] # Placeholder - update with actual Container Apps IP

  tags = local.common_tags
}

# Certificate renewal automation using Logic Apps
resource "azurerm_logic_app_workflow" "certificate_renewal" {
  count               = var.enable_pki ? 1 : 0
  name                = "${local.resource_prefix}-cert-renewal"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name

  tags = local.common_tags
}

# Logic App trigger for certificate renewal (monthly check)
resource "azurerm_logic_app_trigger_recurrence" "monthly_check" {
  count        = var.enable_pki ? 1 : 0
  name         = "monthly-certificate-check"
  logic_app_id = azurerm_logic_app_workflow.certificate_renewal[0].id
  frequency    = "Month"
  interval     = 1
}

# Output certificate information
output "pki_certificate_key_vault_url" {
  description = "URL of the Key Vault containing certificates"
  value       = var.enable_pki ? azurerm_key_vault.main.vault_uri : null
}

output "pki_service_certificate_names" {
  description = "Names of certificates in Key Vault"
  value       = var.enable_pki ? [for service in var.certificate_services : "${service}-certificate"] : []
}

output "pki_acme_account_url" {
  description = "ACME account URL"
  value       = var.enable_pki ? acme_registration.account[0].registration_url : null
  sensitive   = true
}
