"""
Tests for Stock Image Service

Simple tests verifying contracts and data transformations.
"""

import inspect

import pytest
from services.image_service import (
    extract_capitalized_words,
    extract_keywords_from_article,
    extract_keywords_from_content,
    fetch_image_for_article,
    has_date_prefix,
    parse_unsplash_photo,
    search_unsplash_image,
    should_skip_image,
)

# ============================================================================
# Skip Logic Tests
# ============================================================================


@pytest.mark.unit
def test_has_date_prefix_detects_standard_format():
    """Should detect (DD MMM) format."""
    assert has_date_prefix("(15 Oct) Article Title")
    assert has_date_prefix("(1 Jan) News")


@pytest.mark.unit
def test_has_date_prefix_no_false_positives():
    """Should not detect date prefix in clean titles."""
    assert not has_date_prefix("Article Title")
    assert not has_date_prefix("10 Reasons to Use AI")


@pytest.mark.unit
def test_should_skip_image_for_short_titles():
    """Should skip images for suspiciously short titles."""
    assert should_skip_image("AI")  # Too short
    assert should_skip_image("Short")  # < 20 chars
    assert not should_skip_image("Understanding Quantum Computing")  # Good length


@pytest.mark.unit
def test_should_skip_image_for_date_prefix():
    """Should skip images for titles with date prefixes."""
    assert should_skip_image("(15 Oct) Article Title")
    assert not should_skip_image("Article Title Without Date")


@pytest.mark.unit
def test_should_skip_image_for_mostly_numbers():
    """Should skip images for titles that are mostly numbers/symbols."""
    assert should_skip_image("123-456-789")
    assert should_skip_image("###")
    assert not should_skip_image("Windows 11 Security Update")


# ============================================================================
# Keyword Extraction Tests
# ============================================================================


@pytest.mark.unit
def test_extract_capitalized_words():
    """Should extract capitalized words from text."""
    words = extract_capitalized_words("Windows Security Update Released")
    assert "Windows" in words
    assert "Security" in words
    assert "Update" in words
    assert "Released" in words


@pytest.mark.unit
def test_extract_keywords_from_content():
    """Should extract meaningful keywords from content."""
    content = (
        "Artificial Intelligence is transforming healthcare. "
        "AI systems can analyze medical data efficiently. "
        "Healthcare providers are adopting machine learning."
    )
    keywords = extract_keywords_from_content(content, max_keywords=5)

    assert len(keywords) <= 5
    # Should have some capitalized terms
    assert any(k[0].isupper() for k in keywords)
    # Should have meaningful words
    assert any(len(k) > 5 for k in keywords)


@pytest.mark.unit
def test_extract_keywords_prioritizes_tags():
    """Keywords should come from tags first."""
    keywords = extract_keywords_from_article(
        title="Some Long Article Title Here That Is Good Length",
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
        title="Machine Learning Basics Tutorial",
        tags=None,
    )
    assert keywords is not None
    assert "Machine" in keywords
    assert "Learning" in keywords


@pytest.mark.unit
def test_extract_keywords_returns_none_for_poor_titles():
    """Should return None for poor quality titles to skip images."""
    # Short title
    assert extract_keywords_from_article(title="AI", tags=[]) is None

    # Date prefix
    assert extract_keywords_from_article(title="(15 Oct) Short", tags=[]) is None

    # Too short
    assert extract_keywords_from_article(title="Test", tags=[]) is None


@pytest.mark.unit
def test_extract_keywords_uses_content():
    """Should extract keywords from content when available."""
    keywords = extract_keywords_from_article(
        title="Article About Technology Trends",
        content=(
            "Artificial Intelligence systems are revolutionizing healthcare. "
            "Machine learning algorithms analyze patient data efficiently. "
            "Healthcare providers benefit from AI-driven insights."
        ),
        tags=[],
    )
    assert keywords is not None
    # Should prioritize content keywords over title
    assert any(
        word in keywords for word in ["Artificial", "Intelligence", "healthcare"]
    )


@pytest.mark.unit
def test_extract_keywords_uses_category():
    """Should use category when tags and content unavailable."""
    keywords = extract_keywords_from_article(
        title="Some Generic Article Title Here",
        content="",
        tags=[],
        category="Technology",
    )
    assert keywords == "Technology"


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
