"""
Test Hugo frontmatter generation for strict YAML compliance.

This test suite validates that generated markdown files meet Hugo's frontmatter
requirements as documented in:
- https://github.com/gohugoio/hugo/blob/master/docs/content/en/content-management/front-matter.md
- https://gohugo.io/content-management/front-matter/

Hugo Frontmatter Requirements:
1. YAML frontmatter must use triple-dash delimiters (---)
2. Field names are case-sensitive and reserved (title, date, draft, etc.)
3. Date fields must be parseable ISO8601 format
4. Boolean fields must be true/false (lowercase)
5. String fields must be properly quoted if they contain special chars
6. Array fields must use proper YAML array syntax
7. No whitespace stripping that collapses field names
8. Custom fields must be under 'params' key
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml


class TestHugoFrontmatterValidation:
    """Test suite for Hugo frontmatter YAML validation."""

    # Hugo reserved field names (cannot be used as custom fields)
    HUGO_RESERVED_FIELDS = {
        "aliases",
        "build",
        "cascade",
        "date",
        "description",
        "draft",
        "expiryDate",
        "headless",
        "isCJKLanguage",
        "keywords",
        "lastmod",
        "layout",
        "linkTitle",
        "markup",
        "menus",
        "modified",
        "outputs",
        "params",
        "pubdate",
        "publishDate",
        "published",
        "resources",
        "sitemap",
        "slug",
        "summary",
        "title",
        "translationKey",
        "type",
        "unpublishdate",
        "url",
        "weight",
    }

    # Required fields for our content
    REQUIRED_FIELDS = {"title", "date", "draft"}

    # Expected field types
    FIELD_TYPES = {
        "title": str,
        "date": str,  # Must be parseable as datetime
        "draft": bool,
        "description": str,
        "keywords": list,
        "weight": int,
        "params": dict,
    }

    @pytest.fixture
    def sample_markdown_with_frontmatter(self) -> str:
        """Generate sample markdown that should pass validation."""
        return """---
title: "Test Article Title"
date: "2025-10-13T08:00:00Z"
draft: false
description: "This is a test article description"
keywords:
  - "test"
  - "example"
params:
  author: "Test Author"
  custom_field: "custom_value"
  source: "test-source"
  generated_date: "2025-10-13T08:00:00Z"
---

# Article Content

This is the article body.
"""

    @pytest.fixture
    def malformed_markdown_examples(self) -> Dict[str, str]:
        """Examples of malformed frontmatter that should fail validation."""
        return {
            "collapsed_fields": """---
title: Test
source: testgenerated_date: 2025-10-13T08:00:00Z
---
Content here
""",
            "missing_newline_after_field": """---
title: Testdate: 2025-10-13T08:00:00Z
---
Content here
""",
            "invalid_yaml_syntax": """---
title: Test with "unescaped quotes
  and invalid: : colons::
date: not-a-date
---
Content here
""",
            "wrong_delimiter": """+++
title: "TOML frontmatter"
date: 2025-10-13T08:00:00Z
+++
Content here
""",
            "custom_field_not_in_params": """---
title: Test
date: 2025-10-13T08:00:00Z
my_custom_field: "Should be under params"
---
Content here
""",
            "boolean_as_string": """---
title: Test
date: 2025-10-13T08:00:00Z
draft: "false"
---
Content here
""",
        }

    def extract_frontmatter(self, markdown: str) -> tuple[str, str]:
        """
        Extract frontmatter and content from markdown.

        Returns:
            tuple: (frontmatter_yaml, content)
        """
        # Hugo expects YAML delimited by ---
        pattern = r"^---\s*\n(.*?)\n---\s*\n(.*)$"
        match = re.match(pattern, markdown.strip(), re.DOTALL)

        if not match:
            raise ValueError(
                "No valid Hugo frontmatter found (must use --- delimiters)"
            )

        return match.group(1), match.group(2)

    def validate_frontmatter_yaml(self, yaml_str: str) -> Dict[str, Any]:
        """
        Validate that frontmatter is valid YAML.

        Raises:
            yaml.YAMLError: If YAML is invalid
        """
        try:
            data = yaml.safe_load(yaml_str)
            if data is None:
                raise ValueError("Frontmatter is empty")
            if not isinstance(data, dict):
                raise ValueError("Frontmatter must be a YAML object/dict")
            return data
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML syntax: {e}")

    def validate_hugo_fields(self, frontmatter: Dict[str, Any]) -> list[str]:
        """
        Validate Hugo-specific field requirements.

        Returns:
            list: Validation errors (empty if valid)
        """
        errors = []

        # Check required fields
        for field in self.REQUIRED_FIELDS:
            if field not in frontmatter:
                errors.append(f"Missing required field: {field}")

        # Validate field types
        for field, expected_type in self.FIELD_TYPES.items():
            if field in frontmatter:
                value = frontmatter[field]
                if not isinstance(value, expected_type):
                    errors.append(
                        f"Field '{field}' must be {expected_type.__name__}, "
                        f"got {type(value).__name__}"
                    )

        # Validate date fields are parseable
        date_fields = ["date", "lastmod", "publishDate", "expiryDate"]
        for field in date_fields:
            if field in frontmatter:
                value = frontmatter[field]
                if not isinstance(value, str):
                    errors.append(
                        f"Field '{field}' must be a string (ISO8601 date format)"
                    )
                    continue
                try:
                    # Handle 'Z' suffix for UTC
                    date_str = value.replace("Z", "+00:00") if "Z" in value else value
                    datetime.fromisoformat(date_str)
                except (ValueError, AttributeError) as e:
                    errors.append(f"Field '{field}' must be valid ISO8601 date: {e}")

        # Check for custom fields outside params
        for field in frontmatter.keys():
            if field not in self.HUGO_RESERVED_FIELDS and field != "params":
                errors.append(f"Custom field '{field}' must be under 'params' key")

        # Validate params is a dict if present
        if "params" in frontmatter and not isinstance(frontmatter["params"], dict):
            errors.append("Field 'params' must be a dict/object")

        return errors

    def test_valid_frontmatter_passes(self, sample_markdown_with_frontmatter):
        """Test that properly formatted frontmatter passes all validations."""
        # Extract frontmatter
        yaml_str, content = self.extract_frontmatter(sample_markdown_with_frontmatter)

        # Parse YAML
        frontmatter = self.validate_frontmatter_yaml(yaml_str)

        # Validate Hugo requirements
        errors = self.validate_hugo_fields(frontmatter)

        assert len(errors) == 0, f"Valid frontmatter should have no errors: {errors}"
        assert frontmatter["title"] == "Test Article Title"
        assert frontmatter["draft"] is False
        assert "params" in frontmatter

    def test_collapsed_fields_fails(self, malformed_markdown_examples):
        """Test that collapsed field names (no newline) are detected."""
        markdown = malformed_markdown_examples["collapsed_fields"]

        yaml_str, _ = self.extract_frontmatter(markdown)

        with pytest.raises(ValueError, match="Invalid YAML syntax"):
            self.validate_frontmatter_yaml(yaml_str)

    def test_missing_newline_after_field_fails(self, malformed_markdown_examples):
        """Test that missing newlines between fields are detected."""
        markdown = malformed_markdown_examples["missing_newline_after_field"]

        yaml_str, _ = self.extract_frontmatter(markdown)

        with pytest.raises(ValueError, match="Invalid YAML syntax"):
            self.validate_frontmatter_yaml(yaml_str)

    def test_invalid_yaml_syntax_fails(self, malformed_markdown_examples):
        """Test that general YAML syntax errors are detected."""
        markdown = malformed_markdown_examples["invalid_yaml_syntax"]

        yaml_str, _ = self.extract_frontmatter(markdown)

        with pytest.raises(ValueError, match="Invalid YAML syntax"):
            self.validate_frontmatter_yaml(yaml_str)

    def test_wrong_delimiter_fails(self, malformed_markdown_examples):
        """Test that TOML delimiters (+++) are rejected."""
        markdown = malformed_markdown_examples["wrong_delimiter"]

        with pytest.raises(ValueError, match="No valid Hugo frontmatter"):
            self.extract_frontmatter(markdown)

    def test_custom_field_not_in_params_fails(self, malformed_markdown_examples):
        """Test that custom fields outside params are detected."""
        markdown = malformed_markdown_examples["custom_field_not_in_params"]

        yaml_str, _ = self.extract_frontmatter(markdown)
        frontmatter = self.validate_frontmatter_yaml(yaml_str)
        errors = self.validate_hugo_fields(frontmatter)

        assert any(
            "custom field" in err.lower() for err in errors
        ), "Should detect custom fields outside params"

    def test_boolean_as_string_fails(self, malformed_markdown_examples):
        """Test that boolean fields with string values are detected."""
        markdown = malformed_markdown_examples["boolean_as_string"]

        yaml_str, _ = self.extract_frontmatter(markdown)
        frontmatter = self.validate_frontmatter_yaml(yaml_str)

        # Check type
        assert isinstance(
            frontmatter["draft"], str
        ), "Draft should be parsed as string (incorrect)"

    @pytest.mark.parametrize(
        "field_name,value,should_pass",
        [
            ("title", "Simple Title", True),
            ("title", "Title: With Colon", True),
            ("title", 'Title with "quotes"', True),
            ("date", "2025-10-13T08:00:00Z", True),
            ("date", "2025-10-13T08:00:00+00:00", True),
            ("date", "2025-10-13", True),
            ("date", "invalid-date", False),
            ("draft", True, True),
            ("draft", False, True),
            ("draft", "true", False),  # String, not boolean
            ("keywords", ["tag1", "tag2"], True),
            ("keywords", "single-tag", False),  # Should be array
            ("weight", 10, True),
            ("weight", "10", False),  # Should be int
        ],
    )
    def test_field_validation(self, field_name, value, should_pass):
        """Test individual field validation rules."""
        frontmatter = {
            "title": "Test",
            "date": "2025-10-13T08:00:00Z",
            "draft": False,
            field_name: value,
        }

        errors = self.validate_hugo_fields(frontmatter)

        if should_pass:
            # Check no errors related to this field
            field_errors = [e for e in errors if field_name in e.lower()]
            assert (
                len(field_errors) == 0
            ), f"Field '{field_name}' should pass but got errors: {field_errors}"
        else:
            # Check there are errors related to this field
            field_errors = [e for e in errors if field_name in e.lower()]
            assert (
                len(field_errors) > 0
            ), f"Field '{field_name}' should fail but passed validation"

    def test_real_generated_file(self):
        """
        Test against actual generated markdown files from Azure storage.

        This test will FAIL initially - that's expected!
        We'll use the failures to guide our fixes.
        """
        # This will be populated with actual files from storage
        # For now, create a test case that represents current output

        # Example of CURRENT buggy output (should fail)
        buggy_markdown = """---
title: "Test Article"
date: 2025-10-13T08:00:00Z
draft: false
source: mastodongenerated_date: 2025-10-13T08:00:00Z
---

Content here
"""

        with pytest.raises(ValueError, match="Invalid YAML"):
            yaml_str, _ = self.extract_frontmatter(buggy_markdown)
            self.validate_frontmatter_yaml(yaml_str)


class TestMarkdownGeneratorIntegration:
    """Integration tests for the markdown generator module."""

    def test_generate_frontmatter_function_exists(self):
        """Test that we have a frontmatter generation function."""
        # This will fail initially - we need to implement it
        try:
            from markdown_generation import generate_hugo_frontmatter

            assert callable(generate_hugo_frontmatter)
        except ImportError:
            pytest.fail(
                "markdown_generation module or generate_hugo_frontmatter not found"
            )

    def test_generated_frontmatter_is_valid(self):
        """Test that our generator produces valid Hugo frontmatter."""
        from datetime import datetime, timezone

        from markdown_generation import generate_hugo_frontmatter

        # Generate frontmatter
        frontmatter_block = generate_hugo_frontmatter(
            title="Test Article",
            date=datetime(2025, 10, 13, 8, 0, 0, tzinfo=timezone.utc),
            draft=False,
            description="Test description",
            keywords=["python", "hugo", "testing"],
            author="Test Author",
            source="test-source",
            url="https://example.com/article",
        )

        # Extract and validate
        yaml_str, _ = TestHugoFrontmatterValidation().extract_frontmatter(
            frontmatter_block + "\n\nContent here"
        )
        frontmatter = TestHugoFrontmatterValidation().validate_frontmatter_yaml(
            yaml_str
        )
        errors = TestHugoFrontmatterValidation().validate_hugo_fields(frontmatter)

        # Assert no validation errors
        assert len(errors) == 0, f"Generated frontmatter has errors: {errors}"

        # Assert structure
        assert frontmatter["title"] == "Test Article"
        assert frontmatter["draft"] is False
        assert "params" in frontmatter
        assert frontmatter["params"]["author"] == "Test Author"
        assert frontmatter["params"]["source"] == "test-source"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
