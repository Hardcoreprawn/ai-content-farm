"""
Content Discovery and Analysis Functions

Functions for analyzing content to identify trending topics and generate research recommendations.
"""

import logging
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List

from models import DiscoveryResult, ResearchRecommendation, TrendingTopic

from libs.blob_storage import BlobContainers

logger = logging.getLogger(__name__)


def analyze_trending_topics(
    posts: List[Dict[str, Any]], min_mentions: int = 2
) -> List[TrendingTopic]:
    """Analyze posts to identify trending topics."""
    # Extract keywords and topics from posts
    topic_mentions = Counter()
    topic_contexts = defaultdict(list)
    topic_sources = defaultdict(lambda: defaultdict(int))

    for post in posts:
        title = post.get("title", "").lower()
        content = post.get("selftext", "").lower()
        source = post.get("subreddit", "unknown")

        # Simple keyword extraction (in production, use NLP)
        keywords = extract_keywords(title + " " + content)

        for keyword in keywords:
            topic_mentions[keyword] += 1
            topic_contexts[keyword].append(post.get("title", ""))
            topic_sources[keyword][source] += 1

    # Filter and rank topics
    trending_topics = []
    for topic, mentions in topic_mentions.most_common(20):
        if mentions >= min_mentions:
            trending_topic = TrendingTopic(
                topic=topic,
                mentions=mentions,
                growth_rate=0.0,  # Would need historical data
                confidence=min(mentions / 10.0, 1.0),
                related_keywords=[topic],  # Simplified
                sample_content=topic_contexts[topic][:3],
                source_breakdown=dict(topic_sources[topic]),
                sentiment_score=None,  # TODO: Add sentiment analysis
                engagement_metrics={},
            )
            trending_topics.append(trending_topic)

    return trending_topics


def extract_keywords(text: str) -> List[str]:
    """Extract potential topics/keywords from text."""
    # Simple keyword extraction - in production use NLP libraries
    tech_keywords = [
        "artificial intelligence",
        "ai",
        "machine learning",
        "ml",
        "quantum computing",
        "blockchain",
        "cryptocurrency",
        "cloud computing",
        "cybersecurity",
        "automation",
        "neural networks",
        "deep learning",
        "data science",
        "kubernetes",
        "docker",
        "microservices",
        "api",
        "devops",
        "cicd",
        "terraform",
        "ansible",
    ]

    found_keywords = []
    text_lower = text.lower()

    for keyword in tech_keywords:
        if keyword in text_lower:
            found_keywords.append(keyword)

    return found_keywords


def calculate_research_potential(topic: str, mentions: int) -> float:
    """Calculate research potential for a topic."""
    # High research potential for technical topics with good engagement
    research_indicators = [
        "artificial intelligence",
        "machine learning",
        "quantum",
        "blockchain",
        "cybersecurity",
        "automation",
        "climate",
        "healthcare",
        "research",
    ]

    base_score = min(mentions / 10.0, 0.7)

    for indicator in research_indicators:
        if indicator in topic.lower():
            base_score += 0.2
            break

    return min(base_score, 1.0)


def generate_research_recommendations(
    topics: List[TrendingTopic],
) -> List[ResearchRecommendation]:
    """Generate research recommendations for trending topics."""
    recommendations = []

    for topic in topics[:5]:  # Top 5 topics
        research_potential = calculate_research_potential(topic.topic, topic.mentions)
        if research_potential > 0.6:
            recommendation = ResearchRecommendation(
                topic=topic,
                research_potential=research_potential,
                recommended_approach=get_research_approach(topic),
                key_questions=generate_key_questions(topic),
                suggested_sources=recommend_sources(topic),
                estimated_depth=estimate_depth(topic),
            )
            recommendations.append(recommendation)

    return recommendations


def get_research_approach(topic: TrendingTopic) -> str:
    """Recommend research approach for a topic."""
    if "ai" in topic.topic or "machine learning" in topic.topic:
        return (
            "Technical analysis with practical applications and ethical considerations"
        )
    elif "cybersecurity" in topic.topic:
        return "Threat landscape analysis with mitigation strategies"
    elif "blockchain" in topic.topic:
        return "Technology assessment with use case analysis"
    else:
        return "Multi-perspective analysis with trend evaluation"


def generate_key_questions(topic: TrendingTopic) -> List[str]:
    """Generate key research questions for a topic."""
    base_questions = [
        f"What are the latest developments in {topic.topic}?",
        f"What are the practical implications of {topic.topic}?",
        f"What challenges exist in {topic.topic} implementation?",
    ]

    if topic.confidence > 0.7:
        base_questions.append(f"Why is {topic.topic} trending now?")

    if "ai" in topic.topic or "machine learning" in topic.topic:
        base_questions.append(f"What are the ethical considerations of {topic.topic}?")

    return base_questions


def recommend_sources(topic: TrendingTopic) -> List[str]:
    """Recommend source types for researching a topic."""
    sources = ["academic papers", "industry reports", "expert interviews"]

    if "ai" in topic.topic or "technology" in topic.topic:
        sources.extend(["technical documentation", "open source projects"])

    if topic.confidence > 0.7:
        sources.append("news articles")

    return sources


def estimate_depth(topic: TrendingTopic) -> str:
    """Estimate recommended research depth."""
    research_potential = calculate_research_potential(topic.topic, topic.mentions)
    if research_potential > 0.8:
        return "deep"
    elif research_potential > 0.6:
        return "medium"
    else:
        return "brief"


async def save_discovery_results(result: DiscoveryResult, blob_client) -> None:
    """Save discovery results to blob storage."""
    try:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        blob_name = f"topic_discovery_{timestamp}.json"

        # Save to collected content container
        blob_client.upload_json(
            container_name=BlobContainers.COLLECTED_CONTENT,
            blob_name=blob_name,
            data=result.model_dump(),
        )

        logger.info(f"Saved discovery results to {blob_name}")

    except Exception as e:
        logger.error(f"Failed to save discovery results: {e}")
        raise
