"""
Property-Based Testing for Site Generator

Uses Hypothesis library to test functions with generated inputs,
discovering edge cases and validating properties that should always hold.
"""

import pytest
from content_utility_functions import create_markdown_content
from hypothesis import given, settings
from hypothesis import strategies as st
from models import GenerationRequest, GenerationResponse
from pydantic import ValidationError


class TestPropertyBasedEdgeCases:
    """Property-based testing for edge cases using Hypothesis."""

    @given(st.text(min_size=1, max_size=100))
    @settings(max_examples=20, deadline=1000)  # Limit for fast execution
    def test_create_markdown_content_with_various_titles(self, title):
        """Test markdown content creation with various title inputs."""
        # Assume any non-empty string should produce valid markdown
        article_data = {"title": title, "content": "Test content"}

        result = create_markdown_content(article_data)

        # Properties that should always hold
        assert isinstance(result, str)
        assert len(result) > 0
        # Should contain title
        assert f'title: "{title}"' in result or "title:" in result
        assert "Test content" in result  # Should contain content
        assert "---" in result  # Should contain YAML frontmatter markers

    @given(
        st.lists(
            st.dictionaries(
                keys=st.sampled_from(["title", "content", "topic_id"]),
                values=st.text(min_size=1, max_size=50),
                min_size=1,
            ),
            min_size=0,
            max_size=10,
        )
    )
    @settings(max_examples=15, deadline=1000)
    def test_generation_response_with_various_file_lists(self, file_data_list):
        """Test GenerationResponse creation with various file data inputs."""
        try:
            # Create response with generated file list
            response = GenerationResponse(
                generator_id="property-test-001",
                operation_type="property_testing",
                files_generated=len(file_data_list),
                processing_time=1.0,
                output_location="test-output",
                generated_files=[f"test_{i}.md" for i in range(len(file_data_list))],
            )

            # Properties that should always hold
            assert response.files_generated == len(file_data_list)
            assert len(response.generated_files) == len(file_data_list)
            assert response.generator_id == "property-test-001"
            assert response.processing_time > 0

        except ValidationError:
            # Some combinations might be invalid - that's okay for property testing
            pass

    @given(
        st.integers(min_value=1, max_value=100),
        st.booleans(),
        st.text(min_size=1, max_size=20),
    )
    @settings(max_examples=10, deadline=1000)
    def test_generation_request_property_validation(
        self, batch_size, force_regen, source
    ):
        """Test GenerationRequest with various property combinations."""
        try:
            request = GenerationRequest(
                source=source, batch_size=batch_size, force_regenerate=force_regen
            )

            # Properties that should always hold for valid requests
            assert request.batch_size >= 1
            assert request.batch_size <= 100  # Based on model constraints
            assert isinstance(request.force_regenerate, bool)
            assert len(request.source) > 0

        except ValidationError:
            # Some combinations might be invalid due to Pydantic validation
            pass

    @given(
        st.dictionaries(
            keys=st.sampled_from(
                ["title", "content", "topic_id", "metadata", "timestamp"]
            ),
            values=st.one_of(
                st.text(min_size=0, max_size=200),
                st.dictionaries(
                    keys=st.text(min_size=1, max_size=10),
                    values=st.text(min_size=1, max_size=20),
                    max_size=3,
                ),
            ),
            min_size=1,
            max_size=5,
        )
    )
    @settings(max_examples=25, deadline=1500)
    def test_markdown_content_with_arbitrary_article_data(self, article_data):
        """Test markdown creation with various article data structures."""
        try:
            result = create_markdown_content(article_data)

            # Properties that should always hold for valid inputs
            assert isinstance(result, str)
            assert len(result) > 0
            assert "---" in result  # YAML frontmatter

            # If title exists, it should be in the output
            if "title" in article_data and article_data["title"]:
                assert "title:" in result

            # If content exists, it should be in the output
            if "content" in article_data and article_data["content"]:
                assert str(article_data["content"]) in result

        except (TypeError, ValueError, AttributeError):
            # Some data structures might be invalid - expected for property testing
            pass

    @given(
        st.text(min_size=0, max_size=50),
        st.one_of(st.none(), st.text(min_size=0, max_size=20)),
    )
    @settings(max_examples=15, deadline=1000)
    def test_generation_request_with_optional_theme(self, source, theme):
        """Test GenerationRequest creation with various theme combinations."""
        try:
            request = GenerationRequest(
                source=source if source else "default",  # Ensure non-empty source
                theme=theme,
            )

            # Properties that should hold
            assert len(request.source) > 0
            assert request.theme == theme  # Should preserve None or string value
            assert isinstance(request.batch_size, int)
            assert isinstance(request.force_regenerate, bool)

        except ValidationError:
            # Invalid combinations are expected in property testing
            pass

    @given(
        st.floats(
            min_value=0.0, max_value=1000.0, allow_nan=False, allow_infinity=False
        ),
        st.lists(st.text(min_size=1, max_size=30), min_size=0, max_size=20),
    )
    @settings(max_examples=10, deadline=1000)
    def test_generation_response_timing_and_files(self, processing_time, file_names):
        """Test GenerationResponse with various timing and file combinations."""
        try:
            response = GenerationResponse(
                generator_id="timing-test",
                operation_type="timing_validation",
                files_generated=len(file_names),
                processing_time=processing_time,
                output_location="timing-output",
                generated_files=file_names,
            )

            # Properties that should hold
            assert response.processing_time >= 0.0
            assert response.files_generated >= 0
            assert len(response.generated_files) == response.files_generated
            assert response.generator_id == "timing-test"

        except ValidationError:
            # Some combinations might be invalid
            pass


class TestPropertyBasedStringHandling:
    """Property-based tests focused on string handling edge cases."""

    @given(
        st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Pc", "Pd"))
        )
    )
    @settings(max_examples=20, deadline=1000)
    def test_markdown_content_with_safe_characters(self, safe_text):
        """Test markdown creation with various safe character combinations."""
        if not safe_text.strip():  # Skip empty/whitespace-only strings
            return

        article_data = {"title": safe_text[:50], "content": safe_text}  # Limit length

        result = create_markdown_content(article_data)

        # Should handle safe characters without issues
        assert isinstance(result, str)
        assert len(result) > 0
        assert "---" in result

    @given(st.text(min_size=1, max_size=20).filter(lambda x: x.isprintable()))
    @settings(max_examples=15, deadline=1000)
    def test_generator_id_format_validation(self, generator_id_base):
        """Test various generator ID formats."""
        try:
            response = GenerationResponse(
                generator_id=generator_id_base,
                operation_type="id_validation",
                files_generated=1,
                processing_time=1.0,
                output_location="test-location",
                generated_files=["test.md"],
            )

            # Generator ID should be preserved as-is
            assert response.generator_id == generator_id_base
            assert len(response.generator_id) > 0

        except ValidationError:
            # Some formats might be invalid
            pass
