"""
Tests for Stock Image Service

Simple tests verifying contracts and data transformations.
"""

import inspect

import pytest
from services.image_service import (
    extract_keywords_from_article,
    fetch_image_for_article,
    parse_unsplash_photo,
    search_unsplash_image,
)


@pytest.mark.unit
def test_extract_keywords_prioritizes_tags():
    """Keywords should come from tags first."""
    keywords = extract_keywords_from_article(
        title="Some Long Article Title Here",
        tags=["AI", "machine-learning"],
    )
    assert keywords == "AI machine-learning"


@pytest.mark.unit
def test_extract_keywords_from_title_when_no_tags():
    """Should extract keywords from title when no tags."""
    keywords = extract_keywords_from_article(
        title="The Future of Quantum Computing", tags=[]
    )
    assert keywords == "Future Quantum Computing"
    assert "The" not in keywords  # Stopword removed


@pytest.mark.unit
def test_extract_keywords_handles_none_tags():
    """Should handle None tags gracefully."""
    keywords = extract_keywords_from_article(
        title="Machine Learning Basics",
        tags=None,
    )
    assert "Machine" in keywords
    assert "Learning" in keywords


@pytest.mark.unit
def test_extract_keywords_fallback():
    """Should provide fallback when nothing available."""
    keywords = extract_keywords_from_article(title="", tags=[])
    assert keywords == "technology"


@pytest.mark.unit
def test_parse_unsplash_photo_extracts_all_fields():
    """Should extract all required fields from Unsplash API response."""
    unsplash_response = {
        "urls": {
            "raw": "https://images.unsplash.com/raw-url",
            "regular": "https://images.unsplash.com/regular-url",
            "small": "https://images.unsplash.com/small-url",
        },
        "user": {
            "name": "Test Photographer",
            "links": {"html": "https://unsplash.com/@testphoto"},
        },
        "description": "Test image description",
        "alt_description": "Alt description",
        "color": "#C0FFEE",
        "links": {"html": "https://unsplash.com/photos/test123"},
    }

    result = parse_unsplash_photo(unsplash_response)

    # Verify we extract what we need for frontmatter
    assert result["url_regular"] == "https://images.unsplash.com/regular-url"
    assert result["photographer"] == "Test Photographer"
    assert result["photographer_url"] == "https://unsplash.com/@testphoto"
    assert result["description"] == "Test image description"
    assert result["color"] == "#C0FFEE"
    assert result["unsplash_url"] == "https://unsplash.com/photos/test123"


@pytest.mark.unit
def test_parse_unsplash_photo_uses_alt_description_fallback():
    """Should use alt_description when description is None."""
    unsplash_response = {
        "urls": {
            "raw": "https://raw",
            "regular": "https://regular",
            "small": "https://small",
        },
        "user": {
            "name": "Photographer",
            "links": {"html": "https://unsplash.com/@photo"},
        },
        "description": None,
        "alt_description": "Fallback alt description",
        "color": "#ABCDEF",
        "links": {"html": "https://unsplash.com/photos/abc"},
    }

    result = parse_unsplash_photo(unsplash_response)
    assert result["description"] == "Fallback alt description"


@pytest.mark.unit
def test_api_functions_have_correct_signatures():
    """Verify API functions accept the right parameters."""
    # search_unsplash_image should take access_key and query
    search_sig = inspect.signature(search_unsplash_image)
    assert "access_key" in search_sig.parameters
    assert "query" in search_sig.parameters

    # fetch_image_for_article should take access_key, title, tags
    fetch_sig = inspect.signature(fetch_image_for_article)
    assert "access_key" in fetch_sig.parameters
    assert "title" in fetch_sig.parameters
    assert "tags" in fetch_sig.parameters


@pytest.mark.unit
def test_parsed_photo_has_all_required_fields():
    """Verify parsed photo dict has all fields we need for frontmatter."""
    minimal_unsplash_photo = {
        "urls": {"raw": "a", "regular": "b", "small": "c"},
        "user": {"name": "Name", "links": {"html": "url"}},
        "description": "desc",
        "color": "#FFF",
        "links": {"html": "link"},
    }

    result = parse_unsplash_photo(minimal_unsplash_photo)

    # These are the fields markdown_generator.py expects
    required_fields = [
        "photographer",
        "photographer_url",
        "url_regular",
        "description",
        "color",
        "unsplash_url",
    ]

    for field in required_fields:
        assert field in result, f"Missing required field: {field}"
