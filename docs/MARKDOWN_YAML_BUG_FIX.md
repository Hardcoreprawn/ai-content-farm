# Critical Bug Fix: Markdown YAML Frontmatter Malformation

**Date:** October 12, 2025
**Severity:** 🔴 CRITICAL - Blocking site generation
**Status:** ✅ Fixed, awaiting deployment

## Problem Summary

The markdown-generator container was producing **456 malformed markdown files** with invalid YAML frontmatter, preventing the site-publisher from building the static site.

## Root Cause

**Jinja2 Template Bug:** The `{% endif -%}` directive with trailing `-` was stripping newlines after optional fields.

### Malformed Output
```yaml
---
title: "Australia's Journey to 100% Clean Energy"
url: /articles/2025-10-11-australias-journey-to-100-clean-energy.html
source: rssgenerated_date: 2025-10-12T16:46:50.885853+00:00Z
---
```

### Correct Output
```yaml
---
title: "Australia's Journey to 100% Clean Energy"
url: /articles/2025-10-11-australias-journey-to-100-clean-energy.html
source: rss
generated_date: 2025-10-12T16:46:50.885853+00:00Z
---
```

## Technical Details

### Template Issue
In `default.md.j2` and `with-toc.md.j2`:
```jinja
source: "{{ metadata.source }}"
{% if metadata.author -%}
author: "{{ metadata.author }}"
{% endif -%}   ← This trailing hyphen strips the newline!
{% if metadata.published_date -%}
```

When optional fields (author, published_date, category, tags) are **all empty** (common for RSS articles), Jinja2 removes the conditional blocks AND the newlines, causing fields to run together.

### Fix Applied
Changed all `{% endif -%}` to `{% endif %}` (removed trailing `-`):

**Files Modified:**
- `/containers/markdown-generator/templates/default.md.j2`
- `/containers/markdown-generator/templates/with-toc.md.j2`

## Impact

### Affected Files
- **456 markdown files quarantined** by site-publisher
- All files from collection periods: 2025-10-11 and 2025-10-12
- Mix of RSS and Mastodon sources

### Site-Publisher Behavior
- ✅ Scaled up successfully (KEDA authentication fix worked!)
- ❌ Downloaded all markdown files from blob storage
- ❌ Validated YAML frontmatter
- ❌ Quarantined 456 malformed files
- ❌ Aborted Hugo build: "Content organization failed"
- ✅ Gracefully scaled back to zero

## Deployment Plan

### 1. Rebuild Markdown-Generator Container
```bash
# From containers/markdown-generator directory
docker build -t markdown-generator:fixed .

# Push to Azure Container Registry
az acr build --registry <acr-name> \
  --image markdown-generator:fixed \
  --file Dockerfile .
```

### 2. Update Container App
```bash
az containerapp update \
  --name ai-content-prod-markdown-generator \
  --resource-group ai-content-prod-rg \
  --image <acr-name>.azurecr.io/markdown-generator:fixed
```

### 3. Clean Up Malformed Files
```bash
# Delete malformed markdown (456 files from 2025-10-11 and 2025-10-12)
az storage blob delete-batch \
  --account-name aicontentprodstkwakpx \
  --source markdown-content \
  --pattern "processed/2025/10/11/*.md" \
  --auth-mode login

az storage blob delete-batch \
  --account-name aicontentprodstkwakpx \
  --source markdown-content \
  --pattern "processed/2025/10/12/*.md" \
  --auth-mode login
```

### 4. Reprocess Content
```bash
# Trigger markdown regeneration (will process from processed JSON files)
# The markdown-generation-requests queue should still have messages,
# or we can manually trigger reprocessing
```

### 5. Verify Site Publisher
```bash
# Monitor site-publisher logs after markdown regeneration
az containerapp logs show \
  --name ai-content-prod-site-publisher \
  --resource-group ai-content-prod-rg \
  --tail 100 \
  --follow

# Check for successful Hugo build
# Look for: "Successfully built static site"
# Verify static files in $web blob container
```

## Testing Strategy

### Unit Test Addition
Add test case to `containers/markdown-generator/tests/` to verify YAML frontmatter validity:

```python
def test_markdown_yaml_frontmatter_with_missing_fields():
    """Test that YAML frontmatter is valid when optional fields are empty."""
    metadata = ArticleMetadata(
        title="Test Article",
        url="https://example.com",
        source="rss",
        author=None,  # Empty optional field
        published_date=None,  # Empty optional field
        category=None,  # Empty optional field
        tags=[]  # Empty optional field
    )
    
    markdown = generate_markdown(metadata, {...})
    
    # Parse YAML frontmatter
    frontmatter = extract_frontmatter(markdown)
    assert "source" in frontmatter
    assert "generated_date" in frontmatter
    assert frontmatter["source"] == "rss"
    assert frontmatter["generated_date"].startswith("2025")
```

### Integration Test
1. Generate markdown with fixed template
2. Validate YAML parses correctly
3. Verify Hugo can build static site
4. Confirm files appear in $web container

## Prevention Measures

### 1. Template Testing
Add automated tests for all Jinja2 templates with various combinations of empty/populated fields.

### 2. YAML Validation
Add YAML parsing validation to markdown-generator before uploading to blob storage:

```python
import yaml

def validate_yaml_frontmatter(markdown_content: str) -> bool:
    """Validate YAML frontmatter is parseable."""
    try:
        parts = markdown_content.split("---", 2)
        if len(parts) >= 3:
            yaml.safe_load(parts[1])
            return True
    except yaml.YAMLError:
        return False
    return False
```

### 3. Site-Publisher Pre-Flight Check
Before Hugo build, run YAML validation on all markdown files and log specific errors.

## Lessons Learned

### Jinja2 Whitespace Control
- `-` in `{%-` or `-%}` strips **all** adjacent whitespace including newlines
- Be careful with conditional blocks in structured formats (YAML, JSON, XML)
- Test templates with all combinations of empty/populated fields

### Container Testing
- Integration tests should process real-world data scenarios
- Validate output formats, don't assume template rendering is correct
- Test with minimal metadata (common for RSS feeds without authors)

### Error Detection
- Site-publisher correctly quarantined malformed files ✅
- Should fail EARLIER at markdown generation stage
- Add validation before blob upload to catch issues at source

## Related Issues

- Site-publisher KEDA authentication bug (FIXED)
- Markdown-generator premature scale-down (PENDING - see MARKDOWN_GENERATOR_SCALING_ISSUE.md)
- Duplicate site-publish messages (PENDING)

## Success Criteria

- ✅ Template fix applied
- ⏳ Container rebuilt and deployed
- ⏳ Malformed files cleaned up
- ⏳ Content reprocessed with valid YAML
- ⏳ Hugo build successful
- ⏳ Static files in $web container
- ⏳ Unit test added
- ⏳ YAML validation added to pipeline

## Next Actions

1. **Commit and push template fixes**
2. **Trigger CI/CD to rebuild markdown-generator** 
3. **Monitor deployment and clean up malformed files**
4. **Verify end-to-end pipeline** (collector → processor → markdown-gen → site-publisher)
5. **Add unit tests and YAML validation** to prevent recurrence
