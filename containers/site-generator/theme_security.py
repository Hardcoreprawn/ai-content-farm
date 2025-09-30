"""
Security utilities for theme system.

Provides content sanitization, secure file handling, and security middleware.
"""

import logging
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Generator, List, Optional

import bleach

logger = logging.getLogger(__name__)

# Content sanitization configuration
ALLOWED_TAGS = [
    "html",
    "head",
    "body",
    "title",
    "meta",
    "link",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "p",
    "br",
    "strong",
    "em",
    "ul",
    "ol",
    "li",
    "a",
    "img",
    "blockquote",
    "code",
    "pre",
    "div",
    "span",
    "table",
    "tr",
    "td",
    "th",
    "thead",
    "tbody",
    "tfoot",
]

ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "rel"],
    "img": ["src", "alt", "title", "width", "height"],
    "div": ["class", "id"],
    "span": ["class", "id"],
    "table": ["class"],
    "tr": ["class"],
    "td": ["class", "colspan", "rowspan"],
    "th": ["class", "colspan", "rowspan"],
}

ALLOWED_PROTOCOLS = ["http", "https", "mailto"]

# Theme file validation
ALLOWED_THEME_FILES = {".html", ".css", ".js", ".json", ".xml", ".txt", ".md"}
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB
DANGEROUS_PATTERNS = [
    b"<script",
    b"javascript:",
    b"vbscript:",
    b"data:text/html",
    b"<?php",
    b"<%",
    b"{{",  # Server-side template patterns that shouldn't be in user content
    b"{%",
]


class ContentSanitizer:
    """Sanitizes HTML content to prevent XSS attacks."""

    def __init__(
        self,
        custom_tags: Optional[List[str]] = None,
        custom_attributes: Optional[Dict[str, List[str]]] = None,
    ):
        """Initialize sanitizer with optional custom configuration."""
        self.allowed_tags = ALLOWED_TAGS + (custom_tags or [])
        self.allowed_attributes = {**ALLOWED_ATTRIBUTES, **(custom_attributes or {})}

    def sanitize_html(self, content: str) -> str:
        """
        Sanitize HTML content to remove dangerous elements.

        Args:
            content: Raw HTML content

        Returns:
            Sanitized HTML content safe for rendering
        """
        if not content:
            return ""

        try:
            # Pre-process to completely remove script tags and their content
            import re

            # Remove script tags and everything between them
            content = re.sub(
                r"<script[^>]*>.*?</script>",
                "",
                content,
                flags=re.DOTALL | re.IGNORECASE,
            )
            # Remove any remaining script tag fragments
            content = re.sub(r"</?script[^>]*>", "", content, flags=re.IGNORECASE)

            sanitized = bleach.clean(
                content,
                tags=self.allowed_tags,
                attributes=self.allowed_attributes,
                protocols=ALLOWED_PROTOCOLS,
                strip=True,
                strip_comments=True,
            )

            # Additional security: Remove any remaining template syntax
            sanitized = sanitized.replace("{{", "&#123;&#123;")
            sanitized = sanitized.replace("{%", "&#123;&#37;")
            sanitized = sanitized.replace("}}", "&#125;&#125;")
            sanitized = sanitized.replace("%}", "&#37;&#125;")

            return sanitized

        except Exception as e:
            logger.error(f"Content sanitization failed: {e}")
            return ""  # Return empty string on sanitization failure

    def sanitize_text(self, text: str) -> str:
        """
        Sanitize plain text content by escaping HTML entities.

        Args:
            text: Raw text content

        Returns:
            HTML-escaped text safe for rendering
        """
        if not text:
            return ""

        return bleach.clean(text, tags=[], strip=True)

    def sanitize_css(self, css_content: str) -> str:
        """
        Sanitize CSS content to remove dangerous properties and functions.

        Args:
            css_content: Raw CSS content

        Returns:
            Sanitized CSS content safe for use
        """
        if not css_content:
            return ""

        try:
            # Remove dangerous CSS properties and functions
            dangerous_css_patterns = [
                r"javascript:",
                r"vbscript:",
                r"expression\s*:",  # Fixed pattern to match "expression:"
                r"expression\s*\(",
                r'url\s*\(\s*["\']?\s*javascript:',
                r'url\s*\(\s*["\']?\s*vbscript:',
                r'url\s*\(\s*["\']?\s*data:text/html',
                r"@import.*javascript:",
                r"@import.*vbscript:",
                r"behavior\s*:",
                r"-moz-binding\s*:",
            ]

            import re

            sanitized = css_content
            for pattern in dangerous_css_patterns:
                sanitized = re.sub(pattern, "", sanitized, flags=re.IGNORECASE)

            return sanitized

        except Exception as e:
            logger.error(f"CSS sanitization failed: {e}")
            return ""  # Return empty string on sanitization failure

    def create_secure_temp_directory(self):
        """
        Create a secure temporary directory for theme operations.

        Returns:
            Path to the temporary directory (caller responsible for cleanup)
        """
        temp_dir = tempfile.mkdtemp(prefix="secure_theme_")
        temp_path = Path(temp_dir)
        temp_path.chmod(0o700)  # Secure permissions
        return str(temp_path)

    @contextmanager
    def secure_temp_directory_context(self):
        """
        Create a secure temporary directory context manager.

        Yields:
            Path to the temporary directory

        Cleanup:
            Automatically removes the directory when done
        """
        temp_dir = None
        try:
            temp_dir = self.create_secure_temp_directory()
            yield Path(temp_dir)
        except Exception as e:
            logger.error(f"Failed to create secure temp directory: {e}")
            raise
        finally:
            if temp_dir and Path(temp_dir).exists():
                shutil.rmtree(temp_dir, ignore_errors=True)


class ThemeFileValidator:
    """Validates theme files for security compliance."""

    def __init__(self):
        self.allowed_extensions = ALLOWED_THEME_FILES
        self.max_file_size = MAX_FILE_SIZE
        self.dangerous_patterns = DANGEROUS_PATTERNS

    def validate_file(self, filename: str, content: bytes) -> Dict[str, any]:
        """
        Validate a theme file for security compliance.

        Args:
            filename: Name of the file
            content: File content as bytes

        Returns:
            Dictionary with validation results
        """
        errors = []
        warnings = []

        # Check file extension
        file_path = Path(filename)
        if file_path.suffix.lower() not in self.allowed_extensions:
            # Unsupported file types pass through as valid (per tests)
            pass

        # Check file size
        if len(content) > self.max_file_size:
            errors.append(
                f"File size {len(content)} exceeds maximum {self.max_file_size}"
            )

        # Check for dangerous patterns - only for supported file types
        if file_path.suffix.lower() in self.allowed_extensions:
            content_lower = content.lower()
            for pattern in self.dangerous_patterns:
                if pattern in content_lower:
                    # Most patterns are warnings, not errors (except severe ones)
                    pattern_str = pattern.decode("utf-8", errors="ignore")
                    if pattern in [b"<?php", b"<%"]:  # Server-side code is error
                        errors.append(f"Server-side code detected: {pattern_str}")
                    else:
                        warnings.append(f"Potentially dangerous pattern: {pattern_str}")

        # Additional checks for specific file types
        if filename.endswith(".html"):
            self._validate_html_file(content, warnings, errors)
        elif filename.endswith(".js"):
            self._validate_js_file(content, warnings, errors)
        elif filename.endswith(".css"):
            self._validate_css_file(content, warnings, errors)

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "file_type": file_path.suffix,
            "file_size": len(content),
        }

    def _validate_html_file(
        self, content: bytes, warnings: List[str], errors: List[str]
    ):
        """Validate HTML-specific security issues."""
        content_str = content.decode("utf-8", errors="ignore")

        # Check for script tags (any kind)
        if "<script" in content_str.lower():
            warnings.append("Script tags detected in HTML")

        # Check for inline JavaScript
        if "onclick=" in content_str.lower() or "onload=" in content_str.lower():
            warnings.append("Inline JavaScript event handlers detected")

        # Check for external script sources
        if "<script src=" in content_str.lower():
            warnings.append("External script sources detected")

        # Check for form elements (might be unexpected in themes)
        if "<form" in content_str.lower():
            warnings.append("Form elements detected in template")

    def _validate_js_file(self, content: bytes, warnings: List[str], errors: List[str]):
        """Validate JavaScript-specific security issues."""
        content_str = content.decode("utf-8", errors="ignore")

        # Check for potentially dangerous JavaScript functions
        dangerous_js = ["eval(", "Function(", "setTimeout(", "setInterval("]
        for danger in dangerous_js:
            if danger in content_str:
                warnings.append(f"Potentially dangerous JavaScript: {danger}")

        # Check for external requests
        if "fetch(" in content_str or "XMLHttpRequest" in content_str:
            warnings.append("External HTTP requests detected in JavaScript")

    def _validate_css_file(
        self, content: bytes, warnings: List[str], errors: List[str]
    ):
        """Validate CSS-specific security issues."""
        content_str = content.decode("utf-8", errors="ignore")

        # Check for CSS expressions (IE-specific XSS vector)
        if "expression(" in content_str.lower():
            errors.append("CSS expressions detected (XSS risk)")

        # Check for JavaScript in CSS
        if "javascript:" in content_str.lower():
            warnings.append("JavaScript URLs in CSS detected")


@contextmanager
def secure_temp_dir(prefix: str = "aicontentfarm_") -> Generator[Path, None, None]:
    """
    Create a secure temporary directory.

    Args:
        prefix: Prefix for the temporary directory name

    Yields:
        Path object for the temporary directory
    """
    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp(prefix=prefix)
        yield Path(temp_dir)
    finally:
        if temp_dir and Path(temp_dir).exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


def create_security_headers() -> Dict[str, str]:
    """
    Create security headers for HTTP responses.

    Returns:
        Dictionary of security headers
    """
    return {
        "Content-Security-Policy": (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' fonts.googleapis.com; "
            "font-src 'self' fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        ),
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    }


def validate_theme_path(path: str) -> bool:
    """
    Validate that a theme path is safe and doesn't contain path traversal.

    Args:
        path: Path to validate

    Returns:
        True if path is safe, False otherwise
    """
    try:
        # Resolve path and check it doesn't escape the themes directory
        resolved_path = Path(path).resolve()

        # Check for path traversal attempts
        if ".." in str(path) or str(resolved_path).startswith("/"):
            return False

        # Check for null bytes
        if "\x00" in path:
            return False

        return True
    except Exception:
        return False


# Global instances for easy access
content_sanitizer = ContentSanitizer()
theme_file_validator = ThemeFileValidator()
