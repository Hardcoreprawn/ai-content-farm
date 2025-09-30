"""
Site Generator Exception Hierarchy

Provides structured exception types for the site generator container,
following established patterns and integrating with SecureErrorHandler.

Uses standard library approaches and proper error handling patterns.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from libs import SecureErrorHandler

logger = logging.getLogger(__name__)
error_handler = SecureErrorHandler("site-generator-exceptions")


class SiteGeneratorError(Exception):
    """
    Base exception for all site generator operations.

    Provides structured error information with optional context details
    for debugging and error reporting, integrated with SecureErrorHandler.

    Args:
        message: Human-readable error description
        details: Additional context information (will be sanitized)
        error_code: Machine-readable error code for categorization

    Example:
        >>> try:
        ...     process_content()
        ... except SiteGeneratorError as e:
        ...     logger.error(f"Operation failed [{e.error_code}]: {e}")
        ...     # Access sanitized details safely
        ...     context = e.get_safe_context()
    """

    def __init__(
        self,
        message: str,
        *,
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
    ):
        super().__init__(message)
        self.details = details or {}
        self.error_code = error_code
        self._safe_context: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:
        """Return formatted error message with context."""
        base_msg = super().__str__()
        if self.error_code:
            return f"[{self.error_code}] {base_msg}"
        return base_msg

    def get_safe_context(self) -> Dict[str, Any]:
        """
        Get sanitized context information safe for logging.

        Returns:
            Sanitized context dictionary
        """
        if self._safe_context is None:
            try:
                # Use SecureErrorHandler to sanitize context
                sanitized = error_handler.handle_error(
                    error=None, error_type="context_sanitization", context=self.details
                )
                self._safe_context = sanitized.get("context", {})
            except Exception:
                # Fallback to empty context if sanitization fails
                self._safe_context = {}

        return self._safe_context


class ConfigurationError(SiteGeneratorError):
    """
    Raised when configuration is invalid, missing, or incomplete.

    Examples:
        - Missing required environment variables
        - Invalid Azure storage URLs
        - Malformed configuration files

    Args:
        message: Error description
        config_key: Specific configuration key that failed
        **kwargs: Additional context passed to parent

    Example:
        >>> if not storage_url:
        ...     raise ConfigurationError(
        ...         "Azure storage URL is required",
        ...         config_key="AZURE_STORAGE_ACCOUNT_URL",
        ...         details={"section": "storage_config"}
        ...     )
    """

    def __init__(self, message: str, *, config_key: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="CONFIG_ERROR", **kwargs)
        if config_key:
            self.details["config_key"] = config_key


class ContentProcessingError(SiteGeneratorError):
    """
    Raised when content processing operations fail.

    Examples:
        - Markdown parsing failures
        - Template rendering errors
        - Content validation failures

    Args:
        message: Error description
        operation: Specific operation that failed
        **kwargs: Additional context passed to parent

    Example:
        >>> try:
        ...     render_template(data)
        ... except TemplateError as e:
        ...     raise ContentProcessingError(
        ...         "Template rendering failed",
        ...         operation="template_render",
        ...         details={"template": template_name}
        ...     ) from e
    """

    def __init__(self, message: str, *, operation: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="PROCESSING_ERROR", **kwargs)
        if operation:
            self.details["operation"] = operation


class StorageError(SiteGeneratorError):
    """
    Raised when storage operations fail.

    Examples:
        - Blob upload/download failures
        - Container access denied
        - Network connectivity issues

    Args:
        message: Error description
        container: Storage container name
        blob_name: Specific blob name
        **kwargs: Additional context passed to parent

    Example:
        >>> try:
        ...     await blob_client.upload_blob(container, name, data)
        ... except Exception as e:
        ...     raise StorageError(
        ...         "Failed to upload content",
        ...         container=container,
        ...         blob_name=name
        ...     ) from e
    """

    def __init__(
        self,
        message: str,
        *,
        container: Optional[str] = None,
        blob_name: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(message, error_code="STORAGE_ERROR", **kwargs)
        if container:
            self.details["container"] = container
        if blob_name:
            self.details["blob_name"] = blob_name


class ValidationError(SiteGeneratorError):
    """
    Raised when data validation fails.

    Examples:
        - Invalid input parameters
        - Schema validation failures
        - Business rule violations

    Args:
        message: Error description
        field_name: Specific field that failed validation
        validation_rule: Rule that was violated
        **kwargs: Additional context passed to parent

    Example:
        >>> if batch_size <= 0:
        ...     raise ValidationError(
        ...         "Batch size must be positive",
        ...         field_name="batch_size",
        ...         validation_rule="positive_integer",
        ...         details={"provided_value": batch_size}
        ...     )
    """

    def __init__(
        self,
        message: str,
        *,
        field_name: Optional[str] = None,
        validation_rule: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(message, error_code="VALIDATION_ERROR", **kwargs)
        if field_name:
            self.details["field_name"] = field_name
        if validation_rule:
            self.details["validation_rule"] = validation_rule


class ThemeError(SiteGeneratorError):
    """
    Raised when theme operations fail.

    Examples:
        - Theme not found
        - Template compilation errors
        - Asset loading failures

    Args:
        message: Error description
        theme_name: Name of the theme that failed
        **kwargs: Additional context passed to parent
    """

    def __init__(self, message: str, *, theme_name: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="THEME_ERROR", **kwargs)
        if theme_name:
            self.details["theme_name"] = theme_name
