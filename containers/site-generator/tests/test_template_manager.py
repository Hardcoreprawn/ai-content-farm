#!/usr/bin/env python3
"""
Tests for Template Manager

Tests the new blob-based template loading system.
"""

from template_manager import TemplateManager, BlobTemplateLoader, LocalTemplateLoader
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import sys
sys.path.append('/workspaces/ai-content-farm')


class TestBlobTemplateLoader:
    """Test blob-based template loading"""

    def test_blob_loader_init(self, mock_blob_client):
        """Test BlobTemplateLoader initialization"""
        loader = BlobTemplateLoader(mock_blob_client, "test-container")
        assert loader.blob_client == mock_blob_client
        assert loader.container_name == "test-container"
        assert loader.cache == {}

    def test_blob_loader_get_source(self, mock_blob_client):
        """Test loading template from blob storage"""
        mock_blob_client.download_text.return_value = "<html>Test Template</html>"

        loader = BlobTemplateLoader(mock_blob_client)
        source, filename, uptodate = loader.get_source(None, "test.html")

        assert source == "<html>Test Template</html>"
        assert filename is None
        assert uptodate() is True

        # Verify blob client was called correctly
        mock_blob_client.download_text.assert_called_once_with(
            "site-templates", "templates/test.html"
        )

    def test_blob_loader_caching(self, mock_blob_client):
        """Test that templates are cached after first load"""
        mock_blob_client.download_text.return_value = "<html>Cached Template</html>"

        loader = BlobTemplateLoader(mock_blob_client)

        # First call
        source1, _, _ = loader.get_source(None, "cached.html")

        # Second call - should use cache
        source2, _, _ = loader.get_source(None, "cached.html")

        assert source1 == source2
        # Blob client should only be called once
        mock_blob_client.download_text.assert_called_once()

    def test_blob_loader_template_not_found(self, mock_blob_client):
        """Test handling of missing templates"""
        mock_blob_client.download_text.side_effect = Exception(
            "Blob not found")

        loader = BlobTemplateLoader(mock_blob_client)

        with pytest.raises(Exception):  # Should raise TemplateNotFound
            loader.get_source(None, "missing.html")


class TestLocalTemplateLoader:
    """Test filesystem-based template loading (development mode)"""

    def test_local_loader_init(self, temp_templates_dir):
        """Test LocalTemplateLoader initialization"""
        loader = LocalTemplateLoader(temp_templates_dir)
        assert loader.template_dir == Path(temp_templates_dir)

    def test_local_loader_get_source(self, temp_templates_dir):
        """Test loading template from local filesystem"""
        loader = LocalTemplateLoader(temp_templates_dir)

        source, filename, uptodate = loader.get_source(None, "base.html")

        assert "DOCTYPE html" in source
        assert filename == str(Path(temp_templates_dir) / "base.html")
        assert callable(uptodate)

    def test_local_loader_template_not_found(self, temp_templates_dir):
        """Test handling of missing local templates"""
        loader = LocalTemplateLoader(temp_templates_dir)

        with pytest.raises(Exception):  # Should raise TemplateNotFound
            loader.get_source(None, "missing.html")


class TestTemplateManager:
    """Test the main TemplateManager functionality"""

    def test_template_manager_init_local(self, mock_blob_client):
        """Test TemplateManager initialization in local mode"""
        manager = TemplateManager(mock_blob_client, use_local=True)

        assert manager.blob_client == mock_blob_client
        assert manager.use_local is True
        assert manager.jinja_env is not None

    def test_template_manager_init_blob(self, mock_blob_client):
        """Test TemplateManager initialization in blob mode"""
        manager = TemplateManager(mock_blob_client, use_local=False)

        assert manager.blob_client == mock_blob_client
        assert manager.use_local is False
        assert manager.jinja_env is not None

    @patch('template_manager.LocalTemplateLoader')
    def test_render_template_local(self, mock_local_loader, mock_blob_client, temp_templates_dir):
        """Test template rendering in local mode"""
        # Setup mock to return a real template loader
        mock_local_loader.return_value = LocalTemplateLoader(
            temp_templates_dir)

        manager = TemplateManager(mock_blob_client, use_local=True)

        # Test rendering with context
        result = manager.render_template("index.html",
                                         site_metadata={"title": "Test Site"},
                                         articles=[
                                             {"title": "Test Article", "ranking_score": 0.9}]
                                         )

        assert "Test Site" in result
        assert "Test Article" in result
        assert "0.9" in result

    def test_get_static_assets_with_fallback(self, mock_blob_client):
        """Test getting static assets with fallback to default CSS"""
        # Mock blob client to fail CSS download
        mock_blob_client.download_text.side_effect = Exception("CSS not found")

        manager = TemplateManager(mock_blob_client, use_local=False)

        assets = manager.get_static_assets()

        assert "assets/style.css" in assets
        # Default CSS should be present
        assert "font-family" in assets["assets/style.css"]

    def test_get_static_assets_from_blob(self, mock_blob_client):
        """Test getting static assets from blob storage"""
        mock_blob_client.download_text.return_value = "body { color: red; }"

        manager = TemplateManager(mock_blob_client, use_local=False)

        assets = manager.get_static_assets()

        assert assets["assets/style.css"] == "body { color: red; }"
        mock_blob_client.download_text.assert_called_with(
            "site-templates", "templates/style.css")

    def test_upload_templates_to_blob(self, mock_blob_client, temp_templates_dir):
        """Test uploading local templates to blob storage"""
        # Create a mock manager with real template directory
        manager = TemplateManager(mock_blob_client, use_local=True)

        # Mock the template directory to point to our test templates
        with patch('template_manager.Path') as mock_path:
            mock_path.return_value.exists.return_value = True
            mock_path.return_value.glob.return_value = [
                Path(temp_templates_dir) / "base.html",
                Path(temp_templates_dir) / "index.html"
            ]
            mock_path.return_value.__truediv__ = lambda self, other: Path(
                temp_templates_dir) / other

            # Mock file reading
            def mock_read_text(*args, **kwargs):
                return "<html>Mock template content</html>"

            with patch.object(Path, 'read_text', return_value="<html>Mock template content</html>"):
                result = manager.upload_templates_to_blob()

                assert result is True
                assert mock_blob_client.ensure_container.called
                assert mock_blob_client.upload_text.called


class TestTemplateManagerIntegration:
    """Integration tests for template manager with real templates"""

    def test_full_site_generation_flow(self, mock_blob_client, temp_templates_dir, sample_ranked_content, test_site_metadata):
        """Test the complete flow from ranked content to rendered HTML"""
        manager = TemplateManager(mock_blob_client, use_local=True)

        # Mock the local template directory
        with patch.object(manager.jinja_env.loader, 'template_dir', Path(temp_templates_dir)):
            # Render index page
            index_html = manager.render_template(
                "index.html",
                site_metadata=test_site_metadata,
                articles=sample_ranked_content["ranked_topics"]
            )

            # Verify content is rendered correctly
            assert test_site_metadata["title"] in index_html
            assert sample_ranked_content["ranked_topics"][0]["title"] in index_html
            assert str(
                sample_ranked_content["ranked_topics"][0]["ranking_score"]) in index_html

            # Render individual article
            article_html = manager.render_template(
                "article.html",
                title=sample_ranked_content["ranked_topics"][0]["title"],
                article=sample_ranked_content["ranked_topics"][0]
            )

            # Verify article content
            assert sample_ranked_content["ranked_topics"][0]["title"] in article_html
            assert sample_ranked_content["ranked_topics"][0]["content"] in article_html

    def test_error_handling_missing_template(self, mock_blob_client):
        """Test error handling when template is missing"""
        manager = TemplateManager(mock_blob_client, use_local=False)

        # Mock blob client to fail
        mock_blob_client.download_text.side_effect = Exception(
            "Template not found")

        with pytest.raises(Exception):
            manager.render_template("missing-template.html", data="test")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
