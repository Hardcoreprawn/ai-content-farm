"""
Content Enricher - Main Orchestrator

Simple orchestrator that calls individual enrichment modules.
Keeps the main logic clean and focused.
"""

from typing import Dict, Any, List
from datetime import datetime

# Import our enrichment modules
from .topic_classifier import classify_topic
from .sentiment_analyzer import analyze_sentiment
from .content_summarizer import generate_summary
from .trend_calculator import calculate_trend_score


def enrich_content_item(content_item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enrich a single content item with all available enrichments.

    Args:
        content_item: Content dictionary to enrich

    Returns:
        Enriched content dictionary
    """
    # Start with the original content
    enriched = content_item.copy()

    # Add enrichment timestamp
    enriched["enrichment_timestamp"] = datetime.utcnow().isoformat()

    try:
        # Add topic classification
        topic_result = classify_topic(content_item)
        enriched["topic_classification"] = topic_result

        # Add sentiment analysis
        sentiment_result = analyze_sentiment(content_item)
        enriched["sentiment_analysis"] = sentiment_result

        # Add summary
        summary_result = generate_summary(content_item)
        enriched["summary"] = summary_result

        # Add trend score
        trend_result = calculate_trend_score(content_item)
        enriched["trend_analysis"] = trend_result

        # Mark as successfully enriched
        enriched["enrichment_status"] = "success"

    except Exception as e:
        # If enrichment fails, mark it but don't crash
        enriched["enrichment_status"] = "failed"
        enriched["enrichment_error"] = str(e)

    return enriched


def enrich_content_batch(content_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Enrich a batch of content items.

    Args:
        content_items: List of content dictionaries to enrich

    Returns:
        Dictionary with enriched items and batch metadata
    """
    if not isinstance(content_items, list):
        return {
            "enriched_items": [],
            "total_items": 0,
            "successful_enrichments": 0,
            "failed_enrichments": 0,
            "processing_time_ms": 0,
            "error": "Input must be a list of content items"
        }

    start_time = datetime.utcnow()
    enriched_items = []
    successful_count = 0
    failed_count = 0

    for item in content_items:
        enriched_item = enrich_content_item(item)
        enriched_items.append(enriched_item)

        if enriched_item.get("enrichment_status") == "success":
            successful_count += 1
        else:
            failed_count += 1

    end_time = datetime.utcnow()
    processing_time = (end_time - start_time).total_seconds() * \
        1000  # Convert to milliseconds

    return {
        "enriched_items": enriched_items,
        "total_items": len(content_items),
        "successful_enrichments": successful_count,
        "failed_enrichments": failed_count,
        "processing_time_ms": round(processing_time, 2),
        "batch_timestamp": start_time.isoformat()
    }
