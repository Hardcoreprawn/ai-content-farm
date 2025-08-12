#!/usr/bin/env python3
"""
Functional Content Ranker Implementation
Pure functions for ranking Reddit topics using functional programming principles.
"""

import math
import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Set
from difflib import SequenceMatcher


# High-value keywords for monetization scoring
HIGH_VALUE_KEYWORDS = {
    'ai', 'artificial intelligence', 'machine learning', 'ml', 'deep learning',
    'crypto', 'cryptocurrency', 'bitcoin', 'blockchain', 'ethereum',
    'startup', 'funding', 'investment', 'ipo', 'venture capital',
    'tech', 'technology', 'innovation', 'software', 'saas',
    'productivity', 'tools', 'automation', 'api', 'developer',
    'market', 'finance', 'trading', 'stock', 'economy',
    'cybersecurity', 'cloud', 'aws', 'azure', 'google cloud'
}

SEO_INDICATORS = {
    'how to', 'guide', 'tutorial', 'best', 'top', 'ultimate',
    'complete', 'beginner', 'advanced', 'tips', 'tricks',
    '2025', '2024', 'new', 'latest', 'breaking', 'review'
}


def calculate_engagement_score(topic: Dict[str, Any]) -> float:
    """
    Calculate engagement score based on Reddit metrics (pure function).

    Uses logarithmic scaling to handle extreme values gracefully.
    Score ranges from 0.0 to 1.0.
    """
    score = topic.get('score', 0)
    comments = topic.get('num_comments', 0)

    # Logarithmic scaling for better distribution
    # Base thresholds: 1000 score, 100 comments = 0.5
    score_component = min(1.0, math.log(score + 1) / math.log(10000))
    comments_component = min(1.0, math.log(comments + 1) / math.log(1000))

    # Weight score more heavily than comments (60/40 split)
    engagement = (score_component * 0.6) + (comments_component * 0.4)

    return round(engagement, 3)


def calculate_freshness_score(topic: Dict[str, Any]) -> float:
    """
    Calculate freshness score based on post age (pure function).

    Fresh content (< 24 hours) gets high score.
    Score decays exponentially over time.
    """
    created_utc = topic.get('created_utc', 0)
    now = datetime.now(timezone.utc).timestamp()

    age_hours = (now - created_utc) / 3600

    # Exponential decay: half-life of 48 hours
    # Fresh (< 24h) = 0.8+, Old (7 days) = 0.1-
    if age_hours < 0:
        return 1.0  # Future posts (edge case)

    freshness = math.exp(-age_hours / 48.0)

    return round(freshness, 3)


def calculate_monetization_score(topic: Dict[str, Any]) -> float:
    """
    Calculate monetization potential based on keywords (pure function).

    Scores topics based on commercial value indicators.
    """
    title = topic.get('title', '').lower()
    selftext = topic.get('selftext', '').lower()
    content = f"{title} {selftext}"

    # Count high-value keywords
    keyword_matches = sum(
        1 for keyword in HIGH_VALUE_KEYWORDS if keyword in content)

    # Normalize by keyword set size (diminishing returns)
    # 1 keyword = 0.2, 3 keywords = 0.5, 5+ keywords = 0.8+
    score = min(1.0, keyword_matches / 5.0)

    # Bonus for multiple keyword categories
    if keyword_matches >= 3:
        score *= 1.2

    return round(min(1.0, score), 3)


def calculate_seo_score(topic: Dict[str, Any]) -> float:
    """
    Calculate SEO potential based on title quality (pure function).

    Factors: question format, guides, year mentions, title length.
    """
    title = topic.get('title', '').lower()

    score = 0.0

    # SEO-friendly indicators
    seo_matches = sum(1 for indicator in SEO_INDICATORS if indicator in title)
    score += min(0.4, seo_matches * 0.1)

    # Question format (high search intent)
    if any(q in title for q in ['how', 'what', 'why', 'when', 'where']):
        score += 0.3

    # Title length (50-60 chars is optimal for SEO)
    title_len = len(topic.get('title', ''))
    if 40 <= title_len <= 70:
        score += 0.2
    elif 30 <= title_len <= 80:
        score += 0.1

    # Capitalization (proper title case)
    if title.count(' ') > 0:  # Multiple words
        words = title.split()
        capitalized = sum(1 for word in words if word[0].isupper())
        if capitalized / len(words) > 0.5:
            score += 0.1

    return round(min(1.0, score), 3)


def rank_topic_functional(topic: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Rank a single topic using functional composition (pure function).

    Returns a new topic dict with ranking data added.
    """
    weights = config['weights']
    
    # Default weights for missing values
    default_weights = {
        'engagement': 0.3,
        'freshness': 0.2,
        'monetization': 0.3,
        'seo_potential': 0.2
    }

    # Calculate individual scores
    engagement = calculate_engagement_score(topic)
    freshness = calculate_freshness_score(topic)
    monetization = calculate_monetization_score(topic)
    seo = calculate_seo_score(topic)

    # Weighted final score with defaults for missing weights
    final_score = (
        engagement * weights.get('engagement', default_weights['engagement']) +
        freshness * weights.get('freshness', default_weights['freshness']) +
        monetization * weights.get('monetization', default_weights['monetization']) +
        seo * weights.get('seo_potential', default_weights['seo_potential'])
    )

    # Create new topic with ranking data (immutable)
    return {
        **topic,
        'ranking_score': round(final_score, 3),
        'ranking_details': {
            'engagement': engagement,
            'freshness': freshness,
            'monetization': monetization,
            'seo_potential': seo,
            'final': round(final_score, 3)
        }
    }


def meets_quality_threshold(topic: Dict[str, Any], config: Dict[str, Any]) -> bool:
    """
    Check if topic meets minimum quality thresholds (pure function).
    """
    min_score = config.get('min_score_threshold', 100)
    min_comments = config.get('min_comments_threshold', 10)

    return (
        topic.get('score', 0) >= min_score and
        topic.get('num_comments', 0) >= min_comments and
        bool(topic.get('title', '').strip())  # Must have title
    )


def calculate_title_similarity(title1: str, title2: str) -> float:
    """
    Calculate similarity between two titles (pure function).

    Uses word overlap and sequence matching.
    """
    # Normalize titles
    t1_words = set(re.findall(r'\w+', title1.lower()))
    t2_words = set(re.findall(r'\w+', title2.lower()))

    if not t1_words or not t2_words:
        return 0.0

    # Word overlap similarity
    overlap = len(t1_words & t2_words) / len(t1_words | t2_words)

    # Sequence similarity
    sequence_sim = SequenceMatcher(
        None, title1.lower(), title2.lower()).ratio()

    # Combined similarity (favor word overlap for content)
    return (overlap * 0.7) + (sequence_sim * 0.3)


def deduplicate_topics(topics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove duplicate topics based on title similarity and URLs (pure function).

    Keeps highest-scoring version of duplicates.
    """
    if not topics:
        return []

    # Sort by score descending to keep best duplicates
    sorted_topics = sorted(
        topics, key=lambda x: x.get('score', 0), reverse=True)

    deduplicated = []
    seen_urls: Set[str] = set()

    for topic in sorted_topics:
        # Check URL duplicates first (exact match)
        external_url = topic.get('external_url', '')
        if external_url and external_url in seen_urls:
            continue

        # Check title similarity with existing topics
        is_duplicate = False
        current_title = topic.get('title', '')

        for existing in deduplicated:
            similarity = calculate_title_similarity(
                current_title, existing.get('title', ''))
            if similarity > 0.8:  # 80% similarity threshold
                is_duplicate = True
                break

        if not is_duplicate:
            deduplicated.append(topic)
            if external_url:
                seen_urls.add(external_url)

    return deduplicated


def rank_topics_functional(topics: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Rank multiple topics with filtering, deduplication, and sorting (pure function).

    Pipeline: filter -> deduplicate -> rank -> sort
    """
    if not topics:
        return []

    # 1. Filter by quality thresholds
    quality_topics = [
        topic for topic in topics if meets_quality_threshold(topic, config)]

    # 2. Deduplicate similar topics
    unique_topics = deduplicate_topics(quality_topics)

    # 3. Rank each topic
    ranked_topics = [rank_topic_functional(
        topic, config) for topic in unique_topics]

    # 4. Sort by ranking score (highest first)
    sorted_topics = sorted(
        ranked_topics, key=lambda x: x['ranking_score'], reverse=True)

    return sorted_topics


def transform_blob_to_topics(blob_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Transform blob input format to topics list (pure function).

    Handles SummaryWomble output format.
    """
    if 'topics' not in blob_data:
        return []

    topics = blob_data['topics']
    if not isinstance(topics, list):
        return []

    # Add source metadata to each topic
    source_metadata = {
        'source_file': f"{blob_data.get('fetched_at', 'unknown')}_{blob_data.get('source', 'unknown')}_{blob_data.get('subject', 'unknown')}.json",
        'job_id': blob_data.get('job_id')
    }

    return [
        {**topic, **source_metadata}
        for topic in topics
        if isinstance(topic, dict)
    ]


def create_ranking_output(ranked_topics: List[Dict[str, Any]],
                          source_files: List[str],
                          config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create final ranking output format (pure function).

    Matches the expected output format for ContentEnricher.
    """
    return {
        'ranked_topics': ranked_topics,
        'metadata': {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'source_files': source_files,
            'total_topics': len(ranked_topics),
            'filtered_topics': len(ranked_topics)  # Assuming all topics passed filtering
        },
        'ranking_config': {
            'min_score_threshold': config.get('min_score_threshold', 100),
            'min_comments_threshold': config.get('min_comments_threshold', 10),
            'weights': config.get('weights', {})
        }
    }


# Main composition function for Azure Function
def process_content_ranking(blob_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main content ranking pipeline (pure function composition).

    Orchestrates the complete ranking workflow.
    """
    # Transform input
    topics = transform_blob_to_topics(blob_data)

    # Process ranking
    ranked_topics = rank_topics_functional(topics, config)

    # Create output
    source_file = blob_data.get(
        'fetched_at', 'unknown') + '_' + blob_data.get('subject', 'unknown') + '.json'
    output = create_ranking_output(ranked_topics, [source_file], config)

    return output
