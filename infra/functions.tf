# Azure Functions for Event-Driven Processing
# Static Site Deployment Function
# Updated: Security fixes applied to Function App code

# Storage Account for Function App (separate from main storage for isolation)
resource "azurerm_storage_account" "functions" {
  name                     = "${local.clean_prefix}func${random_string.suffix.result}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"

  # Security configurations
  allow_nested_items_to_be_public = false
  shared_access_key_enabled       = true

  tags = merge(local.common_tags, {
    Service = "functions"
    Purpose = "event-processing"
  })
}

# App Service Plan for Functions (Consumption Plan)
resource "azurerm_service_plan" "functions" {
  name                = "${var.resource_prefix}-functions-plan"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  os_type             = "Linux"
  sku_name            = "Y1" # Consumption plan

  tags = local.common_tags
}

# Function App for Static Site Deployment
resource "azurerm_linux_function_app" "static_site_deployer" {
  name                = "${var.resource_prefix}-static-deployer"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  service_plan_id            = azurerm_service_plan.functions.id
  storage_account_name       = azurerm_storage_account.functions.name
  storage_account_access_key = azurerm_storage_account.functions.primary_access_key

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.functions.id]
  }

  site_config {
    application_stack {
      python_version = "3.11"
    }

    # Enable CORS for local testing
    cors {
      allowed_origins = ["https://portal.azure.com"]
    }
  }

  app_settings = {
    "WEBSITE_RUN_FROM_PACKAGE"    = "1"
    "FUNCTIONS_EXTENSION_VERSION" = "~4"
    "FUNCTIONS_WORKER_RUNTIME"    = "python"

    # Static Web App Configuration
    "STATIC_WEB_APP_ID"     = azurerm_static_web_app.jablab.id
    "STATIC_WEB_APP_NAME"   = azurerm_static_web_app.jablab.name
    "RESOURCE_GROUP_NAME"   = azurerm_resource_group.main.name
    "AZURE_SUBSCRIPTION_ID" = data.azurerm_client_config.current.subscription_id

    # Storage Configuration
    "STORAGE_ACCOUNT_URL"    = azurerm_storage_account.main.primary_blob_endpoint
    "AzureWebJobsStorage"    = azurerm_storage_account.main.primary_connection_string
    "STATIC_SITES_CONTAINER" = "static-sites"

    # Azure Configuration
    "AZURE_CLIENT_ID" = azurerm_user_assigned_identity.functions.client_id
    "AZURE_TENANT_ID" = data.azurerm_client_config.current.tenant_id

    # Environment
    "ENVIRONMENT" = var.environment
  }

  tags = merge(local.common_tags, {
    Service = "static-site-deployment"
    Purpose = "blob-triggered-deployment"
  })

  depends_on = [
    azurerm_static_web_app.jablab,
    azurerm_storage_account.main,
    azurerm_user_assigned_identity.functions
  ]
}

# User-assigned identity for Functions
resource "azurerm_user_assigned_identity" "functions" {
  location            = azurerm_resource_group.main.location
  name                = "${var.resource_prefix}-functions-identity"
  resource_group_name = azurerm_resource_group.main.name

  tags = local.common_tags
}

# Grant Functions identity access to main storage account (to read blobs)
resource "azurerm_role_assignment" "functions_storage_blob_data_reader" {
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azurerm_user_assigned_identity.functions.principal_id
}

# Grant Functions identity access to Static Web App (for deployment)
# Using Contributor role which provides necessary permissions for Static Web App management
resource "azurerm_role_assignment" "functions_static_web_app_contributor" {
  scope                = azurerm_static_web_app.jablab.id
  role_definition_name = "Contributor"
  principal_id         = azurerm_user_assigned_identity.functions.principal_id
}

# Grant Functions identity access to resource group (for Static Web App management)
resource "azurerm_role_assignment" "functions_resource_group_contributor" {
  scope                = azurerm_resource_group.main.id
  role_definition_name = "Contributor"
  principal_id         = azurerm_user_assigned_identity.functions.principal_id
}
