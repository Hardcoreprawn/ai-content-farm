"""
Content Enricher - Core Business Logic

Minimal implementation to make tests pass.
Pure functions with no side effects.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import re
import math


def classify_topic(content: Dict[str, Any]) -> Dict[str, Any]:
    """
    Classify content into topics.

    Args:
        content: Content dictionary with title, clean_title, content fields

    Returns:
        Dictionary with primary_topic, confidence, and topics list

    Raises:
        ValueError: If content is not a dictionary
    """
    if not isinstance(content, dict):
        raise ValueError("Content must be a dictionary")

    title = content.get("title", "").lower()
    content_text = content.get("content", "").lower()
    clean_title = content.get("clean_title", "").lower()

    # Combine all text for analysis
    full_text = f"{title} {clean_title} {content_text}".strip()

    if not full_text:
        return {
            "primary_topic": "general",
            "confidence": 0.0,
            "topics": []
        }

    # Simple keyword-based classification
    topic_keywords = {
        "technology": ["ai", "machine learning", "neural", "algorithm", "computer", "software", "tech", "digital", "programming", "code"],
        "science": ["research", "study", "experiment", "discovery", "climate", "biology", "physics", "chemistry", "scientific"],
        "business": ["company", "market", "financial", "economy", "business", "startup", "revenue", "investment"],
        "health": ["medical", "health", "disease", "treatment", "doctor", "patient", "medicine", "clinical"],
        "politics": ["government", "policy", "election", "political", "congress", "senate", "president", "vote"],
        "entertainment": ["movie", "film", "music", "game", "gaming", "entertainment", "celebrity", "show"],
        "sports": ["sport", "game", "team", "player", "match", "championship", "football", "basketball"],
    }

    topic_scores = {}

    for topic, keywords in topic_keywords.items():
        score = 0
        for keyword in keywords:
            if keyword in full_text:
                score += 1
        topic_scores[topic] = score / len(keywords) if keywords else 0

    # Find primary topic
    if not topic_scores or all(score == 0 for score in topic_scores.values()):
        primary_topic = "general"
        confidence = 0.0
        topics = []
    else:
        primary_topic = max(topic_scores.keys(), key=lambda k: topic_scores[k])
        # Scale and cap at 1.0
        confidence = min(topic_scores[primary_topic] * 2, 1.0)

        # Get all topics with non-zero scores
        topics = [
            {"topic": topic, "score": score}
            for topic, score in topic_scores.items()
            if score > 0
        ]
        topics.sort(key=lambda x: x["score"], reverse=True)  # type: ignore

    return {
        "primary_topic": primary_topic,
        "confidence": confidence,
        "topics": topics
    }


def analyze_sentiment(content: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze sentiment of content.

    Args:
        content: Content dictionary with title and content fields

    Returns:
        Dictionary with sentiment, confidence, and scores
    """
    title = content.get("title", "")
    content_text = content.get("content", "")

    # Combine text for analysis
    full_text = f"{title} {content_text}".lower()

    if not full_text.strip():
        return {
            "sentiment": "neutral",
            "confidence": 0.0,
            "scores": {"positive": 0.0, "negative": 0.0, "neutral": 1.0}
        }

    # Simple keyword-based sentiment analysis
    positive_words = [
        "amazing", "fantastic", "great", "excellent", "wonderful", "awesome",
        "brilliant", "outstanding", "incredible", "breakthrough", "success",
        "good", "better", "best", "love", "like", "happy", "exciting"
    ]

    negative_words = [
        "terrible", "awful", "bad", "worse", "worst", "hate", "disaster",
        "problem", "issue", "fail", "failure", "disappointing", "sad",
        "angry", "frustrated", "concerned", "worried", "crisis"
    ]

    positive_count = sum(1 for word in positive_words if word in full_text)
    negative_count = sum(1 for word in negative_words if word in full_text)

    total_sentiment_words = positive_count + negative_count

    if total_sentiment_words == 0:
        return {
            "sentiment": "neutral",
            "confidence": 0.5,
            "scores": {"positive": 0.33, "negative": 0.33, "neutral": 0.34}
        }

    positive_score = positive_count / total_sentiment_words
    negative_score = negative_count / total_sentiment_words
    neutral_score = 1.0 - positive_score - negative_score

    # Determine primary sentiment
    if positive_score > negative_score and positive_score > 0.4:
        sentiment = "positive"
        confidence = positive_score
    elif negative_score > positive_score and negative_score > 0.4:
        sentiment = "negative"
        confidence = negative_score
    else:
        sentiment = "neutral"
        confidence = max(neutral_score, 0.5)

    return {
        "sentiment": sentiment,
        "confidence": min(confidence, 1.0),
        "scores": {
            "positive": positive_score,
            "negative": negative_score,
            "neutral": neutral_score
        }
    }


def generate_summary(content: Dict[str, Any], max_length: int = 200) -> Dict[str, Any]:
    """
    Generate summary of content.

    Args:
        content: Content dictionary with title and content fields
        max_length: Maximum length of summary in characters

    Returns:
        Dictionary with summary and word_count
    """
    title = content.get("title", "")
    content_text = content.get("content", "")

    # Combine title and content
    full_text = f"{title}. {content_text}".strip()

    if not full_text or full_text == ".":
        return {
            "summary": "",
            "word_count": 0
        }

    # If content is already short, return as-is
    if len(full_text) <= max_length:
        word_count = len(full_text.split())
        return {
            "summary": full_text,
            "word_count": word_count
        }

    # Simple truncation-based summarization
    # In a real implementation, this would use an AI service
    sentences = re.split(r'[.!?]+', full_text)

    summary = ""
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        if len(summary + sentence + ". ") <= max_length:
            summary += sentence + ". "
        else:
            break

    # If no complete sentences fit, truncate the first sentence
    if not summary and sentences:
        first_sentence = sentences[0].strip()
        if len(first_sentence) > max_length:
            summary = first_sentence[:max_length-3] + "..."
        else:
            summary = first_sentence + "."

    word_count = len(summary.split()) if summary else 0

    return {
        "summary": summary.strip(),
        "word_count": word_count
    }


def calculate_trend_score(content: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate trending score for content.

    Args:
        content: Content dictionary with scores and metadata

    Returns:
        Dictionary with trend_score and factors
    """
    normalized_score = content.get("normalized_score", 0.0)
    engagement_score = content.get("engagement_score", 0.0)
    published_at = content.get("published_at", "")
    source_metadata = content.get("source_metadata", {})

    # Parse published date for time decay calculation
    try:
        if published_at:
            pub_date = datetime.fromisoformat(
                published_at.replace('Z', '+00:00'))
        else:
            pub_date = datetime.now(timezone.utc)
    except (ValueError, TypeError):
        pub_date = datetime.now(timezone.utc)

    # Calculate time decay (content loses relevance over time)
    now = datetime.now(timezone.utc)
    hours_since_published = (now - pub_date).total_seconds() / 3600

    # Decay function: starts at 1.0, halves every 24 hours
    time_decay = math.exp(-hours_since_published / 24)
    time_decay = max(time_decay, 0.01)  # Minimum decay factor

    # Combine factors
    base_score = (normalized_score * 0.4 + engagement_score * 0.6)

    # Velocity factor (how fast it's gaining engagement)
    original_score = source_metadata.get("original_score", 0)
    original_comments = source_metadata.get("original_comments", 0)

    # Simple velocity approximation
    velocity_factor = 1.0
    if hours_since_published > 0:
        score_per_hour = original_score / max(hours_since_published, 1)
        comments_per_hour = original_comments / max(hours_since_published, 1)
        velocity_factor = min((score_per_hour + comments_per_hour) / 10, 2.0)

    # Final trend score
    trend_score = base_score * time_decay * velocity_factor
    trend_score = min(trend_score, 1.0)  # Cap at 1.0

    factors = {
        "base_score": base_score,
        "time_decay": time_decay,
        "velocity_factor": velocity_factor,
        "hours_since_published": hours_since_published
    }

    return {
        "trend_score": trend_score,
        "factors": factors
    }


def enrich_content_item(content_item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enrich a single content item with all enrichment data.

    Args:
        content_item: Processed content item from content-processor

    Returns:
        Enriched content item with enrichment data
    """
    # Prepare content for enrichment
    enrichment_content = {
        "title": content_item.get("title", ""),
        "clean_title": content_item.get("clean_title", ""),
        "content": content_item.get("source_metadata", {}).get("selftext", "")
    }

    # Perform enrichment
    topic_classification = classify_topic(enrichment_content)
    sentiment_analysis = analyze_sentiment(enrichment_content)
    summary = generate_summary(enrichment_content)
    trend_score = calculate_trend_score(content_item)

    # Create enriched item
    enriched_item = content_item.copy()
    enriched_item["enrichment"] = {
        "topic_classification": topic_classification,
        "sentiment_analysis": sentiment_analysis,
        "summary": summary,
        "trend_score": trend_score,
        "processed_at": datetime.now(timezone.utc).isoformat()
    }

    return enriched_item


def enrich_content_batch(content_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Enrich a batch of content items.

    Args:
        content_items: List of processed content items

    Returns:
        Dictionary with enriched_items and metadata
    """
    enriched_items = []

    for item in content_items:
        try:
            enriched_item = enrich_content_item(item)
            enriched_items.append(enriched_item)
        except Exception as e:
            # Log error but continue processing other items
            print(f"Error enriching item {item.get('id', 'unknown')}: {e}")
            continue

    metadata = {
        "items_processed": len(enriched_items),
        "items_failed": len(content_items) - len(enriched_items),
        "processing_version": "1.0.0",
        "processed_at": datetime.now(timezone.utc).isoformat()
    }

    return {
        "enriched_items": enriched_items,
        "metadata": metadata
    }
