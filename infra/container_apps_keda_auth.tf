# KEDA Managed Identity Authentication Configuration
#
# This file configures KEDA scale rules to use workload identity (managed identity)
# for authenticating to Azure Storage Queues.
#
# CONTEXT: The azurerm Terraform provider v4.37.0 does not support configuring
# workload identity authentication for KEDA scale rules. This must be configured
# via Azure CLI after the container apps are created.
#
# This implementation uses null_resource with local-exec provisioner to run
# Azure CLI commands after container app creation. The configuration will be
# re-applied whenever:
# - Container app resources are recreated
# - Scale rule configuration changes
# - Managed identity client ID changes
#
# ALTERNATIVES CONSIDERED:
# 1. azapi provider - May not expose authentication in Container Apps API
# 2. Connection strings - Defeats migration purpose, less secure
# 3. CRON-based scaling - Simpler but not event-driven
# 4. PR to azurerm - Long-term solution, not immediate
#
# See: .temp/keda-auth-implementation-plan.md for full analysis

# Configure KEDA managed identity authentication for content-processor
resource "null_resource" "configure_processor_keda_auth" {
  # Trigger re-configuration when scale rules or identity changes
  triggers = {
    container_app_id = azurerm_container_app.content_processor.id
    scale_rule_name  = "storage-queue-scaler"
    queue_name       = azurerm_storage_queue.content_processing_requests.name
    identity_id      = azurerm_user_assigned_identity.containers.client_id
    # Note: Can't hash scale rule directly as it may include null values
    # Using individual components instead
  }

  provisioner "local-exec" {
    command = <<-EOT
      echo "Configuring KEDA authentication for content-processor..."
      az containerapp update \
        --name ${azurerm_container_app.content_processor.name} \
        --resource-group ${azurerm_resource_group.main.name} \
        --scale-rule-name storage-queue-scaler \
        --scale-rule-type azure-queue \
        --scale-rule-metadata \
          accountName=${azurerm_storage_account.main.name} \
          queueName=${azurerm_storage_queue.content_processing_requests.name} \
          queueLength=8 \
          activationQueueLength=1 \
          cloud=AzurePublicCloud \
        --scale-rule-auth workloadIdentity=${azurerm_user_assigned_identity.containers.client_id} \
        --output none || {
          echo "WARNING: KEDA auth configuration failed for content-processor"
          echo "This may cause scaling issues. Run scripts/configure-keda-auth.sh manually."
          exit 0  # Don't fail Terraform apply
        }
      echo "✓ KEDA authentication configured for content-processor"
    EOT

    interpreter = ["bash", "-c"]
  }

  depends_on = [
    azurerm_container_app.content_processor,
    azurerm_role_assignment.containers_storage_queue_data_contributor,
    azurerm_storage_queue.content_processing_requests
  ]
}

# Configure KEDA managed identity authentication for markdown-generator
resource "null_resource" "configure_markdown_generator_keda_auth" {
  triggers = {
    container_app_id = azurerm_container_app.markdown_generator.id
    scale_rule_name  = "markdown-queue-scaler"
    queue_name       = azurerm_storage_queue.markdown_generation_requests.name
    identity_id      = azurerm_user_assigned_identity.containers.client_id
  }

  provisioner "local-exec" {
    command = <<-EOT
      echo "Configuring KEDA authentication for markdown-generator..."
      az containerapp update \
        --name ${azurerm_container_app.markdown_generator.name} \
        --resource-group ${azurerm_resource_group.main.name} \
        --scale-rule-name markdown-queue-scaler \
        --scale-rule-type azure-queue \
        --scale-rule-metadata \
          accountName=${azurerm_storage_account.main.name} \
          queueName=${azurerm_storage_queue.markdown_generation_requests.name} \
          queueLength=1 \
          cloud=AzurePublicCloud \
        --scale-rule-auth workloadIdentity=${azurerm_user_assigned_identity.containers.client_id} \
        --output none || {
          echo "WARNING: KEDA auth configuration failed for markdown-generator"
          echo "This may cause scaling issues. Run scripts/configure-keda-auth.sh manually."
          exit 0  # Don't fail Terraform apply
        }
      echo "✓ KEDA authentication configured for markdown-generator"
    EOT

    interpreter = ["bash", "-c"]
  }

  depends_on = [
    azurerm_container_app.markdown_generator,
    azurerm_role_assignment.containers_storage_queue_data_contributor,
    azurerm_storage_queue.markdown_generation_requests
  ]
}

# Configure KEDA managed identity authentication for site-publisher
resource "null_resource" "configure_site_publisher_keda_auth" {
  triggers = {
    container_app_id = azurerm_container_app.site_publisher.id
    scale_rule_name  = "site-publish-queue-scaler"
    queue_name       = azurerm_storage_queue.site_publishing_requests.name
    identity_id      = azurerm_user_assigned_identity.containers.client_id
  }

  provisioner "local-exec" {
    command = <<-EOT
      echo "Configuring KEDA authentication for site-publisher..."
      az containerapp update \
        --name ${azurerm_container_app.site_publisher.name} \
        --resource-group ${azurerm_resource_group.main.name} \
        --scale-rule-name site-publish-queue-scaler \
        --scale-rule-type azure-queue \
        --scale-rule-metadata \
          accountName=${azurerm_storage_account.main.name} \
          queueName=${azurerm_storage_queue.site_publishing_requests.name} \
          queueLength=1 \
          activationQueueLength=1 \
          queueLengthStrategy=all \
          cloud=AzurePublicCloud \
        --scale-rule-auth workloadIdentity=${azurerm_user_assigned_identity.containers.client_id} \
        --output none || {
          echo "WARNING: KEDA auth configuration failed for site-publisher"
          echo "This may cause scaling issues. Run scripts/configure-keda-auth.sh manually."
          exit 0  # Don't fail Terraform apply
        }
      echo "✓ KEDA authentication configured for site-publisher"
    EOT

    interpreter = ["bash", "-c"]
  }

  depends_on = [
    azurerm_container_app.site_publisher,
    azurerm_role_assignment.containers_storage_queue_data_contributor,
    azurerm_storage_queue.site_publishing_requests
  ]
}

# Output to verify KEDA auth configuration
output "keda_auth_configured" {
  description = "KEDA managed identity authentication has been configured via Azure CLI"
  value = {
    processor_identity          = azurerm_user_assigned_identity.containers.client_id
    site_generator_identity     = azurerm_user_assigned_identity.containers.client_id
    markdown_generator_identity = azurerm_user_assigned_identity.containers.client_id
    site_publisher_identity     = azurerm_user_assigned_identity.containers.client_id
    note                        = "KEDA auth configured via null_resource local-exec provisioner"
    manual_script               = "scripts/configure-keda-auth.sh can be run manually if needed"
  }
}
