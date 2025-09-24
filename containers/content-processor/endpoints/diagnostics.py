"""
Diagnostics Endpoints - Health, Status, and Troubleshooting

RESTful endpoints for service health checks and diagnostic information.
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends

from config import ENVIRONMENT, settings
from libs.shared_models import StandardResponse, create_service_dependency
from libs.standard_endpoints import (
    create_standard_health_endpoint,
    create_standard_root_endpoint,
    create_standard_status_endpoint,
)

# Create router for diagnostics
router = APIRouter(tags=["diagnostics"])

# Create service metadata dependency
service_metadata = create_service_dependency("content-processor")

# Standard endpoints
router.add_api_route(
    "/",
    create_standard_root_endpoint(
        service_name="content-processor",
        description="AI-powered content processing service",
        version=settings.service_version,
    ),
    methods=["GET"],
    summary="Service Root",
    description="Get basic information about the content processor service",
)

router.add_api_route(
    "/health",
    create_standard_health_endpoint(
        service_name="content-processor",
        version=settings.service_version,
        environment=ENVIRONMENT,
        service_metadata_dep=service_metadata,
    ),
    methods=["GET"],
    summary="Health Check",
    description="Check service health and dependencies",
)

router.add_api_route(
    "/status",
    create_standard_status_endpoint(
        service_name="content-processor",
        version=settings.service_version,
        environment=ENVIRONMENT,
        service_metadata_dep=service_metadata,
    ),
    methods=["GET"],
    summary="Service Status",
    description="Get detailed service status and configuration",
)


@router.get(
    "/processing/diagnostics",
    response_model=StandardResponse,
    summary="Processing Diagnostics",
    description="Get content processing service diagnostics",
    tags=["diagnostics"],
)
async def get_processing_diagnostics(
    metadata: Dict[str, Any] = Depends(service_metadata),
) -> StandardResponse:
    """Get content processing service diagnostics."""
    try:
        # Basic processing service checks
        diagnostics = {
            "processing_service": "available",
            "ai_models": {
                "openai": "configured" if _check_openai_config() else "not_configured",
                "anthropic": (
                    "configured" if _check_anthropic_config() else "not_configured"
                ),
            },
            "storage": {
                "blob_storage": "available" if _check_blob_storage() else "unavailable",
            },
            "dependencies": {
                "content_generator": (
                    "available" if _check_content_generator() else "unavailable"
                ),
                "processing_service": (
                    "available" if _check_processing_service() else "unavailable"
                ),
            },
            "environment": ENVIRONMENT,
        }

        return StandardResponse(
            status="success",
            message="Content processor diagnostics retrieved successfully",
            data=diagnostics,
            errors=None,
            metadata=metadata,
        )

    except Exception as e:
        return StandardResponse(
            status="error",
            message=f"Failed to get diagnostics: {str(e)}",
            data=None,
            errors=[str(e)],
            metadata=metadata,
        )


def _check_openai_config() -> bool:
    """Check if OpenAI is properly configured."""
    try:
        import os

        return bool(os.getenv("OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_ENDPOINT"))
    except Exception:
        return False


def _check_anthropic_config() -> bool:
    """Check if Anthropic is properly configured."""
    try:
        import os

        return bool(os.getenv("ANTHROPIC_API_KEY"))
    except Exception:
        return False


def _check_blob_storage() -> bool:
    """Check if blob storage is available."""
    try:
        from libs import BlobStorageClient

        storage = BlobStorageClient()
        # Simple check - if we can create client, it's configured
        return True
    except Exception:
        return False


def _check_content_generator() -> bool:
    """Check if content generator is available."""
    try:
        from content_generation import get_content_generator

        generator = get_content_generator()
        return True
    except Exception:
        return False


def _check_processing_service() -> bool:
    """Check if processing service is available."""
    try:
        from processing_service import ContentProcessingService

        from config import settings

        processor = ContentProcessingService(settings)
        return True
    except Exception:
        return False
