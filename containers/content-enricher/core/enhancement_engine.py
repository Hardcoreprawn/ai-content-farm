"""
Content Enhancement Engine - Pure Functions

AI-powered content enhancement with OpenAI integration.
Follows the established Container Apps pure functions architecture.
"""

import asyncio
import json
import os
import re
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None


@dataclass
class EnhancementConfig:
    """Configuration for content enhancement"""
    openai_model: str = "gpt-3.5-turbo"
    max_tokens: int = 500
    temperature: float = 0.7
    rate_limit_delay: float = 1.0  # seconds between API calls
    max_retries: int = 3
    include_sentiment: bool = True
    include_tags: bool = True
    include_insights: bool = True
    max_content_length: int = 4000  # Max chars to send to OpenAI


@dataclass 
class EnhancementResult:
    """Result from content enhancement operation"""
    topic_id: str
    summary: Optional[str]
    key_insights: List[str]
    tags: List[str]
    sentiment: Optional[str]
    enhancement_metadata: Dict[str, Any]
    processing_time_seconds: float
    success: bool
    error: Optional[str] = None


def get_openai_client() -> Optional[AsyncOpenAI]:
    """
    Get OpenAI client with API key from environment.
    
    Returns None if OpenAI is not available or API key not set.
    """
    if AsyncOpenAI is None:
        return None
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    
    return AsyncOpenAI(api_key=api_key)


def extract_content_preview(topic: Dict[str, Any], max_length: int = 4000) -> str:
    """
    Extract content preview for OpenAI processing.
    
    Combines title, content, and any available text while respecting length limits.
    """
    parts = []
    
    # Add title
    title = topic.get('title', '').strip()
    if title:
        parts.append(f"Title: {title}")
    
    # Add content/selftext
    content = topic.get('content', '') or topic.get('selftext', '')
    if content and content.strip():
        parts.append(f"Content: {content.strip()}")
    
    # Add any description
    description = topic.get('description', '')
    if description and description.strip():
        parts.append(f"Description: {description.strip()}")
    
    # Combine and truncate
    full_text = "\n\n".join(parts)
    
    if len(full_text) > max_length:
        full_text = full_text[:max_length] + "..."
    
    return full_text


async def generate_summary(content: str, client: AsyncOpenAI, config: EnhancementConfig) -> Tuple[Optional[str], Optional[str]]:
    """
    Generate a concise summary using OpenAI.
    
    Returns (summary, error_message)
    """
    try:
        prompt = f"""
Please provide a concise 2-3 sentence summary of the following content:

{content}

Summary:"""

        response = await client.chat.completions.create(
            model=config.openai_model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that creates concise, informative summaries."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=config.max_tokens,
            temperature=config.temperature
        )
        
        summary = response.choices[0].message.content.strip()
        return summary, None
        
    except Exception as e:
        return None, str(e)


async def extract_key_insights(content: str, client: AsyncOpenAI, config: EnhancementConfig) -> Tuple[List[str], Optional[str]]:
    """
    Extract key insights and important points using OpenAI.
    
    Returns (insights_list, error_message)
    """
    try:
        prompt = f"""
Analyze the following content and extract 3-5 key insights or important points. 
Return them as a numbered list.

{content}

Key insights:"""

        response = await client.chat.completions.create(
            model=config.openai_model,
            messages=[
                {"role": "system", "content": "You are an expert analyst who extracts key insights from content."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=config.max_tokens,
            temperature=config.temperature
        )
        
        insights_text = response.choices[0].message.content.strip()
        
        # Parse numbered list into array
        insights = []
        for line in insights_text.split('\n'):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                # Remove numbering/bullets and clean up
                cleaned = re.sub(r'^[\d\.\-\•\*\s]+', '', line).strip()
                if cleaned:
                    insights.append(cleaned)
        
        return insights, None
        
    except Exception as e:
        return [], str(e)


async def generate_tags(content: str, client: AsyncOpenAI, config: EnhancementConfig) -> Tuple[List[str], Optional[str]]:
    """
    Generate relevant tags for content categorization using OpenAI.
    
    Returns (tags_list, error_message)
    """
    try:
        prompt = f"""
Generate 5-8 relevant tags for the following content. Tags should be single words or short phrases that help categorize the content.
Return only the tags, separated by commas.

{content}

Tags:"""

        response = await client.chat.completions.create(
            model=config.openai_model,
            messages=[
                {"role": "system", "content": "You are a content categorization expert who generates relevant tags."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=config.temperature
        )
        
        tags_text = response.choices[0].message.content.strip()
        
        # Parse comma-separated tags
        tags = []
        for tag in tags_text.split(','):
            tag = tag.strip().lower()
            if tag and len(tag) <= 30:  # Reasonable tag length limit
                tags.append(tag)
        
        return tags[:8], None  # Limit to 8 tags
        
    except Exception as e:
        return [], str(e)


async def sentiment_analysis(content: str, client: AsyncOpenAI, config: EnhancementConfig) -> Tuple[Optional[str], Optional[str]]:
    """
    Analyze sentiment of content using OpenAI.
    
    Returns (sentiment, error_message)
    """
    try:
        prompt = f"""
Analyze the sentiment of the following content. Respond with one word: positive, negative, or neutral.

{content}

Sentiment:"""

        response = await client.chat.completions.create(
            model=config.openai_model,
            messages=[
                {"role": "system", "content": "You are a sentiment analysis expert. Respond with only one word: positive, negative, or neutral."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=10,
            temperature=0.1
        )
        
        sentiment = response.choices[0].message.content.strip().lower()
        
        # Validate sentiment value
        if sentiment in ['positive', 'negative', 'neutral']:
            return sentiment, None
        else:
            return 'neutral', None  # Default fallback
        
    except Exception as e:
        return None, str(e)


def generate_fallback_content(topic: Dict[str, Any]) -> EnhancementResult:
    """
    Generate fallback enhancement when OpenAI is not available.
    
    Uses rule-based approaches for basic enhancement.
    """
    topic_id = topic.get('reddit_id') or topic.get('id') or 'unknown'
    title = topic.get('title', '')
    
    # Basic rule-based tags from title
    tags = []
    title_lower = title.lower()
    
    # Technology keywords
    tech_keywords = ['ai', 'artificial intelligence', 'machine learning', 'blockchain', 'crypto', 'technology', 'software', 'programming']
    for keyword in tech_keywords:
        if keyword in title_lower:
            tags.append(keyword)
    
    # Business keywords  
    business_keywords = ['startup', 'business', 'market', 'economy', 'finance', 'investment']
    for keyword in business_keywords:
        if keyword in title_lower:
            tags.append(keyword)
    
    if not tags:
        tags = ['general', 'discussion']
    
    # Simple sentiment based on title words
    positive_words = ['breakthrough', 'success', 'amazing', 'great', 'excellent', 'innovative']
    negative_words = ['failure', 'problem', 'issue', 'concern', 'warning', 'crisis']
    
    sentiment = 'neutral'
    for word in positive_words:
        if word in title_lower:
            sentiment = 'positive'
            break
    if sentiment == 'neutral':
        for word in negative_words:
            if word in title_lower:
                sentiment = 'negative'
                break
    
    # Basic summary (just truncated title)
    summary = title[:200] + "..." if len(title) > 200 else title
    
    return EnhancementResult(
        topic_id=topic_id,
        summary=summary,
        key_insights=[f"Topic discusses: {title}"],
        tags=tags[:5],
        sentiment=sentiment,
        enhancement_metadata={
            "method": "rule_based_fallback",
            "openai_available": False,
            "timestamp": datetime.utcnow().isoformat()
        },
        processing_time_seconds=0.1,
        success=True
    )


async def enhance_content(topic: Dict[str, Any], config: Optional[EnhancementConfig] = None) -> EnhancementResult:
    """
    Main content enhancement function.
    
    Processes a single topic with AI enhancement capabilities.
    """
    start_time = time.time()
    
    if config is None:
        config = EnhancementConfig()
    
    topic_id = topic.get('reddit_id') or topic.get('id') or 'unknown'
    
    # Get OpenAI client
    client = get_openai_client()
    if client is None:
        # Fall back to rule-based enhancement
        return generate_fallback_content(topic)
    
    # Extract content for processing
    content = extract_content_preview(topic, config.max_content_length)
    if not content.strip():
        return EnhancementResult(
            topic_id=topic_id,
            summary=None,
            key_insights=[],
            tags=[],
            sentiment=None,
            enhancement_metadata={
                "error": "No content available for enhancement",
                "timestamp": datetime.utcnow().isoformat()
            },
            processing_time_seconds=time.time() - start_time,
            success=False,
            error="No content available for enhancement"
        )
    
    # Initialize results
    summary = None
    insights = []
    tags = []
    sentiment = None
    errors = []
    
    try:
        # Generate summary
        summary, summary_error = await generate_summary(content, client, config)
        if summary_error:
            errors.append(f"Summary generation failed: {summary_error}")
        
        # Rate limiting delay
        await asyncio.sleep(config.rate_limit_delay)
        
        # Extract key insights if enabled
        if config.include_insights:
            insights, insights_error = await extract_key_insights(content, client, config)
            if insights_error:
                errors.append(f"Insights extraction failed: {insights_error}")
            await asyncio.sleep(config.rate_limit_delay)
        
        # Generate tags if enabled
        if config.include_tags:
            tags, tags_error = await generate_tags(content, client, config)
            if tags_error:
                errors.append(f"Tag generation failed: {tags_error}")
            await asyncio.sleep(config.rate_limit_delay)
        
        # Analyze sentiment if enabled
        if config.include_sentiment:
            sentiment, sentiment_error = await sentiment_analysis(content, client, config)
            if sentiment_error:
                errors.append(f"Sentiment analysis failed: {sentiment_error}")
    
    except Exception as e:
        errors.append(f"Enhancement failed: {str(e)}")
    
    processing_time = time.time() - start_time
    
    # If everything failed, fall back to rule-based
    if not summary and not insights and not tags and not sentiment:
        return generate_fallback_content(topic)
    
    return EnhancementResult(
        topic_id=topic_id,
        summary=summary,
        key_insights=insights,
        tags=tags,
        sentiment=sentiment,
        enhancement_metadata={
            "method": "openai_enhanced",
            "model": config.openai_model,
            "timestamp": datetime.utcnow().isoformat(),
            "content_length": len(content),
            "errors": errors if errors else None
        },
        processing_time_seconds=processing_time,
        success=True
    )


async def enhance_topics_batch(topics: List[Dict[str, Any]], config: Optional[EnhancementConfig] = None) -> List[EnhancementResult]:
    """
    Enhance multiple topics with rate limiting and error handling.
    
    Processes topics sequentially to respect API rate limits.
    """
    if config is None:
        config = EnhancementConfig()
    
    results = []
    
    for i, topic in enumerate(topics):
        try:
            result = await enhance_content(topic, config)
            results.append(result)
            
            # Add delay between topics to respect rate limits
            if i < len(topics) - 1:  # Don't delay after last topic
                await asyncio.sleep(config.rate_limit_delay)
                
        except Exception as e:
            # Create error result for failed topics
            topic_id = topic.get('reddit_id') or topic.get('id') or f'unknown_{i}'
            error_result = EnhancementResult(
                topic_id=topic_id,
                summary=None,
                key_insights=[],
                tags=[],
                sentiment=None,
                enhancement_metadata={
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                },
                processing_time_seconds=0.0,
                success=False,
                error=str(e)
            )
            results.append(error_result)
    
    return results