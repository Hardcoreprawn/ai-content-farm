# Site Generator Bug Resolution Plan

**Created**: October 5, 2025  
**Status**: In Progress  
**GitHub Issues**: #582, #584, #586, #587, #588, #534

## Executive Summary

This document outlines the comprehensive plan to resolve 6 critical site-generator bugs affecting reader experience. All fixes follow the project's functional programming principles with proper separation of concerns and security-first approach.

## Issues Overview

| Issue | Priority | Impact | Status |
|-------|----------|--------|--------|
| #582 - Markdown Rendering | HIGH | Articles unreadable | 🔨 In Progress |
| #588 - Preview Formatting | HIGH | Homepage unprofessional | 🔨 In Progress |
| #586 - URLs in Titles | MEDIUM | Content quality | 📋 Planned |
| #587 - Homepage Pagination | HIGH | 93% content hidden | 📋 Planned |
| #584 - Responsive Design | MEDIUM | Mobile UX poor | 📋 Planned |
| #534 - HTML Rendering | LOW | Duplicate of #582 | 📋 Monitor |

## Architecture Principles

Following project guidelines from `AGENTS.md` and `.github/copilot-instructions.md`:

- **Functional Programming**: Pure functions with no side effects
- **Security First**: Input validation, XSS prevention, secure error handling
- **Separation of Concerns**: Text processing separated from rendering
- **Standard Libraries**: Use `re`, `html.escape` over custom solutions
- **Testability**: All functions unit testable with clear contracts

## Phase 1: Critical Rendering Fixes (Week 1)

### Issue #582: Fix Markdown Rendering in Article Pages

**Problem**: Naive string replacement creates malformed HTML (`<p>#<h1>` tags, unclosed `<strong>`)

**Root Cause**: Line 58-63 in `templates/minimal/article.html` uses double string replacement:
```html
{% set content_html = article.content | replace('**', '<strong>') | replace('**', '</strong>') %}
```

**Solution**: Create proper markdown-to-HTML converter

**Files to Create**:
```
containers/site-generator/text_processing.py      # New pure functions module
containers/site-generator/tests/test_text_processing.py  # Unit tests
```

**Files to Modify**:
```
containers/site-generator/html_page_generation.py         # Add markdown conversion
containers/site-generator/templates/minimal/article.html  # Remove naive replacement
```

**Implementation**:
1. Create `text_processing.py` with `markdown_to_html()` function
2. Add Jinja2 custom filter registration
3. Update article template to use filter
4. Add comprehensive unit tests

**Test Coverage**:
- Headers (# ## ###)
- Bold (**text**)
- Italic (*text*)
- Links [text](url)
- Mixed formatting
- XSS prevention (HTML escaping)
- Edge cases (empty content, malformed markdown)

**Acceptance Criteria**:
- [ ] No `<p>#<h1>` malformed tags
- [ ] Proper `<h1>`, `<h2>`, `<h3>` header hierarchy
- [ ] Correctly closed `<strong>` and `<em>` tags
- [ ] Normal text weight (no all-bold content)
- [ ] HTML entities properly escaped
- [ ] Test with 10+ existing articles

---

### Issue #588: Strip Markdown from Preview Text

**Problem**: Homepage previews show raw markdown formatting (`**Title:**`, `**Introduction:**`)

**Root Cause**: Line 39 in `templates/minimal/index.html` directly truncates markdown:
```html
<p>{{ article.content[:200] }}...{% endif %}</p>
```

**Solution**: Generate clean plain-text previews

**Files to Modify**:
```
containers/site-generator/text_processing.py        # Add preview function
containers/site-generator/article_processing.py     # Add preview enrichment
containers/site-generator/html_page_generation.py   # Generate preview in context
containers/site-generator/templates/minimal/index.html  # Use article.preview
```

**Implementation**:
1. Create `create_plain_text_preview()` in `text_processing.py`
2. Add preview generation to article processing pipeline
3. Update index template to use preview field
4. Fallback to truncated content if preview missing

**Preview Generation Logic**:
- Strip all markdown formatting (`**`, `*`, `##`, `#`)
- Remove structural headers ("Title:", "Introduction:")
- Remove URLs
- Clean whitespace
- Truncate at word boundary with ellipsis
- Maximum length: 200 characters

**Acceptance Criteria**:
- [ ] No markdown symbols in previews
- [ ] No structural headers visible
- [ ] Clean, readable preview text
- [ ] Proper ellipsis on truncation
- [ ] No HTML entities (`&#39;` etc.)
- [ ] Test with all content sources (RSS, Mastodon, Reddit)

---

## Phase 2: Content Quality Fixes (Week 2)

### Issue #586: Clean URLs from Article Titles

**Problem**: Titles contain embedded URLs: `"OpenAI prepares $4 ChatGPT Go https://www.bleepingcomputer.com/news/artifi..."`

**Root Cause**: Title extraction from Mastodon posts includes URLs

**Solution**: Layered defense - clean at multiple stages

**Files to Modify**:
```
containers/site-generator/text_processing.py        # Add clean_title()
containers/site-generator/article_processing.py     # Apply title cleaning
containers/content-collector/mastodon_collector.py  # Early cleaning (separate PR)
```

**Implementation Strategy**:

**1. Immediate Fix (Site Generator)**:
- Add `clean_title()` function to text_processing.py
- Apply to all articles during preprocessing
- Remove URLs, truncated URL fragments, common URL patterns

**2. Upstream Fix (Content Collector)** - Separate Issue:
- Better title extraction from Mastodon posts
- Use post metadata instead of content when available
- Truncate at first URL occurrence

**Title Cleaning Rules**:
- Remove full URLs: `https?://\S+`
- Remove truncated URLs: `\S*\.{3}`
- Remove URL fragments: `www\.\S+`
- Clean whitespace and trailing punctuation
- Preserve title meaning and readability

**Acceptance Criteria**:
- [ ] No URLs in article titles
- [ ] No truncated URL fragments
- [ ] Titles grammatically correct
- [ ] Works across all content sources
- [ ] Whitespace properly normalized

---

### Issue #587: Homepage Pagination

**Problem**: Only 10 articles shown out of 131 generated (93% hidden)

**Current State**:
- `ARTICLES_PER_PAGE = 10` in `functional_config.py`
- Pagination logic exists but no UI controls
- Single `index.html` generated

**Recommended Solution**: Pagination with increased page size

**Decision Points**:
1. **Immediate**: Increase `ARTICLES_PER_PAGE` from 10 to 30
2. **Short-term**: Implement full pagination UI
3. **Future**: Consider infinite scroll with lazy loading

**Files to Modify**:
```
containers/site-generator/functional_config.py          # Increase page size
containers/site-generator/content_utility_functions.py  # Multi-page generation
containers/site-generator/templates/minimal/index.html  # Add pagination controls
containers/site-generator/templates/minimal/archive.html # New archive template
```

**Implementation Plan**:

**Step 1: Quick Fix** (Deploy immediately):
```python
# functional_config.py line 201
ARTICLES_PER_PAGE=int(
    startup_config.get("ARTICLES_PER_PAGE", os.getenv("ARTICLES_PER_PAGE", "30"))
)
```

**Step 2: Full Pagination** (Next sprint):
- Generate multiple index pages: `index.html`, `page-2.html`, `page-3.html`
- Add pagination controls to template
- Implement page navigation logic
- SEO: Proper rel="next"/"prev" links

**Step 3: Archive Page**:
- Create `archive.html` template with all articles
- Group by date/source/quality
- Full pagination support
- Link from homepage footer

**Pagination UI Design**:
```html
<nav class="pagination">
  <a href="/page-1.html" class="pagination-link">« Previous</a>
  <span class="pagination-pages">
    <a href="/index.html" class="pagination-number">1</a>
    <a href="/page-2.html" class="pagination-number active">2</a>
    <a href="/page-3.html" class="pagination-number">3</a>
    <span>...</span>
    <a href="/page-14.html" class="pagination-number">14</a>
  </span>
  <a href="/page-3.html" class="pagination-link">Next »</a>
</nav>
```

**Quality Filtering** (Optional enhancement):
- Sort by `quality_score` if available
- Show highest quality articles first
- Filter threshold: > 0.7 quality score

**Acceptance Criteria**:
- [ ] Users can access all generated articles
- [ ] Pagination controls visible and functional
- [ ] Page size configurable via environment variable
- [ ] SEO-friendly pagination (rel tags, sitemap)
- [ ] Performance acceptable with 200+ articles
- [ ] Test with varying article counts (10, 50, 100, 200+)

**Future Enhancement**: Infinite Scroll
- Implement lazy loading after initial 50 articles
- AJAX endpoint for additional articles
- Fallback to pagination for no-JS users
- Performance optimization for large datasets

---

## Phase 3: UX Improvements (Week 3)

### Issue #584: Fix Responsive Design

**Problem**: Site not properly responsive across device sizes

**Investigation Required**:
- CSS location: No `static/` directory found in minimal theme
- Styles may be embedded in `base.html` or missing
- Possible theme mixing (minimal + modern-grid)

**Files to Check**:
```
containers/site-generator/templates/minimal/base.html  # Check for embedded styles
containers/site-generator/theme_manager.py             # Verify theme selection
```

**Recommended Approach**:

**1. Create Separate CSS File** (Best practice):
```
containers/site-generator/templates/minimal/static/
  ├── css/
  │   ├── style.css        # Main styles
  │   ├── responsive.css   # Media queries
  │   └── fallback.css     # Minimal embedded fallback
  └── js/
      └── main.js          # Optional enhancements
```

**2. Responsive Breakpoints**:
```css
/* Mobile First Approach */
/* Default: Mobile (< 768px) */
.articles-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;
}

/* Tablet (768px - 1024px) */
@media (min-width: 768px) {
  .articles-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 1.5rem;
  }
}

/* Desktop (> 1024px) */
@media (min-width: 1024px) {
  .articles-grid {
    grid-template-columns: repeat(3, 1fr);
    gap: 2rem;
  }
}
```

**3. Embedded Fallback** (base.html):
```html
<style>
  /* Critical CSS only - grid layout fallback */
  .articles-grid { display: grid; gap: 1rem; }
  @media (min-width: 768px) { .articles-grid { grid-template-columns: repeat(2, 1fr); }}
  @media (min-width: 1024px) { .articles-grid { grid-template-columns: repeat(3, 1fr); }}
</style>
<link rel="stylesheet" href="/static/css/style.css">
```

**Acceptance Criteria**:
- [ ] Single consistent theme (minimal only)
- [ ] Responsive grid: 1 col (mobile), 2 col (tablet), 3 col (desktop)
- [ ] Navigation works on all screen sizes
- [ ] Text readable without horizontal scroll
- [ ] Images scale properly
- [ ] Test on real devices (iOS Safari, Android Chrome, desktop)

---

## Phase 4: Testing & Validation (Week 4)

### Issue #534: Improperly Rendered HTML (Legacy)

**Status**: Likely duplicate of #582

**Action**: Monitor after #582 fix is deployed
- If issue persists, investigate separately
- If resolved, close as duplicate with reference to #582

---

## Testing Strategy

### Unit Tests
```python
# test_text_processing.py
def test_markdown_to_html_headers()
def test_markdown_to_html_bold()
def test_markdown_to_html_xss_prevention()
def test_create_plain_text_preview_strips_markdown()
def test_clean_title_removes_urls()
```

### Integration Tests
```python
# test_article_rendering.py
async def test_article_page_renders_valid_html()
async def test_index_page_shows_clean_previews()
async def test_pagination_generates_all_pages()
```

### Visual Regression Tests
- Screenshot comparison before/after fixes
- Test on staging environment first
- Validate with sample articles from each source type

### Performance Tests
- Page load time with 30+ articles
- CSS/JS bundle size
- Responsive layout performance on mobile

---

## Implementation Schedule

### Week 1: Critical Rendering Fixes
- **Day 1-2**: Create text_processing.py with markdown_to_html()
- **Day 3**: Fix article template, add unit tests
- **Day 4**: Implement preview stripping
- **Day 5**: Integration testing, deploy to staging

### Week 2: Content Quality & Pagination
- **Day 1-2**: Implement title cleaning
- **Day 3**: Increase pagination limit, test
- **Day 4-5**: Full pagination implementation

### Week 3: Responsive Design
- **Day 1**: Audit existing styles
- **Day 2-3**: Create responsive CSS
- **Day 4**: Mobile testing
- **Day 5**: Cross-browser validation

### Week 4: Final Testing & Deployment
- **Day 1-2**: Integration testing all fixes
- **Day 3**: Staging validation
- **Day 4**: Production deployment
- **Day 5**: Monitoring and bug fixes

---

## Risk Mitigation

### Breaking Changes
- All changes deployed to staging first
- Rollback plan for each phase
- Keep old templates as backup

### Performance Impact
- Monitor page load times
- CSS bundle size < 50KB
- Lazy load images if needed

### Content Compatibility
- Test with articles from all sources (RSS, Mastodon, Reddit)
- Handle edge cases (empty content, very long titles)
- Backwards compatibility with existing markdown content

---

## Success Metrics

- [ ] Zero malformed HTML in article pages
- [ ] 100% of generated articles accessible from homepage
- [ ] Clean, professional previews on homepage
- [ ] No URLs in article titles
- [ ] Responsive design works on all device sizes
- [ ] Page load time < 3 seconds
- [ ] All unit tests passing
- [ ] Zero security vulnerabilities

---

## Related Documentation

- `AGENTS.md` - AI agent working principles
- `.github/copilot-instructions.md` - Project coding standards
- `site-generator-refactor.md` - Functional programming migration
- `docs/development-standards.md` - Line endings, security rules

---

## Changelog

- **2025-10-05**: Initial plan created
- **2025-10-05**: Phase 1 implementation started (markdown rendering)

