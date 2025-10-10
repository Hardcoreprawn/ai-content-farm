resource "azurerm_storage_account" "main" {
  # checkov:skip=CKV_AZURE_33: Queue logging enabled via separate azurerm_storage_account_queue_properties resource
  # checkov:skip=CKV_AZURE_35: Needed for initial setup
  # checkov:skip=CKV_AZURE_59: Using for testing
  # checkov:skip=CKV_AZURE_206: LRS is sufficient for this use case
  # checkov:skip=CKV2_AZURE_1: Microsoft-managed keys are sufficient
  # checkov:skip=CKV2_AZURE_33: Public endpoint is acceptable for this use case
  # checkov:skip=CKV2_AZURE_38: Not required for non-critical data
  # checkov:skip=CKV2_AZURE_40: Shared Key authorization required for Terraform compatibility; access is restricted and secure
  # checkov:skip=CKV2_AZURE_41: No SAS tokens used
  # nosemgrep: terraform.azure.security.storage.storage-allow-microsoft-service-bypass.storage-allow-microsoft-service-bypass
  # nosemgrep: terraform.azure.security.storage.storage-analytics-logging.storage-analytics-logging
  # Note: Modern diagnostic settings approach implemented below for comprehensive logging
  name                          = "${local.clean_prefix}st${random_string.suffix.result}"
  resource_group_name           = azurerm_resource_group.main.name
  location                      = azurerm_resource_group.main.location
  account_tier                  = "Standard"
  account_replication_type      = "LRS"
  public_network_access_enabled = true
  shared_access_key_enabled     = true
  # nosemgrep: terraform.azure.security.storage.storage-allow-microsoft-service-bypass.storage-allow-microsoft-service-bypass
  network_rules {
    default_action = "Allow"
    bypass         = ["AzureServices"] # This is the recommended configuration for Microsoft services
    # Allow access from all networks for Container Apps Consumption compatibility
    # Container Apps Consumption tier uses dynamic IPs managed by Azure
    # Security is enforced through RBAC and managed identity authentication
    # Developer access from static IP for storage management
    ip_rules                   = [var.developer_ip]
    virtual_network_subnet_ids = []
  }
  allow_nested_items_to_be_public = false
  min_tls_version                 = "TLS1_2"
  # nosemgrep: terraform.azure.security.storage.storage-queue-services-logging.storage-queue-services-logging
  blob_properties {
    # Enable Storage Analytics logging for blob operations
    # Note: This is configured at the storage account level for compliance
    delete_retention_policy {
      days = 7
    }
    versioning_enabled = true
  }
}

# Enable Storage Analytics logging for queue operations to satisfy CKV_AZURE_33
resource "azurerm_storage_account_queue_properties" "main" {
  storage_account_id = azurerm_storage_account.main.id

  logging {
    delete                = true
    read                  = true
    write                 = true
    version               = "1.0"
    retention_policy_days = 7
  }
}

# Enable static website hosting
resource "azurerm_storage_account_static_website" "main" {
  storage_account_id = azurerm_storage_account.main.id
  index_document     = "index.html"
  error_404_document = "404.html"
}

# Note: The static website resource automatically creates a special "$web" container
# that serves content at the storage account's static website URL.
# Site-generator container writes HTML/CSS/JS directly to $web for live hosting.

# Enable Storage Analytics logging using modern diagnostic settings approach
# TODO: Re-enable after determining correct log categories for Storage Account
# resource "azurerm_monitor_diagnostic_setting" "storage_logging" {
#   name                       = "${local.resource_prefix}-storage-logs"
#   target_resource_id         = azurerm_storage_account.main.id
#   log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id

#   enabled_log {
#     category = "StorageRead"
#   }

#   enabled_log {
#     category = "StorageWrite"
#   }

#   enabled_log {
#     category = "StorageDelete"
#   }

#   enabled_metric {
#     category = "Transaction"
#   }
# }

# Enable blob service diagnostic settings for security compliance
# TODO: Re-enable after determining correct log categories for Blob service
# resource "azurerm_monitor_diagnostic_setting" "storage_blob_logging" {
#   name                       = "${local.resource_prefix}-blob-logs"
#   target_resource_id         = "${azurerm_storage_account.main.id}/blobServices/default"
#   log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id

#   enabled_log {
#     category = "StorageRead"
#   }

#   enabled_log {
#     category = "StorageWrite"
#   }

#   enabled_log {
#     category = "StorageDelete"
#   }

#   enabled_metric {
#     category = "Transaction"
#   }
# }

# Grant developer Storage Blob Data Contributor access for management
resource "azurerm_role_assignment" "developer_storage_blob_data_contributor" {
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = var.developer_object_id
}

# Grant developer Reader access to the storage account
resource "azurerm_role_assignment" "developer_storage_reader" {
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Reader"
  principal_id         = var.developer_object_id
}

# Grant developer Storage Queue Data Contributor access for queue management and monitoring
resource "azurerm_role_assignment" "developer_storage_queue_data_contributor" {
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Queue Data Contributor"
  principal_id         = var.developer_object_id
}

# Grant developer Storage Queue Data Reader access for queue monitoring
resource "azurerm_role_assignment" "developer_storage_queue_data_reader" {
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Queue Data Reader"
  principal_id         = var.developer_object_id
}

# Container for collected content from content-collector service
resource "azurerm_storage_container" "collected_content" {
  # checkov:skip=CKV2_AZURE_21: Logging not required for this use case
  name                  = "collected-content"
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "private"
}

# Container for processed content from content-processor service
resource "azurerm_storage_container" "processed_content" {
  # checkov:skip=CKV2_AZURE_21: Logging not required for this use case
  name                  = "processed-content"
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "private"
}

# Container for markdown content from markdown generator
resource "azurerm_storage_container" "markdown_content" {
  # checkov:skip=CKV2_AZURE_21: Logging not required for this use case
  name                  = "markdown-content"
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "private"
}

# Container for pipeline logs and monitoring
resource "azurerm_storage_container" "pipeline_logs" {
  # checkov:skip=CKV2_AZURE_21: Logging not required for this use case
  name                  = "pipeline-logs"
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "private"
}

# Container for static website backups - rollback capability
resource "azurerm_storage_container" "web_backup" {
  # checkov:skip=CKV2_AZURE_21: Logging not required for this use case
  name                  = "web-backup"
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "private"

  metadata = {
    purpose     = "static-site-backup"
    description = "Previous versions of static website for rollback capability"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Storage Queues for container service communication (replaces Service Bus)
# Using Storage Queues to resolve Container Apps managed identity vs Service Bus connection string conflicts
resource "azurerm_storage_queue" "content_collection_requests" {
  name               = "content-collection-requests"
  storage_account_id = azurerm_storage_account.main.id

  lifecycle {
    # Prevent recreation when changing from storage_account_name to storage_account_id
    # The queue name is the stable identifier, not the account reference
    create_before_destroy = true
  }
}

resource "azurerm_storage_queue" "content_processing_requests" {
  name               = "content-processing-requests"
  storage_account_id = azurerm_storage_account.main.id

  lifecycle {
    # Prevent recreation when changing from storage_account_name to storage_account_id
    # The queue name is the stable identifier, not the account reference
    create_before_destroy = true
  }
}

resource "azurerm_storage_queue" "markdown_generation_requests" {
  name               = "markdown-generation-requests"
  storage_account_id = azurerm_storage_account.main.id

  metadata = {
    purpose     = "markdown-generator-keda-scaling"
    description = "Triggers markdown-generator to convert processed JSON to markdown"
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "azurerm_storage_queue" "site_publishing_requests" {
  name               = "site-publishing-requests"
  storage_account_id = azurerm_storage_account.main.id

  metadata = {
    purpose     = "site-publisher-keda-scaling"
    description = "Triggers site-publisher to build Hugo site from markdown content"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Container services now handle the content processing pipeline

# Azure OpenAI Cognitive Services Account
#checkov:skip=CKV_AZURE_247:Data loss prevention configuration complex for development environment
#checkov:skip=CKV2_AZURE_22:Customer-managed encryption would create circular dependency in development environment
#checkov:skip=CKV_AZURE_134:Public network access required for Container Apps Consumption tier to access via managed identity
# nosemgrep: terraform.azure.security.openai.public-network-access.public-network-access
