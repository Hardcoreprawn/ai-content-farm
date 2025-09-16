# Storage Queue Migration Implementation Plan

## Phase 1: Infrastructure Changes

### Remove Service Bus Resources
- azurerm_servicebus_namespace.main
- azurerm_servicebus_queue.content_collection_requests  
- azurerm_servicebus_queue.content_processing_requests
- azurerm_servicebus_queue.site_generation_requests

### Add Storage Queue Resources  
- azurerm_storage_queue.content_collection_requests
- azurerm_storage_queue.content_processing_requests  
- azurerm_storage_queue.site_generation_requests

### Update Container Apps
- Remove SERVICE_BUS_* environment variables
- Remove azure-servicebus-connection-string secrets
- Add STORAGE_ACCOUNT_* environment variables
- Update KEDA scaling rules from azure-servicebus to azure-queue
- Use managed identity authentication instead of connection strings

## Phase 2: Application Changes

### Create Storage Queue Client
- Create libs/storage_queue_client.py modeled after service_bus_client.py
- Support managed identity authentication (no connection strings needed)
- Implement queue operations: send_message, receive_message, get_queue_properties

### Update Containers
- Replace ServiceBusClient with StorageQueueClient in all containers
- Update wake-up pattern logic
- Remove Service Bus dependencies from requirements files

## Phase 3: Testing & Validation
- Test KEDA scaling with Storage Queues
- Verify managed identity authentication works
- Validate wake-up pattern end-to-end
- Performance testing and monitoring

## Benefits
- Resolves managed identity vs connection string authentication conflict
- Better Container Apps integration with managed identity
- More cost-effective than Service Bus for simple messaging
- Simpler architecture without connection string management
