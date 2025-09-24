"""
Sources Endpoints - Source Configuration and Metadata

RESTful endpoints for managing content source configurations.
"""

from typing import Any, Dict

from collectors.factory import CollectorFactory
from fastapi import APIRouter, Depends
from source_collectors import SourceCollectorFactory

from libs.shared_models import StandardResponse, create_service_dependency

# Create router for sources
router = APIRouter(prefix="/sources", tags=["sources"])

# Create service metadata dependency
service_metadata = create_service_dependency("content-womble")


@router.get(
    "",
    response_model=StandardResponse,
    summary="List Available Sources",
    description="Get list of available content sources and their configurations",
)
async def list_sources(
    metadata: Dict[str, Any] = Depends(service_metadata),
):
    """
    Get available content sources and their configuration options.

    Returns information about supported source types (Reddit, RSS, etc.)
    and their configuration requirements.
    """
    try:
        # Dynamically discover available collectors from factory
        sources_info = {}

        # Get all registered collectors
        for source_type in CollectorFactory.COLLECTORS.keys():
            if source_type == "reddit":
                # Get Reddit collector information with authentication details
                reddit_info = SourceCollectorFactory.get_reddit_collector_info()
                sources_info["reddit"] = {
                    "type": "reddit",
                    "description": "Reddit content collection via public API or PRAW",
                    "parameters": {
                        "subreddits": "List of subreddit names (required)",
                        "limit": "Number of posts to collect (max 100)",
                        "sort": "Sort type: hot, new, top, rising (default: hot)",
                    },
                    "authentication": reddit_info.get(
                        "authentication_status", "unauthenticated"
                    ),
                    "recommended_collector": reddit_info.get(
                        "recommended_collector", "RedditPublicCollector"
                    ),
                    "status": reddit_info.get("status", "available"),
                }
            elif source_type == "mastodon":
                sources_info["mastodon"] = {
                    "type": "mastodon",
                    "description": "Mastodon social network content collection",
                    "parameters": {
                        "server_url": "Mastodon server URL (e.g., mastodon.social)",
                        "hashtags": "List of hashtags to monitor",
                        "limit": "Number of posts to collect per request",
                    },
                    "authentication": "none_required",
                    "status": "available",
                }
            elif source_type == "rss":
                sources_info["rss"] = {
                    "type": "rss",
                    "description": "RSS feed content collection",
                    "parameters": {
                        "feed_urls": "List of RSS feed URLs (required)",
                        "limit": "Number of items to collect per feed",
                    },
                    "authentication": "none_required",
                    "status": "available",
                }
            elif source_type == "web":
                sources_info["web"] = {
                    "type": "web",
                    "description": "Web content scraping",
                    "parameters": {
                        "urls": "List of web page URLs (required)",
                        "extract_text": "Whether to extract text content",
                    },
                    "authentication": "none_required",
                    "status": "available",
                }

        return StandardResponse(
            status="success",
            message="Retrieved available content sources",
            data={"sources": sources_info, "total_sources": len(sources_info)},
            errors=[],
            metadata=metadata,
        )

    except Exception as e:
        return StandardResponse(
            status="error",
            message=f"Failed to retrieve sources: {str(e)}",
            data={},
            errors=[str(e)],
            metadata=metadata,
        )


@router.get(
    "/{source_type}",
    response_model=StandardResponse,
    summary="Get Source Configuration",
    description="Get detailed configuration for a specific source type",
)
async def get_source_config(
    source_type: str,
    metadata: Dict[str, Any] = Depends(service_metadata),
):
    """
    Get detailed configuration information for a specific source type.

    Provides source-specific configuration options, authentication requirements,
    and status information.
    """
    try:
        if source_type == "reddit":
            reddit_info = SourceCollectorFactory.get_reddit_collector_info()

            config_data = {
                "type": "reddit",
                "description": "Reddit content collection with multiple authentication options",
                "parameters": {
                    "subreddits": {
                        "type": "array",
                        "description": "List of subreddit names to collect from",
                        "required": True,
                        "example": ["technology", "MachineLearning"],
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of posts to collect per subreddit",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 100,
                    },
                    "sort": {
                        "type": "string",
                        "description": "Sort order for posts",
                        "default": "hot",
                        "enum": ["hot", "new", "top", "rising"],
                    },
                },
                "authentication": reddit_info,
                "status": reddit_info.get("status", "unknown"),
            }

        elif source_type == "rss":
            config_data = {
                "type": "rss",
                "description": "RSS feed content collection",
                "parameters": {
                    "feed_urls": {
                        "type": "array",
                        "description": "List of RSS feed URLs",
                        "required": True,
                        "example": ["https://feeds.feedburner.com/TechCrunch"],
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of items per feed",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50,
                    },
                },
                "authentication": {"required": False},
                "status": "available",
            }

        elif source_type == "web":
            config_data = {
                "type": "web",
                "description": "Web content scraping",
                "parameters": {
                    "urls": {
                        "type": "array",
                        "description": "List of web page URLs to scrape",
                        "required": True,
                        "example": ["https://example.com/article"],
                    },
                    "extract_text": {
                        "type": "boolean",
                        "description": "Extract text content from HTML",
                        "default": True,
                    },
                },
                "authentication": {"required": False},
                "status": "available",
            }

        else:
            return StandardResponse(
                status="error",
                message=f"Unknown source type: {source_type}",
                data={},
                errors=[f"Supported types: reddit, rss, web"],
                metadata=metadata,
            )

        return StandardResponse(
            status="success",
            message=f"Retrieved configuration for {source_type}",
            data=config_data,
            errors=[],
            metadata=metadata,
        )

    except Exception as e:
        return StandardResponse(
            status="error",
            message=f"Failed to get source configuration: {str(e)}",
            data={},
            errors=[str(e)],
            metadata=metadata,
        )
