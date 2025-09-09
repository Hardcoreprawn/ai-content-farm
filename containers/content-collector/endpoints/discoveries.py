"""
Discoveries Endpoints - Content Discovery and Analysis

RESTful endpoints for topic discovery and trend analysis.
"""

import time
from typing import Any, Dict

from discovery import (
    analyze_trending_topics,
    generate_research_recommendations,
    save_discovery_results,
)
from fastapi import APIRouter, Depends
from models import DiscoveryRequest, DiscoveryResult
from reddit_client import RedditClient

from libs.blob_storage import BlobStorageClient
from libs.shared_models import StandardResponse, create_service_dependency

# Create router for discoveries
router = APIRouter(prefix="/discoveries", tags=["discoveries"])

# Create service metadata dependency
service_metadata = create_service_dependency("content-womble")


def get_blob_client():
    """Get blob storage client."""
    if not hasattr(get_blob_client, "_client"):
        get_blob_client._client = BlobStorageClient()
    return get_blob_client._client


@router.post(
    "",
    response_model=StandardResponse,
    summary="Create Content Discovery",
    description="Analyze trending topics and generate research recommendations",
)
async def create_discovery(
    request: DiscoveryRequest,
    metadata: Dict[str, Any] = Depends(service_metadata),
):
    """
    Create a new content discovery analysis.

    Analyzes trending topics from Reddit and generates research recommendations
    for content creation opportunities.
    """
    start_time = time.time()

    try:
        # Initialize Reddit client
        reddit_client = RedditClient()

        if not reddit_client.is_available():
            return StandardResponse(
                status="error",
                message="Reddit client not available",
                data={},
                errors=["Reddit API connection failed"],
                metadata=metadata,
            )

        # Collect data from specified subreddits
        all_posts = []
        for subreddit in request.subreddits:
            posts = reddit_client.get_trending_posts(
                subreddit, request.limit_per_subreddit
            )
            all_posts.extend(posts)

        if not all_posts:
            return StandardResponse(
                status="success",
                message="No trending topics found",
                data=DiscoveryResult(
                    trending_topics=[],
                    research_recommendations=[],
                    analysis_summary="No trending content found in specified subreddits",
                    total_posts_analyzed=0,
                    subreddits_analyzed=request.subreddits,
                    processing_time_ms=int((time.time() - start_time) * 1000),
                ).model_dump(),
                errors=[],
                metadata=metadata,
            )

        # Analyze trending topics
        trending_topics = analyze_trending_topics(all_posts, request.analysis_criteria)

        # Generate research recommendations
        research_recommendations = generate_research_recommendations(
            trending_topics, request.research_focus
        )

        # Save results if requested
        storage_location = None
        if request.save_results:
            discovery_id = f"discovery_{int(time.time())}"
            results_data = {
                "trending_topics": trending_topics,
                "research_recommendations": research_recommendations,
                "analysis_criteria": request.analysis_criteria,
                "research_focus": request.research_focus,
            }
            storage_location = save_discovery_results(
                discovery_id, results_data, get_blob_client()
            )

        processing_time_ms = int((time.time() - start_time) * 1000)

        result = DiscoveryResult(
            trending_topics=trending_topics,
            research_recommendations=research_recommendations,
            analysis_summary=f"Analyzed {len(all_posts)} posts from {len(request.subreddits)} subreddits",
            total_posts_analyzed=len(all_posts),
            subreddits_analyzed=request.subreddits,
            processing_time_ms=processing_time_ms,
            storage_location=storage_location,
        )

        # Update metadata with timing
        metadata["execution_time_ms"] = processing_time_ms

        return StandardResponse(
            status="success",
            message=f"Created discovery analysis of {len(all_posts)} posts",
            data=result.model_dump(),
            errors=[],
            metadata=metadata,
        )

    except Exception as e:
        processing_time_ms = int((time.time() - start_time) * 1000)
        metadata["execution_time_ms"] = processing_time_ms

        return StandardResponse(
            status="error",
            message=f"Failed to create discovery: {str(e)}",
            data={},
            errors=[str(e)],
            metadata=metadata,
        )
