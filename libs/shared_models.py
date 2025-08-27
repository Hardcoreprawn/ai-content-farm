"""
Shared API Models for Content Platform - FastAPI Native

FastAPI-native standardized response formats using Pydantic response models,
dependency injection, and natural FastAPI patterns instead of complex exception handling.

Key Benefits:
- Works WITH FastAPI instead of against it
- Type-safe with automatic validation and OpenAPI docs
- Simpler to implement, test, and maintain
- Better performance (no exception handler overhead)
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class ErrorCodes:
    """Standard error codes for API responses"""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    RATE_LIMIT_ERROR = "RATE_LIMIT_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"

    # Backward compatibility methods for old exception handler approach
    @classmethod
    def internal_error(cls, message: str, details: Optional[str] = None):
        """Create internal error response - backward compatibility"""
        return APIError(message=message, code=cls.INTERNAL_ERROR, details=details)

    @classmethod
    def validation_error(cls, field: str, message: str):
        """Create validation error response - backward compatibility"""
        return APIError(
            message=f"Validation error in {field}: {message}", code=cls.VALIDATION_ERROR
        )

    @classmethod
    def not_found(cls, resource: str):
        """Create not found error response - backward compatibility"""
        return APIError(message=f"{resource} not found", code=cls.NOT_FOUND)

    @classmethod
    def unauthorized(cls, message: str):
        """Create unauthorized error response - backward compatibility"""
        return APIError(message=message, code=cls.AUTHENTICATION_ERROR)

    @classmethod
    def forbidden(cls, message: str):
        """Create forbidden error response - backward compatibility"""
        return APIError(message=message, code=cls.AUTHORIZATION_ERROR)


class HealthStatus(BaseModel):
    """Health status model for health check endpoints"""

    status: str = Field(..., description="Health status: healthy|warning|error")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    issues: Optional[List[str]] = Field(
        default_factory=list, description="Any health issues"
    )


class ServiceStatus(BaseModel):
    """Service status model for status endpoints"""

    service: str = Field(..., description="Service name")
    status: str = Field(..., description="Service status: running|stopped|error")
    uptime_seconds: Optional[float] = Field(
        None, description="Service uptime in seconds"
    )
    stats: Optional[Dict[str, Any]] = Field(None, description="Service statistics")


class StandardResponse(BaseModel):
    """
    FastAPI-native standard response format using Pydantic response models.

    Used with response_model=StandardResponse on FastAPI endpoints.

    Example:
        @app.get("/api/service/health", response_model=StandardResponse)
        async def health():
            return StandardResponse(
                status="success",
                message="Service healthy",
                data={"service": "content-ranker"},
                metadata={"timestamp": "2025-08-27T10:00:00Z"}
            )
    """

    status: str = Field(..., description="success|error|processing")
    message: str = Field(..., description="Human-readable description")
    data: Optional[Any] = Field(None, description="Response data")
    errors: Optional[List[str]] = Field(None, description="Error details")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Response metadata"
    )


class StandardError(BaseModel):
    """
    FastAPI-native error response for HTTPException detail field.

    Used with HTTPException for consistent error responses.

    Example:
        raise HTTPException(
            status_code=404,
            detail=StandardError(
                message="Resource not found",
                errors=["The requested item does not exist"],
                metadata={"function": "content-ranker"}
            ).model_dump()
        )
    """

    status: str = Field(default="error", description="Always 'error' for errors")
    message: str = Field(..., description="Error message")
    errors: Optional[List[str]] = Field(None, description="Detailed error information")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Error metadata")


# FastAPI Dependencies for automatic metadata injection
async def add_standard_metadata(service: str) -> Dict[str, Any]:
    """
    FastAPI dependency to automatically add standard metadata to responses.

    Args:
        service: Service name (e.g., "content-collector")

    Returns:
        Dictionary with timestamp, function, and version metadata
    """
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "function": service,
        "version": "1.0.0",
    }


def create_service_dependency(service_name: str):
    """
    Factory to create service-specific metadata dependencies.

    Args:
        service_name: Name of the service (e.g., "content-collector")

    Returns:
        FastAPI dependency function for the service

    Example:
        service_metadata = create_service_dependency("content-collector")

        @app.get("/health", response_model=StandardResponse)
        async def health(metadata: Dict = Depends(service_metadata)):
            return StandardResponse(...)
    """

    async def service_metadata() -> Dict[str, Any]:
        return await add_standard_metadata(service_name)

    return service_metadata


# Helper functions for common response patterns
def create_success_response(
    message: str, data: Optional[Any] = None, metadata: Optional[Dict[str, Any]] = None
) -> StandardResponse:
    """Helper to create success responses."""
    return StandardResponse(
        status="success",
        message=message,
        data=data,
        errors=None,
        metadata=metadata or {},
    )


def create_error_response(
    message: str,
    errors: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> StandardError:
    """Helper to create error responses for HTTPException."""
    return StandardError(message=message, errors=errors, metadata=metadata or {})


# Health and Status Models (still useful for structured data)
class HealthStatus(BaseModel):
    """Standard health check response data structure."""

    status: str = Field(..., description="healthy|warning|unhealthy")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    dependencies: Dict[str, bool] = Field(
        default_factory=dict, description="Dependency health"
    )
    issues: List[str] = Field(default_factory=list, description="Health issues")
    uptime_seconds: Optional[float] = Field(None, description="Service uptime")
    environment: Optional[str] = Field(None, description="Environment name")


class ServiceStatus(BaseModel):
    """Standard status response data structure."""

    service: str = Field(..., description="Service name")
    status: str = Field(..., description="Service status")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    uptime_seconds: Optional[float] = Field(None, description="Service uptime")
    stats: Dict[str, Any] = Field(
        default_factory=dict, description="Service statistics"
    )
    last_operation: Optional[Dict[str, Any]] = Field(
        None, description="Last operation details"
    )
    configuration: Dict[str, Any] = Field(
        default_factory=dict, description="Current configuration"
    )


class ContentItem(BaseModel):
    """Standard content item interface across all services."""

    id: str = Field(..., description="Unique identifier")
    title: str = Field(..., description="Content title")
    content: Optional[str] = Field(None, description="Content body")
    url: Optional[str] = Field(None, description="Source URL")
    published_at: Optional[datetime] = Field(None, description="Publication timestamp")

    # Metadata containers for different processing stages
    source_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Source metadata"
    )
    processing_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Processing metadata"
    )
    enrichment_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Enrichment metadata"
    )


# Legacy wrapper function for backward compatibility during transition
def wrap_legacy_response(
    legacy_data: Any, message: str = "Operation completed"
) -> StandardResponse:
    """
    Temporary helper to wrap legacy responses in StandardResponse format.
    Use during transition period only.
    """
    return StandardResponse(
        status="success",
        message=message,
        data=legacy_data if isinstance(legacy_data, dict) else {"result": legacy_data},
        errors=None,
        metadata={
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "legacy_wrapper": True,
        },
    )


# Backward compatibility classes for containers still using old API
class APIError(BaseModel):
    """Backward compatibility class for containers using old exception handler approach"""

    message: str
    code: str = "INTERNAL_ERROR"
    details: Optional[Any] = None
    function_name: Optional[str] = None  # For backward compatibility

    def to_standard_response(self) -> StandardResponse:
        """Convert APIError to StandardResponse format for backward compatibility"""
        metadata = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error_code": self.code,
        }
        if self.function_name:
            metadata["function"] = self.function_name

        return StandardResponse(
            status="error",
            message=self.message,
            data=None,
            errors=[self.details] if self.details else None,
            metadata=metadata,
        )


# Backward compatibility factory class for old StandardResponse usage
class StandardResponseFactory:
    """Factory class providing backward compatibility for StandardResponse.success() and .error() methods"""

    @staticmethod
    def success(
        message: str, data: Any = None, metadata: Optional[Dict[str, Any]] = None
    ):
        """Create success response - backward compatibility method"""
        return StandardResponse(
            status="success",
            message=message,
            data=data,
            errors=None,
            metadata=metadata or {"timestamp": datetime.now(timezone.utc).isoformat()},
        )

    @staticmethod
    def error(
        message: str,
        errors: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Create error response - backward compatibility method"""
        return StandardResponse(
            status="error",
            message=message,
            data=None,
            errors=errors,
            metadata=metadata or {"timestamp": datetime.now(timezone.utc).isoformat()},
        )


# For backward compatibility - create an alias
# Use: from libs.shared_models import StandardResponseFactory as StandardResponse
# Then: StandardResponse.success("message", data)
