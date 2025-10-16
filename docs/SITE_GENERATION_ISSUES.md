# Site Generation Issues - Analysis & Fix Plan

**Date**: October 16, 2025  
**Issue**: Published articles have multiple quality problems  
**Example**: https://aicontentprodstkwakpx.z33.web.core.windows.net/processed/2025/10/16/20251016_104549_mastodon_mastodon.social_115383358597059180/

## Pipeline Traceability Analysis

Successfully traced article through entire pipeline:

1. **Collected Content**: (not found - may have been cleaned up)
2. **Processed Content**: `processed-content/processed/2025/10/16/20251016_104549_mastodon_mastodon.social_115383358597059180.json`
3. **Markdown Content**: `markdown-content/processed/2025/10/16/20251016_104549_mastodon_mastodon.social_115383358597059180.md`
4. **Published Site**: `$web/processed/2025/10/16/20251016_104549_mastodon_mastodon.social_115383358597059180/index.html`

## Critical Issues Identified

### 1. Title Truncation (High Priority)
**Current**: `(15 Oct) Two New Windows Zero-Days Exploited in the Wild One Affects Every Version Ever Shipped ht...`  
**Expected**: Full, readable title or AI-generated concise title

**Root Cause**: 
- Processed JSON has truncated title from collection phase
- No AI title generation happening despite being in the plan
- Markdown generator uses this truncated title directly

**Fix Required**:
- Content processor should generate clean titles using AI
- If title > 100 chars, use AI to create concise version
- Never truncate mid-word

### 2. Missing Article Content (Critical Priority)
**Current**: Markdown file contains only frontmatter + "Source:" link  
**Expected**: Full article body with sections

**Root Cause**:
- Processed JSON has `content` field with full article
- Markdown template (`default.md.j2`) expects `article_content` field
- Field name mismatch: JSON has `content`, template expects `article_content`

**Files**:
- Template: `/containers/markdown-generator/templates/default.md.j2`
- Generator: `/containers/markdown-generator/markdown_generator.py`

**Fix Required**:
```jinja2
{# Current (broken) #}
{%- if article_data.article_content %}
{{ article_data.article_content }}
{%- endif %}

{# Should be #}
{%- if article_data.content %}
{{ article_data.content }}
{%- endif %}
```

### 3. Wrong Source Attribution (High Priority)
**Current**: `source: unknown`, `source_platform: unknown`  
**Expected**: `source: mastodon`, `source_platform: mastodon`

**Root Cause**:
- Processed JSON has correct source in `source_metadata.source: "mastodon"`
- Metadata extraction not pulling from correct nested field
- Falls back to default "unknown"

**Fix Required** in `/containers/markdown-generator/metadata_utils.py`:
```python
# Current (broken)
source=article_data.get("source", "unknown")

# Should be
source=article_data.get("source_metadata", {}).get("source", "unknown")
```

### 4. Wrong Source URL (High Priority)
**Current**: Points to local `/articles/...` path  
**Expected**: Actual Mastodon post URL from `source_metadata.source_url`

**Processed JSON has**:
```json
"source_metadata": {
  "source_url": "https://fed.brid.gy/r/https://bsky.app/profile/did:plc:xwbve7fktqqaph76re6bjwnh/post/3m3ck5r2njk2m",
  "original_title": "(15 Oct) Two New Windows Zero-Days..."
}
```

**Fix Required** in `/containers/markdown-generator/markdown_generator.py`:
```python
# Current
source_url = article_data.get("original_url", metadata.url)

# Should be
source_url = article_data.get("source_metadata", {}).get("source_url", metadata.url)
```

### 5. Irrelevant Stock Images (Medium Priority)
**Current**: Generic image based on truncated title search  
**Expected**: Relevant image or no image

**Root Cause**:
- Unsplash search uses truncated title
- Search for "(15 Oct) Two..." returns random results
- Should extract keywords from content or disable for short titles

**Fix Required**:
- Disable stock images for titles < 50 chars or with date prefixes
- OR extract keywords from article content for better image search
- OR use article category/tags for image search

### 6. Verbose Directory Names (Low Priority)
**Current**: `20251016_104549_mastodon_mastodon.social_115383358597059180`  
**Expected**: Clean slug like `windows-zero-day-vulnerabilities`

**Root Cause**:
- Using technical ID instead of article slug
- Processed JSON has proper slug: `"slug": "15-oct-two-new-windows-zero-days..."`

**Fix Required**:
- Use slug from processed JSON for directory naming
- Keep ID as metadata for traceability

## Implementation Priority

### Phase 1: Critical Fixes ✅ COMPLETED
**Status**: Deployed (commit 4ee1820, Oct 16 2025)

1. ✅ Fix missing article content (field name mismatch)
2. ✅ Fix source attribution (extract from nested field)
3. ✅ Fix source URL (use source_metadata.source_url)

**Results**:
- All tests passing (5 new tests added)
- CI/CD pipeline running
- Articles now show full content, correct attribution, working links

### Phase 2: Quality Improvements (CURRENT PRIORITY)
**Target**: Next deployment cycle

4. 🔄 **Implement AI title generation for truncated titles**
   - Priority: HIGH
   - Effort: Medium
   - Impact: High user experience improvement
   - Owner: content-processor container

5. 🔄 **Improve stock image selection logic**
   - Priority: MEDIUM
   - Effort: Low
   - Impact: Better visual quality
   - Owner: markdown-generator container

6. 🔄 **Use article slugs for directory names**
   - Priority: MEDIUM
   - Effort: Medium
   - Impact: Better SEO and human-readable URLs
   - Owner: site-publisher container

### Phase 3: Enhanced Traceability (Future)
7. ⏳ Add collection ID to frontmatter for full traceability
8. ⏳ Add "View Original Post" link in article template (DONE in Phase 1)
9. ⏳ Display source platform badge in UI

## Testing Results

### Phase 1 Tests ✅
- ✅ `test_article_content_field_extraction` - PASSED
- ✅ `test_source_extraction_from_nested_metadata` - PASSED
- ✅ `test_source_url_from_nested_metadata` - PASSED
- ✅ `test_fallback_to_unknown_source` - PASSED
- ✅ `test_real_world_mastodon_article` - PASSED

### Visual Verification (Post-Deployment)
- [x] Article content appears in published HTML
- [x] Source shows "Originally posted on Mastodon" with working link
- [ ] Title is readable and not truncated (Phase 2)
- [ ] Images are contextually relevant (Phase 2)
- [ ] Directory names are human-readable (Phase 2)

---

**Current Status**: Phase 1 completed and deployed. Ready to begin Phase 2 implementation.  
**Next Steps**: See PHASE_2_IMPLEMENTATION_PLAN.md for detailed task breakdown.
