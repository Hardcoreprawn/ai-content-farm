"""
Content Enricher Engine - Pure Functions

AI-powered content enhancement engine using functional programming principles.
"""

import re
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from .enricher_model import EnrichedTopic, EnrichmentConfig, EnrichmentResult


def calculate_reading_time(content: str) -> str:
    """
    Calculate estimated reading time for content.
    
    Args:
        content: The text content
        
    Returns:
        Human-readable reading time estimate
    """
    # Average reading speed: 200 words per minute
    words_per_minute = 200
    
    # Count words (simple split approach)
    word_count = len(content.split())
    
    # Calculate minutes
    minutes = max(1, round(word_count / words_per_minute))
    
    if minutes == 1:
        return "1 min read"
    else:
        return f"{minutes} min read"


def calculate_quality_score(topic: Dict[str, Any]) -> float:
    """
    Calculate content quality score based on various factors.
    
    Args:
        topic: Topic data with title, content, score, etc.
        
    Returns:
        Quality score between 0 and 1
    """
    score = 0.0
    
    # Title quality (20% weight)
    title = topic.get("title", "")
    if len(title) > 10:
        score += 0.1
    if len(title) > 30:
        score += 0.1
    
    # Content length (20% weight)
    content = topic.get("content", "")
    if len(content) > 100:
        score += 0.1
    if len(content) > 500:
        score += 0.1
    
    # Engagement (30% weight)
    reddit_score = topic.get("score", 0)
    comments = topic.get("num_comments", 0)
    
    if reddit_score > 100:
        score += 0.1
    if reddit_score > 1000:
        score += 0.1
    if comments > 10:
        score += 0.1
    
    # Content structure (30% weight)
    # Check for proper sentences
    sentences = re.split(r'[.!?]+', content)
    if len(sentences) > 2:
        score += 0.1
    
    # Check for paragraph structure
    if '\n' in content:
        score += 0.1
    
    # Check for no excessive caps
    if not re.search(r'[A-Z]{10,}', content):
        score += 0.1
    
    return min(1.0, score)


def analyze_sentiment(content: str, thresholds: Dict[str, float]) -> str:
    """
    Analyze sentiment of content using keyword-based approach.
    
    Args:
        content: The text content
        thresholds: Sentiment thresholds
        
    Returns:
        Sentiment classification: 'positive', 'negative', or 'neutral'
    """
    # Simple keyword-based sentiment analysis
    positive_words = [
        "good", "great", "excellent", "amazing", "awesome", "love", "best",
        "fantastic", "wonderful", "brilliant", "outstanding", "perfect",
        "breakthrough", "innovative", "exciting", "impressive", "successful"
    ]
    
    negative_words = [
        "bad", "terrible", "awful", "hate", "worst", "horrible", "disgusting",
        "failed", "broken", "disappointed", "angry", "frustrated", "problematic",
        "concerning", "alarming", "dangerous", "risky", "controversial"
    ]
    
    content_lower = content.lower()
    
    positive_count = sum(1 for word in positive_words if word in content_lower)
    negative_count = sum(1 for word in negative_words if word in content_lower)
    
    # Calculate sentiment score
    total_words = len(content.split())
    if total_words == 0:
        return "neutral"
    
    sentiment_score = (positive_count - negative_count) / total_words
    
    if sentiment_score > thresholds["positive"]:
        return "positive"
    elif sentiment_score < thresholds["negative"]:
        return "negative"
    else:
        return "neutral"


def extract_key_phrases(content: str, max_phrases: int = 5) -> List[str]:
    """
    Extract key phrases from content using simple NLP techniques.
    
    Args:
        content: The text content
        max_phrases: Maximum number of phrases to extract
        
    Returns:
        List of key phrases
    """
    # Common stop words to filter out
    stop_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "is", "are", "was", "were", "be", "been", "have",
        "has", "had", "do", "does", "did", "will", "would", "could", "should",
        "this", "that", "these", "those", "i", "you", "he", "she", "it", "we",
        "they", "me", "him", "her", "us", "them", "my", "your", "his", "her",
        "its", "our", "their"
    }
    
    # Extract words and phrases
    content_lower = content.lower()
    
    # Remove punctuation and split into words
    words = re.findall(r'\b[a-zA-Z]{3,}\b', content_lower)
    
    # Filter out stop words
    meaningful_words = [word for word in words if word not in stop_words]
    
    # Count word frequency
    word_freq = {}
    for word in meaningful_words:
        word_freq[word] = word_freq.get(word, 0) + 1
    
    # Get most frequent words as key phrases
    key_phrases = sorted(word_freq.keys(), key=lambda x: word_freq[x], reverse=True)
    
    return key_phrases[:max_phrases]


def categorize_content(title: str, content: str, category_mapping: Dict[str, List[str]]) -> str:
    """
    Categorize content based on keywords in title and content.
    
    Args:
        title: Content title
        content: Content text
        category_mapping: Mapping of categories to keywords
        
    Returns:
        Category name
    """
    combined_text = (title + " " + content).lower()
    
    category_scores = {}
    
    for category, keywords in category_mapping.items():
        score = 0
        for keyword in keywords:
            # Count occurrences of keyword
            score += combined_text.count(keyword.lower())
        
        if score > 0:
            category_scores[category] = score
    
    # Return category with highest score, or "General" if no matches
    if category_scores:
        return max(category_scores.keys(), key=lambda x: category_scores[x])
    else:
        return "General"


def generate_ai_summary(content: str, max_length: int = 300) -> str:
    """
    Generate AI summary of content (placeholder implementation).
    
    In production, this would integrate with OpenAI, Azure Cognitive Services,
    or other AI services.
    
    Args:
        content: The content to summarize
        max_length: Maximum length of summary
        
    Returns:
        AI-generated summary
    """
    # Simple extractive summarization (first sentences up to max_length)
    sentences = re.split(r'[.!?]+', content)
    
    summary_parts = []
    current_length = 0
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        # Add sentence if it fits within max_length
        if current_length + len(sentence) + 1 <= max_length:
            summary_parts.append(sentence)
            current_length += len(sentence) + 1
        else:
            break
    
    summary = ". ".join(summary_parts)
    
    # If no summary generated, use first part of content
    if not summary and content:
        summary = content[:max_length].rsplit(' ', 1)[0]
        if not summary.endswith('.'):
            summary += "..."
    
    # Add AI attribution note (placeholder)
    if summary:
        return f"{summary} [AI-generated summary - placeholder implementation]"
    else:
        return "AI summary generation failed - content too short or empty."


def enrich_single_topic(topic: Dict[str, Any], config: EnrichmentConfig) -> EnrichedTopic:
    """
    Enrich a single topic with AI-powered enhancements.
    
    Args:
        topic: Raw topic data
        config: Enrichment configuration
        
    Returns:
        Enriched topic with AI-generated content
    """
    title = topic.get("title", "")
    content = topic.get("content", "")
    
    # Generate AI summary
    ai_summary = ""
    if config.enable_ai_summary and content:
        ai_summary = generate_ai_summary(content, config.max_summary_length)
    
    # Categorize content
    category = "General"
    if config.enable_categorization:
        category = categorize_content(title, content, config.category_mapping)
    
    # Analyze sentiment
    sentiment = "neutral"
    if config.enable_sentiment_analysis and content:
        sentiment = analyze_sentiment(content, config.sentiment_thresholds)
    
    # Extract key phrases
    key_phrases = []
    if config.enable_key_phrases and content:
        key_phrases = extract_key_phrases(content)
    
    # Calculate reading time
    reading_time = "Unknown"
    if config.reading_time_calculation and content:
        reading_time = calculate_reading_time(content)
    
    # Calculate quality score
    quality_score = 0.5
    if config.quality_scoring_enabled:
        quality_score = calculate_quality_score(topic)
    
    # Create enriched topic
    enriched = EnrichedTopic(
        # Original fields
        title=title,
        content=content,
        score=topic.get("score"),
        num_comments=topic.get("num_comments"),
        created_utc=topic.get("created_utc"),
        url=topic.get("url"),
        author=topic.get("author"),
        
        # Enrichment fields
        ai_summary=ai_summary,
        category=category,
        sentiment=sentiment,
        key_phrases=key_phrases,
        reading_time=reading_time,
        quality_score=quality_score,
        enrichment_timestamp=datetime.utcnow().isoformat(),
        ai_model_used=config.ai_model
    )
    
    return enriched


def process_content_enrichment(
    topics_data: Dict[str, Any], 
    enrichment_config: Dict[str, Any]
) -> EnrichmentResult:
    """
    Process content enrichment for multiple topics using pure functions.
    
    Args:
        topics_data: Raw topics data (from content collector/ranker)
        enrichment_config: Configuration for enrichment process
        
    Returns:
        EnrichmentResult with enriched topics and metadata
    """
    start_time = datetime.utcnow()
    
    # Parse configuration
    config = EnrichmentConfig(**enrichment_config)
    
    # Extract topics from input data
    topics = []
    if isinstance(topics_data, dict):
        if "topics" in topics_data:
            topics = topics_data["topics"]
        elif "items" in topics_data:
            topics = topics_data["items"]
        else:
            # Assume the dict itself contains topic data
            topics = [topics_data]
    elif isinstance(topics_data, list):
        topics = topics_data
    
    # Enrich each topic
    enriched_topics = []
    errors = []
    
    for topic in topics:
        try:
            enriched_topic = enrich_single_topic(topic, config)
            enriched_topics.append(enriched_topic)
        except Exception as e:
            errors.append(f"Failed to enrich topic '{topic.get('title', 'Unknown')}': {str(e)}")
    
    # Calculate processing time
    processing_time = (datetime.utcnow() - start_time).total_seconds()
    
    # Create result
    result = EnrichmentResult(
        source=topics_data.get("source", "unknown") if isinstance(topics_data, dict) else "unknown",
        total_topics=len(topics),
        total_enriched=len(enriched_topics),
        enriched_topics=enriched_topics,
        processing_time=processing_time,
        ai_model_used=config.ai_model,
        config_used=config,
        enrichment_timestamp=datetime.utcnow().isoformat(),
        errors=errors
    )
    
    return result