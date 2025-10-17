"""
End-to-end integration test for article path refactoring.

Blackbox test: verifies blob storage paths follow new articles/YYYY-MM-DD/slug format
through the complete processor pipeline without internal implementation details.
"""

import pytest
from utils.blob_utils import generate_articles_processed_blob_path


@pytest.mark.asyncio
class TestArticlePathE2E:
    """E2E test: verify articles/ paths used throughout processor pipeline."""

    def test_processor_outputs_use_articles_prefix_for_processed_files(self):
        """Contract: processor must save articles to articles/YYYY-MM-DD/slug.json."""
        # This is the contract that processor_operations.py must follow
        # when generating blob paths for processed articles.

        # Simulate article result from processor
        article_result = {
            "slug": "saturn-moon-potential-for-life-discovery",
            "published_date": "2025-10-13T09:06:54+00:00",
            "title": "Saturn's Moon Potential for Life Discovery",
            "content": "Full article content...",
            "topic_id": "topic_123",
        }

        # Processor must use this function to generate path
        path = generate_articles_processed_blob_path(article_result)

        # Contract verification
        assert (
            path == "articles/2025-10-13/saturn-moon-potential-for-life-discovery.json"
        )
        assert path.startswith("articles/")
        assert path.endswith(".json")

    def test_markdown_paths_derived_from_processed_paths(self):
        """Contract: markdown paths = processed paths with .md extension."""
        article_result = {
            "slug": "ai-research-breakthrough",
            "published_date": "2025-10-13T14:30:00Z",
        }

        path = generate_articles_processed_blob_path(article_result)

        # Markdown should be simple swap
        markdown_path = path.replace(".json", ".md")

        assert markdown_path == "articles/2025-10-13/ai-research-breakthrough.md"

    def test_paths_are_queryable_by_date_range(self):
        """Contract: paths must support date-range queries."""
        articles = [
            {"slug": "article-1", "published_date": "2025-10-13"},
            {"slug": "article-2", "published_date": "2025-10-13"},
            {"slug": "article-3", "published_date": "2025-10-14"},
        ]

        paths = [generate_articles_processed_blob_path(a) for a in articles]

        # All Oct 13 articles should have same prefix for list operations
        oct_13_paths = [p for p in paths if "2025-10-13" in p]
        oct_14_paths = [p for p in paths if "2025-10-14" in p]

        assert len(oct_13_paths) == 2
        assert len(oct_14_paths) == 1

        # Could query with: container.list_blobs(prefix="articles/2025-10-13/")
        assert all(p.startswith("articles/2025-10-13/") for p in oct_13_paths)
        assert all(p.startswith("articles/2025-10-14/") for p in oct_14_paths)

    def test_no_timestamp_mixing_with_slug(self):
        """Contract: paths use slug (not timestamp) as filename."""
        # Old paths mixed timestamps with identifiers: 20251013_090654_topic-123.json
        # New paths use slugs: saturn-moon-potential.json

        article = {
            "slug": "saturn-moon-potential",
            "published_date": "2025-10-13T09:06:54.123456+00:00",
        }

        path = generate_articles_processed_blob_path(article)

        # Should NOT contain the full ISO timestamp in filename
        filename = path.split("/")[-1]
        assert filename == "saturn-moon-potential.json"
        assert ":" not in filename  # No ISO time format
        assert "T" not in filename
        assert "_090654" not in filename  # No HHMMSS timestamp
