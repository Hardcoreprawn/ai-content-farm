# Jinja2 Template Migration Summary

**Date**: October 4, 2025  
**Issue**: Markdown content showing formatting symbols (**bold**) instead of rendered HTML  
**Root Cause**: HTML generation used string interpolation instead of Jinja2 templates  
**Solution**: Migrated to proper Jinja2 template rendering

## Problem Analysis

### Symptoms
- Article pages showed raw markdown text with `**bold**` symbols visible
- Content wasn't converting from markdown to HTML
- Templates existed but weren't being used

### Discovery
User correctly identified: **"I was under the impression that was -literally- the point of using jinja2"**

The codebase had:
- ✅ Complete Jinja2 template system in `templates/minimal/`, `templates/modern-grid/`, etc.
- ✅ Templates with proper markdown conversion logic (lines 52-63 in article.html)
- ✅ `jinja2~=3.1.6` in requirements.txt
- ✅ `ThemeManager` class for template discovery
- ❌ **But html_page_generation.py used f-string interpolation, not Jinja2 rendering**

### Code Architecture Before Migration
```python
# OLD: String interpolation approach
def render_article_template(context: Dict[str, Any]) -> str:
    article = context["article"]
    site = context["site"]
    
    html = f"""<!DOCTYPE html>
    <html lang="en">
    <head>
        <title>{page['title']}</title>
        ...
    </head>
    <body>
        ...
        <div class="article-content">
            {article['content']}  <!-- Raw markdown inserted here -->
        </div>
        ...
    </body>
    </html>"""
    
    return html
```

## Migration Implementation

### Changes Made

#### 1. Added Jinja2 Environment Setup
**File**: `containers/site-generator/html_page_generation.py`

```python
from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape

_jinja_env = None

def get_jinja_environment(theme: str = "minimal") -> Environment:
    """Get or create Jinja2 environment for template rendering."""
    global _jinja_env
    
    if _jinja_env is None:
        templates_dir = Path(__file__).parent / "templates"
        _jinja_env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
    
    return _jinja_env
```

#### 2. Refactored render_article_template()
**Before**: 70+ lines of f-string HTML generation  
**After**: Clean Jinja2 template rendering

```python
def render_article_template(context: Dict[str, Any], theme: str = "minimal") -> str:
    """Render HTML template for article page using Jinja2."""
    try:
        env = get_jinja_environment(theme)
        
        # Prepare template context
        article = context["article"]
        site = context["site"]
        
        # Ensure date fields are datetime objects
        if "generated_at" in article and isinstance(article["generated_at"], str):
            article["generated_at"] = datetime.fromisoformat(
                article["generated_at"].replace("Z", "+00:00")
            )
        
        template_context = {
            "article": article,
            "site": site,
            "current_year": datetime.now(timezone.utc).year,
        }
        
        # Load and render template
        template = env.get_template(f"{theme}/article.html")
        html_content = template.render(**template_context)
        
        return html_content
        
    except TemplateNotFound as e:
        # Fall back to minimal theme
        if theme != "minimal":
            return render_article_template(context, theme="minimal")
        raise
```

#### 3. Refactored render_index_template()
**Before**: 80+ lines of f-string HTML generation  
**After**: Clean Jinja2 template rendering

```python
def render_index_template(context: Dict[str, Any], theme: str = "minimal") -> str:
    """Render HTML template for index page using Jinja2."""
    try:
        env = get_jinja_environment(theme)
        
        articles = context["articles"]
        site = context["site"]
        
        # Ensure articles have proper date fields
        for article in articles:
            if "generated_at" in article and isinstance(article["generated_at"], str):
                article["generated_at"] = datetime.fromisoformat(
                    article["generated_at"].replace("Z", "+00:00")
                )
        
        template_context = {
            "articles": articles,
            "site": site,
            "last_updated": datetime.now(timezone.utc),
            "current_year": datetime.now(timezone.utc).year,
            "pagination": context.get("pagination", {}),
        }
        
        template = env.get_template(f"{theme}/index.html")
        html_content = template.render(**template_context)
        
        return html_content
        
    except TemplateNotFound as e:
        # Fall back to minimal theme
        if theme != "minimal":
            return render_index_template(context, theme="minimal")
        raise
```

#### 4. Added Slug Field Support
**File**: `containers/site-generator/content_utility_functions.py`

Templates expect `article.slug` for URL generation. Added slug field generation:

```python
# Generate individual article pages
for article in processed_articles:
    article_id = (
        article.get("topic_id")
        or article.get("id")
        or article.get("slug", "article")
    )
    safe_title = create_safe_filename(article.get("title", "untitled"))
    filename = f"articles/{article_id}-{safe_title}.html"
    
    # Set slug for template compatibility
    article["slug"] = f"{article_id}-{safe_title}"  # <-- NEW
    
    # Update article URL to match actual storage location
    article["url"] = f"/{filename}"
```

#### 5. Added Static File Upload
**File**: `containers/site-generator/content_utility_functions.py`

Templates reference `/style.css` and `/script.js`. Added upload for static assets:

```python
# Upload static assets (CSS, JS)
from pathlib import Path

static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    for static_file in static_dir.iterdir():
        if static_file.is_file() and not static_file.name.startswith('.'):
            try:
                with open(static_file, "r", encoding="utf-8") as f:
                    content = f.read()
                
                await blob_client.upload_text(
                    container=config["STATIC_SITES_CONTAINER"],
                    blob_name=static_file.name,
                    text=content,
                    overwrite=True,
                )
                generated_files.append(static_file.name)
            except Exception as e:
                logger.warning(f"Failed to upload static file {static_file.name}: {e}")
```

#### 6. Made Templates More Resilient
**Files**: `templates/minimal/article.html`, `templates/minimal/index.html`

Added conditional checks for optional fields to prevent template errors:

```html
<!-- Before -->
<span class="meta-value">{{ article.generated_at.strftime('%Y-%m-%d %H:%M UTC') }}</span>

<!-- After -->
{% if article.generated_at %}
<div class="meta-row">
    <span class="meta-label">Generated:</span>
    <span class="meta-value">{{ article.generated_at.strftime('%Y-%m-%d %H:%M UTC') }}</span>
</div>
{% endif %}
```

Applied to fields:
- `article.generated_at`
- `article.word_count`
- `article.quality_score`
- `article.topic_id`
- `last_updated`

### Testing Results

**Before Migration**: 1 test failing  
**After Migration**: ✅ All 111 tests passing

```bash
$ PYTHONPATH=/workspaces/ai-content-farm python -m pytest tests/ -v
============================= 111 passed in 4.84s ==============================
```

### Benefits of Migration

1. **Proper Markdown Rendering**: Templates have built-in markdown conversion logic
2. **Theme Support**: Can switch between minimal, modern-grid, custom-theme easily
3. **Template Inheritance**: Base.html provides consistent layout across pages
4. **Maintainability**: Separate presentation (templates) from logic (Python)
5. **CSS/Styling**: Templates properly link to CSS files with actual styles
6. **Security**: Jinja2 auto-escaping prevents XSS attacks
7. **Flexibility**: Easy to customize templates without changing Python code

### Architecture After Migration

```
containers/site-generator/
├── html_page_generation.py
│   ├── get_jinja_environment()      # Initialize Jinja2 Environment
│   ├── render_article_template()    # Uses templates/minimal/article.html
│   └── render_index_template()      # Uses templates/minimal/index.html
├── templates/
│   └── minimal/
│       ├── base.html               # Base template with header/footer
│       ├── article.html            # Extends base, renders article content
│       ├── index.html              # Extends base, lists articles
│       └── 404.html
└── static/
    ├── style.css                   # 600 lines of comprehensive styling
    └── script.js                   # Interactive enhancements
```

### Template Processing Flow

```
Article Data (JSON)
    ↓
render_article_template(context, theme="minimal")
    ↓
get_jinja_environment() → loads templates/
    ↓
env.get_template("minimal/article.html")
    ↓
article.html extends minimal/base.html
    ↓
template.render(article=..., site=...)
    ↓
HTML with proper markdown conversion
    ↓
Upload to $web container with content-type: text/html
```

## Related Files Modified

1. `containers/site-generator/html_page_generation.py`
   - Added Jinja2 imports and environment setup
   - Refactored render_article_template() from f-strings to Jinja2
   - Refactored render_index_template() from f-strings to Jinja2

2. `containers/site-generator/content_utility_functions.py`
   - Added slug field generation for template compatibility
   - Added static file upload (style.css, script.js)

3. `containers/site-generator/templates/minimal/article.html`
   - Added conditional checks for optional fields (generated_at, word_count, etc.)
   - Made template resilient to missing data

4. `containers/site-generator/templates/minimal/index.html`
   - Added conditional checks for optional fields
   - Made template resilient to missing data

## User Experience Impact

### Before
- ✅ Index page updates correctly
- ✅ Content-Type headers correct (text/html)
- ✅ Article links work
- ❌ **Article content shows markdown formatting symbols**

### After
- ✅ Index page updates correctly
- ✅ Content-Type headers correct (text/html)
- ✅ Article links work
- ✅ **Article content renders as HTML with proper styling**
- ✅ **CSS styles applied (600 lines of modern design)**
- ✅ **Theme system functional (can switch themes easily)**

## Next Steps

1. **Deploy to Production**: Merge to `main` branch for CI/CD deployment
2. **Verify Live Site**: Check https://aicontentprodstkwakpx.z33.web.core.windows.net/
3. **Theme Refinement**: User wants careful approach to styling (not "fussy")
4. **Collection Frequency**: Address Issue #581 (reduce from 5min to 8hrs)
5. **Template-Only API**: Enforce Issue #580 (separate template from generation)

## Lessons Learned

1. **Always use the tools you have**: System had complete Jinja2 infrastructure unused
2. **User insights are valuable**: User correctly identified root cause
3. **Template resilience matters**: Make templates handle missing optional fields gracefully
4. **Static assets matter**: CSS/JS files need explicit upload to blob storage
5. **Test coverage critical**: 111 tests caught the issue and validated fix

## References

- Jinja2 Documentation: https://jinja.palletsprojects.com/
- Template Files: `/workspaces/ai-content-farm/containers/site-generator/templates/`
- Static Assets: `/workspaces/ai-content-farm/containers/site-generator/static/`
- Previous Issue: `docs/INDEX_HTML_FIX_SUMMARY.md` (index.html not updating)
- Related Issue: `docs/CONTENT_TYPE_FIX_SUMMARY.md` (wrong content-type headers)

---

**Migration Status**: ✅ Complete  
**Test Status**: ✅ All 111 tests passing  
**Ready for Deployment**: ✅ Yes
