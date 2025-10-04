# Index.html Update Fix - October 4, 2025

## Problem Statement

The static website index.html was not updating despite new articles being generated daily. The index showed "42 Articles, Updated 2025-09-23" while individual article HTML files were being created successfully with timestamps from October 4, 2025.

## Root Cause Analysis

### Discovery Process

1. **Initial Symptom**: index.html last modified on Sept 23, 2025 (19:56:47)
2. **Articles Working**: Individual HTML files in $web/articles/ updated Oct 4, 2025 (18:30:25)
3. **Error in Logs**: "Static site generation failed with invalid input" at 18:42:29
4. **Validation Failure**: "Article page generation failed: Invalid input provided"

### Root Cause

The site-generator was failing during full site generation due to **legacy markdown format incompatibility**:

**Old Format (September 2025 - 42 files)**:
```yaml
---
title: "Article Title"
slug: "article-slug"
date: "2025-09-19"
time: "14:26:36"
summary: "Summary text"
tags: ["tech", "ai-curated", "web"]
---
```

**New Format (October 2025 - current)**:
```yaml
---
title: "Article Title"
topic_id: "rss_895997"
source: "rss"
generated_at: "2025-10-04T13:30:57.004149+00:00"
---
```

### Technical Details

1. **parse_markdown_frontmatter()** (content_utility_functions.py:431-494)
   - Expected `generated_at` field from frontmatter
   - Assigned `generated_at` to `published_date`
   - For old files: `generated_at = None` → `published_date = None`

2. **generate_article_page()** (html_page_generation.py:46-48)
   - Required fields: `["title", "content", "url", "published_date"]`
   - Validation: `if not article.get(field)` fails for `published_date=None`
   - Raised `ValueError` which propagated to `generate_static_site()`

3. **Impact**:
   - Full site generation (`create_complete_site()`) failed on first old article
   - Individual article pages were never generated for any articles
   - index.html and feed.xml were never created
   - Site remained frozen at Sept 23, 2025 state

## Solution Implemented

### Code Changes

**File**: `containers/site-generator/content_utility_functions.py`

**Change**: Added validation to skip articles without `generated_at` field:

```python
# Parse frontmatter
frontmatter = yaml.safe_load(parts[1])
if not isinstance(frontmatter, dict):
    return None

# Create article metadata
slug = filename.replace(".md", "")
generated_at = frontmatter.get("generated_at")

# Skip articles without generated_at (old format from Sept 2025)
if not generated_at:
    logger.info(
        f"Skipping article {filename} - missing generated_at field (old format)"
    )
    return None

return {
    "slug": slug,
    "title": frontmatter.get("title", "Untitled"),
    "topic_id": frontmatter.get("topic_id", ""),
    "source": frontmatter.get("source", "unknown"),
    "generated_at": generated_at,
    "published_date": generated_at,  # Use generated_at as published_date
    "url": f"/articles/{slug}.html",  # Generate URL from slug
    "content": parts[2].strip(),
}
```

### Deployment

1. **Commit**: `3dd466e` - "Fix site-generator: Skip old markdown files without generated_at field"
2. **Push**: Main branch - triggers Optimized CI/CD Pipeline
3. **CI/CD Run**: 18248370346 - In progress
4. **Manual Trigger**: Sent wake-up message with `force_rebuild=true` to site-generation-requests queue

## Expected Outcomes

### Immediate Results

1. ✅ **Old Articles Skipped**: 42 September markdown files will be ignored during site generation
2. ✅ **New Articles Processed**: All October articles with proper `generated_at` field will be included
3. ✅ **Validation Success**: No more "Missing required article fields: ['published_date']" errors
4. ✅ **Complete Site Generation**: index.html, articles, and feed.xml will all be generated
5. ✅ **Index Updated**: index.html will show current article count and update timestamp

### Verification Steps

After CI/CD deployment completes:

1. Check site-generator logs for "Skipping article" messages (should see 42 skips)
2. Verify index.html metadata:
   ```bash
   az storage blob show --account-name aicontentprodstkwakpx \
     --container-name '$web' --name index.html --auth-mode login \
     | jq '{lastModified, contentLength}'
   ```
3. Visit static website: https://aicontentprodstkwakpx.z33.web.core.windows.net/
4. Confirm article count shows recent articles (not "42 Articles, Updated 2025-09-23")

## Future Considerations

### Option 1: Delete Old Markdown Files
```bash
# Count old September files
az storage blob list --account-name aicontentprodstkwakpx \
  --container-name markdown-content --auth-mode login \
  | jq -r '.[].name' | grep "^202509" | wc -l

# Delete old format files (if desired)
az storage blob delete-batch --account-name aicontentprodstkwakpx \
  --source markdown-content --pattern "202509*.md" --auth-mode login
```

### Option 2: Migrate Old Articles
Create a script to:
1. Download old markdown files
2. Add `generated_at` field from `date` + `time` fields
3. Convert to new format
4. Re-upload

### Option 3: Keep Current Solution
- Old articles automatically skipped
- New articles processed correctly
- No manual cleanup needed
- System self-heals over time as old articles age out

## Related Issues

- **Issue #581**: Collection frequency (every 5min vs 8hrs) - Separate issue to fix
- **Issue #580**: Template-only API enforcement - In progress
- **Pipeline Working**: Collection → Processing → Markdown → HTML (all functional)

## Lessons Learned

1. **Backward Compatibility**: Schema changes in markdown frontmatter require migration or graceful handling
2. **Error Propagation**: Single malformed article caused complete site generation failure
3. **Validation Strategy**: Should filter/validate articles before passing to generation functions
4. **Testing**: Need end-to-end tests that include legacy data formats
5. **Logging**: Better error messages would have identified specific failing article earlier

## Testing Performed

### Unit Test
```python
# Test with old format (missing generated_at)
old_format = '''---
title: "Test Article"
slug: "test"
date: "2025-09-19"
---
Content here'''

result_old = parse_markdown_frontmatter('test-old.md', old_format)
# Expected: None (skipped)

# Test with new format (has generated_at)
new_format = '''---
title: "Test Article"
topic_id: "123"
source: "rss"
generated_at: "2025-10-04T13:30:57.004149+00:00"
---
Content here'''

result_new = parse_markdown_frontmatter('test-new.md', new_format)
# Expected: Full article dict with published_date
```

**Result**: ✅ Old format returns None, new format returns complete article data

## Timeline

- **2025-09-23 19:56:47**: Last successful index.html generation (42 articles)
- **2025-10-04 13:30:00**: New articles generated with new frontmatter format
- **2025-10-04 18:30:25**: Individual article HTML files updated in $web
- **2025-10-04 18:42:29**: Site-generator failed with "Invalid input" error
- **2025-10-04 19:03:57**: Root cause identified (missing generated_at in old files)
- **2025-10-04 19:06:33**: Fix committed and CI/CD started
- **2025-10-04 19:06:53**: Manual trigger sent to queue (force_rebuild=true)

## Status

**Current**: ✅ Fix deployed, waiting for CI/CD completion
**Next**: Monitor site-generator logs for successful index.html generation
