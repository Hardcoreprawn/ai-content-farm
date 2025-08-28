"""
Legacy API endpoints for Content Ranker service.

This module contains the original API endpoints that maintain backward compatibility
during the migration to standardized FastAPI-native patterns. These endpoints use
the original response formats and error handling approaches.

Once all clients are migrated to the standardized API endpoints (/api/content-ranker/*),
these legacy endpoints can be deprecated and eventually removed.
"""

import logging

from fastapi import APIRouter, HTTPException
from models import BatchRankingRequest, RankingResponse, SpecificRankingRequest
from service_logic import ContentRankerService

# Configure logging
logger = logging.getLogger(__name__)

# Create router for legacy endpoints
router = APIRouter(tags=["Legacy API - Backward Compatibility"])

# Initialize the ranker service
ranker_service = ContentRankerService()


@router.post("/rank/enriched")
async def rank_enriched_content(request: BatchRankingRequest):
    """
    Rank all enriched content using multi-factor scoring.

    Retrieves all enriched content from blob storage and ranks it
    based on the specified weights and criteria.

    **Legacy Endpoint**: Use /api/content-ranker/process for new implementations.
    """
    try:
        result = await ranker_service.rank_content_batch(
            weights=request.weights,
            target_topics=request.target_topics,
            limit=request.limit,
        )
        return result
    except Exception as e:
        logger.error(f"Enriched content ranking failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to rank enriched content")


@router.post("/rank/batch")
async def rank_content_batch_endpoint(request: BatchRankingRequest):
    """
    Rank content using batch processing.

    Args:
        request: Batch ranking request with weights and options

    Returns:
        Ranked content items with metadata

    **Legacy Endpoint**: Use /api/content-ranker/process for new implementations.
    """
    try:
        result = await ranker_service.rank_content_batch(
            weights=request.weights,
            target_topics=request.target_topics,
            limit=request.limit,
        )
        return result
    except Exception as e:
        logger.error(f"Batch ranking failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to process batch ranking")


@router.post("/rank", response_model=RankingResponse)
async def rank_content(request: SpecificRankingRequest):
    """
    Rank specific content items using multi-factor scoring.

    Combines engagement scores, recency factors, and topic relevance
    to provide intelligent content ranking.

    Args:
        request: Ranking request with content items and options

    Returns:
        Ranked content items with scoring metadata

    Raises:
        HTTPException: If ranking fails

    **Legacy Endpoint**: Use /api/content-ranker/process for new implementations.
    """
    try:
        # Rank the provided content items
        ranked_items = await ranker_service.rank_specific_content(
            content_items=request.content_items,
            weights=request.weights,
            target_topics=request.target_topics,
            limit=request.limit,
        )

        # Create response metadata
        metadata = {
            "total_items_processed": len(request.content_items),
            "items_returned": len(ranked_items),
            "ranking_algorithm": "multi_factor_composite",
            "factors_used": ["engagement", "recency", "topic_relevance"],
        }

        return RankingResponse(ranked_items=ranked_items, metadata=metadata)

    except Exception as e:
        logger.error(f"Content ranking failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to rank content items")
