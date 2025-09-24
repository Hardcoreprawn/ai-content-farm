"""
Unit tests for theme_security module
Tests ContentSanitizer and ThemeFileValidator classes
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest
from theme_security import ContentSanitizer, ThemeFileValidator, create_security_headers

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestContentSanitizer:
    """Test cases for ContentSanitizer class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.sanitizer = ContentSanitizer()

    def test_sanitize_html_removes_script_tags(self):
        """Test that script tags are removed from HTML content"""
        dirty_html = '<p>Safe content</p><script>alert("xss")</script>'
        clean_html = self.sanitizer.sanitize_html(dirty_html)

        assert "<script>" not in clean_html
        assert 'alert("xss")' not in clean_html
        assert "<p>Safe content</p>" in clean_html

    def test_sanitize_html_removes_dangerous_attributes(self):
        """Test that dangerous attributes like onclick are removed"""
        dirty_html = '<div onclick="alert(\'xss\')" class="safe">Content</div>'
        clean_html = self.sanitizer.sanitize_html(dirty_html)

        assert "onclick" not in clean_html
        assert 'class="safe"' in clean_html
        assert ">Content<" in clean_html

    def test_sanitize_html_preserves_safe_content(self):
        """Test that safe HTML content is preserved"""
        safe_html = '<div class="container"><p><strong>Bold</strong> text</p></div>'
        clean_html = self.sanitizer.sanitize_html(safe_html)

        assert clean_html == safe_html

    def test_sanitize_html_with_custom_tags(self):
        """Test sanitization with custom allowed tags"""
        sanitizer = ContentSanitizer(custom_tags=["article", "section"])
        html_content = (
            "<article><section>Content</section></article><script>bad</script>"
        )
        clean_html = sanitizer.sanitize_html(html_content)

        assert "<article>" in clean_html
        assert "<section>" in clean_html
        assert "<script>" not in clean_html

    def test_sanitize_html_with_custom_attributes(self):
        """Test sanitization with custom allowed attributes"""
        custom_attrs = {"div": ["data-test", "aria-label"]}
        sanitizer = ContentSanitizer(custom_attributes=custom_attrs)
        html_content = (
            '<div data-test="value" aria-label="test" onclick="bad">Content</div>'
        )
        clean_html = sanitizer.sanitize_html(html_content)

        assert 'data-test="value"' in clean_html
        assert 'aria-label="test"' in clean_html
        assert "onclick" not in clean_html

    def test_sanitize_css_removes_dangerous_properties(self):
        """Test that dangerous CSS properties are removed"""
        css_content = """
        .safe { color: blue; }
        .dangerous {
            background: url('javascript:alert("xss")');
            expression: alert('xss');
        }
        """
        clean_css = self.sanitizer.sanitize_css(css_content)

        assert "color: blue" in clean_css
        assert "javascript:" not in clean_css
        assert "expression:" not in clean_css

    def test_sanitize_css_preserves_safe_styles(self):
        """Test that safe CSS is preserved"""
        safe_css = """
        .container {
            display: flex;
            margin: 20px;
            color: #333;
        }
        """
        clean_css = self.sanitizer.sanitize_css(safe_css)

        assert "display: flex" in clean_css
        assert "margin: 20px" in clean_css
        assert "color: #333" in clean_css

    def test_create_secure_temp_directory(self):
        """Test that secure temporary directory is created correctly"""
        with (
            patch("tempfile.mkdtemp") as mock_mkdtemp,
            patch("theme_security.Path.chmod") as mock_chmod,
        ):
            mock_mkdtemp.return_value = "/tmp/secure_theme_123"

            temp_dir = self.sanitizer.create_secure_temp_directory()

            mock_mkdtemp.assert_called_once_with(prefix="secure_theme_")
            mock_chmod.assert_called_once_with(0o700)
            assert temp_dir == "/tmp/secure_theme_123"


class TestThemeFileValidator:
    """Test cases for ThemeFileValidator class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.validator = ThemeFileValidator()

    def test_validate_html_file_success(self):
        """Test successful validation of HTML file"""
        valid_html = (
            b"<html><head><title>Test</title></head><body>Content</body></html>"
        )
        result = self.validator.validate_file("template.html", valid_html)

        assert result["valid"] is True
        assert len(result["warnings"]) == 0
        assert len(result["errors"]) == 0

    def test_validate_html_file_with_warnings(self):
        """Test HTML validation with warnings"""
        html_with_warnings = b'<div><script>console.log("debug")</script></div>'
        result = self.validator.validate_file("template.html", html_with_warnings)

        assert result["valid"] is True  # Warnings don't make file invalid
        assert len(result["warnings"]) > 0
        assert any("script" in warning.lower() for warning in result["warnings"])

    def test_validate_css_file_success(self):
        """Test successful validation of CSS file"""
        valid_css = b".container { display: flex; margin: 20px; }"
        result = self.validator.validate_file("styles.css", valid_css)

        assert result["valid"] is True
        assert len(result["warnings"]) == 0
        assert len(result["errors"]) == 0

    def test_validate_css_file_with_dangerous_content(self):
        """Test CSS validation with dangerous content"""
        dangerous_css = b".bad { background: url(\"javascript:alert('xss')\"); }"
        result = self.validator.validate_file("styles.css", dangerous_css)

        assert len(result["warnings"]) > 0
        assert any("javascript:" in warning for warning in result["warnings"])

    def test_validate_js_file_success(self):
        """Test successful validation of JavaScript file"""
        valid_js = b'document.addEventListener("DOMContentLoaded", function() { console.log("loaded"); });'
        result = self.validator.validate_file("script.js", valid_js)

        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_validate_js_file_with_dangerous_content(self):
        """Test JavaScript validation with dangerous content"""
        dangerous_js = b'eval("alert(\'dangerous code\')"); document.write("<script>bad</script>");'
        result = self.validator.validate_file("script.js", dangerous_js)

        assert len(result["warnings"]) > 0
        assert any("eval" in warning.lower() for warning in result["warnings"])

    def test_validate_unsupported_file_type(self):
        """Test validation of unsupported file type"""
        result = self.validator.validate_file("image.png", b"binary data")

        assert result["valid"] is True  # Unsupported files pass through
        assert len(result["warnings"]) == 0
        assert len(result["errors"]) == 0

    @patch("theme_security.Path.exists")
    def test_validate_nonexistent_file(self, mock_exists):
        """Test validation of non-existent file"""
        mock_exists.return_value = False

        result = self.validator.validate_file("missing.html", b"")

        # Should handle gracefully without raising exceptions
        assert isinstance(result, dict)
        assert "valid" in result


class TestSecurityHeaders:
    """Test cases for security headers creation"""

    def test_create_security_headers_returns_dict(self):
        """Test that security headers function returns a dictionary"""
        headers = create_security_headers()

        assert isinstance(headers, dict)
        assert len(headers) > 0

    def test_create_security_headers_includes_csp(self):
        """Test that CSP header is included"""
        headers = create_security_headers()

        assert "Content-Security-Policy" in headers
        csp_value = headers["Content-Security-Policy"]
        assert "default-src" in csp_value
        assert "script-src" in csp_value

    def test_create_security_headers_includes_security_headers(self):
        """Test that essential security headers are included"""
        headers = create_security_headers()

        expected_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Referrer-Policy",
        ]

        for header in expected_headers:
            assert header in headers
            assert headers[header]  # Ensure not empty

    def test_create_security_headers_csp_values(self):
        """Test specific CSP directive values"""
        headers = create_security_headers()
        csp = headers["Content-Security-Policy"]

        # Check for safe default values
        assert "'self'" in csp
        assert "'unsafe-inline'" not in csp or "'unsafe-eval'" not in csp

        # Should include specific directives
        assert "img-src" in csp
        assert "style-src" in csp


@pytest.fixture
def temp_theme_file():
    """Fixture to create a temporary theme file"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
        f.write('<div class="theme-container"><p>Test theme content</p></div>')
        temp_path = f.name

    yield temp_path

    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


class TestIntegrationSecurity:
    """Integration tests for security module"""

    def test_sanitizer_validator_integration(self, temp_theme_file):
        """Test integration between sanitizer and validator"""
        # Read the temp file
        with open(temp_theme_file, "rb") as f:
            content = f.read()

        # Validate first
        validator = ThemeFileValidator()
        result = validator.validate_file(temp_theme_file, content)

        assert result["valid"] is True

        # Then sanitize
        sanitizer = ContentSanitizer()
        clean_html = sanitizer.sanitize_html(content.decode("utf-8"))

        assert '<div class="theme-container">' in clean_html
        assert "<p>" in clean_html
        assert "Test theme content" in clean_html

    def test_security_headers_with_sanitized_content(self):
        """Test that security headers work with sanitized content"""
        sanitizer = ContentSanitizer()
        headers = create_security_headers()

        # Simulate a request with sanitized content
        dangerous_content = '<script>alert("xss")</script><p>Safe content</p>'
        safe_content = sanitizer.sanitize_html(dangerous_content)

        # Verify content is safe
        assert "<script>" not in safe_content
        assert "<p>Safe content</p>" in safe_content

        # Verify headers provide protection
        assert "X-XSS-Protection" in headers
        assert headers["X-Content-Type-Options"] == "nosniff"
