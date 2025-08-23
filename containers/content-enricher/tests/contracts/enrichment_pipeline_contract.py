"""
Enrichment Pipeline Contract - Defines expected enrichment data structures.

This ensures consistent data formats across all enrichment functions and
provides realistic test data for pipeline testing.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class SentimentAnalysisContract:
    """Contract for sentiment analysis results."""

    sentiment: str
    confidence: float
    scores: Dict[str, float]

    @classmethod
    def create_mock(
        cls, sentiment: str = "positive", **overrides
    ) -> "SentimentAnalysisContract":
        """Create mock sentiment analysis result."""
        sentiment_configs = {
            "positive": {
                "confidence": 0.85,
                "scores": {"positive": 0.85, "neutral": 0.10, "negative": 0.05},
            },
            "negative": {
                "confidence": 0.90,
                "scores": {"positive": 0.05, "neutral": 0.05, "negative": 0.90},
            },
            "neutral": {
                "confidence": 0.75,
                "scores": {"positive": 0.30, "neutral": 0.50, "negative": 0.20},
            },
        }

        config = sentiment_configs.get(sentiment, sentiment_configs["neutral"])
        defaults = {"sentiment": sentiment, **config}
        defaults.update(overrides)
        return cls(**defaults)


@dataclass
class TopicClassificationContract:
    """Contract for topic classification results."""

    primary_topic: str
    confidence: float
    topics: List[str]
    categories: Optional[List[str]] = None

    @classmethod
    def create_mock(
        cls, primary_topic: str = "technology", **overrides
    ) -> "TopicClassificationContract":
        """Create mock topic classification result."""
        topic_configs = {
            "technology": {
                "confidence": 0.88,
                "topics": ["technology", "artificial intelligence", "software"],
            },
            "science": {
                "confidence": 0.92,
                "topics": ["science", "research", "environment"],
            },
            "business": {
                "confidence": 0.78,
                "topics": ["business", "finance", "economy"],
            },
            "health": {
                "confidence": 0.85,
                "topics": ["health", "medicine", "wellness"],
            },
        }

        config = topic_configs.get(primary_topic, topic_configs["technology"])
        defaults = {"primary_topic": primary_topic, **config}
        defaults.update(overrides)
        return cls(**defaults)


@dataclass
class ContentSummaryContract:
    """Contract for content summary results."""

    summary: str
    word_count: int
    key_points: Optional[List[str]] = None

    @classmethod
    def create_mock(
        cls, content_type: str = "technology", **overrides
    ) -> "ContentSummaryContract":
        """Create mock content summary."""
        summaries = {
            "technology": {
                "summary": "This article discusses recent advances in artificial intelligence technology, focusing on machine learning applications and their potential impact on various industries.",
                "key_points": [
                    "AI technology advances",
                    "Machine learning applications",
                    "Industry impact",
                ],
            },
            "science": {
                "summary": "A comprehensive study on climate change reveals new insights into environmental patterns and their effects on global ecosystems.",
                "key_points": [
                    "Climate change research",
                    "Environmental patterns",
                    "Global ecosystem effects",
                ],
            },
            "business": {
                "summary": "Market analysis shows significant growth in renewable energy investments, with major corporations shifting towards sustainable practices.",
                "key_points": [
                    "Renewable energy growth",
                    "Corporate sustainability",
                    "Market investment trends",
                ],
            },
        }

        config = summaries.get(content_type, summaries["technology"])
        defaults = {"word_count": len(config["summary"].split()), **config}
        defaults.update(overrides)
        return cls(**defaults)


@dataclass
class TrendScoreContract:
    """Contract for trend score calculations."""

    trend_score: float
    factors: Dict[str, float]

    @classmethod
    def create_mock(
        cls, engagement_level: str = "medium", **overrides
    ) -> "TrendScoreContract":
        """Create mock trend score."""
        engagement_configs = {
            "high": {
                "trend_score": 0.85,
                "factors": {"normalized": 0.8, "engagement": 0.9, "decay": 1.0},
            },
            "medium": {
                "trend_score": 0.65,
                "factors": {"normalized": 0.6, "engagement": 0.7, "decay": 0.9},
            },
            "low": {
                "trend_score": 0.35,
                "factors": {"normalized": 0.4, "engagement": 0.3, "decay": 0.8},
            },
        }

        config = engagement_configs.get(engagement_level, engagement_configs["medium"])
        defaults = config
        defaults.update(overrides)
        return cls(**defaults)


@dataclass
class EnrichmentResultContract:
    """Contract for complete enrichment result."""

    id: str
    title: str
    content: str
    enrichment: Dict[str, Any]
    metadata: Dict[str, Any]

    @classmethod
    def create_mock(
        cls, content_id: str = "test_123", **overrides
    ) -> "EnrichmentResultContract":
        """Create mock enrichment result."""
        sentiment = SentimentAnalysisContract.create_mock()
        topics = TopicClassificationContract.create_mock()
        summary = ContentSummaryContract.create_mock()
        trend = TrendScoreContract.create_mock()

        defaults = {
            "id": content_id,
            "title": "Test Article: AI Technology Breakthrough",
            "content": "This is a comprehensive article about artificial intelligence and its impact on modern technology...",
            "enrichment": {
                "sentiment": {
                    "sentiment": sentiment.sentiment,
                    "confidence": sentiment.confidence,
                    "scores": sentiment.scores,
                },
                "topics": {
                    "primary_topic": topics.primary_topic,
                    "confidence": topics.confidence,
                    "topics": topics.topics,
                },
                "summary": {
                    "summary": summary.summary,
                    "word_count": summary.word_count,
                    "key_points": summary.key_points,
                },
                "trend": {"trend_score": trend.trend_score, "factors": trend.factors},
            },
            "metadata": {
                "enriched_at": datetime.now(timezone.utc).isoformat(),
                "enrichment_version": "1.0.0",
                "processing_time": 2.5,
                "ai_model_used": "text-davinci-003",
            },
        }
        defaults.update(overrides)
        return cls(**defaults)


class MockEnrichmentPipeline:
    """Mock enrichment pipeline for testing."""

    def __init__(self):
        self.enrichment_count = 0
        self.last_enrichment = None

    def enrich_content(self, content_item: Dict[str, Any]) -> Dict[str, Any]:
        """Mock content enrichment with realistic results."""
        self.enrichment_count += 1

        # Create realistic enrichment based on content
        content_text = content_item.get("content", "") + content_item.get("title", "")

        # Determine content characteristics
        if any(
            word in content_text.lower() for word in ["amazing", "fantastic", "great"]
        ):
            sentiment_type = "positive"
        elif any(word in content_text.lower() for word in ["terrible", "awful", "bad"]):
            sentiment_type = "negative"
        else:
            sentiment_type = "neutral"

        if any(
            word in content_text.lower() for word in ["science", "climate", "research"]
        ):
            topic_type = "science"
        elif any(
            word in content_text.lower() for word in ["business", "market", "finance"]
        ):
            topic_type = "business"
        else:
            topic_type = "technology"

        # Generate enrichment
        result = EnrichmentResultContract.create_mock(
            content_id=content_item.get("id", f"mock_{self.enrichment_count}")
        )

        # Customize based on content analysis
        result.enrichment["sentiment"] = SentimentAnalysisContract.create_mock(
            sentiment_type
        ).__dict__
        result.enrichment["topics"] = TopicClassificationContract.create_mock(
            topic_type
        ).__dict__
        result.enrichment["summary"] = ContentSummaryContract.create_mock(
            topic_type
        ).__dict__

        self.last_enrichment = result
        return result.__dict__
