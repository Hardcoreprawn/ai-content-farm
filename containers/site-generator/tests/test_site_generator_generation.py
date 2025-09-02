"""
Tests for SiteGenerator generation methods.

Tests markdown and static site generation functionality.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from models import GenerationResponse
from site_generator import SiteGenerator


class TestMarkdownGeneration:
    """Test markdown generation functionality."""

    @pytest.mark.asyncio
    async def test_generate_markdown_success(
        self, mock_generator, sample_generation_response
    ):
        """Test successful markdown generation."""
        # Mock the markdown service response
        mock_generator.markdown_service.generate_batch.return_value = (
            sample_generation_response
        )

        result = await mock_generator.generate_markdown()

        assert isinstance(result, GenerationResponse)
        assert result.files_generated == 5
        assert result.generator_id == "test_gen_123"
        assert result.operation_type == "markdown_generation"

    @pytest.mark.asyncio
    async def test_generate_markdown_failure(self, mock_generator):
        """Test markdown generation failure."""
        # Mock service to return failure
        error_response = GenerationResponse(
            generator_id="test_gen_error",
            operation_type="markdown_generation",
            files_generated=2,
            processing_time=1.2,
            output_location="blob://markdown-content",
            generated_files=["article1.md", "article2.md"],
            errors=["Error processing article 3", "Error processing article 4"],
        )
        mock_generator.markdown_service.generate_batch.return_value = error_response

        result = await mock_generator.generate_markdown()

        assert isinstance(result, GenerationResponse)
        assert result.files_generated == 2
        assert len(result.errors) == 2

    @pytest.mark.asyncio
    async def test_generate_markdown_with_custom_container(self, mock_generator):
        """Test markdown generation with custom container."""
        custom_response = GenerationResponse(
            generator_id="test_gen_custom",
            operation_type="markdown_generation",
            files_generated=3,
            processing_time=1.8,
            output_location="blob://custom-container",
            generated_files=["custom1.md", "custom2.md", "custom3.md"],
            errors=[],
        )
        mock_generator.markdown_service.generate_batch.return_value = custom_response

        result = await mock_generator.generate_markdown(source="custom", batch_size=3)

        assert result.files_generated == 3
        assert result.output_location == "blob://custom-container"

    @pytest.mark.asyncio
    async def test_generate_markdown_status_tracking(
        self, mock_generator, sample_generation_response
    ):
        """Test that markdown generation updates status."""
        mock_generator.markdown_service.generate_batch.return_value = (
            sample_generation_response
        )

        # Check initial status
        assert mock_generator.current_status == "idle"

        # Call generation and check status updates
        await mock_generator.generate_markdown()

        # Should return to idle after successful generation
        assert mock_generator.current_status == "idle"
        assert mock_generator.last_generation is not None

    @pytest.mark.asyncio
    async def test_generate_markdown_exception_handling(self, mock_generator, caplog):
        """Test markdown generation handles exceptions."""
        mock_generator.markdown_service.generate_batch.side_effect = Exception(
            "Service error"
        )

        with pytest.raises(Exception, match="Service error"):
            await mock_generator.generate_markdown()

        # Check error state was set with secure message
        assert mock_generator.current_status == "error"
        assert mock_generator.error_message == "Markdown generation failed"

    @pytest.mark.asyncio
    async def test_generate_markdown_partial_success(self, mock_generator):
        """Test markdown generation with partial success."""
        partial_response = GenerationResponse(
            generator_id="test_gen_partial",
            operation_type="markdown_generation",
            files_generated=8,
            processing_time=3.2,
            output_location="blob://markdown-content",
            generated_files=[
                "art1.md",
                "art2.md",
                "art3.md",
                "art4.md",
                "art5.md",
                "art6.md",
                "art7.md",
                "art8.md",
            ],
            errors=[
                "Warning: Could not process metadata for article X",
                "Warning: Missing field in article Y",
            ],
        )
        mock_generator.markdown_service.generate_batch.return_value = partial_response

        result = await mock_generator.generate_markdown()

        assert result.files_generated == 8
        assert len(result.errors) == 2
        assert result.processing_time == 3.2


class TestStaticSiteGeneration:
    """Test static site generation functionality."""

    @pytest.mark.asyncio
    async def test_generate_static_site_success(
        self, mock_generator, sample_site_response
    ):
        """Test successful static site generation."""
        # Mock the site service response
        mock_generator.site_service.generate_site.return_value = sample_site_response

        result = await mock_generator.generate_static_site()

        assert isinstance(result, GenerationResponse)
        assert result.files_generated == 15
        assert result.pages_generated == 8
        assert result.operation_type == "site_generation"

    @pytest.mark.asyncio
    async def test_generate_static_site_with_theme(self, mock_generator):
        """Test static site generation with custom theme."""
        theme_response = GenerationResponse(
            generator_id="test_site_theme",
            operation_type="site_generation",
            files_generated=12,
            pages_generated=6,
            processing_time=6.2,
            output_location="blob://static-sites",
            generated_files=["index.html", "archive.html", "modern.css"],
            errors=[],
        )
        mock_generator.site_service.generate_site.return_value = theme_response

        result = await mock_generator.generate_static_site(theme="modern")

        assert result.files_generated == 12
        assert result.pages_generated == 6
        assert mock_generator.current_theme == "modern"

    @pytest.mark.asyncio
    async def test_generate_static_site_failure(self, mock_generator):
        """Test static site generation failure."""
        error_response = GenerationResponse(
            generator_id="test_site_error",
            operation_type="site_generation",
            files_generated=5,
            processing_time=3.1,
            output_location="blob://static-sites",
            generated_files=["partial.html"],
            errors=["Template error", "Asset compilation failed"],
        )
        mock_generator.site_service.generate_site.return_value = error_response

        result = await mock_generator.generate_static_site()

        assert result.files_generated == 5
        assert len(result.errors) == 2

    @pytest.mark.asyncio
    async def test_generate_static_site_status_tracking(
        self, mock_generator, sample_site_response
    ):
        """Test that site generation updates status."""
        mock_generator.site_service.generate_site.return_value = sample_site_response

        # Check initial status
        assert mock_generator.current_status == "idle"

        await mock_generator.generate_static_site()

        # Should return to idle after successful generation
        assert mock_generator.current_status == "idle"
        assert mock_generator.last_generation is not None

    @pytest.mark.asyncio
    async def test_generate_static_site_exception_handling(
        self, mock_generator, caplog
    ):
        """Test static site generation handles exceptions."""
        mock_generator.site_service.generate_site.side_effect = Exception(
            "Site service error"
        )

        with pytest.raises(Exception, match="Site service error"):
            await mock_generator.generate_static_site()

        # Check error state was set with secure message
        assert mock_generator.current_status == "error"
        assert mock_generator.error_message == "Static site generation failed"

    @pytest.mark.asyncio
    async def test_get_preview_url(self, mock_generator):
        """Test getting preview URL after site generation."""
        mock_generator.site_service.get_preview_url.return_value = (
            "https://example.com/preview"
        )

        url = await mock_generator.get_preview_url("test-site-123")

        assert url == "https://example.com/preview"
        mock_generator.site_service.get_preview_url.assert_called_once_with(
            "test-site-123"
        )

    @pytest.mark.asyncio
    async def test_get_preview_url_not_available(self, mock_generator):
        """Test getting preview URL when not available."""
        mock_generator.site_service.get_preview_url.return_value = None

        url = await mock_generator.get_preview_url("non-existent-site")

        assert url is None
