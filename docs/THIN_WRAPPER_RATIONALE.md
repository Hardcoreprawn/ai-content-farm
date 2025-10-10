# Thin Wrapper Pattern - When It's Justified vs Anti-Pattern

**Date**: October 10, 2025  
**Context**: Discussion about `error_handling.py` wrapper around `libs.secure_error_handler`

## The Wrapper Anti-Pattern (What to Avoid) ❌

### Bad Example: Unnecessary Abstraction
```python
# DON'T DO THIS - Pointless wrapper that adds no value
def handle_error(error: Exception) -> Dict:
    """Just passes through to library with no added benefit."""
    from libs.secure_error_handler import SecureErrorHandler
    handler = SecureErrorHandler(service_name="site-publisher")
    return handler.handle_error(error)
```

**Problems**:
- ❌ No value added
- ❌ Extra indirection for no reason
- ❌ Makes code harder to understand
- ❌ "Why not just use the library directly?"
- ❌ Maintenance burden (wrapper must stay in sync with library)

## When Thin Wrappers ARE Justified ✅

### 1. **Pre-configured Instance Pattern** (Our Case)

```python
# GOOD - Provides pre-configured service-specific instance
"""
Error handling wrapper for site-publisher.
Provides pre-configured SecureErrorHandler instance.
"""
from libs.secure_error_handler import SecureErrorHandler, ErrorSeverity
from typing import Any, Dict, Optional

# Single instance with service name pre-configured
_error_handler = SecureErrorHandler(service_name="site-publisher")


def handle_error(
    error: Exception,
    error_type: str = "general",
    user_message: Optional[str] = None,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Handle errors for site-publisher.
    
    Pre-configured with service_name="site-publisher" so every
    error log automatically includes correct service identifier.
    """
    return _error_handler.handle_error(
        error=error,
        error_type=error_type,
        severity=severity,
        context=context,
        user_message=user_message
    )
```

**Benefits**:
- ✅ **DRY Principle**: Service name configured once, not repeated in every call
- ✅ **Consistency**: Impossible to typo service name in different files
- ✅ **Convenience**: Simpler imports (`from error_handling import handle_error`)
- ✅ **Single Instance**: Shared handler instance (more efficient)
- ✅ **Clear Ownership**: This file "owns" error handling for this service

### Without Wrapper (Repetitive) ❌
```python
# app.py
from libs.secure_error_handler import SecureErrorHandler

handler = SecureErrorHandler(service_name="site-publisher")
result = handler.handle_error(exc, ...)

# site_builder.py  
from libs.secure_error_handler import SecureErrorHandler

handler = SecureErrorHandler(service_name="site-publisher")  # Repeated!
result = handler.handle_error(exc, ...)

# deployment.py
from libs.secure_error_handler import SecureErrorHandler

handler = SecureErrorHandler(service_name="site-publisher")  # Repeated!
result = handler.handle_error(exc, ...)
```

**Problems**:
- ❌ Service name repeated everywhere (DRY violation)
- ❌ Risk of typos ("site-publsher", "sitepublisher", etc.)
- ❌ Multiple handler instances created unnecessarily
- ❌ If service name changes, update in 10+ places

### With Wrapper (Clean) ✅
```python
# app.py
from error_handling import handle_error

result = handle_error(exc, ...)

# site_builder.py
from error_handling import handle_error

result = handle_error(exc, ...)

# deployment.py
from error_handling import handle_error

result = handle_error(exc, ...)
```

**Benefits**:
- ✅ Service name configured once
- ✅ Clean, simple imports
- ✅ Single handler instance
- ✅ Change service name in one place

## Alternative: Direct Import (When It's Better)

### Option 1: Import Library Directly
```python
# In every file that needs error handling
from libs.secure_error_handler import SecureErrorHandler, ErrorSeverity

# Must initialize with service name
handler = SecureErrorHandler(service_name="site-publisher")
result = handler.handle_error(error, ...)
```

**When to use**:
- ✅ Service name used ONLY once or twice in entire codebase
- ✅ Need different service names in same container (rare)
- ✅ Very simple application (1-2 files)

**When NOT to use**:
- ❌ Service name repeated across multiple files (our case)
- ❌ Want consistent error handling across all modules

### Option 2: Module-level Singleton
```python
# config.py or __init__.py
from libs.secure_error_handler import SecureErrorHandler

# Create singleton instance
error_handler = SecureErrorHandler(service_name="site-publisher")

# Then in other files:
from config import error_handler
result = error_handler.handle_error(error, ...)
```

**When to use**:
- ✅ Want to share handler instance across modules
- ✅ Already have a config/initialization module
- ✅ Don't mind accessing handler via attribute (`error_handler.handle_error()`)

**Our wrapper vs this**:
- Both approaches are valid
- Wrapper gives cleaner function-style API: `handle_error()`
- Singleton gives explicit handler object: `error_handler.handle_error()`
- Personal preference / team style choice

## The Site Publisher Case: Why Wrapper Makes Sense

### Specific Rationale

1. **Service Name Configuration** (Primary Benefit)
   - Service name "site-publisher" used in 6+ files
   - Pre-configuring eliminates repetition
   - Ensures consistency across all error logs

2. **Import Convenience**
   ```python
   # With wrapper - clean
   from error_handling import handle_error, ErrorSeverity
   
   # Without wrapper - verbose
   from libs.secure_error_handler import SecureErrorHandler, ErrorSeverity
   handler = SecureErrorHandler(service_name="site-publisher")
   ```

3. **Single Responsibility Boundary**
   - `error_handling.py` becomes the "error handling layer" for site-publisher
   - Clear separation: this file handles errors, others call it
   - Easier to add site-publisher-specific error handling later

4. **Testing Convenience**
   ```python
   # Test files can mock one location
   @patch('error_handling.handle_error')
   def test_something(mock_handler):
       ...
   
   # vs mocking in every test file
   @patch('libs.secure_error_handler.SecureErrorHandler')
   def test_something(mock_handler):
       ...
   ```

5. **Future Extension Point**
   If we need site-publisher-specific error handling:
   ```python
   def handle_error(error, ...):
       # Add site-publisher-specific logic
       if isinstance(error, HugoExecutionError):
           # Custom handling for Hugo errors
           severity = ErrorSeverity.HIGH
           error_type = "hugo_failure"
       
       return _error_handler.handle_error(error, ...)
   ```

## Decision Matrix: When to Use Thin Wrapper

| Scenario | Use Wrapper? | Rationale |
|----------|--------------|-----------|
| **Service-specific configuration** | ✅ YES | Pre-configure service name, environment, etc. |
| **Used in 3+ files** | ✅ YES | DRY principle, avoid repetition |
| **Consistent API needed** | ✅ YES | Ensure all callers use same pattern |
| **Future customization likely** | ✅ YES | Provides extension point |
| **Testing convenience** | ✅ YES | Single mock point |
| | | |
| **Simple pass-through only** | ❌ NO | Adds no value |
| **Used once or twice** | ❌ NO | Direct import simpler |
| **No configuration needed** | ❌ NO | Just re-exports, pointless |
| **Duplicates library API exactly** | ⚠️ MAYBE | Only if configuration/consistency needed |

## Alternative Approaches We Considered

### Option A: No Wrapper (Direct Import Everywhere)
```python
# Every file does:
from libs.secure_error_handler import SecureErrorHandler
handler = SecureErrorHandler(service_name="site-publisher")
```

**Rejected because**:
- Repeats service name in 6+ files
- Risk of inconsistency
- More verbose imports

### Option B: Config Module Singleton
```python
# config.py
error_handler = SecureErrorHandler(service_name="site-publisher")

# Usage:
from config import error_handler
error_handler.handle_error(...)
```

**Also valid! Could use this instead.**
- Slightly more explicit (shows it's a handler object)
- Less functional-style API
- Both approaches are defensible

### Option C: Our Chosen Wrapper
```python
# error_handling.py
_error_handler = SecureErrorHandler(service_name="site-publisher")

def handle_error(...):
    return _error_handler.handle_error(...)

# Usage:
from error_handling import handle_error
handle_error(...)
```

**Why we chose this**:
- Functional-style API (matches our pure functional design)
- Cleaner imports
- Clear "error handling layer" abstraction
- Easy to extend later if needed

## Common Wrapper Anti-Patterns to Avoid

### 1. The "Enterprise" Over-Abstraction
```python
# DON'T DO THIS
class ErrorHandlerFactory:
    def create_handler(self, service_name: str) -> AbstractErrorHandler:
        return ConcreteErrorHandlerImpl(
            strategy=ErrorHandlingStrategy(),
            formatter=ErrorFormatterStrategy(),
            ...
        )
```
**Problem**: Massive over-engineering for no benefit

### 2. The Leaky Abstraction
```python
# DON'T DO THIS
def handle_error(error):
    # Wrapper that forces you to know about underlying library
    return SecureErrorHandler(service_name="...").handle_error(
        error=error,
        # Oops, you need to know about ErrorSeverity from library
        severity=ErrorSeverity.MEDIUM  # Leaks library details
    )
```
**Problem**: Doesn't actually hide the library, just adds indirection

### 3. The "Framework Builder"
```python
# DON'T DO THIS
def handle_error(error, **kwargs):
    """
    Wraps SecureErrorHandler but might swap to LoggingErrorHandler
    or CustomErrorHandler based on config...
    """
    handler_class = get_error_handler_class_from_config()
    return handler_class(**kwargs).handle(error)
```
**Problem**: YAGNI - You Ain't Gonna Need It

## Our Wrapper: The Code

### Implementation (Simple & Clear)

```python
"""
Error handling for site-publisher.

Provides pre-configured SecureErrorHandler instance to ensure
consistent error handling across all site-publisher modules.

Why this wrapper exists:
1. Pre-configures service_name="site-publisher" (used in 6+ files)
2. Provides clean functional API matching our design patterns
3. Single instance shared across all modules (efficient)
4. Easy to mock in tests (one import location)
5. Extension point for site-publisher-specific error logic if needed

Usage:
    from error_handling import handle_error, ErrorSeverity
    
    result = handle_error(
        error=exc,
        error_type="validation",
        severity=ErrorSeverity.HIGH,
        context={"blob": "article.md"}
    )
"""
from libs.secure_error_handler import (
    SecureErrorHandler,
    ErrorSeverity,
    handle_error_safely  # Re-export for convenience
)
from typing import Any, Dict, Optional

# Pre-configured handler for site-publisher service
_error_handler = SecureErrorHandler(service_name="site-publisher")


def handle_error(
    error: Exception,
    error_type: str = "general",
    user_message: Optional[str] = None,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Handle errors securely for site-publisher.
    
    Pre-configured with service_name="site-publisher" so all error
    logs automatically include correct service identifier.
    
    Args:
        error: Exception that occurred
        error_type: Type of error (general, validation, authentication, etc.)
        user_message: Optional custom message for users
        severity: Error severity level
        context: Additional context (automatically sanitized)
    
    Returns:
        Sanitized error response with correlation ID
        
    Example:
        try:
            build_site()
        except Exception as e:
            return handle_error(
                error=e,
                error_type="hugo_failure",
                severity=ErrorSeverity.HIGH,
                context={"step": "build", "version": "0.138.0"}
            )
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
    """
    Create standardized HTTP error response for site-publisher.
    
    Returns format matching our API contract with pre-configured
    service name.
    
    Args:
        status_code: HTTP status code
        error: Optional exception for logging
        error_type: Type of error
        user_message: Optional custom message
        context: Additional context
    
    Returns:
        Standardized HTTP error response
    """
    return _error_handler.create_http_error_response(
        status_code=status_code,
        error=error,
        error_type=error_type,
        user_message=user_message,
        context=context
    )


# Re-export for convenience (callers don't need to import from libs)
__all__ = [
    "handle_error",
    "create_http_error_response",
    "ErrorSeverity",
    "SecureErrorHandler",
    "handle_error_safely",
]
```

**Total Lines**: ~70 (including docstrings and comments)
**Added Value**: Service name configuration, clean API, documentation

## Summary: Our Justification

### Why This Wrapper is NOT an Anti-Pattern

1. ✅ **Adds Real Value**: Pre-configures service name, eliminates repetition
2. ✅ **Used Widely**: 6+ files need error handling
3. ✅ **Clear Purpose**: Documented rationale in docstring
4. ✅ **Simple**: 2 functions, no complex logic
5. ✅ **Testable**: Easy to mock, doesn't complicate testing
6. ✅ **Maintainable**: If library API changes, update in one place
7. ✅ **Extension Point**: Can add site-publisher-specific logic if needed
8. ✅ **Follows Project Patterns**: Matches functional design philosophy

### Could We Skip It?

**Yes, alternatives exist:**
- Direct import with manual service name everywhere
- Config module singleton
- Module-level handler instance

**But wrapper is justified because:**
- Eliminates 6+ service name repetitions
- Cleaner API matches our functional design
- Clear abstraction boundary
- Minimal cost (~70 lines)

### The Principle

**Good wrapper**: Adds value through configuration, convenience, or consistency  
**Bad wrapper**: Pure pass-through that adds indirection with no benefit

Our wrapper adds **configuration** (service name) and **convenience** (clean API), so it's justified! ✅

---

**Verdict**: This is a **justified thin wrapper**, not an anti-pattern. The key is that it provides real value (pre-configuration + consistency) rather than just adding indirection.
