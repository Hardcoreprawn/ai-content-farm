# Monorepo Import Configuration - Complete Guide

## Summary
Fixed all imports in `content-processor` container to use **absolute imports** instead of relative imports, ensuring reliable operation across all contexts: local development, pytest, and CI/CD.

## Problem
Mixed import styles caused failures:
- `processor_operations.py` used **relative imports** (`from .models import ...`)
- `processing_operations.py` used **absolute imports** (`from models import ...`)
- Inconsistency caused import errors in different execution contexts

## Solution: Standardize on Absolute Imports

### Monorepo Structure
```
/workspaces/ai-content-farm/          # Project root
├── libs/                              # Shared libraries (in sys.path)
│   ├── blob_storage.py
│   ├── queue_client.py
│   └── ...
├── containers/
│   └── content-processor/            # Container directory (added to sys.path by conftest.py)
│       ├── models.py
│       ├── processor.py
│       ├── processor_operations.py
│       ├── processing_operations.py
│       ├── queue_operations.py       # Backward compat re-exports
│       ├── queue_message_builder.py  # Split module (166 lines)
│       ├── queue_client_operations.py # Split module (339 lines)
│       └── ...
└── conftest.py                        # Adds container dir to sys.path
```

### Import Rules (MANDATORY)

#### ✅ **Container Modules - Use Absolute Imports**
```python
# ✅ CORRECT - Works in all contexts
from models import TopicMetadata, ProcessorStatus
from processor_context import ProcessorContext
from session_state import SessionState
from queue_operations import trigger_markdown_for_article
```

#### ✅ **Shared Libraries - Use Absolute Imports with libs. prefix**
```python
# ✅ CORRECT - Works in all contexts
from libs.blob_storage import BlobStorageClient
from libs.queue_client import StorageQueueClient
```

#### ❌ **Relative Imports - DO NOT USE**
```python
# ❌ WRONG - Only works when imported as package
from .models import TopicMetadata
from .processor_context import ProcessorContext
```

### Why Absolute Imports Work

The `conftest.py` setup adds container directory to `sys.path`:

```python
# From containers/content-processor/conftest.py
root = Path(__file__).parent  # /workspaces/ai-content-farm/containers/content-processor
sys.path.insert(0, str(root))  # Add to sys.path

repo_root = root.parent.parent  # /workspaces/ai-content-farm
sys.path.insert(0, str(repo_root))  # Add to sys.path
```

This makes container modules importable by name, just like stdlib or third-party packages.

## Files Changed

### 1. processor_operations.py (376 lines)
**Changed**: All 9 local imports from relative → absolute
```python
# BEFORE:
from .models import ProcessingResult, ProcessorStatus, TopicMetadata
from .queue_operations import trigger_markdown_for_article

# AFTER:
from models import ProcessingResult, ProcessorStatus, TopicMetadata
from queue_operations import trigger_markdown_for_article
```

### 2. queue_operations.py (45 lines)
**Changed**: Re-export imports from relative → absolute
```python
# BEFORE:
from .queue_message_builder import create_queue_message
from .queue_client_operations import send_queue_message

# AFTER:
from queue_message_builder import create_queue_message
from queue_client_operations import send_queue_message
```

### 3. queue_client_operations.py (339 lines)
**Changed**: Cross-module import from relative → absolute
```python
# BEFORE:
from .queue_message_builder import create_markdown_trigger_message

# AFTER:
from queue_message_builder import create_markdown_trigger_message
```

### 4. dependencies.py
**Changed**: Commented out missing `ExternalAPIClient` import (deprecated during functional refactoring)
```python
# BEFORE:
from external_api_client import ExternalAPIClient

# AFTER:
# DEPRECATED: ExternalAPIClient was part of OOP architecture, removed during functional refactoring
# from external_api_client import ExternalAPIClient
```

## Verification

### Test Script Created: `test_imports.py`
Comprehensive test covering:
1. ✅ Shared libs imports (`libs.blob_storage`, `libs.queue_client`)
2. ✅ Container module imports (`models`, `processor_context`, `session_state`)
3. ✅ Split queue module imports (`queue_message_builder`, `queue_client_operations`)
4. ✅ Backward compatibility (`queue_operations` re-exports)
5. ✅ Processor operations imports
6. ✅ Function callability verification

**Result**: ✅ ALL TESTS PASSED

### How to Run Tests

```bash
# Test imports directly
cd /workspaces/ai-content-farm/containers/content-processor
python test_imports.py

# Test with pytest (uses conftest.py setup)
cd /workspaces/ai-content-farm/containers/content-processor
python -m pytest tests/ -v

# Test compilation
python -m py_compile *.py
```

## CI/CD Compatibility

### GitHub Actions Setup
The same pattern works in CI/CD because pytest automatically uses `conftest.py`:

```yaml
# From .github/workflows/*.yml
- name: Run Tests
  run: |
    cd containers/content-processor
    PYTHONPATH="${GITHUB_WORKSPACE}" python -m pytest tests/ -v
```

The `PYTHONPATH` is set to workspace root, and `conftest.py` handles adding the container directory.

## Benefits

1. ✅ **Works Everywhere**: Local development, pytest, CI/CD, direct execution
2. ✅ **No Package Complexity**: No `__init__.py` files needed, no `python -m` required
3. ✅ **IDE Support**: PyLance/Pylint/mypy all work correctly
4. ✅ **Clear Dependencies**: Easy to see what imports what
5. ✅ **Namespace Isolation**: Each container's modules don't collide with others
6. ✅ **Standard Python**: Uses standard sys.path mechanism, no special magic

## Common Pitfalls to Avoid

### ❌ Don't Mix Import Styles
```python
# ❌ BAD - Mixing relative and absolute
from .models import TopicMetadata
from processor_context import ProcessorContext  # Inconsistent!
```

### ❌ Don't Use Relative Imports for Container Modules
```python
# ❌ BAD - Fails when run directly
from .queue_operations import trigger_markdown_for_article
```

### ❌ Don't Forget libs. Prefix for Shared Code
```python
# ❌ BAD - Won't find shared library
from blob_storage import BlobStorageClient

# ✅ GOOD - Correct path
from libs.blob_storage import BlobStorageClient
```

## Summary

**All imports in content-processor container now use absolute imports**, making the code work reliably in:
- ✅ Local development (direct `python file.py`)
- ✅ Test execution (`pytest tests/`)
- ✅ CI/CD pipelines (GitHub Actions)
- ✅ IDE type checking and autocomplete
- ✅ Import verification (`python -m py_compile`)

**Line counts remain compliant:**
- `queue_message_builder.py`: 166 lines ✅
- `queue_client_operations.py`: 339 lines ✅  
- `queue_operations.py`: 45 lines ✅
- `processor_operations.py`: 376 lines ✅

**All functional refactoring preserved**, just with corrected import statements.
