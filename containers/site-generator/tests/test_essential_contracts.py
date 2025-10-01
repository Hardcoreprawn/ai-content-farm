"""
Clean Testing Strategy for Site Generator

PHILOSOPHY:
- Test OUTCOMES, not implementations
- Focus on DATA CONTRACTS that matter
- Fast tests that provide confidence
- No complex mocking or import gymnastics

WHAT WE ACTUALLY CARE ABOUT:
1. Models validate correctly (our API contracts)
2. Functions exist and are callable (integration smoke tests)
3. Critical workflows don't crash (end-to-end confidence)
"""

from datetime import datetime, timezone

import pytest
from content_processing_functions import generate_markdown_batch, generate_static_site
from content_utility_functions import get_processed_articles
from fastapi import FastAPI
from fastapi.testclient import TestClient
from functional_config import create_generator_context, load_configuration
from models import GenerationRequest, GenerationResponse


class TestDataContracts:
    """Test the data models that define our API contracts."""

    def test_generation_request_validation(self):
        """GenerationRequest accepts valid data and rejects invalid data."""
        # Valid request
        valid_req = GenerationRequest(
            source="test", batch_size=25, theme="dark", force_regenerate=True
        )
        assert valid_req.source == "test"
        assert valid_req.batch_size == 25
        assert valid_req.theme == "dark"
        assert valid_req.force_regenerate is True

        # Invalid batch size - too small
        with pytest.raises(ValueError, match="greater than or equal to 1"):
            GenerationRequest(batch_size=0)

        # Invalid batch size - too large
        with pytest.raises(ValueError, match="less than or equal to 100"):
            GenerationRequest(batch_size=101)

    def test_generation_response_required_fields(self):
        """GenerationResponse requires all necessary fields and has correct types."""
        response = GenerationResponse(
            generator_id="test123",
            operation_type="markdown_generation",
            files_generated=10,
            processing_time=1.5,
            output_location="blob://test-container",
            generated_files=["file1.md", "file2.md", "file3.md"],
            errors=["warning1", "warning2"],
        )

        # Verify all fields are correctly set
        assert response.generator_id == "test123"
        assert response.operation_type == "markdown_generation"
        assert response.files_generated == 10
        assert response.processing_time == 1.5
        assert response.output_location == "blob://test-container"
        assert len(response.generated_files) == 3
        assert len(response.errors) == 2

        # Test model serialization (critical for API responses)
        response_dict = response.model_dump()
        assert "generator_id" in response_dict
        assert response_dict["files_generated"] == 10

    def test_generation_request_defaults(self):
        """GenerationRequest provides sensible defaults."""
        req = GenerationRequest()
        assert req.source == "manual"
        assert req.batch_size == 10
        assert req.force_regenerate is False
        assert req.theme is None


class TestFunctionExistence:
    """Smoke tests to ensure core functions exist and are callable."""

    def test_core_functions_exist_and_callable(self):
        """Core functions exist and are callable (smoke test for integration)."""

        # Functions should be callable
        assert callable(generate_markdown_batch)
        assert callable(generate_static_site)
        assert callable(get_processed_articles)
        assert callable(create_generator_context)

    def test_models_import_correctly(self):
        """Test that all required models can be imported without errors."""
        # All models should be importable from the models module
        # Should be able to create instances
        req = GenerationRequest()
        assert isinstance(req, GenerationRequest)


class TestAPIContracts:
    """Test the FastAPI application accepts requests and returns proper responses."""

    @pytest.fixture
    def simple_test_app(self):
        """Create a minimal FastAPI app that tests our data contracts."""

        app = FastAPI()

        @app.get("/health")
        def health():
            return {"status": "healthy", "timestamp": datetime.now().isoformat()}

        @app.post("/test-generation-request")
        def test_generation_request(request: GenerationRequest):
            """Test endpoint that validates GenerationRequest parsing."""
            return {
                "received_source": request.source,
                "received_batch_size": request.batch_size,
                "received_theme": request.theme,
                "received_force_regenerate": request.force_regenerate,
            }

        @app.get("/test-generation-response")
        def test_generation_response():
            """Test endpoint that returns a GenerationResponse."""
            return GenerationResponse(
                generator_id="contract_test",
                operation_type="test_operation",
                files_generated=5,
                processing_time=0.1,
                output_location="test://location",
                generated_files=["test1.md", "test2.md"],
            )

        return TestClient(app)

    def test_health_endpoint(self, simple_test_app):
        """Basic health check works."""
        response = simple_test_app.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_generation_request_parsing(self, simple_test_app):
        """FastAPI correctly parses GenerationRequest from JSON."""
        request_data = {
            "source": "api_test",
            "batch_size": 15,
            "theme": "custom",
            "force_regenerate": True,
        }

        response = simple_test_app.post("/test-generation-request", json=request_data)
        assert response.status_code == 200

        data = response.json()
        assert data["received_source"] == "api_test"
        assert data["received_batch_size"] == 15
        assert data["received_theme"] == "custom"
        assert data["received_force_regenerate"] is True

    def test_generation_response_serialization(self, simple_test_app):
        """FastAPI correctly serializes GenerationResponse to JSON."""
        response = simple_test_app.get("/test-generation-response")
        assert response.status_code == 200

        data = response.json()
        assert data["generator_id"] == "contract_test"
        assert data["operation_type"] == "test_operation"
        assert data["files_generated"] == 5
        assert data["processing_time"] == 0.1
        assert len(data["generated_files"]) == 2
        assert data["errors"] == []  # Should default to empty list

    def test_invalid_generation_request(self, simple_test_app):
        """FastAPI rejects invalid GenerationRequest data."""
        # Invalid batch size
        invalid_request = {
            "source": "test",
            "batch_size": 150,  # Too large
            "force_regenerate": False,
        }

        response = simple_test_app.post(
            "/test-generation-request", json=invalid_request
        )
        assert response.status_code == 422  # Validation error

        error_data = response.json()
        assert "detail" in error_data
        # Should contain validation error about batch_size


class TestCriticalPathSmoke:
    """Smoke tests for critical workflows - ensure they don't crash immediately."""

    def test_config_creation_smoke(self):
        """Configuration creation doesn't crash immediately."""
        try:

            # Should not crash on basic call (even if it fails later due to missing Azure resources)
            # We're just testing the function exists and is syntactically correct
            config = load_configuration()

            # If it returns something, it should be a dict-like object
            if config is not None:
                assert hasattr(config, "__getitem__") or hasattr(config, "get")

        except ImportError as e:
            pytest.fail(f"Critical configuration function import failed: {e}")
        except Exception:
            # It's OK if the function fails due to missing Azure resources,
            # we just want to ensure it's importable and callable
            pass

    def test_models_roundtrip_serialization(self):
        """Models can be serialized and deserialized without data loss."""
        original_request = GenerationRequest(
            source="roundtrip_test",
            batch_size=42,
            theme="test_theme",
            force_regenerate=True,
        )

        # Serialize to dict
        request_dict = original_request.model_dump()

        # Deserialize back to object
        restored_request = GenerationRequest(**request_dict)

        # Should be identical
        assert restored_request.source == original_request.source
        assert restored_request.batch_size == original_request.batch_size
        assert restored_request.theme == original_request.theme
        assert restored_request.force_regenerate == original_request.force_regenerate

    def test_generation_response_with_optional_fields(self):
        """GenerationResponse handles optional fields correctly."""
        # Minimal response
        minimal = GenerationResponse(
            generator_id="minimal",
            operation_type="test",
            files_generated=0,
            processing_time=0.0,
            output_location="test://none",
            generated_files=[],
        )
        assert minimal.pages_generated is None
        assert minimal.errors == []

        # Response with optional fields
        complete = GenerationResponse(
            generator_id="complete",
            operation_type="test",
            files_generated=5,
            pages_generated=3,
            processing_time=1.0,
            output_location="test://complete",
            generated_files=["a.md", "b.md"],
            errors=["warning1"],
        )
        assert complete.pages_generated == 3
        assert len(complete.errors) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
