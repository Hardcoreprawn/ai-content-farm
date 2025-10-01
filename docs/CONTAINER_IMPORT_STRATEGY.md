# Import Strategy for Hyphenated Containers

## The Problem
- Container directories use hyphens: `site-generator`, `content-processor`, `content-collector`  
- Python modules can't be imported with hyphens: `from site-generator` ❌
- Need consistent import strategy that works in development and production

## **Recommended Solution: Hybrid Import Strategy**

### 1. **Intra-Container Imports** (Within same container)
Use **relative imports** or **direct imports** within the same container:

```python
# ✅ Within site-generator container
from blob_operations import download_blob_content
from rss_generation import generate_rss_feed

# OR relative imports (but only within same package)
from .blob_operations import download_blob_content  # Only if __init__.py exists
```

### 2. **Inter-Container Imports** (Between containers)  
Use **absolute imports** via `libs` or direct module loading:

```python
# ✅ From site-generator to content-processor
import importlib.util
import sys

# Load module dynamically
spec = importlib.util.spec_from_file_location(
    "content_processor.services.content_enricher", 
    "/app/containers/content-processor/services/content_enricher.py"
)
content_enricher = importlib.util.module_from_spec(spec)
```

### 3. **Shared Library Imports** (Always absolute)
```python
# ✅ Always works - shared libraries
from libs.storage import SimplifiedBlobClient
from libs.shared_models import StandardResponse
```

## **Implementation Strategy**

### For site-generator (Current Issue)
```python
# article_loading.py - Within container imports
from blob_operations import download_blob_content  # ✅ Same container

# main.py - External imports  
from libs import SecureErrorHandler  # ✅ Shared library
import importlib  # ✅ For cross-container if needed
```

### Container Structure Benefits
```
containers/
├── site-generator/           # Hyphen OK - not imported as module
│   ├── __init__.py          # Makes it a package
│   ├── main.py              # Entry point
│   ├── article_loading.py   # Imports: blob_operations (same container)
│   └── blob_operations.py   # Imports: libs.storage (shared)
├── content-processor/        # Hyphen OK - not imported as module  
├── content-collector/        # Hyphen OK - not imported as module
└── libs/                     # No hyphens - imported everywhere
```

## **Why This Works**

### ✅ **Development Environment**
- VS Code recognizes each container as separate Python package
- PYTHONPATH includes workspace root for `libs` imports
- Intra-container imports work normally

### ✅ **Container Deployment**  
- Each container runs independently with its own Python environment
- Intra-container imports work (same directory)
- `libs` copied into each container for shared functionality

### ✅ **Maintainability**
- Clear separation: internal vs external imports
- No complex import hacks or renaming needed
- Consistent with existing hyphenated naming

## **Docker Implementation**
```dockerfile
# Copy workspace libs into each container
COPY libs/ /app/libs/
COPY containers/site-generator/ /app/

# Set Python path to find libs
ENV PYTHONPATH="/app"

# Run from app directory
WORKDIR /app
CMD ["python", "main.py"]
```

## **VS Code Configuration**
Already implemented in `.vscode/settings.json` and `pyrightconfig.json` to support this pattern.

## **Testing Strategy**
```bash
# Test from container directory (mimics deployment)
cd containers/site-generator
PYTHONPATH=/workspaces/ai-content-farm python -m pytest tests/

# Test imports work
python -c "import article_loading; print('✅ Intra-container imports work')"
python -c "from libs.storage import SimplifiedBlobClient; print('✅ Shared library imports work')"
```

This hybrid approach is the **cleanest solution** because:
1. **No renaming required** - keeps existing hyphenated structure
2. **Follows Python conventions** - packages vs modules handled correctly  
3. **Works in all environments** - development, testing, production
4. **Scalable** - pattern works for any number of containers
5. **Clear boundaries** - internal vs external imports are obvious