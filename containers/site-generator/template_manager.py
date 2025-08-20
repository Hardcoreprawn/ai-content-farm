#!/usr/bin/env python3
"""
Template Manager for Site Generator

Handles loading and rendering of HTML templates, with support for both
blob storage and local file loading for development.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from jinja2 import BaseLoader, Environment, TemplateNotFound, select_autoescape

from libs.blob_storage import BlobStorageClient

logger = logging.getLogger(__name__)


class BlobTemplateLoader(BaseLoader):
    """Jinja2 template loader that loads templates from Azure blob storage."""

    def __init__(
        self, blob_client: BlobStorageClient, container_name: str = "site-templates"
    ):
        self.blob_client = blob_client
        self.container_name = container_name
        self.cache: Dict[str, str] = {}

    def get_source(self, environment, template):
        """Load template source from blob storage."""
        try:
            # Check cache first
            if template in self.cache:
                source = self.cache[template]
                return source, None, lambda: True

            # Download from blob storage
            blob_name = f"templates/{template}"
            source = self.blob_client.download_text(self.container_name, blob_name)

            # Cache the template
            self.cache[template] = source

            return source, None, lambda: True

        except Exception as e:
            logger.error(f"Failed to load template {template}: {e}")
            raise TemplateNotFound(template)


class LocalTemplateLoader(BaseLoader):
    """Jinja2 template loader that loads templates from local filesystem (development only)."""

    def __init__(self, template_dir: str = "/app/templates"):
        self.template_dir = Path(template_dir)

    def get_source(self, environment, template):
        """Load template source from local filesystem."""
        try:
            template_path = self.template_dir / template
            if not template_path.exists():
                raise TemplateNotFound(template)

            source = template_path.read_text(encoding="utf-8")
            mtime = template_path.stat().st_mtime

            return (
                source,
                str(template_path),
                lambda: template_path.stat().st_mtime == mtime,
            )

        except Exception as e:
            logger.error(f"Failed to load local template {template}: {e}")
            raise TemplateNotFound(template)


class TemplateManager:
    """Manages HTML template loading and rendering for site generation."""

    def __init__(self, blob_client: BlobStorageClient, use_local: bool = False):
        self.blob_client = blob_client
        self.use_local = use_local

        # Initialize Jinja2 environment with appropriate loader
        if use_local:
            loader = LocalTemplateLoader()
            logger.info("Using local template loader for development")
        else:
            loader = BlobTemplateLoader(blob_client)
            logger.info("Using blob template loader for production")

        # This is secure: autoescape is properly configured for HTML/XML templates
        self.jinja_env = Environment(  # nosemgrep: python.flask.security.xss.audit.direct-use-of-jinja2.direct-use-of-jinja2
            loader=loader,
            # More specific autoescape for security
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Add custom filters
        self.jinja_env.filters["format"] = lambda value, fmt: fmt % value

    def render_template(self, template_name: str, **context) -> str:
        """Render a template with the given context.

        Note: This is secure as Jinja2 Environment is configured with autoescape=True
        to prevent XSS vulnerabilities.
        """
        try:
            template = self.jinja_env.get_template(template_name)
            # nosemgrep: python.flask.security.xss.audit.direct-use-of-jinja2.direct-use-of-jinja2
            return template.render(**context)
        except Exception as e:
            logger.error(f"Failed to render template {template_name}: {e}")
            raise

    def upload_templates_to_blob(self) -> bool:
        """Upload local templates to blob storage (for deployment)."""
        try:
            template_dir = Path("/app/templates")
            if not template_dir.exists():
                logger.error("Local templates directory not found")
                return False

            # Ensure container exists
            self.blob_client.ensure_container("site-templates")

            # Upload each template file
            for template_file in template_dir.glob("**/*.html"):
                relative_path = template_file.relative_to(template_dir)
                blob_name = f"templates/{relative_path}"

                content = template_file.read_text(encoding="utf-8")
                self.blob_client.upload_text(
                    "site-templates", blob_name, content, content_type="text/html"
                )
                logger.info(f"Uploaded template: {blob_name}")

            # Upload CSS file
            css_file = template_dir / "style.css"
            if css_file.exists():
                css_content = css_file.read_text(encoding="utf-8")
                self.blob_client.upload_text(
                    "site-templates",
                    "templates/style.css",
                    css_content,
                    content_type="text/css",
                )
                logger.info("Uploaded CSS file")

            return True

        except Exception as e:
            logger.error(f"Failed to upload templates to blob: {e}")
            return False

    def get_static_assets(self) -> Dict[str, str]:
        """Get static assets (CSS, JS) for site generation."""
        try:
            if self.use_local:
                # Load from local file
                css_file = Path("/app/templates/style.css")
                if css_file.exists():
                    css_content = css_file.read_text(encoding="utf-8")
                else:
                    css_content = self._get_default_css()
            else:
                # Load from blob storage
                try:
                    css_content = self.blob_client.download_text(
                        "site-templates", "templates/style.css"
                    )
                except Exception:
                    logger.warning("Could not load CSS from blob, using default")
                    css_content = self._get_default_css()

            return {"assets/style.css": css_content}

        except Exception as e:
            logger.error(f"Failed to get static assets: {e}")
            return {"assets/style.css": self._get_default_css()}

    def _get_default_css(self) -> str:
        """Get minimal default CSS as fallback."""
        return """
        body { font-family: -apple-system, sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; }
        .article-card { margin: 20px 0; padding: 20px; border: 1px solid #eee; border-radius: 8px; }
        .article-title a { text-decoration: none; color: #333; }
        .article-meta { color: #666; font-size: 0.9rem; margin: 10px 0; }
        .tag { background: #007acc; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8rem; margin-right: 8px; }
        """


def create_template_manager(
    blob_client: BlobStorageClient, use_local: bool = False
) -> TemplateManager:
    """Factory function to create a TemplateManager instance."""
    return TemplateManager(blob_client, use_local)
