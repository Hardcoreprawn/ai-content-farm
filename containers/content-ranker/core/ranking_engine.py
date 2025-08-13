"""
Content Ranking Engine - Pure Functions

Migrated from Azure Functions ranker_core.py to Container Apps architecture.
Maintains all existing ranking algorithms while adding type safety and testability.
"""

import math
import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Set, Optional, Tuple
from difflib import SequenceMatcher
from dataclasses import dataclass


@dataclass
class RankingConfig:
    """Configuration for content ranking algorithms"""
    engagement_weight: float = 0.4
    monetization_weight: float = 0.3
    recency_weight: float = 0.2
    title_quality_weight: float = 0.1
    minimum_score_threshold: float = 0.1
    max_topics_output: int = 50


@dataclass
class TopicScore:
    """Individual topic scoring breakdown"""
    engagement_score: float
    monetization_score: float
    recency_score: float
    title_quality_score: float
    final_score: float
    ranking_position: int


@dataclass
class RankingResult:
    """Result from content ranking operation"""
    total_topics: int
    ranked_topics: List[Dict[str, Any]]
    processing_time_seconds: float
    config_used: RankingConfig
    timestamp: datetime


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


def calculate_monetization_score(topic: Dict[str, Any]) -> float:
    """
    Calculate monetization potential based on keywords and topic characteristics.
    
    Returns score from 0.0 to 1.0 based on presence of high-value keywords
    and SEO indicators.
    """
    title = topic.get('title', '').lower()
    content = topic.get('content', '').lower()
    
    # Combine title and content for analysis
    text_content = f"{title} {content}"
    
    # Count high-value keyword matches
    keyword_matches = sum(1 for keyword in HIGH_VALUE_KEYWORDS if keyword in text_content)
    keyword_score = min(1.0, keyword_matches / 5.0)  # Normalize to max 5 keywords
    
    # Count SEO indicators
    seo_matches = sum(1 for indicator in SEO_INDICATORS if indicator in text_content)
    seo_score = min(1.0, seo_matches / 3.0)  # Normalize to max 3 indicators
    
    # Combine scores (70% keywords, 30% SEO)
    monetization = (keyword_score * 0.7) + (seo_score * 0.3)
    
    return round(monetization, 3)


def calculate_recency_score(topic: Dict[str, Any]) -> float:
    """
    Calculate recency score based on post age.
    
    Newer posts get higher scores, with exponential decay.
    Score ranges from 0.0 to 1.0.
    """
    created_utc = topic.get('created_utc')
    if not created_utc:
        return 0.0
    
    try:
        # Handle both timestamp and datetime string formats
        if isinstance(created_utc, (int, float)):
            post_time = datetime.fromtimestamp(created_utc, tz=timezone.utc)
        else:
            post_time = datetime.fromisoformat(created_utc.replace('Z', '+00:00'))
        
        now = datetime.now(timezone.utc)
        age_hours = (now - post_time).total_seconds() / 3600
        
        # Exponential decay: 24 hours = 0.5, 48 hours = 0.25, etc.
        recency = math.exp(-age_hours / 24.0)
        
        return round(recency, 3)
        
    except (ValueError, TypeError, AttributeError):
        return 0.0


def calculate_title_quality_score(topic: Dict[str, Any]) -> float:
    """
    Calculate title quality based on length, readability, and SEO factors.
    
    Returns score from 0.0 to 1.0.
    """
    title = topic.get('title', '')
    if not title:
        return 0.0
    
    # Length score (optimal: 50-60 characters)
    length = len(title)
    if 50 <= length <= 60:
        length_score = 1.0
    elif 40 <= length <= 70:
        length_score = 0.8
    elif 30 <= length <= 80:
        length_score = 0.6
    else:
        length_score = 0.4
    
    # Word count score (optimal: 8-12 words)
    words = title.split()
    word_count = len(words)
    if 8 <= word_count <= 12:
        word_score = 1.0
    elif 6 <= word_count <= 15:
        word_score = 0.8
    else:
        word_score = 0.6
    
    # Readability factors
    readability_score = 1.0
    
    # Penalize ALL CAPS
    if title.isupper():
        readability_score -= 0.3
    
    # Penalize excessive punctuation
    punctuation_ratio = sum(1 for c in title if c in '!?.,;:') / len(title)
    if punctuation_ratio > 0.1:
        readability_score -= 0.2
    
    # Bonus for question format
    if title.strip().endswith('?'):
        readability_score += 0.1
    
    readability_score = max(0.0, min(1.0, readability_score))
    
    # Combine scores
    quality = (length_score * 0.3) + (word_score * 0.3) + (readability_score * 0.4)
    
    return round(quality, 3)


def calculate_composite_score(
    engagement: float,
    monetization: float,
    recency: float,
    title_quality: float,
    config: RankingConfig
) -> float:
    """
    Calculate weighted composite score from individual components.
    
    Returns final ranking score from 0.0 to 1.0.
    """
    composite = (
        engagement * config.engagement_weight +
        monetization * config.monetization_weight +
        recency * config.recency_weight +
        title_quality * config.title_quality_weight
    )
    
    return round(composite, 3)


def detect_duplicates(topics: List[Dict[str, Any]], similarity_threshold: float = 0.8) -> Set[int]:
    """
    Detect duplicate or very similar topics using title similarity.
    
    Returns set of indices to remove (keeps the highest scoring).
    """
    if not topics:
        return set()
    
    duplicates = set()
    
    for i, topic1 in enumerate(topics):
        if i in duplicates:
            continue
            
        title1 = topic1.get('title', '').lower()
        if not title1:
            continue
            
        for j, topic2 in enumerate(topics[i+1:], i+1):
            if j in duplicates:
                continue
                
            title2 = topic2.get('title', '').lower()
            if not title2:
                continue
            
            # Calculate similarity ratio
            similarity = SequenceMatcher(None, title1, title2).ratio()
            
            if similarity >= similarity_threshold:
                # Keep the one with higher score, mark other as duplicate
                score1 = topic1.get('final_score', 0)
                score2 = topic2.get('final_score', 0)
                
                if score1 >= score2:
                    duplicates.add(j)
                else:
                    duplicates.add(i)
                    break  # Current topic is duplicate, no need to check further
    
    return duplicates


def rank_topics(
    topics: List[Dict[str, Any]], 
    config: Optional[RankingConfig] = None
) -> RankingResult:
    """
    Main function to rank a list of topics using all scoring algorithms.
    
    Args:
        topics: List of topic dictionaries with Reddit post data
        config: Ranking configuration (uses default if None)
    
    Returns:
        RankingResult with ranked topics and metadata
    """
    start_time = datetime.utcnow()
    
    if config is None:
        config = RankingConfig()
    
    if not topics:
        return RankingResult(
            total_topics=0,
            ranked_topics=[],
            processing_time_seconds=0.0,
            config_used=config,
            timestamp=start_time
        )
    
    # Calculate individual scores for each topic
    scored_topics = []
    
    for topic in topics:
        engagement = calculate_engagement_score(topic)
        monetization = calculate_monetization_score(topic)
        recency = calculate_recency_score(topic)
        title_quality = calculate_title_quality_score(topic)
        
        final_score = calculate_composite_score(
            engagement, monetization, recency, title_quality, config
        )
        
        # Add scoring breakdown to topic
        topic_with_scores = topic.copy()
        topic_with_scores.update({
            'engagement_score': engagement,
            'monetization_score': monetization,
            'recency_score': recency,
            'title_quality_score': title_quality,
            'final_score': final_score
        })
        
        # Only include topics above minimum threshold
        if final_score >= config.minimum_score_threshold:
            scored_topics.append(topic_with_scores)
    
    # Sort by final score (descending)
    scored_topics.sort(key=lambda x: x['final_score'], reverse=True)
    
    # Remove duplicates
    duplicate_indices = detect_duplicates(scored_topics)
    filtered_topics = [
        topic for i, topic in enumerate(scored_topics) 
        if i not in duplicate_indices
    ]
    
    # Limit to maximum output count
    final_topics = filtered_topics[:config.max_topics_output]
    
    # Add ranking positions
    for i, topic in enumerate(final_topics):
        topic['ranking_position'] = i + 1
    
    processing_time = (datetime.utcnow() - start_time).total_seconds()
    
    return RankingResult(
        total_topics=len(final_topics),
        ranked_topics=final_topics,
        processing_time_seconds=processing_time,
        config_used=config,
        timestamp=start_time
    )


def process_content_ranking(
    blob_data: Dict[str, Any], 
    config_dict: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Legacy compatibility function for Azure Functions migration.
    
    Processes blob data in the original format and returns results
    in the expected Azure Functions format.
    """
    # Convert config dict to RankingConfig if provided
    config = RankingConfig()
    if config_dict:
        config = RankingConfig(**{
            k: v for k, v in config_dict.items() 
            if hasattr(config, k)
        })
    
    # Extract topics from blob data
    topics = blob_data.get('topics', [])
    
    # Rank topics
    ranking_result = rank_topics(topics, config)
    
    # Return in original Azure Functions format
    return {
        'total_topics': ranking_result.total_topics,
        'topics': ranking_result.ranked_topics,
        'metadata': {
            'processing_time_seconds': ranking_result.processing_time_seconds,
            'timestamp': ranking_result.timestamp.isoformat(),
            'config_used': {
                'engagement_weight': config.engagement_weight,
                'monetization_weight': config.monetization_weight,
                'recency_weight': config.recency_weight,
                'title_quality_weight': config.title_quality_weight,
                'minimum_score_threshold': config.minimum_score_threshold,
                'max_topics_output': config.max_topics_output
            }
        }
    }
