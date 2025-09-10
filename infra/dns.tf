# DNS Zone for mTLS certificate management
# Supports Let's Encrypt DNS-01 challenges for automated certificate issuance

resource "azurerm_dns_zone" "main" {
  name                = var.domain_name
  resource_group_name = azurerm_resource_group.main.name

  tags = merge(local.common_tags, {
    Purpose = "mtls-certificate-management"
  })
}

# DNS CNAME records for Container Apps with mTLS
resource "azurerm_dns_cname_record" "content_collector" {
  name                = "collector"
  zone_name           = azurerm_dns_zone.main.name
  resource_group_name = azurerm_resource_group.main.name
  ttl                 = 300
  record              = azurerm_container_app.content_collector.latest_revision_fqdn

  tags = local.common_tags
}

resource "azurerm_dns_cname_record" "content_processor" {
  name                = "processor"
  zone_name           = azurerm_dns_zone.main.name
  resource_group_name = azurerm_resource_group.main.name
  ttl                 = 300
  record              = azurerm_container_app.content_processor.latest_revision_fqdn

  tags = local.common_tags
}

resource "azurerm_dns_cname_record" "site_generator" {
  name                = "generator"
  zone_name           = azurerm_dns_zone.main.name
  resource_group_name = azurerm_resource_group.main.name
  ttl                 = 300
  record              = azurerm_container_app.site_generator.latest_revision_fqdn

  tags = local.common_tags
}

# Wildcard certificate for mTLS
resource "azurerm_key_vault_certificate" "mtls_wildcard" {
  name         = "mtls-wildcard-cert"
  key_vault_id = azurerm_key_vault.main.id

  certificate_policy {
    issuer_parameters {
      name = "Self"
    }

    key_properties {
      exportable = true
      key_size   = 2048
      key_type   = "RSA"
      reuse_key  = true
    }

    lifetime_action {
      action {
        action_type = "AutoRenew"
      }

      trigger {
        days_before_expiry = 30
      }
    }

    secret_properties {
      content_type = "application/x-pkcs12"
    }

    x509_certificate_properties {
      # Extended Key Usage
      extended_key_usage = ["1.3.6.1.5.5.7.3.1", "1.3.6.1.5.5.7.3.2"]

      key_usage = [
        "cRLSign",
        "dataEncipherment",
        "digitalSignature",
        "keyAgreement",
        "keyCertSign",
        "keyEncipherment",
      ]

      subject_alternative_names {
        dns_names = [
          "*.${var.domain_name}",
          var.domain_name,
          "collector.${var.domain_name}",
          "processor.${var.domain_name}",
          "generator.${var.domain_name}"
        ]
      }

      subject            = "CN=*.${var.domain_name}"
      validity_in_months = 12
    }
  }

  depends_on = [
    azurerm_key_vault_access_policy.github_actions,
    azurerm_role_assignment.containers_key_vault_secrets_user
  ]

  tags = merge(local.common_tags, {
    Purpose = "mtls-wildcard-certificate"
  })
}