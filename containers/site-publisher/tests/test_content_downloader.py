"""
Unit tests for content_downloader.py

Tests download and organization of markdown content.
"""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from content_downloader import (
    download_markdown_files,
    organize_content_for_hugo,
    validate_markdown_frontmatter,
)


@pytest.mark.asyncio
async def test_download_markdown_files_success(
    mock_blob_client, temp_dir, sample_markdown_content
):
    """Test successful download of markdown files."""
    # Setup mock blob
    mock_blob = Mock()
    mock_blob.name = "test-article.md"
    mock_blob.size = len(sample_markdown_content)

    # Setup mock container client with async iterator for list_blobs
    async def async_blob_iterator():
        """Async generator that yields mock blobs."""
        yield mock_blob

    mock_container = AsyncMock()
    mock_container.list_blobs = Mock(return_value=async_blob_iterator())

    # Setup mock blob download
    mock_blob_client_obj = AsyncMock()
    mock_download_stream = AsyncMock()
    mock_download_stream.readall = AsyncMock(
        return_value=sample_markdown_content.encode()
    )
    mock_blob_client_obj.download_blob = AsyncMock(return_value=mock_download_stream)

    mock_container.get_blob_client = Mock(return_value=mock_blob_client_obj)
    mock_blob_client.get_container_client = Mock(return_value=mock_container)

    # Execute
    result = await download_markdown_files(
        blob_client=mock_blob_client,
        container_name="test-container",
        output_dir=temp_dir,
    )

    # Assert
    assert result.files_downloaded == 1
    assert result.duration_seconds > 0
    assert len(result.errors) == 0
    assert (temp_dir / "test-article.md").exists()


@pytest.mark.asyncio
async def test_download_markdown_files_empty_container(mock_blob_client, temp_dir):
    """Test download from empty container."""
    # Setup mock empty container
    mock_container = AsyncMock()

    async def empty_iterator():
        for _ in []:
            yield

    mock_container.list_blobs = Mock(return_value=empty_iterator())
    mock_blob_client.get_container_client = Mock(return_value=mock_container)

    # Execute
    result = await download_markdown_files(
        blob_client=mock_blob_client,
        container_name="test-container",
        output_dir=temp_dir,
    )

    # Assert
    assert result.files_downloaded == 0
    assert result.duration_seconds >= 0
    assert len(result.errors) == 0


@pytest.mark.asyncio
async def test_download_markdown_files_exceeds_file_limit(mock_blob_client, temp_dir):
    """Test DOS prevention when too many files in container."""
    # Setup mock with too many blobs
    mock_blobs = []
    for i in range(15):
        mock_blob = Mock()
        mock_blob.name = f"file{i}.md"
        mock_blob.size = 100
        mock_blobs.append(mock_blob)

    mock_container = Mock()

    async def blob_iterator():
        for blob in mock_blobs:
            yield blob

    # list_blobs() is called and returns an async iterator
    mock_container.list_blobs = Mock(return_value=blob_iterator())
    mock_blob_client.get_container_client.return_value = mock_container

    # Execute with low max_files
    result = await download_markdown_files(
        blob_client=mock_blob_client,
        container_name="test-container",
        output_dir=temp_dir,
        max_files=10,
    )

    # Assert
    assert result.files_downloaded == 0
    assert any("Too many files" in error for error in result.errors)


@pytest.mark.asyncio
async def test_download_markdown_files_file_too_large(mock_blob_client, temp_dir):
    """Test DOS prevention when file exceeds size limit."""
    # Setup mock blob that's too large
    mock_blob = Mock()
    mock_blob.name = "huge-file.md"
    mock_blob.size = 20_000_000  # 20MB

    mock_container = AsyncMock()

    async def blob_iterator():
        yield mock_blob

    mock_container.list_blobs = Mock(return_value=blob_iterator())
    mock_blob_client.get_container_client = Mock(return_value=mock_container)

    # Execute
    result = await download_markdown_files(
        blob_client=mock_blob_client,
        container_name="test-container",
        output_dir=temp_dir,
        max_file_size=10_485_760,  # 10MB
    )

    # Assert
    assert result.files_downloaded == 0
    assert any("File too large" in error for error in result.errors)


@pytest.mark.asyncio
async def test_download_markdown_files_invalid_blob_name(mock_blob_client, temp_dir):
    """Test that invalid blob names are rejected."""
    # Setup mock blob with path traversal attempt
    mock_blob = Mock()
    mock_blob.name = "../../../etc/passwd.md"
    mock_blob.size = 100

    mock_container = AsyncMock()

    async def blob_iterator():
        yield mock_blob

    mock_container.list_blobs = Mock(return_value=blob_iterator())
    mock_blob_client.get_container_client = Mock(return_value=mock_container)

    # Execute
    result = await download_markdown_files(
        blob_client=mock_blob_client,
        container_name="test-container",
        output_dir=temp_dir,
    )

    # Assert
    assert result.files_downloaded == 0
    assert any("Path traversal" in error for error in result.errors)


@pytest.mark.asyncio
async def test_organize_content_for_hugo_success(temp_dir, sample_markdown_content):
    """Test successful organization of content for Hugo."""
    # Setup source content
    content_dir = temp_dir / "content"
    content_dir.mkdir()
    (content_dir / "article.md").write_text(sample_markdown_content)

    # Setup Hugo content directory
    hugo_content_dir = temp_dir / "hugo" / "content"

    # Execute
    result = await organize_content_for_hugo(
        content_dir=content_dir,
        hugo_content_dir=hugo_content_dir,
    )

    # Assert
    assert result.is_valid
    assert len(result.errors) == 0
    assert (hugo_content_dir / "article.md").exists()
    assert (hugo_content_dir / "article.md").read_text() == sample_markdown_content


@pytest.mark.asyncio
async def test_organize_content_for_hugo_nested_files(
    temp_dir, sample_markdown_content
):
    """Test organization of nested directory structures."""
    # Setup nested content
    content_dir = temp_dir / "content"
    nested_dir = content_dir / "blog" / "2025"
    nested_dir.mkdir(parents=True)
    (nested_dir / "post.md").write_text(sample_markdown_content)

    # Setup Hugo content directory
    hugo_content_dir = temp_dir / "hugo" / "content"

    # Execute
    result = await organize_content_for_hugo(
        content_dir=content_dir,
        hugo_content_dir=hugo_content_dir,
    )

    # Assert
    assert result.is_valid
    assert (hugo_content_dir / "blog" / "2025" / "post.md").exists()


@pytest.mark.asyncio
async def test_organize_content_for_hugo_missing_source(temp_dir):
    """Test handling of missing source directory."""
    content_dir = temp_dir / "nonexistent"
    hugo_content_dir = temp_dir / "hugo" / "content"

    # Execute
    result = await organize_content_for_hugo(
        content_dir=content_dir,
        hugo_content_dir=hugo_content_dir,
    )

    # Assert
    assert not result.is_valid
    assert any("not found" in error for error in result.errors)


@pytest.mark.asyncio
async def test_organize_content_for_hugo_empty_directory(temp_dir):
    """Test organization with no markdown files."""
    # Setup empty content directory
    content_dir = temp_dir / "content"
    content_dir.mkdir()

    # Setup Hugo content directory
    hugo_content_dir = temp_dir / "hugo" / "content"

    # Execute
    result = await organize_content_for_hugo(
        content_dir=content_dir,
        hugo_content_dir=hugo_content_dir,
    )

    # Assert - empty is valid, just no files organized
    assert result.is_valid
    assert len(result.errors) == 0


def test_validate_markdown_frontmatter_valid():
    """Test validation of valid YAML frontmatter."""
    import tempfile

    # Create temp file with valid frontmatter
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(
            """---
title: "Test Article"
url: "https://example.com/test"
source: "reddit"
---

# Test Article

Content here.
"""
        )
        temp_path = Path(f.name)

    try:
        is_valid, errors = validate_markdown_frontmatter(temp_path)
        assert is_valid
        assert len(errors) == 0
    finally:
        temp_path.unlink()


def test_validate_markdown_frontmatter_missing_delimiter():
    """Test validation fails for missing frontmatter delimiter."""
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(
            """# Test Article

Content without frontmatter.
"""
        )
        temp_path = Path(f.name)

    try:
        is_valid, errors = validate_markdown_frontmatter(temp_path)
        assert not is_valid
        assert any("opening delimiter" in error for error in errors)
    finally:
        temp_path.unlink()


def test_validate_markdown_frontmatter_invalid_yaml():
    """Test validation fails for invalid YAML syntax."""
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        # Malformed YAML - missing closing quote
        f.write(
            """---
title: "Test Article
url: "https://example.com/test"
source: "reddit"
---

# Test Article
"""
        )
        temp_path = Path(f.name)

    try:
        is_valid, errors = validate_markdown_frontmatter(temp_path)
        assert not is_valid
        assert any(
            "YAML syntax" in error or "yaml" in error.lower() for error in errors
        )
    finally:
        temp_path.unlink()


def test_validate_markdown_frontmatter_missing_required_fields():
    """Test validation fails for missing required fields."""
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(
            """---
title: "Test Article"
---

# Test Article
"""
        )
        temp_path = Path(f.name)

    try:
        is_valid, errors = validate_markdown_frontmatter(temp_path)
        assert not is_valid
        assert any("url" in error.lower() for error in errors)
        assert any("source" in error.lower() for error in errors)
    finally:
        temp_path.unlink()


@pytest.mark.asyncio
async def test_organize_content_quarantines_malformed_files(temp_dir):
    """Test that malformed files are quarantined instead of causing build failure."""
    # Setup content directory with good and bad files
    content_dir = temp_dir / "content"
    content_dir.mkdir()

    # Good file with valid frontmatter
    good_file = content_dir / "good-article.md"
    good_file.write_text(
        """---
title: "Good Article"
url: "https://example.com/good"
source: "reddit"
---

# Good Article

Content here.
"""
    )

    # Bad file with invalid YAML (unquoted URL)
    bad_file = content_dir / "bad-article.md"
    bad_file.write_text(
        """---
title: "Bad Article"
url: https://example.com/bad
source: reddit
---

# Bad Article
"""
    )

    # Setup Hugo content directory
    hugo_content_dir = temp_dir / "hugo" / "content"

    # Execute
    result = await organize_content_for_hugo(
        content_dir=content_dir,
        hugo_content_dir=hugo_content_dir,
    )

    # Assert - should succeed with 1 valid file
    assert result.is_valid
    assert (hugo_content_dir / "good-article.md").exists()
    assert not (hugo_content_dir / "bad-article.md").exists()

    # Check quarantine directory
    quarantine_dir = temp_dir / "quarantined"
    assert quarantine_dir.exists()
    assert (quarantine_dir / "bad-article.md").exists()

    # Check errors mention quarantine
    assert any("quarantined" in error.lower() for error in result.errors)
