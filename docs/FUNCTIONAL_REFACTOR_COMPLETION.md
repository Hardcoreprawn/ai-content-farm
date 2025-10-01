# Action Plan: Complete the Functional Refactor

## Current State
- ✅ **Import issues fixed** - Intra-container imports now work correctly
- ✅ **Hyphenated folders** - Keep as-is, they're fine for containers
- ❌ **Incomplete refactor** - `main.py` still references old `SiteGenerator` class
- ❌ **Missing functional main** - Need to complete OOP → Functional migration

## Immediate Fix for Issue #562

### Problem
```python
# main.py line 32 - BROKEN
from site_generator import SiteGenerator  # ← This file doesn't exist
```

### Solution Options

#### Option A: **Create Functional Site Generator Module** (Recommended)
Create a new `site_generator.py` that wraps the functional approach in a class-like interface for compatibility:

```python
# containers/site-generator/site_generator.py
class SiteGenerator:
    """Compatibility wrapper for functional site generation."""
    
    def __init__(self):
        self.config = None
        
    async def initialize(self, config):
        """Initialize with functional config."""
        from functional_config import create_generator_context
        self.config = await create_generator_context(config)
        
    # Wrap functional methods as class methods for compatibility
```

#### Option B: **Complete Functional Refactor of main.py** (Better long-term)
Remove the `SiteGenerator` class entirely and use functional patterns in `main.py`:

```python
# main.py - Functional approach
from functional_config import create_generator_context, SiteGeneratorConfig
from content_processing_functions import generate_markdown_batch, generate_static_site

# Replace class instantiation with functional context
generator_context = None

async def get_generator_context():
    global generator_context
    if generator_context is None:
        generator_context = await create_generator_context(config)
    return generator_context
```

## Recommendation

**Use Option A for immediate fix** (Issue #562), then **plan Option B for next PR** (complete functional migration).

This approach:
1. ✅ **Fixes the immediate import error** 
2. ✅ **Maintains API compatibility** 
3. ✅ **Keeps existing folder structure**
4. ✅ **Doesn't break other code**
5. 📋 **Sets up clean functional migration path**

## Why Keep Hyphenated Folders

The folder naming is **perfectly fine**:
- ✅ **Standard DevOps practice** - Kubernetes, Docker, etc. use hyphens
- ✅ **Clear separation** - Folders are containers, not Python modules
- ✅ **Consistent with project** - All containers follow same pattern
- ✅ **No deployment issues** - Container names can have hyphens
- ✅ **URL-friendly** - Works well in service discovery

The import issues were **architectural**, not naming-related.