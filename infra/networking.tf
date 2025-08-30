# Virtual Network infrastructure for secure Container Apps deployment
# Using service endpoints instead of private endpoints for cost optimization
# Service endpoints provide secure access to Azure services at no additional cost
# Trigger pipeline: Test subnet delegation and Key Vault access fixes

# Virtual Network for Container Apps
resource "azurerm_virtual_network" "main" {
  name                = "${var.resource_prefix}-vnet"
  address_space       = ["10.0.0.0/16"]
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name

  tags = local.common_tags
}

# Subnet for Container Apps Environment
# Container Apps require a /21 or larger subnet (minimum 2048 addresses)
resource "azurerm_subnet" "container_apps" {
  name                 = "${var.resource_prefix}-container-apps-subnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.0.0/21"] # Provides 2048 addresses (10.0.0.1 - 10.0.7.254)

  # Enable service endpoints for Azure services (cost-effective alternative to private endpoints)
  service_endpoints = [
    "Microsoft.Storage",
    "Microsoft.KeyVault",
    "Microsoft.CognitiveServices"
  ]

  # Note: Do NOT delegate subnet for Consumption-only Container Apps environments
  # Delegation is only required for Workload profiles environments
}

# Network Security Group for Container Apps subnet
resource "azurerm_network_security_group" "container_apps" {
  name                = "${var.resource_prefix}-container-apps-nsg"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name

  # Allow inbound HTTPS traffic
  security_rule {
    name                       = "AllowHTTPS"
    priority                   = 1000
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  # Allow inbound HTTP traffic
  security_rule {
    name                       = "AllowHTTP"
    priority                   = 1001
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "80"
    destination_address_prefix = "*"
    source_address_prefix      = "*"
  }

  # Allow outbound traffic to Azure services
  security_rule {
    name                       = "AllowAzureServices"
    priority                   = 1000
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "AzureCloud"
  }

  # Allow outbound HTTPS for external APIs
  security_rule {
    name                       = "AllowOutboundHTTPS"
    priority                   = 1001
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  tags = local.common_tags
}

# Associate NSG with Container Apps subnet
resource "azurerm_subnet_network_security_group_association" "container_apps" {
  subnet_id                 = azurerm_subnet.container_apps.id
  network_security_group_id = azurerm_network_security_group.container_apps.id
}
