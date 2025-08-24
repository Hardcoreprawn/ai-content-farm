"""
Blob Storage API contract for site-generator testing.
Based on Azure Blob Storage API structure.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class BlobItemContract:
    """Contract for Azure Blob Storage blob item."""

    name: str
    last_modified: datetime
    size: int = 1024
    content_type: str = "application/json"

    @classmethod
    def create_mock(cls, **overrides) -> "BlobItemContract":
        """Create realistic blob item for testing."""
        defaults = {
            "name": "ranked-topics/2025-08-24.json",
            "last_modified": datetime.now(),
            "size": 2048,
            "content_type": "application/json",
        }
        defaults.update(overrides)
        return cls(**defaults)


@dataclass
class RankedContentContract:
    """Contract for ranked content structure from content-ranker."""

    ranked_topics: List[Dict[str, Any]]
    metadata: Dict[str, Any]

    @classmethod
    def create_mock(cls, num_articles: int = 3, **overrides) -> "RankedContentContract":
        """Create realistic ranked content for testing."""
        articles = []
        for i in range(num_articles):
            articles.append(
                {
                    "title": f"AI Breakthrough #{i+1}: Revolutionary ML Algorithm",
                    "url": f"https://example.com/article-{i+1}",
                    "summary": f"Article {i+1} summary: Latest developments in AI technology.",
                    "content": f"Full content for article {i+1} about AI breakthroughs.",
                    "author": f"Tech Writer {i+1}",
                    "score": 95 - (i * 5),  # Realistic decreasing scores
                    "source": "TechCrunch",
                    "published_date": "2025-08-24T10:00:00Z",
                    "tags": ["AI", "Machine Learning", "Technology"],
                }
            )

        defaults = {
            "ranked_topics": articles,
            "metadata": {
                "generated_at": "2025-08-24T10:30:00Z",
                "total_items": num_articles,
                "source": "content-ranker",
                "ranking_algorithm": "score-based",
            },
        }
        defaults.update(overrides)
        return cls(**defaults)


@dataclass
class SiteGenerationResultContract:
    """Contract for site generation results."""

    site_id: str
    status: str
    files_generated: List[str]
    generation_time: float

    @classmethod
    def create_mock(cls, **overrides) -> "SiteGenerationResultContract":
        """Create realistic site generation result."""
        defaults = {
            "site_id": "test-site-123",
            "status": "completed",
            "files_generated": [
                "index.html",
                "feed.xml",
                "assets/style.css",
                "assets/script.js",
            ],
            "generation_time": 2.5,
        }
        defaults.update(overrides)
        return cls(**defaults)
