"""
Article Metadata Generator

Generates SEO-optimized metadata for articles including:
- English title translation
- URL-safe slug generation
- SEO descriptions
- Language detection

Uses GPT-3.5-turbo for cost-effective metadata generation (~$0.0001/article).
"""

import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, Optional, Union

from openai_client import OpenAIClient

logger = logging.getLogger(__name__)


class MetadataGenerator:
    """
    Generate SEO-optimized metadata for articles.

    Handles:
    - Non-English title translation
    - Hashtag cleanup
    - URL slug generation
    - SEO optimization
    """

    def __init__(self, openai_client: Optional[OpenAIClient] = None):
        """Initialize with OpenAI client."""
        self.openai_client = openai_client or OpenAIClient()

    async def generate_metadata(
        self,
        title: str,
        content_preview: str,
        published_date: str,
        original_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate complete metadata for an article.

        Args:
            title: Original article title (may be non-English, have hashtags, etc.)
            content_preview: First 500 chars of content for context
            published_date: ISO 8601 date string
            original_url: Source URL for reference

        Returns:
            Dict with:
                - original_title: Original title preserved
                - title: Clean English SEO title (45-60 chars)
                - slug: URL-safe slug (lowercase, hyphens, ASCII)
                - seo_description: 140-160 char description
                - language: Detected language code
                - translated: Boolean if translation occurred
                - date_slug: YYYY-MM-DD format
                - filename: Complete filename for static site
                - metadata_cost_usd: Cost of metadata generation
                - metadata_tokens: Tokens used for metadata generation

        Examples:
            >>> # Japanese title
            >>> metadata = await generate_metadata(
            ...     title="米政権内の対中強硬派に焦り",
            ...     content_preview="US officials express concern...",
            ...     published_date="2025-10-06T12:00:00Z"
            ... )
            >>> metadata['title']
            'US China Hawks Grow Anxious Over Trump Trade Deals'
            >>> metadata['slug']
            'us-china-hawks-anxious-trump-trade-deals'
            >>> metadata['filename']
            'articles/2025-10-06-us-china-hawks-anxious-trump-trade-deals.html'

            >>> # Hashtag cleanup
            >>> metadata = await generate_metadata(
            ...     title="Gem.coop #technology #blockchain",
            ...     content_preview="Gem.coop launches new cooperative platform...",
            ...     published_date="2025-10-06T12:00:00Z"
            ... )
            >>> metadata['title']
            'Gem.coop Launches Cooperative Blockchain Platform'
            >>> '#' in metadata['title']
            False
        """

        # Detect if translation needed
        needs_translation = self._needs_translation(title)

        # Generate AI-optimized metadata (with cost tracking)
        ai_metadata = await self._call_openai_for_metadata(
            title, content_preview, needs_translation
        )

        # Generate URL slug from AI title (title is always string)
        slug = self._generate_slug(str(ai_metadata["title"]))

        # Parse date for filename
        date_slug = self._parse_date_slug(published_date)

        # Validate slug length
        if len(slug) > 60:
            logger.warning(f"Slug too long ({len(slug)} chars), truncating: {slug}")
            slug = slug[:57] + "..."  # Keep it under 60

        # Generate final filename
        filename = f"articles/{date_slug}-{slug}.html"

        # Validate total filename length
        if len(filename) > 100:
            raise ValueError(
                f"Filename too long ({len(filename)} chars): {filename}. "
                f"Slug must be shorter."
            )

        return {
            "original_title": title,
            "title": ai_metadata["title"],
            "slug": slug,
            "seo_description": ai_metadata["description"],
            "language": ai_metadata["language"],
            "translated": needs_translation,
            "date_slug": date_slug,
            "filename": filename,
            "url": f"/articles/{date_slug}-{slug}.html",
            # Cost tracking
            "metadata_cost_usd": ai_metadata.get("cost_usd", 0.0),
            "metadata_tokens": ai_metadata.get("tokens_used", 0),
        }

    def _needs_translation(self, title: str) -> bool:
        """
        Detect if title contains non-ASCII characters (needs translation).

        Args:
            title: Title to check

        Returns:
            bool: True if translation needed

        Examples:
            >>> _needs_translation("Hello World")
            False
            >>> _needs_translation("米政権内の対中強硬派に焦り")
            True
            >>> _needs_translation("Café Résumé")
            True
        """
        # Check for non-ASCII characters
        return not title.isascii()

    def _generate_slug(self, title: str) -> str:
        """
        Generate URL-safe slug from title.

        Args:
            title: Clean English title

        Returns:
            str: URL-safe slug (lowercase, hyphens, ASCII only)

        Examples:
            >>> _generate_slug("US China Hawks Grow Anxious")
            'us-china-hawks-grow-anxious'
            >>> _generate_slug("NVIDIA Breaks All Records!")
            'nvidia-breaks-all-records'
            >>> _generate_slug("What's New in AI?")
            'whats-new-in-ai'
        """
        # Convert to lowercase
        slug = title.lower()

        # Remove apostrophes and other punctuation
        slug = re.sub(r"[''`]", "", slug)

        # Replace spaces and special chars with hyphens
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[-\s]+", "-", slug)

        # Remove leading/trailing hyphens
        slug = slug.strip("-")

        return slug

    def _parse_date_slug(self, published_date: str) -> str:
        """
        Parse ISO date to YYYY-MM-DD format.

        Args:
            published_date: ISO 8601 date string

        Returns:
            str: Date in YYYY-MM-DD format

        Examples:
            >>> _parse_date_slug("2025-10-06T12:30:00Z")
            '2025-10-06'
            >>> _parse_date_slug("2025-10-06")
            '2025-10-06'
        """
        try:
            if "T" in published_date:
                dt = datetime.fromisoformat(published_date.replace("Z", "+00:00"))
            else:
                dt = datetime.fromisoformat(published_date)

            return dt.strftime("%Y-%m-%d")
        except Exception as e:
            logger.error(f"Failed to parse date '{published_date}': {e}")
            # Fallback to current date
            return datetime.now().strftime("%Y-%m-%d")

    async def _call_openai_for_metadata(
        self, title: str, content_preview: str, needs_translation: bool
    ) -> Dict[str, Union[str, float, int]]:
        """
        Call OpenAI to generate optimized metadata.

        Args:
            title: Original title
            content_preview: Content preview for context
            needs_translation: Whether translation is needed

        Returns:
            Dict with title, description, language, cost_usd (float), tokens_used (int)

        Examples:
            >>> result = await _call_openai_for_metadata(
            ...     "米政権内の対中強硬派に焦り",
            ...     "US officials...",
            ...     True
            ... )
            >>> result['language']
            'ja'
            >>> result['title']
            'US China Hawks Grow Anxious Over Trump Trade Deals'
            >>> result['cost_usd'] < 0.001  # Very low cost
            True
        """

        # Construct prompt based on whether translation needed
        if needs_translation:
            prompt = f"""Given this non-English article, generate SEO-optimized English metadata:

Original Title: {title}
Content Preview: {content_preview[:300]}

Generate:
1. Engaging English title (45-60 characters, attention-grabbing, no hashtags/emoji)
2. SEO description (140-160 characters)
3. Language code (ISO 639-1, e.g., 'ja', 'fr', 'es')

Return ONLY valid JSON:
{{"title": "...", "description": "...", "language": "..."}}"""
        else:
            prompt = f"""Given this article, generate SEO-optimized metadata:

Title: {title}
Content Preview: {content_preview[:300]}

Generate:
1. Clean engaging title (45-60 characters, no hashtags/emoji/special chars)
2. SEO description (140-160 characters)

Return ONLY valid JSON:
{{"title": "...", "description": "...", "language": "en"}}"""

        try:
            # Call OpenAI with low temperature for consistency
            response = await self.openai_client.generate_completion(
                prompt=prompt,
                max_tokens=200,
                temperature=0.3,  # Low temperature for consistency
            )

            # Parse JSON response
            result_text = response["content"].strip()

            # Extract JSON if wrapped in markdown code blocks
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()

            metadata = json.loads(result_text)

            # Validate required fields
            required_fields = ["title", "description", "language"]
            for field in required_fields:
                if field not in metadata:
                    raise ValueError(f"Missing required field: {field}")

            # Validate lengths
            if len(metadata["title"]) > 70:
                logger.warning(f"Title too long ({len(metadata['title'])}), truncating")
                metadata["title"] = metadata["title"][:60].rsplit(" ", 1)[0]

            if len(metadata["description"]) > 170:
                logger.warning(
                    f"Description too long ({len(metadata['description'])}), truncating"
                )
                metadata["description"] = metadata["description"][:160].rsplit(" ", 1)[
                    0
                ]

            # Add cost tracking from OpenAI response (optional)
            metadata["cost_usd"] = response.get("cost_usd", 0.0)
            metadata["tokens_used"] = response.get("tokens_used", 0)

            # Log with optional cost tracking
            cost_msg = (
                f"cost: ${metadata['cost_usd']:.6f}"
                if metadata["cost_usd"] > 0
                else "cost: N/A"
            )
            logger.info(
                f"Generated metadata: {metadata['title']} "
                f"({cost_msg}, tokens: {metadata['tokens_used']})"
            )
            return metadata

        except Exception as e:
            logger.error(f"OpenAI metadata generation failed: {e}")

            # Fallback to simple cleanup (no cost for fallback)
            cleaned_title = self._fallback_title_cleanup(title)
            return {
                "title": cleaned_title,
                "description": f"{cleaned_title}. Read more about this topic.",
                "language": "en" if title.isascii() else "unknown",
                "cost_usd": 0.0,
                "tokens_used": 0,
            }

    def _fallback_title_cleanup(self, title: str) -> str:
        """
        Fallback title cleanup if AI fails.

        Args:
            title: Original title

        Returns:
            str: Cleaned title

        Examples:
            >>> _fallback_title_cleanup("Gem.coop #technology #blockchain")
            'Gem.coop'
            >>> _fallback_title_cleanup("米政権内の対中強硬派に焦り")
            'Article'
        """
        # Remove hashtags
        title = re.sub(r"#\w+", "", title)

        # Remove emojis and special chars
        title = re.sub(r"[^\w\s\-\.]", "", title)

        # Clean up whitespace
        title = " ".join(title.split())

        # If nothing left or non-ASCII, use generic
        if not title or not title.isascii():
            return "Article"

        # Truncate to 60 chars
        if len(title) > 60:
            title = title[:57] + "..."

        return title or "Article"
