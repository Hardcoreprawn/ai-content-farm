"""
Template Management Endpoints - Collection Template Management

RESTful endpoints for managing collection template source configurations.
Provides easy enable/disable functionality for content sources.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from libs.blob_storage import BlobStorageClient
from libs.shared_models import StandardResponse, create_service_dependency

# Create router for template management
router = APIRouter(prefix="/templates", tags=["templates"])

# Create service metadata dependency
service_metadata = create_service_dependency("content-womble")


class SourceToggleRequest(BaseModel):
    """Request model for toggling source status."""

    source_type: str = Field(
        ..., description="Type of source to toggle (reddit, rss, web, mastodon)"
    )
    enabled: bool = Field(..., description="Enable or disable the sources")


class SourceIndexToggleRequest(BaseModel):
    """Request model for toggling specific source by index."""

    source_index: int = Field(..., description="Index of source to toggle", ge=0)
    enabled: bool = Field(..., description="Enable or disable the source")


class TemplateSourceInfo(BaseModel):
    """Information about a template source."""

    index: int = Field(..., description="Source index in template")
    type: str = Field(..., description="Source type")
    enabled: bool = Field(..., description="Whether source is enabled")
    description: str = Field("", description="Source description/comment")
    config_summary: str = Field("", description="Summary of source configuration")


@router.get(
    "/sources",
    response_model=StandardResponse,
    summary="List Template Sources",
    description="Get list of all sources in the default collection template with their status",
)
async def list_template_sources(
    metadata: Dict[str, Any] = Depends(service_metadata),
):
    """
    List all sources in the default collection template.

    Shows enabled/disabled status and configuration summary for each source.
    """
    try:
        # Load default template
        template = await _load_default_template()
        sources = template.get("sources", [])

        source_list = []
        for i, source in enumerate(sources):
            enabled = source.get("enabled", True)
            source_type = source.get("type", "unknown")

            # Handle legacy _disabled_* format
            if any(key.startswith("_disabled_") for key in source.keys()):
                enabled = False
                # Extract nested source info
                for key, value in source.items():
                    if key.startswith("_disabled_") and isinstance(value, dict):
                        source_type = value.get("type", "legacy-disabled")
                        break

            # Create config summary
            config_summary = ""
            if source_type == "reddit":
                subreddits = source.get("subreddits", [])
                limit = source.get("limit", 0)
                config_summary = f"{len(subreddits)} subreddits, limit: {limit}"
            elif source_type == "rss":
                websites = source.get("websites", [])
                limit = source.get("limit", 0)
                config_summary = f"{len(websites)} feeds, limit: {limit}"
            elif source_type in ["mastodon", "web"]:
                limit = source.get("limit", 0)
                config_summary = f"limit: {limit}"

            source_info = TemplateSourceInfo(
                index=i,
                type=source_type,
                enabled=enabled,
                description=source.get("_comment", ""),
                config_summary=config_summary,
            )
            source_list.append(source_info)

        return StandardResponse(
            status="success",
            message=f"Retrieved {len(source_list)} template sources",
            data={
                "sources": [s.model_dump() for s in source_list],
                "template_path": "collection-templates/default.json",
                "enabled_count": sum(1 for s in source_list if s.enabled),
                "disabled_count": sum(1 for s in source_list if not s.enabled),
            },
            errors=[],
            metadata=metadata,
        )

    except Exception as e:
        return StandardResponse(
            status="error",
            message=f"Failed to list template sources: {str(e)}",
            data={},
            errors=[str(e)],
            metadata=metadata,
        )


@router.post(
    "/sources/toggle-type",
    response_model=StandardResponse,
    summary="Toggle Sources by Type",
    description="Enable or disable all sources of a specific type (reddit, rss, web, mastodon)",
)
async def toggle_sources_by_type(
    request: SourceToggleRequest,
    metadata: Dict[str, Any] = Depends(service_metadata),
):
    """
    Enable or disable all sources of a specific type.

    This is useful for quickly enabling/disabling all Reddit sources,
    all RSS feeds, etc.
    """
    try:
        # Load and modify template
        template = await _load_default_template()
        sources = template.get("sources", [])
        modified_count = 0

        for source in sources:
            # Handle legacy _disabled_* format by converting to new format
            if any(key.startswith("_disabled_") for key in source.keys()):
                # Find the nested source definition
                for key, value in source.items():
                    if key.startswith("_disabled_") and isinstance(value, dict):
                        if value.get("type") == request.source_type:
                            # Convert to new format
                            source.clear()
                            source.update(value)
                            source["enabled"] = request.enabled
                            modified_count += 1
                            break
            elif source.get("type") == request.source_type:
                source["enabled"] = request.enabled
                modified_count += 1

        # Save updated template
        await _save_default_template(template)

        action = "enabled" if request.enabled else "disabled"

        return StandardResponse(
            status="success",
            message=f"{action.capitalize()} {modified_count} {request.source_type} sources",
            data={
                "source_type": request.source_type,
                "enabled": request.enabled,
                "modified_count": modified_count,
                "action": action,
            },
            errors=[],
            metadata=metadata,
        )

    except Exception as e:
        return StandardResponse(
            status="error",
            message=f"Failed to toggle {request.source_type} sources: {str(e)}",
            data={},
            errors=[str(e)],
            metadata=metadata,
        )


@router.post(
    "/sources/toggle-index",
    response_model=StandardResponse,
    summary="Toggle Source by Index",
    description="Enable or disable a specific source by its index position",
)
async def toggle_source_by_index(
    request: SourceIndexToggleRequest,
    metadata: Dict[str, Any] = Depends(service_metadata),
):
    """
    Enable or disable a specific source by its index position.

    Use the /sources endpoint to see source indices.
    """
    try:
        # Load template
        template = await _load_default_template()
        sources = template.get("sources", [])

        if not 0 <= request.source_index < len(sources):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid source index {request.source_index}. Valid range: 0-{len(sources)-1}",
            )

        source = sources[request.source_index]
        source_type = source.get("type", "unknown")

        # Handle legacy _disabled_* format
        if any(key.startswith("_disabled_") for key in source.keys()):
            # Convert to new format
            for key, value in source.items():
                if key.startswith("_disabled_") and isinstance(value, dict):
                    source.clear()
                    source.update(value)
                    source_type = source.get("type", "unknown")
                    break

        source["enabled"] = request.enabled

        # Save updated template
        await _save_default_template(template)

        action = "enabled" if request.enabled else "disabled"

        return StandardResponse(
            status="success",
            message=f"{action.capitalize()} source {request.source_index} ({source_type})",
            data={
                "source_index": request.source_index,
                "source_type": source_type,
                "enabled": request.enabled,
                "action": action,
            },
            errors=[],
            metadata=metadata,
        )

    except HTTPException:
        raise
    except Exception as e:
        return StandardResponse(
            status="error",
            message=f"Failed to toggle source {request.source_index}: {str(e)}",
            data={},
            errors=[str(e)],
            metadata=metadata,
        )


async def _load_default_template() -> Dict:
    """Load the default collection template from local file."""
    template_path = (
        Path(__file__).parent.parent.parent / "collection-templates" / "default.json"
    )

    if template_path.exists():
        with open(template_path, "r") as f:
            return json.load(f)
    else:
        raise FileNotFoundError(f"Default template not found: {template_path}")


async def _save_default_template(template: Dict) -> None:
    """Save the default collection template to local file."""
    template_path = (
        Path(__file__).parent.parent.parent / "collection-templates" / "default.json"
    )

    # Ensure directory exists
    template_path.parent.mkdir(parents=True, exist_ok=True)

    with open(template_path, "w") as f:
        json.dump(template, f, indent=4)
