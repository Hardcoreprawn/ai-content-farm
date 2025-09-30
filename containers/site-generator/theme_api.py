"""
Theme Management API Endpoints

FastAPI router for theme management functionality including listing,
validation, and preview generation.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from theme_manager import ThemeManager

from libs import SecureErrorHandler
from libs.shared_models import StandardResponse, create_success_response

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/themes", tags=["themes"])

# Initialize error handler
error_handler = SecureErrorHandler("theme-api")


def get_theme_manager() -> ThemeManager:
    """
    Get ThemeManager instance with templates directory.

    Creates and returns a configured ThemeManager instance pointing to the
    standard templates directory for theme management operations.

    Returns:
        ThemeManager: Configured theme manager instance

    Examples:
        >>> manager = get_theme_manager()
        >>> themes = manager.list_themes()
        >>> len(themes) >= 0
        True

        >>> # Use for theme operations
        >>> manager = get_theme_manager()
        >>> is_valid = manager.validate_theme("minimal")
        >>> isinstance(is_valid, dict)
        True
    """
    return ThemeManager(Path("templates"))


@router.get("", response_model=StandardResponse)
async def list_themes() -> Dict[str, Any]:
    """
    List all available themes.

    Retrieves all available themes from the templates directory with their
    metadata and validation status.

    Returns:
        Dict[str, Any]: StandardResponse with theme list and metadata

    Raises:
        HTTPException: If theme directory is inaccessible

    Examples:
        Response format:
        {
            "status": "success",
            "message": "Retrieved 3 themes",
            "data": {
                "themes": [
                    {
                        "name": "minimal",
                        "display_name": "Minimal Theme",
                        "description": "Clean, minimal design",
                        "version": "1.0.0",
                        "author": "AI Content Farm",
                        "validation": {"is_valid": True, "errors": []}
                    }
                ],
                "total_count": 1
            }
        }
    """
    try:
        theme_manager = get_theme_manager()
        themes = theme_manager.list_themes()

        theme_list = []
        for theme in themes:
            validation = theme_manager.validate_theme(theme.name)
            theme_list.append(
                {
                    "name": theme.name,
                    "display_name": theme.display_name,
                    "description": theme.description,
                    "version": theme.version,
                    "author": theme.author,
                    "grid_layout": theme.grid_layout,
                    "tech_optimized": theme.tech_optimized,
                    "responsive": theme.responsive,
                    "supports_dark_mode": theme.supports_dark_mode,
                    "is_valid": validation["valid"],
                    "validation_errors": validation["errors"],
                    "validation_warnings": validation["warnings"],
                }
            )

        return create_success_response(
            message=f"Found {len(theme_list)} available themes",
            data={
                "themes": theme_list,
                "default_theme": theme_manager.get_default_theme(),
            },
            metadata={
                "function": "theme-api",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "1.0.0",
            },
        )
    except Exception as e:
        error_response = error_handler.create_http_error_response(
            status_code=500,
            error=e,
            error_type="general",
            user_message="Failed to list themes",
        )
        raise HTTPException(status_code=500, detail=error_response)


@router.get("/{theme_name}", response_model=StandardResponse)
async def get_theme_details(theme_name: str) -> Dict[str, Any]:
    """Get detailed information about a specific theme."""
    try:
        theme_manager = get_theme_manager()
        metadata = theme_manager.get_theme(theme_name)

        if not metadata:
            raise HTTPException(
                status_code=404, detail=f"Theme '{theme_name}' not found"
            )

        validation = theme_manager.validate_theme(theme_name)
        assets = theme_manager.get_theme_assets(theme_name)

        return create_success_response(
            message=f"Theme details for '{theme_name}'",
            data={
                "name": metadata.name,
                "display_name": metadata.display_name,
                "description": metadata.description,
                "version": metadata.version,
                "author": metadata.author,
                "preview_image": metadata.preview_image,
                "grid_layout": metadata.grid_layout,
                "tech_optimized": metadata.tech_optimized,
                "responsive": metadata.responsive,
                "supports_dark_mode": metadata.supports_dark_mode,
                "is_valid": validation["valid"],
                "validation_errors": validation["errors"],
                "validation_warnings": validation["warnings"],
                "template_files": metadata.template_files,
                "assets": [str(asset) for asset in assets],
                "created_at": (
                    metadata.created_at.isoformat() if metadata.created_at else None
                ),
                "updated_at": (
                    metadata.updated_at.isoformat() if metadata.updated_at else None
                ),
            },
            metadata={
                "function": "theme-api",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "1.0.0",
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        error_response = error_handler.create_http_error_response(
            status_code=500,
            error=e,
            error_type="general",
            user_message=f"Failed to get details for theme '{theme_name}'",
        )
        raise HTTPException(status_code=500, detail=error_response)


@router.post("/{theme_name}/validate", response_model=StandardResponse)
async def validate_theme_endpoint(theme_name: str) -> Dict[str, Any]:
    """Validate a theme's structure and templates."""
    try:
        theme_manager = get_theme_manager()

        if not theme_manager.get_theme(theme_name):
            raise HTTPException(
                status_code=404, detail=f"Theme '{theme_name}' not found"
            )

        validation = theme_manager.validate_theme(theme_name)

        return create_success_response(
            message=f"Theme validation {'passed' if validation['valid'] else 'failed'} for '{theme_name}'",
            data={
                "theme_name": theme_name,
                "is_valid": validation["valid"],
                "validation_errors": validation["errors"],
                "validation_warnings": validation["warnings"],
                "validated_at": datetime.now(timezone.utc).isoformat(),
            },
            metadata={
                "function": "theme-api",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "1.0.0",
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        error_response = error_handler.create_http_error_response(
            status_code=500,
            error=e,
            error_type="general",
            user_message=f"Failed to validate theme '{theme_name}'",
        )
        raise HTTPException(status_code=500, detail=error_response)


@router.get("/{theme_name}/preview", response_model=StandardResponse)
async def preview_theme(theme_name: str) -> Dict[str, Any]:
    """Generate a preview of a theme with sample content."""
    try:
        theme_manager = get_theme_manager()

        if not theme_manager.get_theme(theme_name):
            raise HTTPException(
                status_code=404, detail=f"Theme '{theme_name}' not found"
            )

        # Validate theme first
        validation = theme_manager.validate_theme(theme_name)
        if not validation["valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"Theme '{theme_name}' failed validation: {', '.join(validation['errors'])}",
            )

        # For now, return mock preview data since we need site_generator integration
        # This will be implemented when the blob storage migration is complete
        mock_preview_data = {
            "theme_name": theme_name,
            "preview_url": f"/preview/{theme_name}",
            "site_id": f"preview_{theme_name}",
            "pages_generated": 5,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "validation_warnings": validation["warnings"],
            "note": "Preview generation requires site generator integration",
        }

        return create_success_response(
            message=f"Preview metadata generated for theme '{theme_name}'",
            data=mock_preview_data,
            metadata={
                "function": "theme-api",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "1.0.0",
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        error_response = error_handler.create_http_error_response(
            status_code=500,
            error=e,
            error_type="general",
            user_message=f"Failed to generate preview for theme '{theme_name}'",
        )
        raise HTTPException(status_code=500, detail=error_response)
