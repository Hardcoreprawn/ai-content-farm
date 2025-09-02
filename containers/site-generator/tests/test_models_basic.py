"""
Basic model tests

Tests for core request/response models.
Focused on fundamental model validation.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from models import GenerationRequest, GenerationResponse
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))


class TestGenerationRequest:
    """Test GenerationRequest model validation."""

    def test_default_values(self):
        """Test default field values."""
        request = GenerationRequest()

        assert request.source == "manual"
        assert request.batch_size == 10
        assert request.theme is None
        assert request.force_regenerate is False

    def test_valid_request(self):
        """Test valid request creation."""
        request = GenerationRequest(
            source="test_source", batch_size=5, theme="minimal", force_regenerate=True
        )

        assert request.source == "test_source"
        assert request.batch_size == 5
        assert request.theme == "minimal"
        assert request.force_regenerate is True

    def test_batch_size_validation(self):
        """Test batch size constraints."""
        # Valid batch sizes
        GenerationRequest(batch_size=1)
        GenerationRequest(batch_size=50)
        GenerationRequest(batch_size=100)

        # Invalid batch sizes
        with pytest.raises(ValidationError):
            GenerationRequest(batch_size=0)

        with pytest.raises(ValidationError):
            GenerationRequest(batch_size=101)

        with pytest.raises(ValidationError):
            GenerationRequest(batch_size=-1)

    def test_serialization(self):
        """Test model serialization."""
        request = GenerationRequest(
            source="api_test", batch_size=25, theme="modern", force_regenerate=True
        )

        data = request.model_dump()
        assert data["source"] == "api_test"
        assert data["batch_size"] == 25
        assert data["theme"] == "modern"
        assert data["force_regenerate"] is True


class TestGenerationResponse:
    """Test GenerationResponse model validation."""

    def test_required_fields(self):
        """Test required field validation."""
        # Missing required fields should raise ValidationError
        with pytest.raises(ValidationError):
            GenerationResponse()

        # Valid creation with all required fields
        response = GenerationResponse(
            generator_id="test_123",
            operation_type="markdown_generation",
            files_generated=5,
            processing_time=2.5,
            output_location="blob://test",
            generated_files=["file1.md", "file2.md"],
        )

        assert response.generator_id == "test_123"
        assert response.operation_type == "markdown_generation"
        assert response.files_generated == 5
        assert response.processing_time == 2.5
        assert response.output_location == "blob://test"
        assert len(response.generated_files) == 2
        assert response.errors == []

    def test_optional_fields(self):
        """Test optional field handling."""
        response = GenerationResponse(
            generator_id="test_456",
            operation_type="site_generation",
            files_generated=0,
            pages_generated=10,
            processing_time=5.2,
            output_location="blob://static",
            generated_files=[],
            errors=["warning: missing theme"],
        )

        assert response.pages_generated == 10
        assert response.errors == ["warning: missing theme"]

    def test_default_values(self):
        """Test default values for optional fields."""
        response = GenerationResponse(
            generator_id="test_789",
            operation_type="test",
            files_generated=1,
            processing_time=0.5,
            output_location="test://location",
            generated_files=["test.md"],
        )

        assert response.pages_generated is None
        assert response.errors == []
