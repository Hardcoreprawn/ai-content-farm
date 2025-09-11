# Certificate Management Infrastructure for mTLS
# Implements Let's Encrypt integration with DNS-01 challenges for automated certificate issuance

# User Assigned Identity for Certificate Management
resource "azurerm_user_assigned_identity" "cert_manager" {
  name                = "${var.resource_prefix}-cert-manager"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name

  tags = merge(local.common_tags, {
    Purpose = "certificate-management"
    Service = "acme-letsencrypt"
  })
}

# Grant Certificate Manager identity access to DNS Zone for DNS-01 challenges
resource "azurerm_role_assignment" "cert_manager_dns_contributor" {
  scope                = azurerm_dns_zone.jablab.id
  role_definition_name = "DNS Zone Contributor"
  principal_id         = azurerm_user_assigned_identity.cert_manager.principal_id
}

# Grant Certificate Manager identity access to Key Vault for certificate storage
resource "azurerm_key_vault_access_policy" "cert_manager" {
  key_vault_id = azurerm_key_vault.main.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = azurerm_user_assigned_identity.cert_manager.principal_id

  certificate_permissions = [
    "Create",
    "Delete",
    "Get",
    "Import",
    "List",
    "Update",
    "ManageContacts",
    "ManageIssuers",
    "SetIssuers",
    "ListIssuers",
    "DeleteIssuers"
  ]

  secret_permissions = [
    "Get",
    "List",
    "Set",
    "Delete"
  ]

  depends_on = [azurerm_user_assigned_identity.cert_manager]
}

# Storage Account for ACME account information and certificate metadata
resource "azurerm_storage_container" "acme_accounts" {
  name                  = "acme-accounts"
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "private"
}

resource "azurerm_storage_container" "certificate_metadata" {
  name                  = "certificate-metadata"
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "private"
}

# Grant Certificate Manager identity access to certificate storage containers
resource "azurerm_role_assignment" "cert_manager_storage" {
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.cert_manager.principal_id
}

# Key Vault secret for ACME directory URL (Let's Encrypt production)
resource "azurerm_key_vault_secret" "acme_directory_url" {
  name         = "acme-directory-url"
  value        = "https://acme-v02.api.letsencrypt.org/directory"
  key_vault_id = azurerm_key_vault.main.id
  content_type = "text/plain"

  tags = merge(local.common_tags, {
    Purpose = "acme-configuration"
    Service = "letsencrypt"
  })

  depends_on = [
    azurerm_key_vault_access_policy.cert_manager
  ]
}

# Key Vault secret for certificate email contact
resource "azurerm_key_vault_secret" "certificate_email" {
  name         = "certificate-email"
  value        = var.certificate_email != "" ? var.certificate_email : "admin@jablab.com"
  key_vault_id = azurerm_key_vault.main.id
  content_type = "text/plain"

  lifecycle {
    ignore_changes = [value] # Allow manual updates
  }

  tags = merge(local.common_tags, {
    Purpose = "certificate-contact"
  })

  depends_on = [
    azurerm_key_vault_access_policy.cert_manager
  ]
}

# Service domains for certificate generation
locals {
  service_domains = [
    "api.${azurerm_dns_zone.jablab.name}",
    "collector.${azurerm_dns_zone.jablab.name}",
    "processor.${azurerm_dns_zone.jablab.name}",
    "generator.${azurerm_dns_zone.jablab.name}",
    "admin.${azurerm_dns_zone.jablab.name}"
  ]
}

# DNS TXT records for ACME challenges (placeholders)
# These will be dynamically managed by the certificate automation
resource "azurerm_dns_txt_record" "acme_challenge" {
  for_each = toset(local.service_domains)

  name                = "_acme-challenge.${split(".", each.value)[0]}"
  zone_name           = azurerm_dns_zone.jablab.name
  resource_group_name = azurerm_resource_group.main.name
  ttl                 = 60

  record {
    value = "placeholder-will-be-updated-by-acme-client"
  }

  tags = merge(local.common_tags, {
    Purpose = "acme-dns01-challenge"
    Domain  = each.value
  })

  lifecycle {
    ignore_changes = [record] # ACME client will update these
  }
}

# DNS A records for service domains pointing to Container Apps
resource "azurerm_dns_a_record" "service_api" {
  name                = "api"
  zone_name           = azurerm_dns_zone.jablab.name
  resource_group_name = azurerm_resource_group.main.name
  ttl                 = 300
  records             = [azurerm_container_app.content_collector.latest_revision_fqdn] # Will be updated post-deployment

  tags = merge(local.common_tags, {
    Service = "api-gateway"
    Purpose = "service-discovery"
  })

  lifecycle {
    ignore_changes = [records] # Will be managed by service discovery automation
  }

  depends_on = [azurerm_container_app.content_collector]
}

# Log Analytics query for certificate expiration monitoring
resource "azurerm_log_analytics_saved_search" "certificate_expiration" {
  name                       = "CertificateExpirationMonitoring"
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  category                   = "Certificate Management"
  display_name               = "Certificate Expiration Monitoring"

  query = <<-EOT
    AzureDiagnostics
    | where ResourceType == "VAULTS"
    | where OperationName == "CertificateNearExpiry"
    | extend DaysUntilExpiry = toint(parse_json(properties_s).DaysUntilExpiry)
    | where DaysUntilExpiry <= 30
    | project TimeGenerated, Resource, DaysUntilExpiry, properties_s
    | order by DaysUntilExpiry asc
  EOT

  tags = local.common_tags
}