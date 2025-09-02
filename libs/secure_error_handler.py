#!/usr/bin/env python3
"""
Secure Error Handler for AI Content Farm

Provides OWASP-compliant error handling to prevent information disclosure
through error messages and stack traces.

OWASP Security Compliance:
- CWE-209: Prevents information exposure through error messages
- CWE-754: Implements proper error handling without data leakage
- CWE-532: Prevents insertion of sensitive information into log files
"""

import logging
import traceback
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional, Union


class ErrorSeverity(Enum):
    """Error severity levels for classification."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecureErrorHandler:
    """
    OWASP-compliant error handler that prevents information disclosure.

    Features:
    - Sanitizes error messages for public consumption
    - Generates correlation IDs for error tracking
    - Logs detailed errors securely without exposure
    - Provides standardized error responses
    """

    def __init__(self, service_name: str):
        """
        Initialize the secure error handler.

        Args:
            service_name: Name of the service using this handler
        """
        self.service_name = service_name
        self.logger = logging.getLogger(f"{service_name}.security")

        # Common safe error messages
        self._safe_messages = {
            "general": "An error occurred while processing your request",
            "validation": "Invalid input provided",
            "authentication": "Authentication required",
            "authorization": "Access denied",
            "not_found": "Requested resource not found",
            "rate_limit": "Rate limit exceeded",
            "service_unavailable": "Service temporarily unavailable",
            "timeout": "Request timeout occurred",
            "configuration": "Service configuration error",
        }

    def handle_error(
        self,
        error: Exception,
        error_type: str = "general",
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Securely handle an error with proper logging and sanitized response.

        Args:
            error: The exception that occurred
            error_type: Type of error for message selection
            severity: Severity level for logging
            context: Additional context (will be sanitized)
            user_message: Custom safe message for users

        Returns:
            Sanitized error response safe for public consumption
        """
        # Generate correlation ID for tracking
        correlation_id = str(uuid.uuid4())

        # Create sanitized context (remove sensitive data)
        safe_context = self._sanitize_context(context or {})

        # Log detailed error securely (internal only)
        self._log_detailed_error(
            error=error,
            correlation_id=correlation_id,
            severity=severity,
            context=safe_context,
        )

        # Return sanitized response for public consumption
        return {
            "error_id": correlation_id,
            "message": user_message
            or self._safe_messages.get(error_type, self._safe_messages["general"]),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": self.service_name,
        }

    def _sanitize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove sensitive information from context before logging.

        Args:
            context: Raw context dictionary

        Returns:
            Sanitized context safe for logging
        """
        sensitive_keys = {
            "password",
            "secret",
            "key",
            "token",
            "credential",
            "authorization",
            "auth",
            "session",
            "cookie",
            "connection_string",
            "sas_token",
            "api_key",
        }

        sanitized = {}
        for key, value in context.items():
            key_lower = key.lower()

            # Check if key contains sensitive information
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, str) and len(value) > 100:
                # Truncate very long strings that might contain sensitive data
                sanitized[key] = value[:100] + "...[TRUNCATED]"
            elif isinstance(value, dict):
                # Recursively sanitize nested dictionaries
                sanitized[key] = self._sanitize_context(value)
            else:
                sanitized[key] = value

        return sanitized

    def _log_detailed_error(
        self,
        error: Exception,
        correlation_id: str,
        severity: ErrorSeverity,
        context: Dict[str, Any],
    ) -> None:
        """
        Log detailed error information securely (internal only).

        Args:
            error: The exception that occurred
            correlation_id: Unique ID for tracking
            severity: Error severity level
            context: Sanitized context information
        """
        # Determine log level based on severity
        log_level = {
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL,
        }.get(severity, logging.ERROR)

        # Create detailed log entry (safe for internal logs)
        log_data = {
            "correlation_id": correlation_id,
            "service": self.service_name,
            "error_type": type(error).__name__,
            "severity": severity.value,
            "context": context,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Log with appropriate level
        self.logger.log(
            log_level,
            f"Error {correlation_id}: {type(error).__name__} in {self.service_name}",
            extra=log_data,
        )

        # For critical errors, also log stack trace (internal only)
        if severity == ErrorSeverity.CRITICAL:
            self.logger.critical(
                f"Stack trace for {correlation_id}: {traceback.format_exc()}",
                extra={"correlation_id": correlation_id},
            )

    def create_http_error_response(
        self,
        status_code: int,
        error: Optional[Exception] = None,
        error_type: str = "general",
        user_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a standardized HTTP error response.

        Args:
            status_code: HTTP status code
            error: Optional exception for logging
            error_type: Type of error for message selection
            user_message: Custom safe message for users
            context: Additional context (will be sanitized)

        Returns:
            Standardized HTTP error response
        """
        # Determine severity based on status code
        severity = self._get_severity_from_status(status_code)

        # Handle error if provided
        error_details = {}
        if error:
            error_details = self.handle_error(
                error=error,
                error_type=error_type,
                severity=severity,
                context=context,
                user_message=user_message,
            )
        else:
            # Create minimal error response without exception
            error_details = {
                "error_id": str(uuid.uuid4()),
                "message": user_message
                or self._safe_messages.get(error_type, self._safe_messages["general"]),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "service": self.service_name,
            }

        return {
            "status": "error",
            "message": error_details["message"],
            "data": None,
            "errors": [error_details["message"]],
            "metadata": {
                "function": self.service_name,
                "timestamp": error_details["timestamp"],
                "version": "1.0.0",
                "error_id": error_details["error_id"],
            },
        }

    def _get_severity_from_status(self, status_code: int) -> ErrorSeverity:
        """
        Determine error severity from HTTP status code.

        Args:
            status_code: HTTP status code

        Returns:
            Appropriate error severity level
        """
        if status_code < 400:
            return ErrorSeverity.LOW
        elif status_code < 500:
            return ErrorSeverity.MEDIUM
        elif status_code < 600:
            return ErrorSeverity.HIGH
        else:
            return ErrorSeverity.CRITICAL


# Convenience function for quick error handling
def handle_error_safely(
    service_name: str,
    error: Exception,
    error_type: str = "general",
    user_message: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Quick function to handle errors securely.

    Args:
        service_name: Name of the service
        error: The exception that occurred
        error_type: Type of error for message selection
        user_message: Custom safe message for users
        context: Additional context (will be sanitized)

    Returns:
        Sanitized error response
    """
    handler = SecureErrorHandler(service_name)
    return handler.handle_error(
        error=error, error_type=error_type, user_message=user_message, context=context
    )
