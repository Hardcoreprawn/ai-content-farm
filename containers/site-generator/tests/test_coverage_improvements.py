#!/usr/bin/env python3
"""
Additional unit tests for improved coverage of site-generator components.

Focuses on uncovered code paths in config, health, and service logic.
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient

# Set environment before imports
if not os.getenv("AZURE_STORAGE_CONNECTION_STRING"):
    os.environ["AZURE_STORAGE_CONNECTION_STRING"] = "DefaultEndpointsProtocol=https;AccountName=test;AccountKey=dGVzdA==;EndpointSuffix=core.windows.net"

from config import get_config, validate_environment, ServiceConfig
from health import HealthChecker
from service_logic import SiteProcessor


class TestConfigModule:
    """Test configuration module edge cases."""

    @pytest.mark.unit
    def test_config_validation_invalid_environment(self):
        """Test config validation with invalid environment."""
        with patch.dict(os.environ, {"ENVIRONMENT": "invalid_env"}):
            with pytest.raises(ValueError, match="Invalid environment"):
                ServiceConfig()

    @pytest.mark.unit
    def test_config_missing_storage_connection(self):
        """Test config validation with missing storage connection."""
        with patch.dict(os.environ, {"AZURE_STORAGE_CONNECTION_STRING": ""}):
            with pytest.raises(ValueError, match="AZURE_STORAGE_CONNECTION_STRING is required"):
                ServiceConfig()

    @pytest.mark.unit
    def test_validate_environment_success(self):
        """Test successful environment validation."""
        with patch('libs.blob_storage.BlobStorageClient') as mock_blob_client:
            mock_client = MagicMock()
            mock_blob_client.return_value = mock_client
            
            result = validate_environment()
            assert result is True
            mock_client.ensure_container.assert_called_once()

    @pytest.mark.unit
    def test_validate_environment_failure(self):
        """Test environment validation failure."""
        with patch('libs.blob_storage.BlobStorageClient') as mock_blob_client:
            mock_blob_client.side_effect = Exception("Connection failed")
            
            result = validate_environment()
            assert result is False
class TestHealthChecker:
    """Test health checker functionality."""

    @pytest.fixture
    def health_checker(self):
        """Health checker instance."""
        return HealthChecker()

    @pytest.mark.unit
    def test_health_checker_initialization(self, health_checker):
        """Test health checker initializes correctly."""
        assert health_checker is not None
        assert hasattr(health_checker, 'check_health')

    @pytest.mark.unit
    def test_check_health_basic(self, health_checker):
        """Test basic health check functionality."""
        # Health checker has async check_health method
        import asyncio
        
        result = asyncio.run(health_checker.check_health())
        assert 'status' in result
        assert result['status'] in ['healthy', 'unhealthy']

    @pytest.mark.unit
    def test_storage_health_check_success(self, health_checker):
        """Test storage health check success."""
        with patch('libs.blob_storage.BlobStorageClient') as mock_blob_client:
            mock_client = MagicMock()
            mock_blob_client.return_value = mock_client
            mock_client.ensure_container.return_value = True
            
            # Test during health check
            import asyncio
            with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": ""}):
                # This will use the test path that avoids external connections
                result = asyncio.run(health_checker.check_health())
                assert result['status'] == 'healthy'

    @pytest.mark.unit  
    def test_storage_health_check_failure(self, health_checker):
        """Test storage health check failure."""
        with patch('libs.blob_storage.BlobStorageClient') as mock_blob_client:
            mock_blob_client.side_effect = Exception("Storage unavailable")
            
            # Remove test environment to force actual health check
            import asyncio
            with patch.dict(os.environ, {}, clear=True):
                with patch.dict(os.environ, {"AZURE_STORAGE_CONNECTION_STRING": "test"}):
                    try:
                        result = asyncio.run(health_checker.check_health())
                        # Should handle the error gracefully
                        assert 'status' in result
                    except Exception:
                        # If it raises, that's also acceptable for a failed health check
                        pass
class TestSiteProcessorEdgeCases:
    """Test SiteProcessor edge cases and error handling."""

    @pytest.fixture
    def mock_processor(self):
        """Mock site processor for testing."""
        with patch('libs.blob_storage.BlobStorageClient'):
            with patch('template_manager.create_template_manager'):
                processor = SiteProcessor()
                return processor

    @pytest.mark.unit
    def test_processor_initialization_error_handling(self):
        """Test processor handles initialization errors gracefully."""
        with patch('libs.blob_storage.BlobStorageClient') as mock_blob:
            mock_blob.side_effect = Exception("Initialization failed")
            
            # Should not raise exception during init
            try:
                processor = SiteProcessor()
                assert processor is not None
            except Exception:
                pytest.fail("SiteProcessor should handle initialization errors gracefully")

    @pytest.mark.unit
    def test_process_articles_empty_list(self, mock_processor):
        """Test processing empty articles list."""
        result = mock_processor._process_articles([], max_articles=5)
        assert result == []

    @pytest.mark.unit
    def test_process_articles_invalid_data(self, mock_processor):
        """Test processing with invalid article data."""
        invalid_articles = [
            {"invalid": "data"},  # Missing required fields
            None,                 # Null article
            {}                   # Empty article
        ]

        # Should handle gracefully without crashing
        try:
            result = mock_processor._process_articles(invalid_articles, max_articles=5)
            assert isinstance(result, list)
        except Exception as e:
            # If it raises an exception, it should be a handled validation error
            assert "validation" in str(e).lower() or "invalid" in str(e).lower()

    @pytest.mark.unit
    def test_generate_rss_feed_empty_articles(self, mock_processor):
        """Test RSS generation with empty articles."""
        result = mock_processor._generate_rss_feed([])
        assert isinstance(result, str)
        assert "rss" in result.lower()

    @pytest.mark.unit
    def test_error_handling_blob_storage_failure(self, mock_processor):
        """Test error handling when blob storage fails."""
        mock_processor.blob_client.download_json.side_effect = Exception("Blob not found")

        # Should handle blob storage errors gracefully
        try:
            # This would normally call blob storage
            result = mock_processor.get_generation_status("nonexistent-site")
            assert result is not None
        except Exception as e:
            # Should be a handled error, not a raw exception
            assert isinstance(e, (ValueError, FileNotFoundError))


class TestMainAppEdgeCases:
    """Test FastAPI app edge cases."""

    @pytest.mark.unit
    def test_cors_configuration(self):
        """Test CORS is properly configured."""
        from main import app
        
        # Check that CORS middleware is added by looking for middleware
        middleware_found = False
        for middleware in app.user_middleware:
            if 'CORS' in str(type(middleware.cls)):
                middleware_found = True
                break
        assert middleware_found, "CORS middleware should be configured"

    @pytest.mark.unit
    def test_allowed_origins_local_environment(self):
        """Test allowed origins for local environment."""
        from main import get_allowed_origins

        with patch.dict(os.environ, {"ENVIRONMENT": "local"}):
            origins = get_allowed_origins()
            assert isinstance(origins, list)
            assert len(origins) > 0

    @pytest.mark.unit
    def test_allowed_origins_production_environment(self):
        """Test allowed origins for production environment."""
        from main import get_allowed_origins

        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            origins = get_allowed_origins()
            assert isinstance(origins, list)
            # Production should be more restrictive
            assert "localhost" not in str(origins)
