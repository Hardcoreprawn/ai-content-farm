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
    # Force reconfiguration to fix queueLength from 8 to 16
    version = "v2"
  }

  provisioner "local-exec" {
    command = <<-EOT
      set -e  # Exit on any error for better visibility
      echo "🔧 Configuring KEDA authentication for content-processor..."

      # Retry logic for transient failures
      MAX_RETRIES=3
      RETRY_COUNT=0

      while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if az containerapp update \
          --name ${azurerm_container_app.content_processor.name} \
          --resource-group ${azurerm_resource_group.main.name} \
          --scale-rule-name storage-queue-scaler \
          --scale-rule-type azure-queue \
          --scale-rule-metadata \
            accountName=${azurerm_storage_account.main.name} \
            queueName=${azurerm_storage_queue.content_processing_requests.name} \
            queueLength=16 \
            activationQueueLength=1 \
            cloud=AzurePublicCloud \
          --scale-rule-auth workloadIdentity=${azurerm_user_assigned_identity.containers.client_id} \
          --output none; then
          echo "✅ KEDA authentication configured for content-processor (queueLength=16)"
          exit 0
        else
          RETRY_COUNT=$((RETRY_COUNT + 1))
          if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            echo "⚠️  Attempt $RETRY_COUNT failed, retrying in 5s..."
            sleep 5
          fi
        fi
      done

      echo "❌ FAILED: KEDA auth configuration failed for content-processor after $MAX_RETRIES attempts"
      echo "Run manually: scripts/configure-keda-auth.sh"
      exit 1  # Fail Terraform to make issue visible
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
    # Force reconfiguration to add activationQueueLength
    version = "v2"
  }

  provisioner "local-exec" {
    command = <<-EOT
      set -e
      echo "🔧 Configuring KEDA authentication for markdown-generator..."

      MAX_RETRIES=3
      RETRY_COUNT=0

      while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if az containerapp update \
          --name ${azurerm_container_app.markdown_generator.name} \
          --resource-group ${azurerm_resource_group.main.name} \
          --scale-rule-name markdown-queue-scaler \
          --scale-rule-type azure-queue \
          --scale-rule-metadata \
            accountName=${azurerm_storage_account.main.name} \
            queueName=${azurerm_storage_queue.markdown_generation_requests.name} \
            queueLength=1 \
            activationQueueLength=1 \
            cloud=AzurePublicCloud \
          --scale-rule-auth workloadIdentity=${azurerm_user_assigned_identity.containers.client_id} \
          --output none; then
          echo "✅ KEDA authentication configured for markdown-generator"
          exit 0
        else
          RETRY_COUNT=$((RETRY_COUNT + 1))
          if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            echo "⚠️  Attempt $RETRY_COUNT failed, retrying in 5s..."
            sleep 5
          fi
        fi
      done

      echo "❌ FAILED: KEDA auth configuration failed for markdown-generator after $MAX_RETRIES attempts"
      exit 1
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
    version          = "v2"
  }

  provisioner "local-exec" {
    command = <<-EOT
      set -e
      echo "🔧 Configuring KEDA authentication for site-publisher..."

      MAX_RETRIES=3
      RETRY_COUNT=0

      while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if az containerapp update \
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
          --output none; then
          echo "✅ KEDA authentication configured for site-publisher"
          exit 0
        else
          RETRY_COUNT=$((RETRY_COUNT + 1))
          if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            echo "⚠️  Attempt $RETRY_COUNT failed, retrying in 5s..."
            sleep 5
          fi
        fi
      done

      echo "❌ FAILED: KEDA auth configuration failed for site-publisher after $MAX_RETRIES attempts"
      exit 1
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
