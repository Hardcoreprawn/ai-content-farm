"""
Unit tests for theme_api module
Tests ThemeManager and theme API endpoints
"""

import json
import os

# Import the modules to test
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from theme_api import ThemeManager, router

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def app():
    """Create FastAPI app with theme router for testing"""
    test_app = FastAPI()
    test_app.include_router(router)
    return test_app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def theme_manager():
    """Create ThemeManager instance for testing"""
    with (
        patch("pathlib.Path.exists") as mock_exists,
        patch("pathlib.Path.mkdir") as mock_mkdir,
        patch("pathlib.Path.iterdir") as mock_iterdir,
    ):
        mock_exists.return_value = True
        mock_iterdir.return_value = []  # Empty directory
        manager = ThemeManager(Path("test_themes"))
        return manager


@pytest.fixture
def mock_theme_directory():
    """Mock theme directory structure"""
    with tempfile.TemporaryDirectory() as temp_dir:
        theme_path = Path(temp_dir) / "test-theme"
        theme_path.mkdir()

        # Create mock theme files
        (theme_path / "theme.html").write_text("<html><body>{{content}}</body></html>")
        (theme_path / "style.css").write_text(".container { margin: 20px; }")
        (theme_path / "theme.json").write_text(
            json.dumps(
                {"name": "test-theme", "version": "1.0.0", "description": "Test theme"}
            )
        )

        yield temp_dir


class TestThemeManager:
    """Test cases for ThemeManager class"""

    def test_init_creates_templates_directory(self):
        """Test that ThemeManager initialization creates templates directory"""
        with (
            patch("pathlib.Path.exists") as mock_exists,
            patch("pathlib.Path.mkdir") as mock_mkdir,
        ):

            mock_exists.return_value = False
            ThemeManager(Path("test_themes"))
            mock_mkdir.assert_called_once()

    @patch("pathlib.Path.exists")
    def test_list_themes(self, mock_exists, theme_manager):
        """Test listing available themes"""
        mock_exists.return_value = True

        with patch("pathlib.Path.iterdir") as mock_iterdir:
            mock_theme1 = MagicMock()
            mock_theme1.name = "modern-grid"
            mock_theme1.is_dir.return_value = True

            mock_theme2 = MagicMock()
            mock_theme2.name = "classic"
            mock_theme2.is_dir.return_value = True

            mock_iterdir.return_value = [mock_theme1, mock_theme2]

            themes = theme_manager.list_themes()

            assert len(themes) == 2
            assert "modern-grid" in themes
            assert "classic" in themes

    def test_get_theme_info_existing_theme(self, theme_manager, mock_theme_directory):
        """Test getting theme information for existing theme"""
        theme_manager.templates_dir = Path(mock_theme_directory)

        with patch.object(theme_manager, "_read_theme_metadata") as mock_read:
            mock_read.return_value = {
                "name": "test-theme",
                "version": "1.0.0",
                "description": "Test theme",
            }

            info = theme_manager.get_theme_info("test-theme")

            assert info["name"] == "test-theme"
            assert info["version"] == "1.0.0"
            assert "exists" in info
            assert info["exists"] is True

    def test_get_theme_info_nonexistent_theme(self, theme_manager):
        """Test getting theme information for non-existent theme"""
        info = theme_manager.get_theme_info("nonexistent-theme")

        assert info["exists"] is False
        assert info["name"] == "nonexistent-theme"

    def test_read_theme_metadata_with_json(self, theme_manager, mock_theme_directory):
        """Test reading theme metadata from theme.json"""
        theme_manager.templates_dir = Path(mock_theme_directory)

        metadata = theme_manager._read_theme_metadata("test-theme")

        assert metadata["name"] == "test-theme"
        assert metadata["version"] == "1.0.0"
        assert metadata["description"] == "Test theme"

    def test_read_theme_metadata_without_json(
        self, theme_manager, mock_theme_directory
    ):
        """Test reading theme metadata when theme.json doesn't exist"""
        theme_manager.templates_dir = Path(mock_theme_directory)

        # Remove the theme.json file
        (Path(mock_theme_directory) / "test-theme" / "theme.json").unlink()

        metadata = theme_manager._read_theme_metadata("test-theme")

        assert metadata["name"] == "test-theme"
        assert metadata["version"] == "unknown"
        assert "description" in metadata

    @patch("containers.site_generator.theme_security.ThemeFileValidator")
    def test_validate_theme_files(
        self, mock_validator_class, theme_manager, mock_theme_directory
    ):
        """Test theme file validation"""
        theme_manager.templates_dir = Path(mock_theme_directory)

        # Mock validator instance
        mock_validator = MagicMock()
        mock_validator.validate_file.return_value = {
            "valid": True,
            "warnings": [],
            "errors": [],
        }
        mock_validator_class.return_value = mock_validator

        result = theme_manager.validate_theme("test-theme")

        assert result["valid"] is True
        assert len(result["files_checked"]) > 0
        mock_validator.validate_file.assert_called()

    def test_get_theme_files(self, theme_manager, mock_theme_directory):
        """Test getting list of theme files"""
        theme_manager.templates_dir = Path(mock_theme_directory)

        files = theme_manager.get_theme_files("test-theme")

        expected_files = ["theme.html", "style.css", "theme.json"]
        for expected_file in expected_files:
            assert any(expected_file in f for f in files)

    def test_theme_exists(self, theme_manager, mock_theme_directory):
        """Test checking if theme exists"""
        theme_manager.templates_dir = Path(mock_theme_directory)

        assert theme_manager.theme_exists("test-theme") is True
        assert theme_manager.theme_exists("nonexistent") is False


class TestThemeAPIEndpoints:
    """Test cases for theme API endpoints"""

    def test_get_themes_endpoint(self, client):
        """Test GET /themes endpoint"""
        with patch("theme_api.get_theme_manager") as mock_get_manager:
            # Create mock ThemeMetadata objects
            from theme_manager import ThemeMetadata

            mock_theme1 = ThemeMetadata(
                name="modern-grid",
                display_name="Modern Grid",
                description="A modern grid layout",
                version="1.0.0",
                author="Test Author",
            )
            mock_theme2 = ThemeMetadata(
                name="classic",
                display_name="Classic",
                description="A classic layout",
                version="1.0.0",
                author="Test Author",
            )

            mock_manager = MagicMock()
            mock_manager.list_themes.return_value = [mock_theme1, mock_theme2]
            mock_manager.validate_theme.return_value = {
                "valid": True,
                "warnings": [],
                "errors": [],
            }
            mock_get_manager.return_value = mock_manager

            response = client.get("/themes")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            theme_names = [theme["name"] for theme in data["data"]["themes"]]
            assert "modern-grid" in theme_names
            assert "classic" in theme_names

    def test_get_theme_info_endpoint_existing(self, client):
        """Test GET /themes/{name} endpoint for existing theme"""
        with patch("theme_api.get_theme_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_theme = MagicMock()
            mock_theme.name = "modern-grid"
            mock_theme.display_name = "Modern Grid"
            mock_theme.description = "A modern grid layout"
            mock_theme.version = "1.0.0"
            mock_theme.author = "Test Author"
            mock_theme.preview_image = "preview.jpg"
            mock_theme.grid_layout = True
            mock_theme.tech_optimized = True
            mock_theme.responsive = True
            mock_theme.supports_dark_mode = True
            mock_theme.is_valid = True
            mock_theme.validation_errors = []
            mock_theme.validation_warnings = []
            mock_theme.template_files = ["theme.html", "style.css"]
            mock_theme.assets = []
            mock_theme.created_at = "2023-01-01T00:00:00Z"
            mock_theme.updated_at = "2023-01-01T00:00:00Z"

            mock_manager.get_theme.return_value = mock_theme
            mock_manager.validate_theme.return_value = {
                "valid": True,
                "warnings": [],
                "errors": [],
            }
            mock_manager.get_theme_assets.return_value = []
            mock_get_manager.return_value = mock_manager

            response = client.get("/themes/modern-grid")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["name"] == "modern-grid"
            assert data["data"]["exists"] is True

    def test_get_theme_info_endpoint_nonexistent(self, client):
        """Test GET /themes/{name} endpoint for non-existent theme"""
        with patch("theme_api.get_theme_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.get_theme.return_value = None
            mock_get_manager.return_value = mock_manager

            response = client.get("/themes/nonexistent")

            assert response.status_code == 404
            data = response.json()
            assert data["status"] == "error"

    def test_validate_theme_endpoint_valid(self, client):
        """Test POST /themes/{name}/validate endpoint for valid theme"""
        with patch("theme_api.get_theme_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_theme = MagicMock()
            mock_manager.get_theme.return_value = mock_theme
            mock_manager.validate_theme.return_value = {
                "valid": True,
                "warnings": [],
                "errors": [],
                "files_checked": ["theme.html", "style.css"],
            }
            mock_get_manager.return_value = mock_manager

            response = client.post("/themes/modern-grid/validate")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["is_valid"] is True

    def test_validate_theme_endpoint_invalid(self, client):
        """Test POST /themes/{name}/validate endpoint for invalid theme"""
        with patch("theme_api.get_theme_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_theme = MagicMock()
            mock_manager.get_theme.return_value = mock_theme
            mock_manager.validate_theme.return_value = {
                "valid": False,
                "warnings": ["CSS warning"],
                "errors": ["HTML error"],
                "files_checked": ["theme.html", "style.css"],
            }
            mock_get_manager.return_value = mock_manager

            response = client.post("/themes/modern-grid/validate")

            assert (
                response.status_code == 200
            )  # API returns 200 even for invalid themes
            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["is_valid"] is False
            assert len(data["data"]["errors"]) > 0

    def test_validate_theme_endpoint_nonexistent(self, client):
        """Test POST /themes/{name}/validate endpoint for non-existent theme"""
        with patch("theme_api.get_theme_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.get_theme.return_value = None
            mock_get_manager.return_value = mock_manager

            response = client.post("/themes/nonexistent/validate")

            assert response.status_code == 404
            data = response.json()
            assert data["status"] == "error"

    def test_preview_theme_endpoint(self, client):
        """Test GET /themes/{name}/preview endpoint"""
        with patch("theme_api.get_theme_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.theme_exists.return_value = True
            mock_get_manager.return_value = mock_manager

            response = client.get("/themes/modern-grid/preview")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "preview_url" in data["data"]

    def test_api_error_handling(self, client):
        """Test API error handling"""
        with patch("theme_api.get_theme_manager") as mock_get_manager:
            mock_get_manager.side_effect = Exception("Test error")

            response = client.get("/themes")

            assert response.status_code == 500
            data = response.json()
            assert data["status"] == "error"
            assert "error" in data


class TestThemeManagerEdgeCases:
    """Test edge cases and error conditions for ThemeManager"""

    def test_invalid_theme_name(self, theme_manager):
        """Test handling of invalid theme names"""
        invalid_names = ["../evil", "../../etc/passwd", "", None]

        for invalid_name in invalid_names:
            if invalid_name is not None:
                info = theme_manager.get_theme_info(invalid_name)
                assert info["exists"] is False

    def test_corrupted_theme_json(self, theme_manager, mock_theme_directory):
        """Test handling of corrupted theme.json files"""
        theme_manager.templates_dir = Path(mock_theme_directory)

        # Corrupt the theme.json file
        theme_json_path = Path(mock_theme_directory) / "test-theme" / "theme.json"
        theme_json_path.write_text("{invalid json}")

        metadata = theme_manager._read_theme_metadata("test-theme")

        # Should fallback to default metadata
        assert metadata["name"] == "test-theme"
        assert metadata["version"] == "unknown"

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.mkdir")
    def test_permission_error_on_init(self, mock_mkdir, mock_exists):
        """Test handling of permission errors during initialization"""
        mock_exists.return_value = False
        mock_mkdir.side_effect = PermissionError("Permission denied")

        # Should not raise exception, but handle gracefully
        try:
            ThemeManager(Path("test_themes"))
        except PermissionError:
            pytest.fail("ThemeManager should handle PermissionError gracefully")


class TestIntegrationThemeAPI:
    """Integration tests for theme API"""

    def test_full_theme_workflow(self, client):
        """Test complete theme management workflow"""
        with patch("theme_api.get_theme_manager") as mock_get_manager:
            mock_manager = MagicMock()

            # Setup mock responses for workflow
            mock_manager.list_themes.return_value = ["test-theme"]
            mock_manager.theme_exists.return_value = True
            mock_manager.get_theme_info.return_value = {
                "name": "test-theme",
                "exists": True,
                "version": "1.0.0",
            }
            mock_manager.validate_theme.return_value = {
                "valid": True,
                "warnings": [],
                "errors": [],
            }

            mock_get_manager.return_value = mock_manager

            # Test workflow: list -> get info -> validate -> preview

            # 1. List themes
            response = client.get("/themes")
            assert response.status_code == 200
            assert "test-theme" in response.json()["data"]

            # 2. Get theme info
            response = client.get("/themes/test-theme")
            assert response.status_code == 200
            assert response.json()["data"]["name"] == "test-theme"

            # 3. Validate theme
            response = client.post("/themes/test-theme/validate")
            assert response.status_code == 200
            assert response.json()["data"]["valid"] is True

            # 4. Preview theme
            response = client.get("/themes/test-theme/preview")
            assert response.status_code == 200
            assert "preview_url" in response.json()["data"]
