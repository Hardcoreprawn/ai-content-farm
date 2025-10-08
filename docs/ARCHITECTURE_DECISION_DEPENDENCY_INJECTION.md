# Architecture Decision: Eliminate Singleton, Use FastAPI Dependency Injection

**Date**: October 8, 2025  
**Status**: Approved  
**Applies to**: Week 3-4 Refactoring Phase 3

---

## Context

The current `ContentProcessor` class uses a singleton pattern that creates scaling problems:

```python
# Current anti-pattern
_processor_instance: ContentProcessor = None

def get_processor() -> ContentProcessor:
    global _processor_instance
    if _processor_instance is None:
        _processor_instance = ContentProcessor()  # Lives for container lifetime
    return _processor_instance
```

**Problems**:
1. ❌ **Single processor_id per container** - All requests share same ID (breaks tracing)
2. ❌ **Single session_id per container** - Can't track individual request sessions
3. ❌ **Stateful object** - 6 service instances created once, shared across all requests
4. ❌ **Hard to test** - Global state makes mocking difficult
5. ❌ **Scaling issues** - Singleton initialization slows container startup
6. ❌ **Not thread-safe** - Shared mutable state across async requests

---

## Decision

**Completely eliminate ContentProcessor class** and use FastAPI's native dependency injection with:

1. **Cached Azure clients** via `@lru_cache()` - One per container, connection pooling
2. **Fresh IDs per request** - New `processor_id` and `session_id` for each request
3. **Direct pipeline calls** - Endpoints call functional pipeline functions directly
4. **Explicit dependencies** - All parameters passed via `Depends()`

---

## Implementation

### 1. Client Dependencies (Cached Resources)

```python
# client_dependencies.py
from functools import lru_cache
from azure.storage.blob import BlobServiceClient
from azure.storage.queue import QueueServiceClient
from openai import AsyncOpenAI
import os

@lru_cache()
def get_blob_client() -> BlobServiceClient:
    """Cached blob client - initialized once per container."""
    return BlobServiceClient.from_connection_string(
        os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    )

@lru_cache()
def get_queue_client() -> QueueServiceClient:
    """Cached queue client - initialized once per container."""
    return QueueServiceClient.from_connection_string(
        os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    )

@lru_cache()
def get_openai_client() -> AsyncOpenAI:
    """Cached OpenAI client - initialized once per container."""
    return AsyncOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        base_url=os.getenv("AZURE_OPENAI_ENDPOINT"),
        default_headers={"api-key": os.getenv("AZURE_OPENAI_API_KEY")}
    )
```

### 2. Request-Scoped Dependencies (Fresh Per Request)

```python
# client_dependencies.py (continued)
from uuid import uuid4
from datetime import datetime, timezone

def get_processor_id() -> str:
    """Generate unique processor ID per request."""
    return str(uuid4())[:8]

def get_session_id() -> str:
    """Generate unique session ID per request."""
    return str(uuid4())

def get_request_timestamp() -> str:
    """Get current timestamp for request."""
    return datetime.now(timezone.utc).isoformat()
```

### 3. Endpoint Implementation (Clean & Explicit)

```python
# endpoints/processing_router.py
from fastapi import APIRouter, Depends
from azure.storage.blob import BlobServiceClient
from azure.storage.queue import QueueServiceClient
from openai import AsyncOpenAI

from client_dependencies import (
    get_blob_client,
    get_queue_client,
    get_openai_client,
    get_processor_id,
    get_session_id,
)
from processing_pipeline import process_collection_file
from models import ProcessRequest, StandardResponse

router = APIRouter()

@router.post("/process")
async def process_endpoint(
    request: ProcessRequest,
    blob_client: BlobServiceClient = Depends(get_blob_client),
    queue_client: QueueServiceClient = Depends(get_queue_client),
    openai_client: AsyncOpenAI = Depends(get_openai_client),
    processor_id: str = Depends(get_processor_id),
    session_id: str = Depends(get_session_id),
) -> StandardResponse:
    """
    Process collection file - fully functional with dependency injection.
    
    Each request gets:
    - Cached Azure clients (connection pooling)
    - Fresh processor_id (for tracing this request)
    - Fresh session_id (for tracking this session)
    """
    result = await process_collection_file(
        blob_path=request.blob_path,
        blob_client=blob_client,
        queue_client=queue_client,
        openai_client=openai_client,
        processor_id=processor_id,
        session_id=session_id,
    )
    
    return StandardResponse(
        status="success",
        message=f"Processed {result.topics_processed} topics",
        data=result.model_dump()
    )
```

---

## Benefits

### Scaling Benefits
- ✅ **Fast Container Startup**: No singleton initialization delay (< 5 seconds)
- ✅ **Horizontal Scaling**: Each request completely independent
- ✅ **KEDA-Friendly**: Can scale 0 → 10 containers rapidly
- ✅ **No State Conflicts**: Fresh IDs prevent request interference

### Development Benefits
- ✅ **Easy Testing**: Override dependencies with mocks
- ✅ **Clear Dependencies**: Explicit what each endpoint needs
- ✅ **Type Safety**: FastAPI validates dependency types
- ✅ **No Global State**: Pure functional pipeline

### Operational Benefits
- ✅ **Request Tracing**: Unique processor_id per request
- ✅ **Session Tracking**: Unique session_id per processing session
- ✅ **Connection Pooling**: Azure clients efficiently cached
- ✅ **Memory Efficiency**: No service object overhead per request

---

## Migration Path

### Week 3-4 Phase 1: Create Functional Modules
Convert service classes to functional operations:
- `collection_operations.py`
- `topic_conversion.py`
- `article_generation.py`
- `storage_operations.py`
- `lease_operations.py`
- `session_tracking.py`

### Week 3-4 Phase 2: Create Pipeline Composition
Orchestrate functional modules:
- `processing_pipeline.py` with `process_collection_file()`
- `processing_pipeline.py` with `process_single_topic()`

### Week 3-4 Phase 3: Implement Dependency Injection
- Create `client_dependencies.py`
- Update all endpoints to use `Depends()`
- **Delete `processor.py` ContentProcessor class**
- Remove singleton pattern from `endpoints.py`

### Week 5: Performance Testing
- Load test concurrent requests
- Verify client caching works
- Test KEDA autoscaling behavior
- Measure memory under load

---

## Testing Strategy

### Unit Testing (Easy with Dependency Injection)

```python
# test_endpoints.py
from fastapi.testclient import TestClient
from unittest.mock import Mock

def test_process_endpoint():
    """Test endpoint with mocked dependencies."""
    app.dependency_overrides[get_blob_client] = lambda: Mock()
    app.dependency_overrides[get_openai_client] = lambda: Mock()
    
    client = TestClient(app)
    response = client.post("/process", json={"blob_path": "test.json"})
    
    assert response.status_code == 200
```

### Integration Testing (Real Clients)

```python
# test_integration.py
@pytest.mark.integration
async def test_full_pipeline():
    """Test with real Azure clients."""
    blob_client = get_blob_client()  # Real client
    openai_client = get_openai_client()  # Real client
    
    result = await process_collection_file(
        blob_path="test-collection.json",
        blob_client=blob_client,
        openai_client=openai_client,
        processor_id="test-processor",
        session_id="test-session",
    )
    
    assert result.success
```

---

## Alternatives Considered

### Alternative 1: Keep ContentProcessor as Thin Wrapper
**Rejected** - Still creates singleton pattern, doesn't solve scaling issues

### Alternative 2: Context Manager Pattern
**Rejected** - More complex than FastAPI's built-in dependency injection

### Alternative 3: Service Locator Pattern
**Rejected** - Hidden dependencies, harder to test

---

## References

- [FastAPI Dependency Injection](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [Python functools.lru_cache](https://docs.python.org/3/library/functools.html#functools.lru_cache)
- [Azure SDK Connection Pooling](https://learn.microsoft.com/en-us/azure/developer/python/sdk/azure-sdk-overview)
- [KEDA Scaling Best Practices](https://keda.sh/docs/2.14/concepts/scaling-deployments/)

---

## Approval

- [x] Architecture decision approved
- [x] Refactoring checklist updated
- [x] Team aligned on approach
- [x] Testing strategy defined
- [x] Migration path clear

**Next Steps**: Begin Week 3-4 Phase 1 - Create functional modules starting with `collection_operations.py`
