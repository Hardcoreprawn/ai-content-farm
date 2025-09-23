"""
Site content management utilities

Handles content generation, page creation, and template rendering.
Uses project standard libraries for consistency.
"""

import logging

# Import from the local models module in the same directory
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

from jinja2 import Environment, FileSystemLoader, select_autoescape
from models import ArticleMetadata

sys.path.insert(0, str(Path(__file__).parent))

logger = logging.getLogger(__name__)


class ContentManager:
    """Manages content generation and page creation."""

    def __init__(self, templates_dir: Path | None = None):
        """
        Initialize ContentManager.

        Args:
            templates_dir: Directory containing Jinja2 templates
        """
        if templates_dir is None:
            templates_dir = Path(__file__).parent / "templates"

        self.content_id = str(uuid4())[:8]
        # nosemgrep: python.flask.security.xss.audit.direct-use-of-jinja2.direct-use-of-jinja2
        # Jinja2 Environment configured with autoescape enabled for HTML/XML - XSS protection in place
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )
        logger.debug(f"ContentManager initialized: {self.content_id}")

    async def generate_article_page(
        self, article: ArticleMetadata, output_dir: Path, theme: str
    ) -> Optional[Path]:
        """
        Generate HTML page for a single article.

        Args:
            article: Article metadata
            output_dir: Directory to write the page
            theme: Theme name for styling

        Returns:
            Path to generated page file, or None if failed
        """
        try:
            template = self.jinja_env.get_template("article.html")

            # Create safe filename from article slug
            filename = f"{article.slug}.html"
            output_path = output_dir / filename

            # Render template with article data
            # nosemgrep: python.flask.security.xss.audit.direct-use-of-jinja2.direct-use-of-jinja2
            # Template from secure Environment with autoescape enabled - XSS protection in place
            site_info = {
                "title": "AI Content Farm",
                "description": "Automated content aggregation and curation",
                "url": "https://aicontentprodstkwakpx.z33.web.core.windows.net",
            }
            # Add comprehensive template context to avoid any missing variable issues
            current_time = datetime.now(timezone.utc)
            content = template.render(
                article=article,
                theme=theme,
                site=site_info,
                site_title=site_info["title"],  # Backward compatibility
                site_description=site_info["description"],  # Additional compatibility
                site_url=site_info["url"],  # Additional compatibility
                generated_at=current_time,
                last_updated=current_time,  # For template compatibility
                timestamp=current_time,  # Additional time variable
                current_date=current_time.strftime("%Y-%m-%d"),
                current_time=current_time.strftime("%H:%M UTC"),
            )

            output_path.write_text(content, encoding="utf-8")
            return output_path

        except Exception as e:
            logger.error(f"Failed to generate article page for {article.slug}")
            logger.debug(
                f"Article page generation error details for {article.slug}: {e}"
            )
            return None

    async def generate_index_page(
        self, articles: List[ArticleMetadata], output_dir: Path, theme: str
    ) -> Optional[Path]:
        """
        Generate the main index page with article listings.

        Args:
            articles: List of article metadata
            output_dir: Directory to write the page
            theme: Theme name for styling

        Returns:
            Path to generated index file, or None if failed
        """
        try:
            template = self.jinja_env.get_template("index.html")
            output_path = output_dir / "index.html"

            # Sort articles by date (newest first)
            sorted_articles = sorted(
                articles,
                key=lambda x: x.generated_at
                or datetime.min.replace(tzinfo=timezone.utc),
                reverse=True,
            )

            # nosemgrep: python.flask.security.xss.audit.direct-use-of-jinja2.direct-use-of-jinja2
            # Template from secure Environment with autoescape enabled - XSS protection in place
            site_info = {
                "title": "AI Content Farm",
                "description": "Automated content aggregation and curation",
                "url": "https://aicontentprodstkwakpx.z33.web.core.windows.net",
            }
            content = template.render(
                articles=sorted_articles,
                theme=theme,
                site=site_info,
                site_title=site_info["title"],  # Backward compatibility
                generated_at=datetime.now(timezone.utc),
                last_updated=datetime.now(timezone.utc),  # For template compatibility
            )

            output_path.write_text(content, encoding="utf-8")
            return output_path

        except Exception as e:
            logger.error("Failed to generate index page")
            logger.debug(f"Index page generation error details: {e}")
            return None

    async def generate_rss_feed(
        self, articles: List[ArticleMetadata], output_dir: Path
    ) -> Optional[Path]:
        """
        Generate RSS feed for the articles.

        Args:
            articles: List of article metadata
            output_dir: Directory to write the feed

        Returns:
            Path to generated RSS file, or None if failed
        """
        try:
            template = self.jinja_env.get_template("feed.xml")
            output_path = output_dir / "feed.xml"

            # Sort articles by date (newest first) and limit to recent ones
            sorted_articles = sorted(
                articles,
                key=lambda x: x.generated_at
                or datetime.min.replace(tzinfo=timezone.utc),
                reverse=True,
            )[
                :50
            ]  # Limit to 50 most recent articles

            # nosemgrep: python.flask.security.xss.audit.direct-use-of-jinja2.direct-use-of-jinja2
            # Template from secure Environment with autoescape enabled - XSS protection in place
            site_info = {
                "title": "AI Content Farm",
                "description": "Automated content aggregation and curation",
                "url": "https://aicontentprodstkwakpx.z33.web.core.windows.net",
            }
            content = template.render(
                articles=sorted_articles,
                generated_at=datetime.now(timezone.utc),
                site=site_info,
                site_title=site_info["title"],
                site_url=site_info["url"],
                site_description=site_info["description"],
                last_updated=datetime.now(timezone.utc),
                timestamp=datetime.now(timezone.utc),
            )

            output_path.write_text(content, encoding="utf-8")
            return output_path

        except Exception as e:
            logger.error("Failed to generate RSS feed")
            logger.debug(f"RSS feed generation error details: {e}")
            return None

    async def generate_404_page(self, output_dir: Path, theme: str) -> Optional[Path]:
        """
        Generate the 404 error page.

        Args:
            output_dir: Directory to write the page
            theme: Theme name for styling

        Returns:
            Path to generated 404 file, or None if failed
        """
        try:
            template = self.jinja_env.get_template("404.html")
            output_path = output_dir / "404.html"

            # nosemgrep: python.flask.security.xss.audit.direct-use-of-jinja2.direct-use-of-jinja2
            # Template from secure Environment with autoescape enabled - XSS protection in place
            site_info = {
                "title": "AI Content Farm",
                "description": "Automated content aggregation and curation",
                "url": "https://aicontentprodstkwakpx.z33.web.core.windows.net",
            }
            content = template.render(
                theme=theme,
                generated_at=datetime.now(timezone.utc),
                site=site_info,
                site_title=site_info["title"],  # Backward compatibility
                site_description=site_info["description"],
                site_url=site_info["url"],
                last_updated=datetime.now(timezone.utc),
                timestamp=datetime.now(timezone.utc),
            )

            output_path.write_text(content, encoding="utf-8")
            return output_path

        except Exception as e:
            logger.error("Failed to generate 404 page")
            logger.debug(f"404 page generation error details: {e}")
            return None

    def create_markdown_content(self, article_data: Dict) -> str:
        """
        Create markdown content from article data.

        Args:
            article_data: Dictionary containing article information

        Returns:
            Formatted markdown content
        """
        title = article_data.get("title", "Untitled")
        description = article_data.get("description", "")
        content = article_data.get("content", "")
        tags = article_data.get("tags", [])

        # Create frontmatter
        frontmatter = ["---"]
        frontmatter.append(f'title: "{title}"')
        frontmatter.append(f'description: "{description}"')
        frontmatter.append(f"date: {datetime.now(timezone.utc).isoformat()}")

        if tags:
            frontmatter.append("tags:")
            for tag in tags:
                frontmatter.append(f"  - {tag}")

        frontmatter.append("---")
        frontmatter.append("")  # Empty line after frontmatter

        # Combine frontmatter and content
        markdown_parts = frontmatter + [content]
        return "\n".join(markdown_parts)

    def create_slug(self, title: str) -> str:
        """
        Create secure URL-safe slug from title using python-slugify.

        This library handles security, unicode, and edge cases automatically.
        """
        from slugify import slugify

        if not title or not title.strip():
            return "untitled"

        # Use python-slugify with secure defaults
        slug = slugify(
            title.strip(),
            max_length=50,  # Reasonable length limit
            lowercase=True,
            separator="-",
            # Only allow word chars and hyphens (spaces will be converted to hyphens)
            regex_pattern=r"[^-\w]",
        )

        # Final safety check - if somehow empty, provide fallback
        if not slug:
            return "article"

        return slug

    async def generate_sitemap(
        self, articles: List[ArticleMetadata], output_dir: Path, base_url: str
    ) -> Optional[Path]:
        """
        Generate XML sitemap for the site.

        Args:
            articles: List of article metadata
            output_dir: Directory to write the sitemap
            base_url: Base URL of the site

        Returns:
            Path to generated sitemap file, or None if failed
        """
        try:
            template = self.jinja_env.get_template("sitemap.xml")
            output_path = output_dir / "sitemap.xml"

            # nosemgrep: python.flask.security.xss.audit.direct-use-of-jinja2.direct-use-of-jinja2
            # Template from secure Environment with autoescape enabled - XSS protection in place
            content = template.render(
                articles=articles,
                base_url=base_url.rstrip("/"),
                generated_at=datetime.now(timezone.utc),
            )

            output_path.write_text(content, encoding="utf-8")
            return output_path

        except Exception as e:
            logger.error("Failed to generate sitemap")
            logger.debug(f"Sitemap generation error details: {e}")
            return None
