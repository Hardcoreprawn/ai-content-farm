"""
Theme Management System for Static Site Generator

Provides a flexible, extensible system for managing multiple themes with proper
asset management, validation, and configuration.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from libs import SecureErrorHandler

logger = logging.getLogger(__name__)
error_handler = SecureErrorHandler("theme-manager")


@dataclass
class ThemeMetadata:
    """Metadata for a theme configuration."""

    name: str
    display_name: str
    description: str
    version: str
    author: str
    preview_image: Optional[str] = None
    supports_dark_mode: bool = True
    responsive: bool = True
    grid_layout: bool = False
    tech_optimized: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    assets: List[str] = None
    template_files: List[str] = None

    def __post_init__(self):
        """Initialize default values."""
        if self.assets is None:
            self.assets = []
        if self.template_files is None:
            self.template_files = []


class ThemeManager:
    """Manages theme discovery, validation, and configuration."""

    def __init__(self, themes_directory: Path):
        """
        Initialize ThemeManager.

        Args:
            themes_directory: Directory containing theme subdirectories
        """
        self.themes_dir = themes_directory
        self.themes_cache: Dict[str, ThemeMetadata] = {}
        self._scan_themes()

    def _scan_themes(self) -> None:
        """Scan themes directory and load theme metadata."""
        self.themes_cache.clear()

        if not self.themes_dir.exists():
            logger.info(f"Creating themes directory: {self.themes_dir}")
            self.themes_dir.mkdir(parents=True, exist_ok=True)

        try:
            for theme_dir in self.themes_dir.iterdir():
                if theme_dir.is_dir() and not theme_dir.name.startswith("."):
                    try:
                        metadata = self._load_theme_metadata(theme_dir)
                        if metadata:
                            self.themes_cache[metadata.name] = metadata
                            logger.debug(f"Loaded theme: {metadata.name}")
                    except (ValueError, TypeError, KeyError) as e:
                        error_response = error_handler.handle_error(
                            error=e,
                            error_type="validation",
                            context={"theme_dir": theme_dir.name},
                        )
                        logger.warning(
                            f"Invalid theme configuration in {theme_dir.name}: {error_response['message']}"
                        )
                    except Exception as e:
                        error_response = error_handler.handle_error(
                            error=e,
                            error_type="general",
                            context={"theme_dir": theme_dir.name},
                        )
                        logger.warning(
                            f"Unexpected error loading theme {theme_dir.name}: {error_response['message']}"
                        )
        except OSError as e:
            logger.warning(f"Failed to scan themes directory {self.themes_dir}: {e}")

    def _load_theme_metadata(self, theme_dir: Path) -> Optional[ThemeMetadata]:
        """
        Load theme metadata from theme.json file or create default.

        Args:
            theme_dir: Path to theme directory

        Returns:
            ThemeMetadata object or None if invalid
        """
        theme_config_file = theme_dir / "theme.json"

        # Check if theme has required template files
        required_templates = ["base.html", "index.html", "article.html"]
        missing_templates = []

        for template in required_templates:
            if not (theme_dir / template).exists():
                missing_templates.append(template)

        if missing_templates:
            logger.warning(
                f"Theme {theme_dir.name} missing templates: {missing_templates}"
            )
            return None

        # Load or create theme configuration
        if theme_config_file.exists():
            try:
                with open(theme_config_file, "r", encoding="utf-8") as f:
                    config_data = json.load(f)

                return ThemeMetadata(
                    name=config_data.get("name", theme_dir.name),
                    display_name=config_data.get(
                        "display_name", theme_dir.name.title()
                    ),
                    description=config_data.get(
                        "description", f"Theme: {theme_dir.name}"
                    ),
                    version=config_data.get("version", "1.0.0"),
                    author=config_data.get("author", "Unknown"),
                    preview_image=config_data.get("preview_image"),
                    supports_dark_mode=config_data.get("supports_dark_mode", True),
                    responsive=config_data.get("responsive", True),
                    grid_layout=config_data.get("grid_layout", False),
                    tech_optimized=config_data.get("tech_optimized", False),
                    assets=config_data.get("assets", []),
                    template_files=self._get_template_files(theme_dir),
                )
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Invalid theme.json for {theme_dir.name}: {e}")
                # Fall through to create default metadata

        # Create default metadata
        return ThemeMetadata(
            name=theme_dir.name,
            display_name=theme_dir.name.title().replace("-", " "),
            description=f"Theme: {theme_dir.name}",
            version="1.0.0",
            author="Unknown",
            template_files=self._get_template_files(theme_dir),
        )

    def _get_template_files(self, theme_dir: Path) -> List[str]:
        """Get list of template files in theme directory."""
        template_files = []
        for file_path in theme_dir.rglob("*.html"):
            relative_path = file_path.relative_to(theme_dir)
            template_files.append(str(relative_path))
        return template_files

    def get_theme(self, theme_name: str) -> Optional[ThemeMetadata]:
        """
        Get theme metadata by name.

        Args:
            theme_name: Name of the theme

        Returns:
            ThemeMetadata object or None if not found
        """
        return self.themes_cache.get(theme_name)

    def list_themes(self) -> List[ThemeMetadata]:
        """
        Get list of all available themes.

        Returns:
            List of ThemeMetadata objects
        """
        return list(self.themes_cache.values())

    def validate_theme(self, theme_name: str) -> Dict[str, Any]:
        """
        Validate theme structure and files.

        Args:
            theme_name: Name of theme to validate

        Returns:
            Dictionary with validation results
        """
        theme = self.get_theme(theme_name)
        if not theme:
            return {
                "valid": False,
                "errors": [f"Theme '{theme_name}' not found"],
                "warnings": [],
            }

        errors = []
        warnings = []

        theme_dir = self.themes_dir / theme_name

        # Check required templates
        required_templates = ["base.html", "index.html", "article.html"]
        for template in required_templates:
            template_path = theme_dir / template
            if not template_path.exists():
                errors.append(f"Missing required template: {template}")
            elif template_path.stat().st_size == 0:
                warnings.append(f"Template file is empty: {template}")

        # Check for optional but recommended templates
        optional_templates = ["404.html", "feed.xml", "sitemap.xml"]
        for template in optional_templates:
            if not (theme_dir / template).exists():
                warnings.append(f"Missing optional template: {template}")

        # Check for CSS files
        css_files = list(theme_dir.glob("*.css"))
        if not css_files:
            # Check if there are CSS files in a subdirectory or shared static dir
            if not (self.themes_dir.parent / "static" / "style.css").exists():
                warnings.append("No CSS files found for theme")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "theme": theme,
        }

    def refresh_themes(self) -> None:
        """Refresh theme cache by rescanning themes directory."""
        self._scan_themes()

    def create_theme_config(self, theme_name: str, config: Dict[str, Any]) -> bool:
        """
        Create or update theme configuration file.

        Args:
            theme_name: Name of the theme
            config: Configuration dictionary

        Returns:
            True if successful, False otherwise
        """
        theme_dir = self.themes_dir / theme_name
        if not theme_dir.exists():
            return False

        config_file = theme_dir / "theme.json"

        try:
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, default=str)

            # Refresh cache
            self._scan_themes()
            return True
        except (ValueError, TypeError) as e:
            error_response = error_handler.handle_error(
                error=e, error_type="validation", context={"theme_name": theme_name}
            )
            logger.error(
                f"Invalid configuration data for theme {theme_name}: {error_response['message']}"
            )
            return False
        except Exception as e:
            error_response = error_handler.handle_error(
                error=e, error_type="general", context={"theme_name": theme_name}
            )
            logger.error(
                f"Failed to create theme config for {theme_name}: {error_response['message']}"
            )
            return False

    def get_theme_assets(self, theme_name: str) -> List[Path]:
        """
        Get list of asset files for a theme.

        Args:
            theme_name: Name of the theme

        Returns:
            List of asset file paths
        """
        theme_dir = self.themes_dir / theme_name
        assets = []

        # Common asset extensions
        asset_extensions = [
            ".css",
            ".js",
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".svg",
            ".ico",
        ]

        for ext in asset_extensions:
            assets.extend(theme_dir.glob(f"*{ext}"))
            assets.extend(theme_dir.glob(f"**/*{ext}"))

        return assets

    def get_default_theme(self) -> str:
        """
        Get name of default theme.

        Returns:
            Name of default theme or 'minimal' as fallback
        """
        # Look for theme marked as default
        for theme in self.themes_cache.values():
            if getattr(theme, "is_default", False):
                return theme.name

        # Fallback to minimal or first available theme
        if "minimal" in self.themes_cache:
            return "minimal"
        elif self.themes_cache:
            return next(iter(self.themes_cache.keys()))
        else:
            return "minimal"  # Ultimate fallback
