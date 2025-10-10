"""
Error handling wrapper for site-publisher.

Uses shared libs.secure_error_handler.SecureErrorHandler for
OWASP-compliant error handling with UUID correlation IDs.
"""

from typing import Any, Dict, Optional

from libs.secure_error_handler import (
    ErrorSeverity,
    SecureErrorHandler,
    handle_error_safely,
)

# Pre-configured handler for site-publisher service
_error_handler = SecureErrorHandler(service_name="site-publisher")


def handle_error(
    error: Exception,
    error_type: str = "general",
    user_message: Optional[str] = None,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Handle errors securely for site-publisher.

    Pre-configured with service_name="site-publisher" so all error
    logs automatically include correct service identifier.

    Features:
    - Automatic UUID correlation IDs for tracking
    - Sensitive data sanitization (passwords, tokens, keys)
    - OWASP-compliant (CWE-209, CWE-754, CWE-532)
    - Severity-based logging
    - Stack traces only for critical errors

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
        user_message=user_message,
    )


def create_http_error_response(
    status_code: int,
    error: Optional[Exception] = None,
    error_type: str = "general",
    user_message: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
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
        context=context,
    )


# Re-export for convenience (callers don't need to import from libs)
__all__ = [
    "handle_error",
    "create_http_error_response",
    "ErrorSeverity",
    "SecureErrorHandler",
    "handle_error_safely",
]
