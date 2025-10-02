# Content Processor Import Standards

**Date**: October 2, 2025  
**Status**: Applied to `processor.py` (first file)  
**Based on**: `/docs/CONTAINER_IMPORT_STRATEGY.md` and site-generator implementation

## 📋 Import Organization Standard

Following PEP 8 and project conventions, all imports are organized in this order:

### 1. Module Docstring
```python
"""
Module description and purpose.
"""
```

### 2. Standard Library Imports (Alphabetically sorted)
```python
import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4
```

### 3. Local Application Imports (Same container, alphabetically sorted)
```python
from config import ContentProcessorSettings
from models import (
    ProcessingAttempt,
    ProcessingResult,
    ProcessorStatus,
    TopicMetadata,
    TopicState,
)
from openai_client import OpenAIClient
from services import (
    ArticleGenerationService,
    LeaseCoordinator,
    ProcessorStorageService,
    TopicDiscoveryService,
)
```

### 4. Shared Library Imports (Alphabetically sorted)
```python
from libs.processing_config import ProcessingConfigManager
from libs.queue_triggers import (
    should_trigger_next_stage,
    trigger_markdown_generation,
)
from libs.simplified_blob_client import SimplifiedBlobClient
```

## 🎯 Key Principles

1. **Module-level imports only** - Never inline imports inside functions
2. **Direct imports from same container** - `from config import ...` (not `from containers.content-processor.config import ...`)
3. **Absolute imports for shared libraries** - `from libs import ...`
4. **Alphabetically organized within each group**
5. **Type hints throughout** - All function signatures have complete type annotations

## ✅ Applied Standards in processor.py

- ✅ Import organization: Standard library → Local → Shared
- ✅ All imports at module level (no inline imports)
- ✅ Type hints: Added assertions for type narrowing
- ✅ Removed invalid `blob_client.close()` call
- ✅ Fixed Optional[int]/Optional[float] type issues with assertions

## 🔍 Known Linter False Positives

### config.py Import Warning
```python
from config import ContentProcessorSettings  # ⚠️ Pylance reports "unknown import symbol"
```

**Status**: False positive - works correctly at runtime  
**Reason**: Pylance analyzes from workspace root, but container runs from `/containers/content-processor/`  
**Resolution**: Ignore this warning - the import is correct per our container strategy

**Runtime verification**:
```bash
cd /workspaces/ai-content-farm/containers/content-processor
python -c "from config import ContentProcessorSettings; print(ContentProcessorSettings)"
# ✅ Works: <class 'config.ContentProcessorSettings'>
```

## 📝 Next Files to Standardize

Apply the same import organization to:
- [ ] `main.py`
- [ ] `openai_client.py`
- [ ] `models.py`
- [ ] `endpoints/*.py`
- [ ] `services/*.py`

## 📚 References

- `/docs/CONTAINER_IMPORT_STRATEGY.md` - Full strategy documentation
- `/containers/site-generator/site-gen-python-standards.md` - Complete standards guide
- Site-generator implementation - Reference for correct patterns
