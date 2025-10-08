# Site Generator Filename Mismatch Issue

**Date**: October 6, 2025  
**Status**: 🐛 BUG IDENTIFIED - Article links in index page are broken

## Problem

**Symptoms**:
- Articles are successfully generated and accessible
- Index page links return 404 errors
- Direct URLs with full filename work correctly

**Root Cause**:
Mismatch between processor-generated metadata and site-generator actual filenames.

### What Processor Generates:
```json
{
  "filename": "articles/2025-09-17-scattered-spider-gang-retirement-to-bank-heist.html",
  "slug": "scattered-spider-gang-retirement-to-bank-heist",
  "url": "/articles/2025-09-17-scattered-spider-gang-retirement-to-bank-heist.html"
}
```

### What Site-Generator Actually Saves:
```
articles/theregister_25319-scattered-spider-gang-retirement-to-bank-heist.html
```

### What Index Links To (from processor metadata):
```html
<a href="/articles/scattered-spider-gang-retirement-to-bank-heist.html">
```

**Result**: 404 because the actual file has a different name!

## Working URLs

✅ **These work** (with full source prefix):
- https://aicontentprodstkwakpx.z33.web.core.windows.net/articles/theregister_25319-scattered-spider-gang-retirement-to-bank-heist.html
- https://aicontentprodstkwakpx.z33.web.core.windows.net/articles/arstechnica_80638-why-as-a-responsible-adult-simcity-2000-hits-diffe.html
- https://aicontentprodstkwakpx.z33.web.core.windows.net/articles/theregister_3146-amd-rocm-7-vs-nvidia-cuda-gpu-dominance-race.html

❌ **These don't work** (from index links):
- /articles/scattered-spider-gang-retirement-to-bank-heist.html
- /articles/why-as-a-responsible-adult-simcity-2000-hits-diffe.html  
- /articles/amd-rocm-7-vs-nvidia-cuda-gpu-dominance-race.html

## Technical Analysis

### Processor Side (`containers/content-processor/metadata_generator.py`)

**What it generates**:
- Date-based filename: `articles/YYYY-MM-DD-slug.html`
- Clean slug: `scattered-spider-gang-retirement-to-bank-heist`
- URL: `/articles/YYYY-MM-DD-slug.html`

**Code location**: `metadata_generator.py` lines ~110-130

### Site-Generator Side

**What it does**:
1. Receives processed article with date-based filename
2. Somewhere adds source prefix (`theregister_25319-`) when saving
3. Doesn't update the metadata to reflect actual filename
4. Index page uses outdated metadata with wrong URLs

**Problem areas**:
- `content_utility_functions.py` line 336: Generates URL from slug only
- Somewhere in save logic: Adds source prefix to actual file

## Solutions (Pick One)

### Option 1: Processor Should Include Source Prefix (RECOMMENDED)
**Pros**: Single source of truth, processor controls naming  
**Cons**: Requires processor metadata_generator change

**Implementation**:
```python
# In metadata_generator.py
filename = f"articles/{source_id}-{slug}.html"
url = f"/articles/{source_id}-{slug}.html"
```

### Option 2: Site-Generator Should NOT Add Source Prefix
**Pros**: Uses processor metadata as-is  
**Cons**: Loses source information in filenames

**Implementation**:
- Remove source prefix addition in site-generator
- Use processor-provided filename directly

### Option 3: Site-Generator Updates Metadata After Rename
**Pros**: Keeps source prefix, fixes links  
**Cons**: More complex, two places manage naming

**Implementation**:
- Keep source prefix addition
- Update article metadata before building index
- Regenerate URL to match actual filename

## Recommendation

**Option 1** is cleanest: The processor already has access to `source` and `source_id` fields. It should generate filenames that include this information from the start.

### Files to Modify:
1. `containers/content-processor/metadata_generator.py` (~line 115)
   - Add source_id to filename generation
   - Update slug/URL generation to match

2. `containers/site-generator/content_utility_functions.py` (~line 322-336)
   - Remove any source prefix addition logic (if exists)
   - Trust processor-provided filename/URL

## Impact Assessment

### Current Reprocess Test (10 items)
- ✅ Articles generated successfully
- ✅ HTML published to $web container
- ✅ Direct URLs work
- ❌ Index page links broken (404s)
- 🟡 RSS feed links likely broken too

### For Full Reprocess (585 items)
**Should we fix this first?** YES
- All 585 articles would have broken index links
- Users can't navigate from homepage
- SEO impact (broken internal links)
- Would need to regenerate all HTML after fix

## Next Steps

1. **Complete current test** - Verify rest of pipeline works
2. **Fix processor metadata_generator** - Add source prefix to filenames
3. **Test with 1-2 articles** - Verify links work
4. **Regenerate test articles** - Re-run 10-item test
5. **Proceed to full reprocess** - Once links confirmed working

---

**Testing Commands**:
```bash
# Check actual files
az storage blob list --container-name '$web' --account-name aicontentprodstkwakpx \\
  --auth-mode login --prefix "articles/" --query "[].name" -o tsv

# Test direct URL (works)
curl -I https://aicontentprodstkwakpx.z33.web.core.windows.net/articles/theregister_25319-scattered-spider-gang-retirement-to-bank-heist.html

# Check index links (broken)
curl -s https://aicontentprodstkwakpx.z33.web.core.windows.net/index.html | grep 'href="/articles'
```

_Created: October 6, 2025 at 21:35 UTC_
