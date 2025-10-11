# YAML Frontmatter Fix for Site Publisher

## Problem

The site-publisher container was failing to build the Hugo static site with this error:

```
Error: error building site: process: readAndProcessContent: "/tmp/site-builder/hugo-site/content/processed/2025/10/09/20251009_153709_rss_392429.md:3:1": failed to unmarshal YAML: yaml: line 3: mapping values are not allowed in this context
```

## Root Cause

**Two-part issue:**

1. **Markdown-generator creating invalid YAML**: The Jinja2 templates were generating unquoted URLs and improper whitespace, creating YAML that Hugo couldn't parse.

2. **Site-publisher not resilient to bad files**: A single malformed markdown file would fail the entire Hugo build, preventing publication of thousands of valid articles.

## Solutions Implemented

### Part 1: Fix Markdown Generation (Preventive)

Fixed all three Jinja2 templates in `markdown-generator`:
- `containers/markdown-generator/templates/default.md.j2`
- `containers/markdown-generator/templates/minimal.md.j2`  
- `containers/markdown-generator/templates/with-toc.md.j2`

**Changes:**

1. **Quoted all YAML values** to properly escape special characters:
   ```yaml
   # Before
   url: {{ metadata.url }}
   source: {{ metadata.source }}
   
   # After  
   url: "{{ metadata.url }}"
   source: "{{ metadata.source }}"
   ```

2. **Fixed Jinja2 whitespace control** to preserve newlines:
   ```jinja
   # Before (strips leading whitespace, causing lines to run together)
   {%- if metadata.author %}
   author: "{{ metadata.author }}"
   {%- endif %}
   
   # After (strips trailing whitespace only, preserving newlines)
   {% if metadata.author -%}
   author: "{{ metadata.author }}"
   {% endif -%}
   ```

3. **Used `tojson` filter for tag arrays** to ensure proper JSON encoding:
   ```jinja
   # Before
   tags: [{{ metadata.tags|join(', ') }}]
   
   # After
   tags: [{{ metadata.tags|map('tojson')|join(', ') }}]
   ```

4. **Added comprehensive test** to validate YAML frontmatter parsing in all templates.

### Part 2: Add Resilience to Site Publisher (Defensive)

Enhanced `site-publisher` container to validate and quarantine malformed files:

**New validation function** (`validate_markdown_frontmatter`):
- Checks for proper `---` delimiters
- Validates YAML syntax with Hugo-strict rules
- Requires quoted URLs (Hugo is stricter than Python's YAML parser)
- Verifies required fields: `title`, `url`, `source`

**Updated `organize_content_for_hugo` function**:
- Validates every markdown file before copying to Hugo directory
- Malformed files are moved to `/quarantined/` directory
- Build continues with valid files only
- Logs quarantined files for review

**Example behavior:**
```
Found 5232 markdown files to organize
Organized 5225 valid files, quarantined 7 malformed files, 0 other errors
Quarantined files (will not be published): bad-article-1.md, bad-article-2.md, ...
```

## Testing

### Markdown Generator Tests
```bash
cd containers/markdown-generator
PYTHONPATH=/workspaces/ai-content-farm python -m pytest tests/test_templates.py -v
# All 9 tests pass including new YAML validation test
```

### Site Publisher Tests  
```bash
cd containers/site-publisher
PYTHONPATH=/workspaces/ai-content-farm python -m pytest tests/test_content_downloader.py -v
# All tests pass including 5 new validation/quarantine tests
```

## Impact

**Before fix:**
- ❌ Single malformed file = entire build fails
- ❌ 5,232 articles blocked from publication
- ❌ No visibility into which files are problematic

**After fix:**
- ✅ Malformed files quarantined automatically
- ✅ Valid articles published successfully  
- ✅ Clear logging of quarantined files
- ✅ Future files generated with valid YAML
- ✅ Resilient to occasional bad data

## Next Steps

### 1. Deploy the Fix

The fix spans two containers:

```bash
git checkout -b fix/yaml-frontmatter-resilience
git add containers/markdown-generator/templates/*.j2
git add containers/markdown-generator/tests/test_templates.py
git add containers/site-publisher/content_downloader.py
git add containers/site-publisher/tests/test_content_downloader.py
git add docs/YAML_FRONTMATTER_FIX.md
git commit -m "Fix YAML frontmatter issues and add resilience

markdown-generator:
- Quote all YAML values to escape special characters
- Fix Jinja2 whitespace control to preserve newlines
- Add YAML validation test

site-publisher:
- Add frontmatter validation before Hugo build
- Quarantine malformed files instead of failing build
- Add strict Hugo-compatible validation rules
- Add comprehensive validation tests

Fixes site build failures from malformed YAML frontmatter."
git push origin fix/yaml-frontmatter-resilience
```

Then create a PR to main.

### 2. Monitor Quarantined Files

After deployment, check quarantine directory for patterns:

```bash
# List quarantined files
az storage blob list \
  --account-name aicontentprodstkwakpx \
  --container-name quarantined \
  --output table
```

If many files are quarantined, investigate root cause in content-processor or markdown-generator.

### 3. Clean Up Existing Bad Files (Optional)

The existing 5,232 markdown files may include ~7 malformed files that will be quarantined on next build. Options:

#### Option A: Let Natural Quarantine Work
- Deploy fix
- Next site build will quarantine bad files automatically
- No manual intervention needed
- **Recommended approach**

#### Option B: Regenerate All Content  
- Delete markdown-content container
- Reprocess all articles through updated markdown-generator
- Ensures all files have perfect YAML
- Higher operational complexity

## Files Changed

**Markdown Generator:**
- `containers/markdown-generator/templates/default.md.j2`
- `containers/markdown-generator/templates/minimal.md.j2`
- `containers/markdown-generator/templates/with-toc.md.j2`
- `containers/markdown-generator/tests/test_templates.py`

**Site Publisher:**
- `containers/site-publisher/content_downloader.py`
- `containers/site-publisher/tests/test_content_downloader.py`

**Documentation:**
- `docs/YAML_FRONTMATTER_FIX.md`

## Lessons Learned

1. **Always quote YAML values** that might contain special characters
2. **Test YAML parsing** as part of template tests, not just rendering
3. **Be careful with Jinja2 whitespace control** - `{%-` strips newlines
4. **Build resilience into pipelines** - one bad file shouldn't block thousands of good ones
5. **Quarantine > Fail** - isolate problematic data for review rather than stopping the pipeline
6. **Hugo YAML is stricter than Python** - validate with Hugo-compatible rules

---

*Date: 2025-10-11*  
*Author: GitHub Copilot*
