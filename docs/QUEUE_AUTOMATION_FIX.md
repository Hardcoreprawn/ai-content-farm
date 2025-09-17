# Queue Automation Fix for Issue #513

## Problem Resolved
The content-collector was successfully saving collected content to blob storage but was not automatically triggering the downstream processing pipeline by adding messages to processing queues.

## Root Cause
1. **Missing Environment Variable**: `AZURE_STORAGE_ACCOUNT_NAME` was not configured for local development with Azurite
2. **Production-Only Queue Client**: Queue clients were hardcoded to use production Azure URLs and managed identity authentication, which don't work with local Azurite emulator
3. **Missing Queue Endpoint**: Azurite connection string was missing the queue service endpoint

## Solution Implemented

### 1. Environment Configuration
- Added `AZURE_STORAGE_ACCOUNT_NAME=devstoreaccount1` to `.env` and `.env.example`
- Updated `docker-compose.yml` to include the storage account name for content-collector
- Added `QueueEndpoint=http://azurite:10001/devstoreaccount1` to Azurite connection string

### 2. Smart Queue Client Detection
Updated both `libs/queue_client.py` and `libs/storage_queue_client.py` to:
- Automatically detect local development environment (Azurite)
- Use connection string authentication for Azurite
- Use managed identity authentication for production Azure
- Properly handle queue endpoint configuration

### 3. Code Changes
```python
# Before: Always used production Azure format
self._queue_client = QueueClient(
    account_url=f"https://{self.storage_account_name}.queue.core.windows.net",
    queue_name=self.queue_name,
    credential=credential,
)

# After: Smart detection
if (connection_string and "devstoreaccount1" in connection_string and "azurite" in connection_string):
    # Use Azurite connection string
    self._queue_client = QueueClient.from_connection_string(
        conn_str=azurite_queue_connection,
        queue_name=self.queue_name
    )
else:
    # Use production managed identity
    self._queue_client = QueueClient(
        account_url=f"https://{self.storage_account_name}.queue.core.windows.net",
        queue_name=self.queue_name,
        credential=credential,
    )
```

## How It Works Now

1. **Content Collection**: When content-collector successfully collects and stores content
2. **Automatic Queue Message**: `_send_processing_request()` method sends a wake-up message to `content-processing-requests` queue
3. **Message Content**: Includes collection ID, item count, storage location, and trigger reason
4. **KEDA Scaling**: Queue message triggers KEDA to scale up content-processor
5. **Downstream Processing**: content-processor wakes up and processes the new collection

## Testing the Fix

### Local Development (Docker Compose)
```bash
# Start services
docker-compose up -d

# Test content collection (should now trigger queue message)
curl -X POST http://localhost:8001/collections \
  -H "Content-Type: application/json" \
  -d '{
    "sources": [{"type": "reddit", "subreddits": ["technology"], "limit": 2}],
    "save_to_storage": true
  }'

# Check queue messages (should show messages in content-processing-requests)
# Access Azurite Storage Explorer or check processor logs for wake-up messages
```

### Verification Points
1. ✅ Collection successfully saves to blob storage
2. ✅ Queue message is sent to `content-processing-requests` queue  
3. ✅ content-processor receives wake-up message via KEDA scaling
4. ✅ End-to-end pipeline: collection → processing → generation

## Files Modified
- `.env` - Added storage account name
- `.env.example` - Added storage account name  
- `docker-compose.yml` - Added environment variables and queue endpoint
- `libs/queue_client.py` - Added Azurite detection and connection logic
- `libs/storage_queue_client.py` - Added Azurite detection and connection logic

## Benefits
- ✅ **Backward Compatible**: Works with existing production Azure configuration
- ✅ **Development Ready**: Works with local Azurite emulator out of the box
- ✅ **Automatic Detection**: No manual configuration needed
- ✅ **Reliable**: Proper error handling and logging
- ✅ **End-to-End**: Enables complete automation pipeline

The fix ensures that content-collector now properly triggers the downstream processing pipeline, resolving the automation gap identified in issue #513.