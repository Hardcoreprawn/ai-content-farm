"""
Integration tests for markdown processor with real Azure blob data.

This test suite validates the complete markdown generation pipeline using
real samples from the processed-content container, including RSS and Mastodon
sources that have historically caused issues.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml
from markdown_generation import prepare_frontmatter, validate_frontmatter_fields
from markdown_processor import MarkdownProcessor
from models import ArticleMetadata

# Sample data directory
SAMPLE_DATA_DIR = (
    Path(__file__).parent.parent.parent.parent / "sample_data" / "markdown-generator"
)


class TestRealDataIntegration:
    """Test markdown generation with real Azure blob samples."""

    @pytest.fixture
    def sample_rss_data(self) -> Dict[str, Any]:
        """Load RSS sample data."""
        sample_file = SAMPLE_DATA_DIR / "sample_rss_1.json"
        with open(sample_file, "r", encoding="utf-8") as f:
            return json.load(f)

    @pytest.fixture
    def sample_mastodon_data(self) -> Dict[str, Any]:
        """Load Mastodon sample data."""
        sample_file = SAMPLE_DATA_DIR / "sample_mastodon_1.json"
        with open(sample_file, "r", encoding="utf-8") as f:
            return json.load(f)

    @pytest.fixture
    def sample_mastodon_2_data(self) -> Dict[str, Any]:
        """Load second Mastodon sample data."""
        sample_file = SAMPLE_DATA_DIR / "sample_mastodon_2.json"
        with open(sample_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_rss_sample_frontmatter_generation(
        self, sample_rss_data: Dict[str, Any]
    ) -> None:
        """Test frontmatter generation with RSS data."""
        frontmatter = prepare_frontmatter(
            title=sample_rss_data["title"],
            source=sample_rss_data["source"],
            original_url=sample_rss_data["original_url"],
            generated_at=sample_rss_data["generated_at"],
            format="hugo",
            tags=sample_rss_data.get("tags", []),
        )

        # Validate it's valid YAML
        assert frontmatter.startswith("---\n")
        assert frontmatter.endswith("---")

        # Extract and parse YAML
        yaml_content = frontmatter.split("---")[1]
        parsed = yaml.safe_load(yaml_content)

        # Validate required fields
        assert "title" in parsed
        assert "date" in parsed
        assert "draft" in parsed

        # Validate custom fields are under params
        assert "params" in parsed
        assert parsed["params"]["source"] == "rss"
        assert "original_url" in parsed["params"]
        assert "generated_at" in parsed["params"]

        # Validate no Hugo violations
        errors = validate_frontmatter_fields(parsed)
        assert len(errors) == 0, f"Hugo validation errors: {errors}"

    def test_mastodon_sample_frontmatter_generation(
        self, sample_mastodon_data: Dict[str, Any]
    ) -> None:
        """Test frontmatter generation with Mastodon data (historically problematic)."""
        frontmatter = prepare_frontmatter(
            title=sample_mastodon_data["title"],
            source=sample_mastodon_data["source"],
            original_url=sample_mastodon_data["original_url"],
            generated_at=sample_mastodon_data["generated_at"],
            format="hugo",
            tags=sample_mastodon_data.get("tags", []),
        )

        # Validate it's valid YAML
        assert frontmatter.startswith("---\n")
        assert frontmatter.endswith("---")

        # Extract and parse YAML
        yaml_content = frontmatter.split("---")[1]
        parsed = yaml.safe_load(yaml_content)

        # Validate required fields
        assert "title" in parsed
        assert "date" in parsed
        assert "draft" in parsed

        # Validate custom fields are under params
        assert "params" in parsed
        assert parsed["params"]["source"] == "mastodon"
        assert "original_url" in parsed["params"]

        # Validate no Hugo violations
        errors = validate_frontmatter_fields(parsed)
        assert len(errors) == 0, f"Hugo validation errors: {errors}"

    def test_mastodon_sample_2_frontmatter_generation(
        self, sample_mastodon_2_data: Dict[str, Any]
    ) -> None:
        """Test frontmatter generation with second Mastodon sample."""
        frontmatter = prepare_frontmatter(
            title=sample_mastodon_2_data["title"],
            source=sample_mastodon_2_data["source"],
            original_url=sample_mastodon_2_data["original_url"],
            generated_at=sample_mastodon_2_data["generated_at"],
            format="hugo",
            tags=sample_mastodon_2_data.get("tags", []),
        )

        # Validate it's valid YAML
        yaml_content = frontmatter.split("---")[1]
        parsed = yaml.safe_load(yaml_content)

        # Validate no Hugo violations
        errors = validate_frontmatter_fields(parsed)
        assert len(errors) == 0, f"Hugo validation errors: {errors}"

    def test_all_samples_have_valid_dates(
        self,
        sample_rss_data: Dict[str, Any],
        sample_mastodon_data: Dict[str, Any],
        sample_mastodon_2_data: Dict[str, Any],
    ) -> None:
        """Verify all sample data has valid RFC3339 dates."""
        samples = [sample_rss_data, sample_mastodon_data, sample_mastodon_2_data]

        for sample in samples:
            frontmatter = prepare_frontmatter(
                title=sample["title"],
                source=sample["source"],
                original_url=sample["original_url"],
                generated_at=sample["generated_at"],
                format="hugo",
            )

            yaml_content = frontmatter.split("---")[1]
            parsed = yaml.safe_load(yaml_content)

            # Date should be parseable
            date_str = parsed["date"]
            parsed_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            assert parsed_date is not None

    def test_special_characters_in_titles(
        self, sample_mastodon_data: Dict[str, Any]
    ) -> None:
        """Test that special characters in titles are properly escaped."""
        # Mastodon titles often have special chars: [#TRADESHOW], colons, etc.
        frontmatter = prepare_frontmatter(
            # Use original title with special chars
            title=sample_mastodon_data["original_title"],
            source=sample_mastodon_data["source"],
            original_url=sample_mastodon_data["original_url"],
            generated_at=sample_mastodon_data["generated_at"],
            format="hugo",
        )

        # Should still be valid YAML despite special characters
        yaml_content = frontmatter.split("---")[1]
        parsed = yaml.safe_load(yaml_content)

        assert "title" in parsed
        # Title should contain the original content
        assert len(parsed["title"]) > 0

    def test_metadata_fields_conversion(self, sample_rss_data: Dict[str, Any]) -> None:
        """Test that all metadata fields are correctly converted."""
        metadata = ArticleMetadata(
            title=sample_rss_data["title"],
            url=sample_rss_data["url"],
            source=sample_rss_data["source"],
            author=None,  # RSS sample doesn't have author
            published_date=None,
            tags=[],
            category=None,
        )

        frontmatter = prepare_frontmatter(
            title=metadata.title,
            source=metadata.source,
            original_url=sample_rss_data["original_url"],
            generated_at=sample_rss_data["generated_at"],
            format="hugo",
            author=metadata.author,
            published_date=metadata.published_date,
            category=metadata.category,
            tags=metadata.tags,
        )

        yaml_content = frontmatter.split("---")[1]
        parsed = yaml.safe_load(yaml_content)

        # Verify structure
        assert "title" in parsed
        assert "date" in parsed
        assert "params" in parsed
        assert "source" in parsed["params"]
        assert "original_url" in parsed["params"]

    def test_empty_tags_list(self, sample_rss_data: Dict[str, Any]) -> None:
        """Test that empty tags list is handled correctly."""
        frontmatter = prepare_frontmatter(
            title=sample_rss_data["title"],
            source=sample_rss_data["source"],
            original_url=sample_rss_data["original_url"],
            generated_at=sample_rss_data["generated_at"],
            format="hugo",
            tags=[],  # Empty tags
        )

        yaml_content = frontmatter.split("---")[1]
        parsed = yaml.safe_load(yaml_content)

        # Empty keywords list is omitted by Hugo generator (Hugo convention)
        # This is valid - Hugo treats missing keywords as no keywords
        assert parsed["title"] == sample_rss_data["title"]
        assert "date" in parsed

    def test_additional_custom_params(self, sample_rss_data: Dict[str, Any]) -> None:
        """Test that additional custom parameters end up in params."""
        frontmatter = prepare_frontmatter(
            title=sample_rss_data["title"],
            source=sample_rss_data["source"],
            original_url=sample_rss_data["original_url"],
            generated_at=sample_rss_data["generated_at"],
            format="hugo",
            word_count=sample_rss_data.get("word_count"),
            quality_score=sample_rss_data.get("quality_score"),
        )

        yaml_content = frontmatter.split("---")[1]
        parsed = yaml.safe_load(yaml_content)

        # Custom params should be under params key
        assert "params" in parsed
        assert "word_count" in parsed["params"]
        assert "quality_score" in parsed["params"]

        # Validate no Hugo violations
        errors = validate_frontmatter_fields(parsed)
        assert len(errors) == 0, f"Hugo validation errors: {errors}"


class TestFormatExtensibility:
    """Test the extensibility of prepare_frontmatter for future formats."""

    def test_hugo_format_supported(self) -> None:
        """Verify Hugo format is supported."""
        frontmatter = prepare_frontmatter(
            title="Test Article",
            source="test",
            original_url="https://example.com",
            generated_at="2025-10-13T08:00:00Z",
            format="hugo",
        )

        assert frontmatter.startswith("---\n")
        assert "title: Test Article" in frontmatter

    def test_unsupported_format_raises_error(self) -> None:
        """Verify unsupported formats raise clear error."""
        with pytest.raises(ValueError, match="Unsupported frontmatter format: jekyll"):
            prepare_frontmatter(
                title="Test Article",
                source="test",
                original_url="https://example.com",
                generated_at="2025-10-13T08:00:00Z",
                format="jekyll",  # Not yet supported
            )

    def test_format_parameter_is_optional(self) -> None:
        """Verify format defaults to 'hugo'."""
        frontmatter = prepare_frontmatter(
            title="Test Article",
            source="test",
            original_url="https://example.com",
            generated_at="2025-10-13T08:00:00Z",
            # format not specified, should default to 'hugo'
        )

        # Should produce valid Hugo frontmatter
        yaml_content = frontmatter.split("---")[1]
        parsed = yaml.safe_load(yaml_content)
        assert "title" in parsed
        assert "date" in parsed


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
