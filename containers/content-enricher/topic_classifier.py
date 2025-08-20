"""
Topic Classification Module

Simple keyword-based topic classification for content.
Keeps it simple and predictable.
"""

from typing import Any, Dict, List


def classify_topic(content: Dict[str, Any]) -> Dict[str, Any]:
    """
    Classify content into topics using simple keyword matching.

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
        return {"primary_topic": "general", "confidence": 0.0, "topics": []}

    # Simple keyword-based classification
    topic_keywords = {
        "technology": [
            "ai",
            "machine learning",
            "neural",
            "algorithm",
            "computer",
            "software",
            "tech",
            "digital",
            "programming",
            "code",
            "data",
        ],
        "science": [
            "research",
            "study",
            "experiment",
            "discovery",
            "climate",
            "biology",
            "physics",
            "chemistry",
            "scientific",
        ],
        "business": [
            "company",
            "market",
            "financial",
            "economy",
            "business",
            "startup",
            "revenue",
            "investment",
        ],
        "health": [
            "medical",
            "health",
            "disease",
            "treatment",
            "doctor",
            "patient",
            "medicine",
            "clinical",
        ],
        "politics": [
            "government",
            "policy",
            "election",
            "political",
            "congress",
            "senate",
            "president",
            "vote",
        ],
        "entertainment": [
            "movie",
            "film",
            "music",
            "game",
            "gaming",
            "entertainment",
            "celebrity",
            "show",
        ],
        "sports": [
            "sport",
            "game",
            "team",
            "player",
            "match",
            "championship",
            "football",
            "basketball",
        ],
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
        topics.sort(key=lambda x: x["score"], reverse=True)

    return {"primary_topic": primary_topic, "confidence": confidence, "topics": topics}
