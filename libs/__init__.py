"""
Shared Libraries for AI Content Farm - FastAPI Native

FastAPI-native shared models and utilities using Pydantic response models
and dependency injection instead of complex exception handling.

Version: 2.0.0 - FastAPI-native API standardization (Aug 27, 2025)
"""

__version__ = "2.0.0"

# Import FastAPI-native shared models
from .shared_models import (  # Core FastAPI-native models; FastAPI dependencies; Helper functions; Data models; Legacy support (temporary)
    APIError,
    ContentItem,
    ErrorCodes,
    HealthStatus,
    ServiceStatus,
    StandardError,
    StandardResponse,
    StandardResponseFactory,
    add_standard_metadata,
    create_error_response,
    create_service_dependency,
    create_success_response,
    wrap_legacy_response,
)

try:
    from .blob_storage import BlobContainers, BlobStorageClient

    blob_storage_available = True
except ImportError:
    blob_storage_available = False

# Import secure error handler
from .secure_error_handler import ErrorSeverity, SecureErrorHandler, handle_error_safely

__all__ = [
    # FastAPI-native core
    "StandardResponse",
    "StandardError",
    "add_standard_metadata",
    "create_service_dependency",
    "create_success_response",
    "create_error_response",
    # Data models
    "HealthStatus",
    "ServiceStatus",
    "ContentItem",
    # Security
    "SecureErrorHandler",
    "ErrorSeverity",
    "handle_error_safely",
    # Legacy support
    "wrap_legacy_response",
]

if blob_storage_available:
    __all__.extend(["BlobStorageClient", "BlobContainers"])
# Test complete optimized pipeline: JSON formatting fixes applied
# 2025-08-26 Trival update for pipeline run
