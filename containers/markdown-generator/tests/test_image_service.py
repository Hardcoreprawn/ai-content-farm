"""
Tests for Stock Image Service

Functional tests for Unsplash API integration.
All tests use pure functions and mocking.
"""

from unittest.mock import AsyncMock, patch

import pytest
from services.image_service import (
    download_image_from_url,
    extract_keywords_from_article,
    fetch_image_for_article,
    parse_unsplash_photo,
    search_unsplash_image,
)


@pytest.mark.unit
def test_extract_keywords_from_tags():
    """Test keyword extraction prioritizes tags."""
    keywords = extract_keywords_from_article(
        title="Some Long Article Title Here",
        tags=["AI", "machine-learning"],
    )

    assert keywords == "AI machine-learning"


@pytest.mark.unit
def test_extract_keywords_from_title():
    """Test keyword extraction from title."""
    keywords = extract_keywords_from_article(
        title="The Future of Quantum Computing", tags=[]
    )

    assert keywords == "Future Quantum Computing"
    assert "The" not in keywords  # Stopword removed
    assert "of" not in keywords  # Stopword removed


@pytest.mark.unit
def test_extract_keywords_fallback():
    """Test keyword extraction fallback."""
    keywords = extract_keywords_from_article(title="", tags=[])

    assert keywords == "technology"


@pytest.mark.unit
def test_extract_keywords_with_none_tags():
    """Test keyword extraction with None tags."""
    keywords = extract_keywords_from_article(
        title="Machine Learning Basics",
        tags=None,
    )

    assert keywords == "Machine Learning Basics"


@pytest.mark.unit
def test_parse_unsplash_photo():
    """Test parsing Unsplash photo response."""
    photo = {
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

    result = parse_unsplash_photo(photo)

    assert result["url_raw"] == "https://images.unsplash.com/raw-url"
    assert result["url_regular"] == "https://images.unsplash.com/regular-url"
    assert result["url_small"] == "https://images.unsplash.com/small-url"
    assert result["photographer"] == "Test Photographer"
    assert result["photographer_url"] == "https://unsplash.com/@testphoto"
    assert result["description"] == "Test image description"
    assert result["color"] == "#C0FFEE"
    assert result["unsplash_url"] == "https://unsplash.com/photos/test123"


@pytest.mark.unit
def test_parse_unsplash_photo_with_alt_description():
    """Test parsing photo with alt_description fallback."""
    photo = {
        "urls": {
            "raw": "https://raw",
            "regular": "https://regular",
            "small": "https://small",
        },
        "user": {
            "name": "Jane Doe",
            "links": {"html": "https://unsplash.com/@jane"},
        },
        "description": None,
        "alt_description": "Alternative description text",
        "color": "#ABCDEF",
        "links": {"html": "https://unsplash.com/photos/abc"},
    }

    result = parse_unsplash_photo(photo)

    assert result["description"] == "Alternative description text"
    assert result["color"] == "#ABCDEF"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_unsplash_image_success():
    """Test successful image search."""
    mock_response = {
        "results": [
            {
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
        ]
    }

    with patch("services.image_service.aiohttp.ClientSession") as mock_session_class:
        # Setup mock response object
        mock_response_obj = AsyncMock()
        mock_response_obj.status = 200
        mock_response_obj.json = AsyncMock(return_value=mock_response)
        mock_response_obj.__aenter__ = AsyncMock(return_value=mock_response_obj)
        mock_response_obj.__aexit__ = AsyncMock()

        # Setup mock session
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_response_obj)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        mock_session_class.return_value = mock_session

        # Call function
        result = await search_unsplash_image(
            access_key="test_key_12345",
            query="artificial intelligence",
        )

        # Assertions
        assert result is not None
        assert result["photographer"] == "Test Photographer"
        assert result["url_regular"] == "https://images.unsplash.com/regular-url"
        assert result["color"] == "#C0FFEE"
        assert result["description"] == "Test image description"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_unsplash_image_no_results():
    """Test search with no results."""
    mock_response = {"results": []}

    with patch("services.image_service.aiohttp.ClientSession") as mock_session_class:
        mock_response_obj = AsyncMock()
        mock_response_obj.status = 200
        mock_response_obj.json = AsyncMock(return_value=mock_response)
        mock_response_obj.__aenter__ = AsyncMock(return_value=mock_response_obj)
        mock_response_obj.__aexit__ = AsyncMock()

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_response_obj)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        mock_session_class.return_value = mock_session

        result = await search_unsplash_image(
            access_key="test_key",
            query="nonexistent topic xyz123",
        )

        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_unsplash_image_api_error():
    """Test handling of API errors."""
    with patch("services.image_service.aiohttp.ClientSession") as mock_session_class:
        mock_response_obj = AsyncMock()
        mock_response_obj.status = 401
        mock_response_obj.text = AsyncMock(return_value="Unauthorized")
        mock_response_obj.__aenter__ = AsyncMock(return_value=mock_response_obj)
        mock_response_obj.__aexit__ = AsyncMock()

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_response_obj)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        mock_session_class.return_value = mock_session

        result = await search_unsplash_image(
            access_key="invalid_key",
            query="test query",
        )

        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_unsplash_image_empty_query():
    """Test handling of empty search query."""
    result = await search_unsplash_image(
        access_key="test_key",
        query="",
    )

    assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_image_for_article():
    """Test complete workflow of fetching image for article."""
    mock_response = {
        "results": [
            {
                "urls": {
                    "raw": "https://images.unsplash.com/raw",
                    "regular": "https://images.unsplash.com/regular",
                    "small": "https://images.unsplash.com/small",
                },
                "user": {
                    "name": "Photographer",
                    "links": {"html": "https://unsplash.com/@photo"},
                },
                "description": "Image description",
                "color": "#ABCDEF",
                "links": {"html": "https://unsplash.com/photos/abc"},
            }
        ]
    }

    with patch("aiohttp.ClientSession") as mock_session_class:
        mock_session = AsyncMock()
        mock_response_obj = AsyncMock()
        mock_response_obj.status = 200
        mock_response_obj.json = AsyncMock(return_value=mock_response)

        mock_session.get = AsyncMock(return_value=mock_response_obj)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        mock_session_class.return_value = mock_session

        # Test with tags
        result = await fetch_image_for_article(
            access_key="test_key",
            title="Machine Learning Trends",
            tags=["AI", "ML"],
        )

        assert result is not None
        assert result["photographer"] == "Photographer"
        assert result["url_regular"] == "https://images.unsplash.com/regular"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_image_for_article_extracts_title_keywords():
    """Test that fetch uses title when no tags provided."""
    mock_response = {
        "results": [
            {
                "urls": {
                    "raw": "https://raw",
                    "regular": "https://regular",
                    "small": "https://small",
                },
                "user": {
                    "name": "John",
                    "links": {"html": "https://unsplash.com/@john"},
                },
                "description": "Photo",
                "color": "#123456",
                "links": {"html": "https://unsplash.com/photos/x"},
            }
        ]
    }

    with patch("aiohttp.ClientSession") as mock_session_class:
        mock_session = AsyncMock()
        mock_response_obj = AsyncMock()
        mock_response_obj.status = 200
        mock_response_obj.json = AsyncMock(return_value=mock_response)

        mock_session.get = AsyncMock(return_value=mock_response_obj)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        mock_session_class.return_value = mock_session

        # No tags - should extract from title
        result = await fetch_image_for_article(
            access_key="test_key",
            title="The Future of Quantum Computing",
            tags=None,
        )

        assert result is not None
        # Verify the search was called with extracted keywords
        call_args = mock_session.get.call_args
        assert "Future Quantum Computing" in str(call_args)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_image_from_url_success():
    """Test successful image download."""
    with patch("aiohttp.ClientSession") as mock_session_class:
        mock_session = AsyncMock()
        mock_response_obj = AsyncMock()
        mock_response_obj.status = 200
        mock_response_obj.read = AsyncMock(return_value=b"fake image data")

        mock_session.get = AsyncMock(return_value=mock_response_obj)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        mock_session_class.return_value = mock_session

        with patch("builtins.open", create=True) as mock_open:
            mock_file = AsyncMock()
            mock_open.return_value.__enter__ = AsyncMock(return_value=mock_file)
            mock_open.return_value.__exit__ = AsyncMock()

            result = await download_image_from_url(
                image_url="https://images.unsplash.com/test.jpg",
                output_path="/tmp/test.jpg",
            )

            assert result is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_image_from_url_failure():
    """Test image download failure."""
    with patch("aiohttp.ClientSession") as mock_session_class:
        mock_session = AsyncMock()
        mock_response_obj = AsyncMock()
        mock_response_obj.status = 404

        mock_session.get = AsyncMock(return_value=mock_response_obj)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        mock_session_class.return_value = mock_session

        result = await download_image_from_url(
            image_url="https://images.unsplash.com/nonexistent.jpg",
            output_path="/tmp/test.jpg",
        )

        assert result is False
