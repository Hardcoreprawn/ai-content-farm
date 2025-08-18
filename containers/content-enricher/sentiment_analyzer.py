"""
Sentiment Analysis Module

Simple rule-based sentiment analysis for content.
No complex models, just reliable keyword matching.
"""

from typing import Dict, Any


def analyze_sentiment(content: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze sentiment of content using simple keyword matching.

    Args:
        content: Content dictionary with title and content fields

    Returns:
        Dictionary with sentiment, confidence, and scores
    """
    title = content.get("title", "")
    content_text = content.get("content", "")

    # Combine title and content for analysis
    full_text = f"{title} {content_text}".lower()

    if not full_text.strip():
        return {
            "sentiment": "neutral",
            "confidence": 0.0,
            "positive_score": 0.0,
            "negative_score": 0.0,
            "neutral_score": 1.0
        }

    # Simple word lists for sentiment
    positive_words = [
        "good", "great", "excellent", "amazing", "wonderful", "fantastic",
        "positive", "success", "win", "best", "love", "like", "happy",
        "exciting", "breakthrough", "innovation", "improve", "benefit"
    ]

    negative_words = [
        "bad", "terrible", "awful", "horrible", "worst", "hate", "dislike",
        "negative", "fail", "failure", "problem", "issue", "concern", "worry",
        "dangerous", "risk", "threat", "crisis", "decline", "damage"
    ]

    # Count sentiment words
    positive_count = sum(1 for word in positive_words if word in full_text)
    negative_count = sum(1 for word in negative_words if word in full_text)

    # Calculate scores
    total_words = len(full_text.split())
    if total_words == 0:
        positive_score = 0.0
        negative_score = 0.0
    else:
        positive_score = min(positive_count / total_words * 10, 1.0)
        negative_score = min(negative_count / total_words * 10, 1.0)

    neutral_score = 1.0 - max(positive_score, negative_score)

    # Determine overall sentiment
    if positive_score > negative_score and positive_score > 0.1:
        sentiment = "positive"
        confidence = positive_score
    elif negative_score > positive_score and negative_score > 0.1:
        sentiment = "negative"
        confidence = negative_score
    else:
        sentiment = "neutral"
        confidence = neutral_score

    return {
        "sentiment": sentiment,
        "confidence": confidence,
        "positive_score": positive_score,
        "negative_score": negative_score,
        "neutral_score": neutral_score
    }
