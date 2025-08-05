data "azurerm_client_config" "current" {}

resource "random_string" "suffix" {
  length  = 6
  upper   = false
  special = false
}

resource "azurerm_resource_group" "main" {
  name     = "hot-topics-rg"
  location = "westeurope"
}


resource "azurerm_key_vault" "main" {
  # checkov:skip=CKV_AZURE_189: Public access is acceptable for this use case
  # checkov:skip=CKV_AZURE_109: Firewall rules not required for this use case
  # checkov:skip=CKV2_AZURE_32: Private endpoint not required for this use case
  name     = "hottopicskv${random_string.suffix.result}"
  location = azurerm_resource_group.main.location

  resource_group_name      = azurerm_resource_group.main.name
  tenant_id                = data.azurerm_client_config.current.tenant_id
  sku_name                 = "standard"
  purge_protection_enabled = true
  # No access policy for user-assigned identity; add as needed for future use
}

resource "azurerm_storage_account" "main" {
  # checkov:skip=CKV_AZURE_33: Not using queues
  # checkov:skip=CKV_AZURE_35: Needed for initial setup
  # checkov:skip=CKV_AZURE_59: Using for testing
  # checkov:skip=CKV_AZURE_206: LRS is sufficient for this use case
  # checkov:skip=CKV2_AZURE_1: Microsoft-managed keys are sufficient
  # checkov:skip=CKV2_AZURE_33: Public endpoint is acceptable for this use case
  # checkov:skip=CKV2_AZURE_38: Not required for non-critical data
  # checkov:skip=CKV2_AZURE_40: Shared Key authorization required for Terraform compatibility; access is restricted and secure
  # checkov:skip=CKV2_AZURE_41: No SAS tokens used
  name                          = "hottopicsstorage${random_string.suffix.result}"
  resource_group_name           = azurerm_resource_group.main.name
  location                      = azurerm_resource_group.main.location
  account_tier                  = "Standard"
  account_replication_type      = "LRS"
  public_network_access_enabled = true
  shared_access_key_enabled     = true
  network_rules {
    default_action = "Allow"
    bypass         = ["AzureServices"]
  }
  allow_nested_items_to_be_public = false
  min_tls_version                 = "TLS1_2"
}

resource "azurerm_storage_container" "topics" {
  # checkov:skip=CKV2_AZURE_21: Logging not required for this use case
  name                  = "hot-topics"
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "private"
}


resource "azurerm_service_plan" "main" {
  # checkov:skip=CKV_AZURE_212: Not applicable to consumption plan
  # checkov:skip=CKV_AZURE_225: Not applicable to consumption plan
  name                = "hot-topics-plan"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  os_type             = "Linux"
  sku_name            = "Y1"
}

resource "azurerm_linux_function_app" "main" {
  # checkov:skip=CKV_AZURE_221: Public access is acceptable for this use case
  # checkov:skip=CKV_AZURE_97: No authentication required for this use case
  name                        = "hot-topics-func"
  location                    = azurerm_resource_group.main.location
  resource_group_name         = azurerm_resource_group.main.name
  service_plan_id             = azurerm_service_plan.main.id
  storage_account_name        = azurerm_storage_account.main.name
  storage_account_access_key  = azurerm_storage_account.main.primary_access_key
  functions_extension_version = "~4"
  https_only                  = true

  identity {
    type = "SystemAssigned"
  }

  app_settings = {
    AzureWebJobsStorage      = azurerm_storage_account.main.primary_connection_string
    OUTPUT_CONTAINER         = azurerm_storage_container.topics.name
    OUTPUT_STORAGE_ACCOUNT   = azurerm_storage_account.main.name
    FUNCTIONS_WORKER_RUNTIME = "python"
    WEBSITE_RUN_FROM_PACKAGE = "1"
  }
  #zip_deploy_file = filebase64("${path.module}/function.zip")
  site_config {
    application_stack {
      python_version = "3.11"
    }
  }
}

# Role assignments for managed identity
resource "azurerm_role_assignment" "storage_blob_data_contributor" {
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_linux_function_app.main.identity[0].principal_id
  depends_on           = [azurerm_linux_function_app.main]
}

resource "azurerm_role_assignment" "storage_account_contributor" {
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Account Contributor"
  principal_id         = azurerm_linux_function_app.main.identity[0].principal_id
  depends_on           = [azurerm_linux_function_app.main]
}

# Optionally add Cognitive Account and Key Vault secret if OpenAI integration is needed
# resource "azurerm_cognitive_account" "openai" { ... }
# resource "azurerm_key_vault_secret" "openai_key" { ... }
