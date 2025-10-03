# Data Model: Pragmatic Approach for AI Content Farm

**Problem**: We have inconsistent data models across containers, leading to confusion and mapping overhead.

**Vision**: Social media discovery → Research → Article generation → Static site publishing

## Current State Analysis

### Three Data Models Exist

1. **`QueueMessageModel`** (libs/queue_client.py)
   - Generic queue transport envelope
   - Fields: service_name, operation, payload (Dict), metadata (Dict)
   - Used by ALL containers for queue communication
   - ✅ Already working and deployed

2. **`ProcessingRequest`** (libs/data_contracts.py)
   - Specific, strongly-typed message for processing
   - Fields: collection_blob_path, batch_size, priority_threshold, etc.
   - ❌ **NEVER USED** - defined but ignored by all code

3. **`CollectionResult`** (libs/data_contracts.py)
   - Blob storage file format
   - Fields: metadata (CollectionMetadata), items (List[CollectionItem])
   - ✅ Used for all collection files in blob storage

### The Problem

```
Collector → Queue Message → Processor
   ↓            ↓               ↓
Saves to    Contains        Ignores
storage     blob path       blob path!
            in payload      
                            Lists ALL
                            blobs instead
```

**Result**: Processor inefficiently lists all blobs and guesses which one to process instead of reading the explicit path from the queue message.

## Pragmatic Solution: "Use What You Have"

### Principle: Minimal Required Fields, Maximum Flexibility

**Rule 1**: Use `QueueMessageModel` for ALL queue communication (it's already deployed and working)

**Rule 2**: Only TWO required fields in queue messages:
- `service_name` - who sent this
- `operation` - what to do

**Rule 3**: Everything else goes in `payload` dict (flexible, extensible)

**Rule 4**: Containers read what they need from payload, ignore the rest

### Standard Payload Fields (All Optional)

```python
{
    "service_name": "content-collector",  # REQUIRED
    "operation": "wake_up",                # REQUIRED
    "payload": {                           # All fields OPTIONAL
        # File references
        "files": ["collected-content/collections/2025/10/03/collection_X.json"],
        
        # Correlation and tracking
        "correlation_id": "collection_20251003_100328",
        "timestamp": "2025-10-03T10:03:59Z",
        
        # Processing hints (processor can use or ignore)
        "batch_size": 10,
        "priority_threshold": 0.5,
        
        # Statistics (informational only)
        "files_count": 1,
        "total_items": 33,
        
        # Content type (for routing/filtering)
        "content_type": "json",
        
        # Trigger context
        "trigger": "scheduled_collection",
        "source": "timer_trigger"
    }
}
```

### Container Behavior: Defensive Reading

**Collector** (sends messages):
```python
# Always include what you know
payload = {
    "files": [storage_location],  # Specific blob path
    "correlation_id": collection_id,
    "total_items": len(items),
    "timestamp": datetime.now().isoformat()
}
# Processor MIGHT use this, might not - that's okay!
```

**Processor** (receives messages):
```python
# Read what's available, fall back gracefully
files = message.payload.get("files", [])

if files:
    # Great! Process specific files
    for file_path in files:
        await process_specific_collection(file_path)
else:
    # No problem, fall back to discovery
    blobs = await list_recent_collections()
    for blob in blobs:
        await process_collection(blob["name"])
```

**Site-Generator** (receives messages):
```python
# Same pattern
processed_files = message.payload.get("files", [])

if processed_files:
    # Generate from specific files
    for file_path in processed_files:
        await generate_from_file(file_path)
else:
    # Discover what needs generation
    articles = await list_ungenerated_articles()
```

## Data Flow Through Pipeline

### Stage 1: Collection → Storage
```
INPUT:  Timer trigger (scheduled collection)
OUTPUT: CollectionResult blob in storage
        └─ metadata: {timestamp, collection_id, total_items, ...}
        └─ items: [{id, title, source, url, content, ...}, ...]
```

### Stage 2: Collection → Queue → Processor
```
INPUT:  QueueMessageModel
        └─ operation: "wake_up"
        └─ payload.files: ["collected-content/collections/.../file.json"]
        
ACTION: Processor downloads blob, processes items, saves results
        
OUTPUT: Multiple processed article blobs in storage
        └─ One file per article (or batch file with multiple)
```

### Stage 3: Processor → Queue → Site-Generator
```
INPUT:  QueueMessageModel
        └─ operation: "wake_up"
        └─ payload.files: ["processed-content/articles/.../article.json"]
        
ACTION: Site-gen downloads processed articles, generates markdown
        
OUTPUT: Markdown files in storage + static website
```

## Implementation: What Changes

### 1. Keep Current Models (No Breaking Changes)

✅ **Keep** `QueueMessageModel` - it works
✅ **Keep** `CollectionResult` - blob format is good
✅ **Keep** `CollectionItem` - standardized item format
❌ **Remove** `ProcessingRequest` - unused, adds confusion

### 2. Update Processor to Read payload.files

**File**: `containers/content-processor/endpoints/processing.py`

```python
# BEFORE (current - inefficient)
blobs = await blob_client.list_blobs("collected-content", prefix="collections/")
latest_blob = sorted(blobs, key=lambda x: x["name"])[-1]
collection_data = await blob_client.download_json("collected-content", latest_blob["name"])

# AFTER (pragmatic - efficient)
files_to_process = request.payload.get("files", [])

if files_to_process:
    # Process specific files from queue message
    for file_path in files_to_process:
        container, blob_name = file_path.split("/", 1)
        collection_data = await blob_client.download_json(container, blob_name)
        await process_collection(collection_data, blob_name)
else:
    # Fall back to discovery (backwards compatible)
    blobs = await blob_client.list_blobs("collected-content", prefix="collections/")
    # ... existing logic
```

### 3. Update Site-Generator Similarly

Same pattern: Read `payload.files` if present, fall back to listing if not.

### 4. Document the Pattern

Create shared utilities in `libs/` for consistent payload handling:

```python
# libs/payload_utils.py

def get_files_from_payload(payload: Dict[str, Any]) -> List[str]:
    """
    Extract file paths from queue message payload.
    
    Handles various formats:
    - payload["files"] = ["path1", "path2"]
    - payload["file"] = "path1"
    - payload["collection_blob_path"] = "path1"
    
    Returns empty list if no files specified.
    """
    files = payload.get("files", [])
    if files:
        return files if isinstance(files, list) else [files]
    
    # Alternative field names
    if "file" in payload:
        return [payload["file"]]
    if "collection_blob_path" in payload:
        return [payload["collection_blob_path"]]
    
    return []
```

## Benefits of This Approach

✅ **No Breaking Changes**: Existing code continues to work
✅ **Backwards Compatible**: Fall back to blob listing if payload.files missing
✅ **Gradually Adoptable**: Can implement per-container incrementally
✅ **Flexible**: New fields can be added to payload without breaking anything
✅ **Pragmatic**: Uses what's already deployed and working
✅ **Performance Win**: Direct file access vs listing all blobs
✅ **Consistency**: Same pattern across all containers
✅ **Testable**: Can test with or without payload.files

## Anti-Patterns to Avoid

❌ **Don't** require specific payload fields (except service_name, operation)
❌ **Don't** create multiple queue message models for different operations
❌ **Don't** put complex objects in payload (use blob references instead)
❌ **Don't** fail if optional fields are missing (graceful fallback)
❌ **Don't** map between models at every boundary (use same model)

## Summary: The Pragmatic Way

**One Model for Queues**: `QueueMessageModel` (generic envelope)
**One Model for Collections**: `CollectionResult` (blob storage format)
**One Model for Items**: `CollectionItem` (standardized content)

**Principle**: 
- Minimal required fields (service_name, operation)
- Maximum flexibility (payload is Dict[str, Any])
- Defensive reading (get with defaults, graceful fallbacks)
- Use what's available, don't demand what isn't

**Result**: Simple, consistent, pragmatic data model that works across all containers without complex mapping or brittleness.
