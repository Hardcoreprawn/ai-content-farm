# Azure Functions for Pipeline Orchestration
# Replaces Logic App with more cost-effective, Terraform-friendly solution

# Function App for pipeline orchestration
resource "azurerm_service_plan" "pipeline_functions" {
  name                = "${var.resource_prefix}-pipeline-functions"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  os_type             = "Linux"
  sku_name            = "Y1" # Consumption plan - cost effective

  tags = merge(local.common_tags, {
    Purpose    = "pipeline-orchestration"
    CostCenter = "functions"
  })
}

resource "azurerm_linux_function_app" "pipeline_orchestrator" {
  name                = "${var.resource_prefix}-pipeline"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location

  storage_account_name       = azurerm_storage_account.main.name
  storage_account_access_key = azurerm_storage_account.main.primary_access_key
  service_plan_id            = azurerm_service_plan.pipeline_functions.id

  # Use system-assigned managed identity
  identity {
    type = "SystemAssigned"
  }

  site_config {
    application_stack {
      python_version = "3.11"
    }

    # Security configurations
    ftps_state          = "Disabled"
    http2_enabled       = true
    minimum_tls_version = "1.2"
    use_32_bit_worker   = false
  }

  app_settings = {
    "FUNCTIONS_WORKER_RUNTIME" = "python"
    "AzureWebJobsFeatureFlags" = "EnableWorkerIndexing"
    "WEBSITE_RUN_FROM_PACKAGE" = "1"
    "SERVICE_BUS_NAMESPACE"    = azurerm_servicebus_namespace.main.name
    "AZURE_CLIENT_ID"          = azurerm_user_assigned_identity.containers.client_id
  }

  tags = local.common_tags
}

# Grant Function App permissions to send Service Bus messages
resource "azurerm_role_assignment" "functions_servicebus_sender" {
  scope                = azurerm_servicebus_namespace.main.id
  role_definition_name = "Azure Service Bus Data Sender"
  principal_id         = azurerm_linux_function_app.pipeline_orchestrator.identity[0].principal_id
}

# Event Grid subscription for blob events → Function
resource "azurerm_eventgrid_event_subscription" "blob_to_function" {
  name  = "${var.resource_prefix}-blob-to-pipeline"
  scope = azurerm_storage_account.main.id

  azure_function_endpoint {
    function_id                       = azurerm_linux_function_app.pipeline_orchestrator.id
    max_events_per_batch              = 1
    preferred_batch_size_in_kilobytes = 64
  }

  included_event_types = [
    "Microsoft.Storage.BlobCreated"
  ]

  subject_filter {
    subject_begins_with = "/blobServices/default/containers/collected-content/"
    subject_ends_with   = ".json"
  }
}

# Timer-triggered function for scheduled collection (replaces Logic App)
# This will be implemented in the function code with a timer trigger
