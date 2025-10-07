# Code Standards for Site Generator Split

**Date:** October 7, 2025  
**Purpose:** Enforce consistent, high-quality code across new containers

---

## 🎯 Core Principles

1. **PEP8 Compliance**: All code follows Python Enhancement Proposal 8
2. **Type Safety**: Complete type hints on all functions and methods
3. **File Size Limits**: Max 500 lines per file (including docstrings)
4. **No Inline Exports**: All imports at module top, no `from x import *`
5. **Outcome-Based Tests**: Test WHAT happens, not HOW it happens

---

## 📏 PEP8 Standards

### Imports
```python
# ✅ GOOD: Grouped and organized
import os
import sys
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from libs.simplified_blob_client import SimplifiedBlobClient
from libs.queue_client import QueueMessageModel

# ❌ BAD: Wildcard imports
from libs.queue_client import *

# ❌ BAD: Inline imports
def process():
    from libs.queue_client import get_queue_client  # Don't do this
```

### Naming Conventions
```python
# ✅ GOOD: Clear, descriptive names
class MarkdownProcessor:
    """Process markdown generation."""
    
    def generate_markdown(self, request: MarkdownGenerationRequest) -> str:
        """Generate markdown from article data."""
        pass

# Module-level constants
MAX_BATCH_SIZE: int = 100
DEFAULT_THEME: str = "minimal"

# Private methods
def _validate_article_data(self, data: Dict[str, Any]) -> None:
    """Private helper for validation."""
    pass

# ❌ BAD: Unclear or misleading names
def proc(r):  # What does this do?
    pass

def generateMarkdown(request):  # Use snake_case, not camelCase
    pass
```

### Type Hints (Required)
```python
# ✅ GOOD: Complete type hints
from typing import Dict, Any, Optional, List

def process_article(
    article_data: Dict[str, Any],
    force_regenerate: bool = False
) -> Optional[str]:
    """
    Process article and return markdown path.
    
    Args:
        article_data: Article metadata and content
        force_regenerate: Force regeneration of existing markdown
        
    Returns:
        Path to generated markdown, or None if failed
    """
    pass

# ✅ GOOD: Pydantic models for complex types
class MarkdownGenerationRequest(BaseModel):
    """Request for markdown generation."""
    blob_path: Optional[str] = None
    article_data: Optional[Dict[str, Any]] = None
    force_regenerate: bool = False

# ❌ BAD: No type hints
def process_article(article_data, force_regenerate=False):
    pass

# ❌ BAD: Incomplete type hints
def process_article(article_data: dict) -> str:  # Use Dict[str, Any]
    pass
```

### Docstrings (Required for Public Functions)
```python
# ✅ GOOD: Complete docstring with Args, Returns, Raises
async def generate_markdown(
    self,
    article_data: Dict[str, Any]
) -> MarkdownGenerationResponse:
    """
    Generate markdown from JSON article data.
    
    Creates markdown file with YAML frontmatter containing article
    metadata. Saves to blob storage and triggers site build queue.
    
    Args:
        article_data: Dictionary containing article fields:
            - title (required): Article title
            - content (required): Article body
            - published_date (optional): Publication timestamp
            - tags (optional): List of article tags
            
    Returns:
        MarkdownGenerationResponse with status and markdown path
        
    Raises:
        ValueError: If required fields are missing
        StorageError: If blob storage operation fails
        
    Example:
        >>> article = {"title": "Test", "content": "Content"}
        >>> result = await processor.generate_markdown(article)
        >>> print(result.markdown_path)
        'test-article.md'
    """
    pass

# ❌ BAD: Missing or incomplete docstring
def generate_markdown(self, article_data):
    """Generates markdown."""  # Too brief, no details
    pass
```

### Line Length & Formatting
```python
# ✅ GOOD: Max 88 characters (Black default)
result = await self.blob_client.upload_text(
    container=self.config["MARKDOWN_CONTENT_CONTAINER"],
    blob_name=filename,
    text=markdown_content
)

# ✅ GOOD: Multi-line strings
error_message = (
    f"Failed to generate markdown for article {article_id}. "
    f"Required fields missing: {missing_fields}. "
    f"Please provide all required article data."
)

# ❌ BAD: Lines too long
result = await self.blob_client.upload_text(container=self.config["MARKDOWN_CONTENT_CONTAINER"], blob_name=filename, text=markdown_content)
```

### Function Length
```python
# ✅ GOOD: Single responsibility, focused function
async def generate_markdown(
    self,
    request: MarkdownGenerationRequest
) -> MarkdownGenerationResponse:
    """Generate markdown from article."""
    article_data = await self._load_article(request)
    self._validate_article_data(article_data)
    markdown_content = self._create_markdown(article_data)
    filename = self._generate_filename(article_data)
    path = await self._save_markdown(filename, markdown_content)
    return MarkdownGenerationResponse(status="success", markdown_path=path)

# ❌ BAD: Function doing too much (>30 lines)
async def generate_markdown(self, request):
    # 100+ lines of inline logic
    # Should be broken into helper functions
    pass
```

---

## 🏗️ File Organization

### Max 500 Lines Per File
```python
# If a file exceeds 500 lines, split into logical modules:

# markdown_processor.py (250 lines)
# - MarkdownProcessor class
# - Core generation logic

# markdown_helpers.py (150 lines)
# - Frontmatter generation
# - Filename sanitization
# - Content formatting

# markdown_validation.py (100 lines)
# - Article data validation
# - Schema checking
# - Error messages
```

### Module Structure Template
```python
"""
Module Name

Brief description of module purpose and responsibilities.

Classes:
    ClassName: Brief description

Functions:
    function_name: Brief description
"""

# Standard library imports
import os
import sys
from datetime import datetime
from typing import Dict, Any

# Third-party imports
from fastapi import FastAPI
from pydantic import BaseModel

# Local imports
from libs.simplified_blob_client import SimplifiedBlobClient
from models import MarkdownGenerationRequest

# Module-level constants
MAX_RETRIES: int = 3
DEFAULT_TIMEOUT: int = 30

# Logger setup
logger = logging.getLogger(__name__)


class MainClass:
    """Primary class for module functionality."""
    
    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize with configuration."""
        pass


def public_function() -> None:
    """Public module function."""
    pass


def _private_helper() -> None:
    """Private helper function."""
    pass
```

---

## 🧪 Test Standards

### Outcome-Based Testing
```python
# ✅ GOOD: Test observable outcomes
@pytest.mark.asyncio
async def test_markdown_generated_from_json_article(
    processor,
    sample_article_data,
    mock_blob_client
):
    """
    GIVEN a valid JSON article
    WHEN markdown generation is requested
    THEN markdown file should be created in blob storage
    AND frontmatter should contain article metadata
    AND site build should be triggered
    """
    # Arrange
    request = MarkdownGenerationRequest(article_data=sample_article_data)
    
    # Act
    result = await processor.generate_markdown(request)
    
    # Assert - Observable outcomes
    assert result.status == "success"
    assert result.markdown_path is not None
    assert mock_blob_client.upload_text.called
    
    # Verify file content (outcome, not method)
    uploaded_content = mock_blob_client.upload_text.call_args[1]["text"]
    assert "---" in uploaded_content
    assert sample_article_data["title"] in uploaded_content


# ❌ BAD: Testing implementation details
def test_internal_method_called(processor, mocker):
    """Don't test that internal methods were called."""
    spy = mocker.spy(processor, '_validate_article_data')
    result = processor.generate_markdown(request)
    assert spy.called  # Testing HOW, not WHAT
```

### Test Naming
```python
# ✅ GOOD: Descriptive test names
def test_markdown_not_regenerated_if_exists():
    pass

def test_error_handling_for_invalid_article():
    pass

def test_queue_message_triggers_site_build():
    pass

# ❌ BAD: Unclear test names
def test_case_1():
    pass

def test_markdown():
    pass
```

### Test Structure (AAA Pattern)
```python
@pytest.mark.asyncio
async def test_feature_name():
    """
    GIVEN initial conditions
    WHEN action is performed
    THEN expected outcomes occur
    """
    # Arrange - Set up test data
    article_data = {"title": "Test", "content": "Content"}
    request = MarkdownGenerationRequest(article_data=article_data)
    
    # Act - Perform the action
    result = await processor.generate_markdown(request)
    
    # Assert - Verify outcomes
    assert result.status == "success"
    assert result.markdown_path is not None
```

---

## 🛠️ Tooling & Automation

### Required Tools
```bash
# Install dev dependencies
pip install black flake8 mypy pytest pytest-cov pytest-asyncio

# Format code (88 char line length)
black containers/markdown-generator/

# Check style compliance
flake8 containers/markdown-generator/ --max-line-length=88

# Type checking
mypy containers/markdown-generator/ --strict

# Run tests with coverage
pytest containers/markdown-generator/tests/ -v --cov --cov-report=html
```

### Pre-commit Hooks
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.8.0
    hooks:
      - id: black
        language_version: python3.11
        
  - repo: https://github.com/pycqa/flake8
    rev: 7.1.1
    hooks:
      - id: flake8
        args: ['--max-line-length=88', '--extend-ignore=E203,W503']
        
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.11.2
    hooks:
      - id: mypy
        additional_dependencies: [types-pyyaml, types-requests]
```

### VS Code Settings
```json
{
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.flake8Args": ["--max-line-length=88"],
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "editor.rulers": [88],
  "[python]": {
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  }
}
```

---

## ✅ Validation Checklist

Before committing code, verify:

- [ ] **PEP8 Compliance**: `black` and `flake8` pass with no errors
- [ ] **Type Hints**: `mypy --strict` passes
- [ ] **File Size**: All files < 500 lines (check with `wc -l`)
- [ ] **No Inline Exports**: All imports at top, no wildcards
- [ ] **Docstrings**: All public functions have complete docstrings
- [ ] **Tests Pass**: `pytest` passes with 90%+ coverage
- [ ] **Test Quality**: Tests focus on outcomes, not implementation
- [ ] **Naming**: Clear, descriptive names following conventions
- [ ] **Error Handling**: Proper exception handling with logging
- [ ] **Security**: No hardcoded secrets, proper input validation

---

## 📚 References

- [PEP 8 - Style Guide for Python Code](https://pep8.org/)
- [PEP 484 - Type Hints](https://peps.python.org/pep-0484/)
- [Black Code Formatter](https://black.readthedocs.io/)
- [pytest Documentation](https://docs.pytest.org/)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/best-practices/)

---

**Enforcement:**
- All PRs must pass automated checks (Black, Flake8, MyPy, pytest)
- Code review will verify compliance with these standards
- CI/CD pipeline will reject non-compliant code

*Last Updated: October 7, 2025*
