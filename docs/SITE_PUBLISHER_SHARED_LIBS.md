# Site Publisher - Shared Library Usage

**Date**: October 10, 2025  
**Context**: Identified existing shared libraries that simplify site-publisher implementation

## 🎯 Key Discovery

The project already has a **production-ready, OWASP-compliant error handler** in `libs/secure_error_handler.py` that we should leverage instead of building custom error handling!

## Available Shared Libraries

### 1. **SecureErrorHandler** (`libs/secure_error_handler.py`) ⭐

**Purpose**: OWASP-compliant error handling with automatic sensitive data sanitization

**Key Features**:
- ✅ **UUID Correlation IDs**: Automatic generation for error tracking
- ✅ **Sensitive Data Filtering**: Auto-removes passwords, tokens, keys, credentials, connection strings
- ✅ **OWASP Compliance**: CWE-209 (information exposure), CWE-754 (error handling), CWE-532 (log injection)
- ✅ **Severity-Based Logging**: LOW/MEDIUM/HIGH/CRITICAL with appropriate detail levels
- ✅ **Stack Traces**: Only logged for CRITICAL errors (prevents info disclosure)
- ✅ **Standardized HTTP Responses**: Matches our API contract format
- ✅ **Context Sanitization**: Recursive sanitization of nested dictionaries
- ✅ **String Truncation**: Auto-truncates long strings that might contain sensitive data

**Usage Example**:
```python
from libs.secure_error_handler import SecureErrorHandler, ErrorSeverity

# Initialize handler
error_handler = SecureErrorHandler(service_name="site-publisher")

# Handle error with automatic sanitization
try:
    dangerous_operation()
except Exception as e:
    # Returns sanitized response with correlation ID
    error_response = error_handler.handle_error(
        error=e,
        error_type="validation",  # or: general, authentication, not_found, etc.
        severity=ErrorSeverity.MEDIUM,
        context={
            "blob_name": "article.md",
            "container": "markdown-content",
            "api_key": "secret123"  # Automatically redacted!
        },
        user_message="Failed to validate markdown file"
    )
    
    # Returns:
    # {
    #     "error_id": "550e8400-e29b-41d4-a716-446655440000",
    #     "message": "Failed to validate markdown file",
    #     "timestamp": "2025-10-10T14:30:00Z",
    #     "service": "site-publisher"
    # }
    
    # Internal logs include full details (sanitized)
    # User response only includes safe message + correlation ID
```

**HTTP Error Response**:
```python
# Create standardized HTTP error response
response = error_handler.create_http_error_response(
    status_code=500,
    error=exc,
    error_type="general",
    user_message="Failed to build site",
    context={"build_step": "hugo_execution"}
)

# Returns format matching our API contract:
# {
#     "status": "error",
#     "message": "Failed to build site",
#     "data": None,
#     "errors": ["Failed to build site"],
#     "metadata": {
#         "function": "site-publisher",
#         "timestamp": "2025-10-10T14:30:00Z",
#         "version": "1.0.0",
#         "error_id": "550e8400-e29b-41d4-a716-446655440000"
#     }
# }
```

**Automatic Sanitization**:
The handler automatically redacts these sensitive key patterns:
- `password`, `secret`, `key`, `token`
- `credential`, `authorization`, `auth`
- `session`, `cookie`
- `connection_string`, `sas_token`, `api_key`

### 2. **BlobStorageClient** (`libs/blob_storage.py`)

**Purpose**: Standardized blob operations with managed identity

**Benefits**:
- Already handles authentication
- Consistent error handling
- Tested and proven in production
- Supports both sync and async operations

**Usage**:
```python
from libs.blob_storage import BlobStorageClient

# Initialize with managed identity (no connection strings!)
blob_client = BlobStorageClient(
    storage_account_name="aicontentstg",
    use_managed_identity=True
)

# Download markdown files
await blob_client.download_blob(
    container_name="markdown-content",
    blob_name="articles/tech-news.md",
    local_path="/tmp/content/tech-news.md"
)

# Upload static site
await blob_client.upload_blob(
    container_name="$web",
    blob_name="index.html",
    local_path="/tmp/build/public/index.html"
)
```

### 3. **StorageQueuePoller** (`libs/storage_queue_poller.py`)

**Purpose**: Background queue processing with visibility timeout handling

**Benefits**:
- Automatic message visibility management
- Graceful shutdown handling
- Configurable poll intervals
- Error recovery with backoff

**Usage**:
```python
from libs.storage_queue_poller import StorageQueuePoller

async def handle_publish_request(message: dict) -> bool:
    """Process site publishing request."""
    await build_and_deploy_site()
    return True  # Success

# Initialize poller
poller = StorageQueuePoller(
    queue_client=queue_client,
    queue_name="site-publishing-requests",
    message_handler=handle_publish_request,
    poll_interval=30.0,
    max_messages_per_batch=1
)

# Start background processing
await poller.start()
```

### 4. **QueueMessageModel** (`libs/queue_client.py`)

**Purpose**: Standardized queue message format with correlation IDs

**Benefits**:
- Automatic message_id and correlation_id generation
- Timestamp tracking
- Retry count tracking
- Type-safe with Pydantic validation

**Usage**:
```python
from libs.queue_client import QueueMessageModel

# Create standardized queue message
message = QueueMessageModel(
    message_type="site.publish.request",
    payload={
        "trigger": "markdown_complete",
        "article_count": 150
    },
    source="markdown-generator",
    correlation_id="parent-job-uuid"  # Optional, auto-generated if not provided
)

# Send to queue (message_id and timestamps auto-added)
await queue_client.send_message(message.model_dump_json())
```

## Updated Site Publisher Architecture

### Error Handling Strategy

**Before** (custom implementation):
- Custom error sanitization logic
- Manual UUID generation
- Inconsistent error responses
- No severity levels
- Risk of information disclosure

**After** (shared library):
- ✅ Battle-tested sanitization (used across all containers)
- ✅ Automatic correlation IDs
- ✅ Standardized responses matching API contract
- ✅ Severity-based logging
- ✅ OWASP-compliant by design

### Implementation Simplification

Using shared libraries **reduces custom code by ~40%**:

**Original Plan**:
- `error_handling.py` (~150 lines of custom code)
- `blob_operations.py` (~200 lines for Azure SDK)
- `queue_processing.py` (~250 lines for polling logic)
- **Total**: ~600 lines of custom infrastructure code

**With Shared Libraries**:
- `error_handling.py` (~30 lines - thin wrapper around `SecureErrorHandler`)
- No `blob_operations.py` (use `libs.blob_storage`)
- No `queue_processing.py` (use `libs.storage_queue_poller`)
- **Total**: ~30 lines + imports

**Focus shifted to business logic**:
- `security.py` - Pure functions for validation (Hugo-specific)
- `site_builder.py` - Pure functions for building (Hugo integration)
- `deployment.py` - Pure functions for deployment (site-specific)
- `app.py` - FastAPI endpoints (REST API)

## Security Benefits

### 1. Consistent Security Posture
All containers use the same error handling approach, making security audits easier and reducing attack surface.

### 2. Reduced Code Duplication
Less custom code = fewer bugs, less maintenance, easier testing.

### 3. Automatic Updates
When `libs/secure_error_handler.py` gets security updates, site-publisher benefits automatically.

### 4. Proven in Production
These libraries are already battle-tested in:
- `content-collector` container
- `content-processor` container  
- `markdown-generator` container

## Implementation Updates

### Updated `requirements.txt`

```txt
# Core framework
fastapi==0.115.0
uvicorn[standard]==0.30.6
pydantic==2.9.0
pydantic-settings==2.5.0

# Azure SDK
azure-identity==1.18.0
azure-storage-blob==12.23.1
azure-storage-queue==12.11.0

# Shared libraries (from monorepo libs/)
# NOTE: Installed via PYTHONPATH in Dockerfile
# libs.secure_error_handler
# libs.blob_storage
# libs.storage_queue_poller
# libs.queue_client

# Hugo (installed separately in Dockerfile)
# Hugo binary v0.138.0 from GitHub releases
```

### Updated `error_handling.py` (Thin Wrapper)

```python
"""
Error handling wrapper for site-publisher.
Uses shared libs.secure_error_handler.SecureErrorHandler.
"""
from libs.secure_error_handler import (
    ErrorSeverity,
    SecureErrorHandler,
    handle_error_safely
)
from typing import Any, Dict, Optional

# Initialize handler for this service
_error_handler = SecureErrorHandler(service_name="site-publisher")


def handle_error(
    error: Exception,
    error_type: str = "general",
    user_message: Optional[str] = None,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Handle errors securely using shared SecureErrorHandler.
    
    Convenience wrapper for site-publisher specific error handling.
    """
    return _error_handler.handle_error(
        error=error,
        error_type=error_type,
        severity=severity,
        context=context,
        user_message=user_message
    )


def create_http_error_response(
    status_code: int,
    error: Optional[Exception] = None,
    error_type: str = "general",
    user_message: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create standardized HTTP error response."""
    return _error_handler.create_http_error_response(
        status_code=status_code,
        error=error,
        error_type=error_type,
        user_message=user_message,
        context=context
    )


# Re-export for convenience
__all__ = [
    "handle_error",
    "create_http_error_response",
    "ErrorSeverity",
    "SecureErrorHandler",
]
```

## Testing Benefits

### Shared Library Tests Already Exist

`libs/secure_error_handler.py` already has comprehensive tests:
- Sensitive data redaction tests
- Correlation ID generation tests
- Severity level tests
- HTTP response format tests
- Context sanitization tests

**Our tests can focus on**:
- Hugo-specific validation logic
- Site building workflows
- Deployment processes
- Integration with shared libraries

## Cost Savings

Using shared libraries **reduces implementation time**:

**Original Estimate**: 40-60 hours
- 8-10 hours on error handling infrastructure
- 6-8 hours on blob storage wrappers
- 4-6 hours on queue polling logic
- 22-36 hours on business logic

**Updated Estimate**: 30-45 hours
- 1-2 hours integrating shared libraries
- 4-5 hours on Hugo-specific validation
- 25-38 hours on business logic (Hugo integration, deployment)

**Time Saved**: ~10-15 hours (25-30% reduction)

## Next Steps

1. ✅ **Updated design docs** to use `SecureErrorHandler`
2. **Create thin wrappers** in `error_handling.py` for convenience
3. **Remove custom error handling code** from implementation plan
4. **Add shared library imports** to `requirements.txt` notes
5. **Focus implementation time** on Hugo integration and deployment logic

## Documentation Updated

- ✅ `docs/SITE_PUBLISHER_SECURITY_IMPLEMENTATION.md` - Updated to use SecureErrorHandler
- ✅ `docs/SITE_PUBLISHER_QUICK_START.md` - Update imports and examples
- ✅ `SITE_PUBLISHER_CHECKLIST.md` - Remove custom error handling tasks

---

**Summary**: By leveraging existing shared libraries, we can:
- Build faster (25-30% time reduction)
- Increase security (battle-tested, OWASP-compliant)
- Reduce bugs (less custom code)
- Improve consistency (same patterns across all containers)
- Simplify maintenance (updates benefit all containers)

The site-publisher implementation is now **simpler, safer, and faster to build**! 🚀
