# Code Quality Improvements Plan

## Issues Identified

### 1. File Size Issues
- ✅ **content_utility_functions.py**: 588 lines (needs to be under 500)
  - **Solution**: Split into two files:
    - `content_retrieval.py` (article fetching, frontmatter parsing) ~300 lines
    - `content_generation.py` (markdown/HTML/RSS generation) ~288 lines

### 2. Inline Imports
- ✅ **content_utility_functions.py**: Line 383 `from pathlib import Path` - FIXED
- **main.py**: Multiple inline imports in functions (lines 91, 102, 109, 110, 114, 115, 117, 118, 246, 496)
  - These are intentional for lazy loading and avoiding circular imports
  - **Recommendation**: Keep for now, document reasoning
- **Other files**: Similar lazy-loading patterns for circular dependency avoidance
  - **Recommendation**: Accept as necessary evil, add comments

### 3. Commented Code
- ✅ **Makefile**: Lines 713-727 commented deploy-staging target - REMOVED

### 4. Mutation Patterns
- **content_utility_functions.py**: 
  - Lines 82-141: List mutation in `get_processed_articles()` - `articles.append()`
  - Lines 168-203: List mutation in `get_markdown_articles()` - `articles.append()`
  - Lines 293-401: List mutation in `create_complete_site()` - `generated_files.append()`
  
  **Solution**: Use list comprehensions or functional patterns where possible

## Implementation Priority

1. ✅ Remove commented Makefile code
2. ✅ Move inline Path import to top
3. ⏳ Split content_utility_functions.py into two files
4. ⏳ Refactor mutation patterns to functional style
5. 📝 Document intentional inline imports for circular dependency resolution

## Refactoring Strategy for Mutations

### Pattern 1: List Building with Validation
```python
# Current (mutation):
articles = []
for item in items:
    if valid(item):
        articles.append(process(item))

# Functional:
articles = [
    process(item)
    for item in items
    if valid(item)
]
```

### Pattern 2: Async List Building
```python
# Current (mutation):
articles = []
for blob in blobs:
    content = await fetch(blob)
    if content:
        articles.append(content)

# Functional with helper:
async def fetch_valid_content(blob):
    content = await fetch(blob)
    return content if content else None

contents = await asyncio.gather(*[fetch_valid_content(b) for b in blobs])
articles = [c for c in contents if c is not None]
```

## Files to Create

1. `content_retrieval.py` - Content fetching and parsing functions
2. `content_generation.py` - HTML/RSS/markdown generation functions
3. Update imports in dependent files
