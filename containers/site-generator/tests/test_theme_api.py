"""
Simplified Theme Manager Tests
Focus on core functionality: can it work with a basic theme?
"""

import json
import tempfile
from pathlib import Path

import pytest
from theme_manager import ThemeManager, ThemeMetadata


class TestThemeManagerSimple:
    """Simple, focused tests for ThemeManager core functionality"""

    def test_theme_manager_initializes(self):
        """Test that ThemeManager can initialize with any directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            theme_dir = Path(temp_dir)
            manager = ThemeManager(theme_dir)

            assert manager.themes_dir == theme_dir
            assert isinstance(manager.themes_cache, dict)

    def test_theme_manager_works_with_basic_theme(self):
        """Test that ThemeManager can load and use a basic theme"""
        with tempfile.TemporaryDirectory() as temp_dir:
            theme_dir = Path(temp_dir)

            # Create a minimal working theme
            basic_theme_dir = theme_dir / "basic"
            basic_theme_dir.mkdir()

            # Create required template files
            (basic_theme_dir / "base.html").write_text(
                """
<!DOCTYPE html>
<html>
<head><title>{{ title | default('Site') }}</title></head>
<body>{% block content %}{% endblock %}</body>
</html>
            """.strip()
            )

            (basic_theme_dir / "index.html").write_text(
                """
{% extends "base.html" %}
{% block content %}
<h1>{{ site_title | default('Welcome') }}</h1>
<div class="articles">{{ articles | default('') }}</div>
{% endblock %}
            """.strip()
            )

            (basic_theme_dir / "article.html").write_text(
                """
{% extends "base.html" %}
{% block content %}
<article>
<h1>{{ article.title | default('Article') }}</h1>
<div>{{ article.content | default('') }}</div>
</article>
{% endblock %}
            """.strip()
            )

            # Create basic theme.json
            theme_config = {
                "name": "basic",
                "display_name": "Basic Theme",
                "description": "A simple, working theme",
                "version": "1.0.0",
                "author": "Test",
            }
            (basic_theme_dir / "theme.json").write_text(json.dumps(theme_config))

            # Test ThemeManager can load it
            manager = ThemeManager(theme_dir)
            themes = manager.list_themes()

            assert len(themes) >= 1
            theme_names = [t.name for t in themes]
            assert "basic" in theme_names

            # Get the basic theme
            basic_theme = next(t for t in themes if t.name == "basic")
            assert basic_theme.display_name == "Basic Theme"
            assert basic_theme.version == "1.0.0"

    def test_theme_manager_handles_empty_directory(self):
        """Test that ThemeManager handles empty theme directory gracefully"""
        with tempfile.TemporaryDirectory() as temp_dir:
            theme_dir = Path(temp_dir)
            manager = ThemeManager(theme_dir)

            themes = manager.list_themes()
            assert len(themes) == 0  # Empty directory, no themes

    def test_theme_manager_handles_invalid_theme(self):
        """Test that ThemeManager skips invalid themes without crashing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            theme_dir = Path(temp_dir)

            # Create a directory that looks like a theme but is invalid
            invalid_theme_dir = theme_dir / "invalid"
            invalid_theme_dir.mkdir()

            # Only create one required file (missing others)
            (invalid_theme_dir / "base.html").write_text("<html></html>")
            # Missing index.html and article.html

            manager = ThemeManager(theme_dir)
            themes = manager.list_themes()

            # Should not crash, should skip invalid theme
            assert len(themes) == 0

    def test_theme_manager_can_get_theme_by_name(self):
        """Test that we can retrieve a specific theme by name"""
        with tempfile.TemporaryDirectory() as temp_dir:
            theme_dir = Path(temp_dir)

            # Create a working theme
            basic_theme_dir = theme_dir / "findme"
            basic_theme_dir.mkdir()

            # Create minimal required files
            for template in ["base.html", "index.html", "article.html"]:
                (basic_theme_dir / template).write_text(f"<!-- {template} -->")

            theme_config = {
                "name": "findme",
                "display_name": "Find Me Theme",
                "version": "1.0.0",
                "author": "Test",
            }
            (basic_theme_dir / "theme.json").write_text(json.dumps(theme_config))

            manager = ThemeManager(theme_dir)

            # Test getting theme by name
            theme = manager.get_theme("findme")
            assert theme is not None
            assert theme.name == "findme"
            assert theme.display_name == "Find Me Theme"

            # Test getting non-existent theme
            missing = manager.get_theme("doesnotexist")
            assert missing is None

    def test_theme_manager_provides_fallback_metadata(self):
        """Test that ThemeManager creates reasonable defaults for themes without metadata"""
        with tempfile.TemporaryDirectory() as temp_dir:
            theme_dir = Path(temp_dir)

            # Create theme with required templates but no theme.json
            no_meta_theme_dir = theme_dir / "nometa"
            no_meta_theme_dir.mkdir()

            for template in ["base.html", "index.html", "article.html"]:
                (no_meta_theme_dir / template).write_text(
                    f"<!-- {template} template -->"
                )

            manager = ThemeManager(theme_dir)
            themes = manager.list_themes()

            assert len(themes) == 1
            theme = themes[0]
            assert theme.name == "nometa"
            assert theme.display_name  # Should have some display name
            assert theme.version  # Should have some version
