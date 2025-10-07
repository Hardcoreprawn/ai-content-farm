# Quick Start: Site Generator Split Implementation

**Ready to start coding?** Follow this guide to begin Phase 1.

---

## 🚀 Pre-Implementation Setup

### 1. Create Feature Branch
```bash
cd /workspaces/ai-content-farm

# Ensure you're on main and up to date
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/split-site-generator

# Confirm branch
git branch
```

### 2. Install Development Tools
```bash
# Ensure development dependencies installed
pip install black flake8 mypy pytest pytest-cov pytest-asyncio pre-commit

# Set up pre-commit hooks (optional but recommended)
cat > .pre-commit-config.yaml << 'EOF'
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
EOF

pre-commit install
```

### 3. Create Directory Structure
```bash
# Create markdown-generator structure
mkdir -p containers/markdown-generator/{tests,templates}

# Create site-builder structure
mkdir -p containers/site-builder/{tests,templates}

# Verify structure
tree containers/markdown-generator containers/site-builder
```

---

## 📝 Phase 1: Markdown Generator (Day 1)

### Step 1: Core Files

#### Create `containers/markdown-generator/requirements.txt`
```bash
cat > containers/markdown-generator/requirements.txt << 'EOF'
fastapi==0.115.0
uvicorn[standard]==0.30.6
pydantic==2.9.2
pyyaml==6.0.2
azure-storage-blob==12.23.1
azure-identity==1.19.0
pytest==8.3.3
pytest-asyncio==0.24.0
pytest-cov==5.0.0
httpx==0.27.2
EOF
```

#### Create `containers/markdown-generator/models.py`
```bash
cat > containers/markdown-generator/models.py << 'EOF'
"""
Markdown Generator Data Models

Pydantic models for request/response validation.
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class MarkdownGenerationRequest(BaseModel):
    """Request to generate markdown from article."""
    
    blob_path: Optional[str] = Field(
        None,
        description="Path to JSON article in blob storage"
    )
    article_data: Optional[Dict[str, Any]] = Field(
        None,
        description="Article data directly provided"
    )
    force_regenerate: bool = Field(
        False,
        description="Force regeneration even if markdown exists"
    )


class MarkdownGenerationResponse(BaseModel):
    """Response from markdown generation."""
    
    status: str = Field(..., description="success or error")
    markdown_path: Optional[str] = Field(
        None,
        description="Path to generated markdown"
    )
    article_id: str = Field(..., description="Article identifier")
    processing_time_ms: float = Field(
        ...,
        description="Processing time in milliseconds"
    )
    error: Optional[str] = Field(None, description="Error message if failed")


class BatchGenerationRequest(BaseModel):
    """Request to generate markdown for multiple articles."""
    
    blob_paths: Optional[List[str]] = Field(
        None,
        description="List of article blob paths"
    )
    discover_articles: bool = Field(
        False,
        description="Auto-discover articles from container"
    )
    max_articles: int = Field(100, description="Maximum articles to process")
    force_regenerate: bool = Field(False, description="Force regeneration")


class GenerationStatus(BaseModel):
    """Current generation status and metrics."""
    
    total_generated: int = Field(
        ...,
        description="Total markdown files generated"
    )
    total_errors: int = Field(..., description="Total generation errors")
    last_generation: Optional[datetime] = Field(
        None,
        description="Last generation timestamp"
    )
    queue_depth: int = Field(0, description="Current queue depth")
EOF
```

#### Create `containers/markdown-generator/config.py`
```bash
cat > containers/markdown-generator/config.py << 'EOF'
"""
Markdown Generator Configuration

Environment-based configuration management.
"""
import os
from typing import Dict, Any


def get_config() -> Dict[str, Any]:
    """
    Get configuration from environment variables.
    
    Returns:
        Configuration dictionary
    """
    return {
        # Azure Storage
        "AZURE_STORAGE_ACCOUNT_NAME": os.getenv(
            "AZURE_STORAGE_ACCOUNT_NAME",
            ""
        ),
        "AZURE_CLIENT_ID": os.getenv("AZURE_CLIENT_ID"),
        
        # Container Names
        "PROCESSED_CONTENT_CONTAINER": os.getenv(
            "PROCESSED_CONTENT_CONTAINER",
            "processed-content"
        ),
        "MARKDOWN_CONTENT_CONTAINER": os.getenv(
            "MARKDOWN_CONTENT_CONTAINER",
            "markdown-content"
        ),
        
        # Queue Configuration
        "QUEUE_NAME": os.getenv(
            "QUEUE_NAME",
            "markdown-generation-requests"
        ),
        "SITE_BUILD_QUEUE": os.getenv(
            "SITE_BUILD_QUEUE",
            "site-build-requests"
        ),
        
        # Processing Settings
        "MAX_BATCH_SIZE": int(os.getenv("MAX_BATCH_SIZE", "10")),
        "ENABLE_AUTO_TRIGGER": os.getenv(
            "ENABLE_AUTO_TRIGGER",
            "true"
        ).lower() == "true",
    }


def validate_config(config: Dict[str, Any]) -> None:
    """
    Validate required configuration values.
    
    Args:
        config: Configuration dictionary
        
    Raises:
        ValueError: If required configuration is missing
    """
    required_keys = [
        "AZURE_STORAGE_ACCOUNT_NAME",
        "PROCESSED_CONTENT_CONTAINER",
        "MARKDOWN_CONTENT_CONTAINER",
        "QUEUE_NAME"
    ]
    
    missing = [key for key in required_keys if not config.get(key)]
    if missing:
        raise ValueError(f"Missing required configuration: {missing}")
EOF
```

### Step 2: Verify Files
```bash
# Check file sizes
wc -l containers/markdown-generator/*.py

# Should see:
# ~100 models.py
# ~100 config.py

# Format with Black
cd containers/markdown-generator
black *.py

# Check PEP8 compliance
flake8 *.py --max-line-length=88

# Run type checking
mypy *.py --strict
```

### Step 3: Create Dockerfile
```bash
cat > containers/markdown-generator/Dockerfile << 'EOF'
FROM python:3.11-slim

# Security: Create non-root user
RUN useradd --create-home --shell /bin/bash app

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=app:app . .

# Copy shared libraries from monorepo
COPY --chown=app:app ../../libs /app/libs

# Switch to non-root user
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Start application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF
```

### Step 4: Test Setup
```bash
# Create initial test file
mkdir -p containers/markdown-generator/tests

cat > containers/markdown-generator/tests/conftest.py << 'EOF'
"""
Test Fixtures for Markdown Generator

Provides reusable test fixtures and mock objects.
"""
import pytest
from typing import Dict, Any


@pytest.fixture
def sample_article_data() -> Dict[str, Any]:
    """Sample article data for testing."""
    return {
        "topic_id": "test-123",
        "title": "Test Article Title",
        "content": "This is the article content.",
        "published_date": "2025-10-07T12:00:00Z",
        "tags": ["test", "article"],
        "source": {
            "name": "reddit",
            "url": "https://example.com/article"
        }
    }
EOF

# Test that pytest can discover tests
cd containers/markdown-generator
pytest --collect-only
```

### Step 5: First Commit
```bash
git add containers/markdown-generator/
git commit -m "feat: markdown-generator scaffolding

- Add models.py with Pydantic validation
- Add config.py with environment configuration
- Add Dockerfile with non-root user
- Add requirements.txt with dependencies
- Add initial test fixtures

Part of #XXX - Split site-generator"
```

---

## 📋 Daily Progress Checklist

### Day 1 Morning: Scaffolding
- [x] Create directory structure
- [x] Add models.py (~100 lines)
- [x] Add config.py (~100 lines)
- [x] Add Dockerfile
- [x] Add requirements.txt
- [x] First commit

### Day 1 Afternoon: Core Logic
- [ ] Implement `markdown_processor.py` (~250 lines)
  - [ ] MarkdownProcessor class
  - [ ] generate_markdown method
  - [ ] Helper methods for frontmatter, filename, etc.
- [ ] Implement `main.py` (~150 lines)
  - [ ] FastAPI app
  - [ ] API endpoints
  - [ ] Health check
- [ ] Format and validate (black, flake8, mypy)
- [ ] Second commit

### Day 2 Morning: Site Builder
- [ ] Repeat Day 1 morning for site-builder
- [ ] Adapt models for site building
- [ ] Create site_builder.py (~300 lines)
- [ ] Create index_manager.py (~150 lines)

### Day 2 Afternoon: Integration
- [ ] Connect both containers to shared libs
- [ ] Test basic functionality locally
- [ ] Verify Docker builds
- [ ] Third commit

---

## 🧪 Testing as You Go

### After Each Component
```bash
# Format code
black .

# Check style
flake8 . --max-line-length=88

# Type check
mypy . --strict

# Run tests (as you write them)
pytest tests/ -v

# Check coverage
pytest tests/ --cov --cov-report=term-missing
```

### Manual Testing
```bash
# Start development server
cd containers/markdown-generator
uvicorn main:app --reload --port 8000

# In another terminal, test health
curl http://localhost:8000/health

# Test status
curl http://localhost:8000/api/markdown/status

# Test generation (when implemented)
curl -X POST http://localhost:8000/api/markdown/generate \
  -H "Content-Type: application/json" \
  -d '{
    "article_data": {
      "title": "Test Article",
      "content": "Test content"
    }
  }'
```

---

## 📊 Progress Tracking

### Create GitHub Issue
```bash
# Use the template from GITHUB_ISSUE_SITE_GENERATOR_SPLIT.md
# Or use GitHub CLI:

gh issue create \
  --title "Split site-generator into specialized containers" \
  --body-file docs/GITHUB_ISSUE_SITE_GENERATOR_SPLIT.md \
  --label "enhancement,infrastructure,containers" \
  --assignee "@me"
```

### Update Issue Progress
After each major milestone:
```bash
# Comment on issue
gh issue comment XXX --body "✅ Day 1 complete: markdown-generator scaffolding done"

# Update checklist in issue description
gh issue edit XXX --body "$(cat updated_description.md)"
```

---

## 🆘 Troubleshooting

### Import Errors
```bash
# If you get "No module named 'libs'":
# Add parent directory to Python path
export PYTHONPATH="/workspaces/ai-content-farm:$PYTHONPATH"

# Or in VS Code, add to .vscode/settings.json:
{
  "python.analysis.extraPaths": [
    "${workspaceFolder}"
  ]
}
```

### Type Checking Issues
```bash
# If mypy complains about missing type stubs:
pip install types-pyyaml types-requests

# If you need to ignore a specific line:
result = complex_function()  # type: ignore[misc]
```

### Test Discovery
```bash
# If pytest can't find tests:
cd containers/markdown-generator
pytest tests/ -v

# Explicitly run specific test:
pytest tests/test_outcomes.py::test_markdown_generated -v
```

---

## 📚 Reference Documents

Keep these open while coding:

1. **Implementation Plan**: `docs/SITE_GENERATOR_SPLIT_IMPLEMENTATION_PLAN.md`
2. **Code Standards**: `docs/CODE_STANDARDS_SITE_GENERATOR_SPLIT.md`
3. **Architecture Decision**: `docs/SITE_GENERATOR_ARCHITECTURE_DECISION.md`
4. **PEP8 Guide**: https://pep8.org/

---

## ✅ End of Day 1 Checklist

Before you finish for the day:

- [ ] All code committed to feature branch
- [ ] Commit messages follow convention
- [ ] Code formatted with Black
- [ ] PEP8 compliant (flake8 passes)
- [ ] Type hints complete (mypy passes)
- [ ] Files under 500 lines each
- [ ] Tests written (even if skeleton)
- [ ] GitHub issue updated with progress
- [ ] Tomorrow's tasks identified

---

## 🚀 Next Steps

**Day 2**: Continue with site-builder container  
**Day 3**: Write comprehensive unit tests  
**Day 4**: Integration testing and fixes  
**Day 5**: Infrastructure (Terraform)

**Questions?** Check the full implementation plan or ask for clarification.

---

*Let's build something great! 🎉*
