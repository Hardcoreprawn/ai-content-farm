 # Content Processor Container: Architecture & Blob Reading Flow

## Overview

The Content Processor is a FastAPI-based container that processes collected content through AI enhancement. It's designed around an event-driven "wake-up work queue" pattern where external triggers (KEDA/HTTP) signal work availability.

## Container Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   CONTENT PROCESSOR CONTAINER                  │
├─────────────────────────────────────────────────────────────────┤
│  📡 TRIGGERS                                                    │
│  ├─ KEDA (Azure Container Apps)                                │
│  ├─ HTTP POST /process/wake-up                                │
│  └─ Manual API calls                                          │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│  🌐 FASTAPI APPLICATION (main.py)                             │
│  ├─ CORS middleware                                           │
│  ├─ Request validation                                        │
│  ├─ Error handling                                            │
│  └─ Lifecycle management                                      │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│  🎯 ENDPOINT LAYER (endpoints.py)                             │
│  ├─ wake_up_endpoint()                                        │
│  ├─ process_batch_endpoint()                                  │
│  ├─ health_endpoint()                                         │
│  └─ status_endpoint()                                         │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│  🧠 PROCESSOR CORE (processor.py)                             │
│  ├─ ContentProcessor class                                    │
│  ├─ Session tracking                                          │
│  ├─ Health monitoring                                         │
│  └─ Service coordination                                      │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│  🔍 SERVICE LAYER                                             │
│  ├─ TopicDiscoveryService   → Blob reading & filtering       │
│  ├─ ArticleGenerationService → AI content creation           │
│  ├─ LeaseCoordinator        → Distributed locking            │
│  └─ ProcessorStorageService → Result persistence             │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│  💾 INFRASTRUCTURE LAYER                                      │
│  ├─ SimplifiedBlobClient    → Azure Storage operations       │
│  ├─ BlobAuthManager         → Authentication & connection    │
│  ├─ AsyncAzureOpenAI        → AI model interaction           │
│  └─ ContractValidator       → Data validation                │
└─────────────────────────────────────────────────────────────────┘
```

## Complete Wake-up to Blob Reading Flow

### 1. Trigger Reception
```
HTTP POST /process/wake-up
{
  "source": "collector",
  "batch_size": 10,
  "priority_threshold": 0.5,
  "debug_bypass": false
}
```

**Components Involved:**
- `main.py` → FastAPI request handling
- `endpoints.py:wake_up_endpoint()` → Request parsing

### 2. Processor Initialization
```python
# endpoints.py:wake_up_endpoint()
processor = get_processor()  # Singleton ContentProcessor instance
result = await processor.process_available_work(
    batch_size=request.batch_size,
    priority_threshold=request.priority_threshold,
    debug_bypass=request.debug_bypass
)
```

**Components Involved:**
- `processor.py:ContentProcessor.__init__()` → Service initialization
- Creates `TopicDiscoveryService` with `SimplifiedBlobClient`

### 3. Topic Discovery Phase
```python
# processor.py:process_available_work()
available_topics = await self.topic_discovery.find_available_topics(
    batch_size, priority_threshold, debug_bypass=debug_bypass
)
```

**Components Involved:**
- `services/topic_discovery.py:find_available_topics()`

### 4. Blob Storage Connection
```python
# libs/simplified_blob_client.py:__init__()
self.auth_manager = BlobAuthManager()
self.blob_service_client = self.auth_manager.get_blob_service_client()
```

**Authentication Flow:**
```
libs/blob_auth.py:BlobAuthManager.get_blob_service_client()
├─ Check AZURE_STORAGE_CONNECTION_STRING (if available)
├─ Fallback to AZURE_STORAGE_ACCOUNT_NAME + Managed Identity
│  ├─ Production: ManagedIdentityCredential(client_id)
│  ├─ Development: DefaultAzureCredential
│  └─ Account URL: https://{account_name}.blob.core.windows.net
└─ Return BlobServiceClient instance
```

### 5. Blob Discovery
```python
# topic_discovery.py:find_available_topics()
blobs = await self.blob_client.list_blobs("collected-content")
```

**Blob Listing Process:**
```
libs/simplified_blob_client.py:list_blobs()
├─ Get container client: blob_service_client.get_container_client("collected-content")
├─ Enumerate blobs: container_client.list_blobs(name_starts_with=prefix)
├─ Extract metadata: {name, size, last_modified, content_type}
└─ Return List[Dict[str, Any]]
```

### 6. Blob Content Download
```python
# topic_discovery.py (for each blob)
collection_data = await self.blob_client.download_json(
    "collected-content", blob_name
)
```

**Download Process:**
```
libs/simplified_blob_client.py:download_json()
├─ Get blob client: blob_service_client.get_blob_client(container, blob_name)
├─ Download content: blob_client.download_blob().readall()
├─ Parse JSON: json.loads(content.decode())
└─ Return Dict[str, Any]
```

### 7. Data Validation & Filtering
```python
# topic_discovery.py
if not debug_bypass and not self._is_valid_collection(collection_data):
    continue  # Skip invalid collections

# Process items
for item_data in collection_data.get("items", []):
    if debug_bypass:
        topic = self._raw_item_to_topic_metadata(item_data, blob_name)
    else:
        validated_item = ContractValidator.validate_collection_item(item_data)
        topic = self._validated_item_to_topic_metadata(validated_item, blob_name)
```

## Why Blob Reading Might Fail

### Common Failure Points

1. **Authentication Issues**
   - Missing `AZURE_STORAGE_ACCOUNT_NAME` environment variable
   - Managed Identity not properly configured
   - Network connectivity to Azure Storage

2. **Container Access**
   - Container `collected-content` doesn't exist
   - Insufficient permissions (Reader role needed)
   - Firewall/network rules blocking access

3. **Data Format Issues**
   - Blob content isn't valid JSON
   - Missing required fields in collections
   - Encoding issues (non-UTF8 content)

4. **Memory/Performance**
   - Large blobs causing timeout
   - Too many blobs overwhelming the container
   - Rate limiting from Azure Storage

### Debug Commands

```bash
# Test blob storage connectivity
curl -X GET "https://ai-content-prod-processor.../processing/diagnostics"

# Test with debug bypass (skips all validation)
curl -X POST "https://ai-content-prod-processor.../process/wake-up" \
  -H "Content-Type: application/json" \
  -d '{"source": "debug", "debug_bypass": true, "batch_size": 1}'

# Check container health
curl -X GET "https://ai-content-prod-processor.../health"
```

## Environment Variables Required

```bash
# Primary authentication (choose one)
AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=..."
# OR
AZURE_STORAGE_ACCOUNT_NAME="aicontentprodstkwakpx"
AZURE_CLIENT_ID="..."  # For managed identity

# Optional
ENVIRONMENT="production"  # affects auth method selection
```

## Container Resource Flow

```
User/KEDA → HTTP Request → FastAPI → Endpoint → Processor → TopicDiscovery
    ↓
SimplifiedBlobClient → BlobAuthManager → Azure Storage API
    ↓
JSON Collections → Data Validation → TopicMetadata Objects
    ↓
AI Processing → Article Generation → Storage → Response
```

The blob reading process involves 6 distinct layers, each with potential failure points. The debug bypass functionality allows us to skip validation layers and identify exactly where the pipeline breaks.