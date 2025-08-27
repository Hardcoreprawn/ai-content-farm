# Secure Error Handling Migration Guide

## Overview

This document covers the migration to secure error handling patterns as part of the shared models standardization. A critical security vulnerability was identified where internal error details were being exposed to clients, potentially leaking sensitive information.

## Security Issue Identified

**CVE Reference**: CodeQL Security Alert (PR #109)

**Problem**: Exception handlers across all containers were exposing internal error details through:
1. Direct error message exposure in HTTP responses
2. Storing actual error messages in service status endpoints  
3. Including sensitive stack traces or system information in client responses

**Impact**: Information disclosure vulnerability allowing attackers to gather internal system details

## Vulnerable Pattern Examples

### ❌ Insecure (Before)
```python
# Exposes internal error details to clients
try:
    result = some_operation()
except Exception as e:
    # BAD: Exposes actual error message
    last_status["error"] = str(e)
    raise HTTPException(status_code=500, detail=f"Operation failed: {str(e)}")
```

### ✅ Secure (After)  
```python
# Logs errors server-side, returns generic message to client
try:
    result = some_operation()
except Exception as e:
    # GOOD: Log actual error server-side only
    logger.error(f"Operation failed: {e}", exc_info=True)
    
    # GOOD: Store generic message in status
    last_status["error"] = "Internal error"
    
    # GOOD: Return generic error to client
    error = ErrorCodes.secure_internal_error(e, "operation_name")
    return JSONResponse(status_code=500, content=error.to_standard_response().model_dump())
```

## Secure Error Handling Methods

### For Backward Compatibility (ErrorCodes approach)

```python
from libs.shared_models import ErrorCodes

# Secure internal error handling
try:
    risky_operation()
except Exception as e:
    error = ErrorCodes.secure_internal_error(e, "content_collection")
    response = error.to_standard_response()
    return JSONResponse(status_code=500, content=response.model_dump())

# Secure validation error handling  
error = ErrorCodes.secure_validation_error("field_name", "Please provide a valid value")
```

### For FastAPI-Native (StandardResponse approach)

```python
from libs.shared_models import StandardResponseFactory as StandardResponse

# Secure internal error handling
try:
    risky_operation()
except Exception as e:
    response = StandardResponse.secure_internal_error(e, "content_collection")
    return JSONResponse(status_code=500, content=response.model_dump())

# Secure validation error handling
response = StandardResponse.secure_validation_error("field_name", "Please provide a valid value")
return JSONResponse(status_code=400, content=response.model_dump())
```

## Migration Checklist

### 1. Exception Handlers
- [ ] Replace `str(e)` in error messages with generic messages
- [ ] Add server-side logging for actual errors
- [ ] Update status tracking to store generic messages
- [ ] Test that no internal details leak in responses

### 2. Validation Errors
- [ ] Review validation error messages for sensitive information
- [ ] Ensure field names don't expose internal structure
- [ ] Use safe, user-friendly validation messages

### 3. Service Status Endpoints
- [ ] Remove actual error details from status responses
- [ ] Store generic error states only
- [ ] Maintain detailed error logs server-side

### 4. HTTP Exception Handling
- [ ] Update all `HTTPException(detail=f"Error: {str(e)}")` patterns
- [ ] Use secure error response methods
- [ ] Ensure consistent error response format

## Container-Specific Fixes Required

### Content-Collector (✅ Fixed)
- ✅ Status endpoint now stores generic "Internal error"
- ✅ HTTP response uses secure error handling methods
- ✅ Both legacy and standardized endpoints updated with secure patterns
- ✅ Server-side logging of actual errors for debugging

### Content-Ranker  
- ❌ General exception handler exposes `str(exc)` directly
- ❌ Validation error handler may expose sensitive field details
- ❌ Status endpoint may store actual error messages

### Other Containers
- ❌ All containers likely have similar patterns
- ❌ Need comprehensive audit and fixing

## Implementation Plan

### Phase 1: Update Shared Models (✅ Complete)
- [x] Add `ErrorCodes.secure_internal_error()` method
- [x] Add `ErrorCodes.secure_validation_error()` method
- [x] Add `StandardResponseFactory.secure_internal_error()` method
- [x] Add `StandardResponseFactory.secure_validation_error()` method

### Phase 2: Fix Content-Collector (✅ Complete)
- [x] Apply PR #109 changes
- [x] Fix remaining HTTP response exposure
- [x] Update both legacy and standardized endpoints
- [x] Test security and functionality

### Phase 3: Fix Content-Ranker
- [ ] Update exception handlers to use secure methods
- [ ] Fix service status error storage
- [ ] Test all error scenarios

### Phase 4: Audit All Containers
- [ ] Systematic review of all error handling
- [ ] Apply secure patterns consistently
- [ ] Update tests to verify security

### Phase 5: Documentation & Guidelines
- [ ] Update development guidelines
- [ ] Create security review checklist
- [ ] Add automated security testing

## Testing Security Fixes

### 1. Error Response Testing
```python
def test_error_response_security():
    """Ensure error responses don't leak internal details"""
    # Trigger internal error
    response = client.post("/api/service/process", json=invalid_data)
    
    assert response.status_code == 500
    data = response.json()
    
    # Should NOT contain internal details
    assert "database connection failed" not in str(data).lower()
    assert "file not found" not in str(data).lower()
    assert "traceback" not in str(data).lower()
    
    # Should contain generic message
    assert data["message"] == "Internal server error"
    assert "unexpected error occurred" in str(data["errors"])
```

### 2. Status Endpoint Testing
```python
def test_status_endpoint_security():
    """Ensure status endpoints don't expose error details"""
    # Trigger error in service
    trigger_internal_error()
    
    # Check status endpoint
    response = client.get("/status")
    data = response.json()
    
    # Should contain generic error only
    assert data["last_operation"]["error"] == "Internal error"
    # Should NOT contain actual error details
```

## Logging Best Practices

### Secure Server-Side Logging
```python
import logging

# Configure secure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Log actual errors server-side with context
try:
    risky_operation()
except Exception as e:
    logger.error(
        "Content collection failed for user %s: %s", 
        user_id, str(e), 
        exc_info=True,  # Include stack trace in logs
        extra={
            "operation": "content_collection",
            "user_id": user_id,
            "request_id": request.headers.get("x-request-id")
        }
    )
```

## Security Review Guidelines

### Code Review Checklist
- [ ] No `str(e)` or `repr(e)` in client responses
- [ ] No stack traces in error responses  
- [ ] Generic error messages for clients
- [ ] Detailed logging server-side only
- [ ] No sensitive data in status endpoints
- [ ] Consistent error response format

### Automated Security Testing
- Add CodeQL rules for error handling patterns
- Include security tests in CI/CD pipeline
- Regular security audits of error responses

## Related Documentation

- [Shared Models Migration Guide](./SHARED_MODELS_MIGRATION.md)
- [API Standardization](./API_STANDARDIZATION.md)
- [Security Policy](./security/security-policy.md)
- [PR #109 - Content Collector Security Fix](https://github.com/Hardcoreprawn/ai-content-farm/pull/109)

## Version History

- **v1.0** (2025-08-27): Initial security issue identification and mitigation plan
- **v1.1** (2025-08-27): Secure error handling methods added to shared models
