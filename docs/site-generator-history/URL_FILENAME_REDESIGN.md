# URL & Filename Structure Redesign

**Date**: October 6, 2025  
**Status**: Planning Phase  
**Priority**: HIGH - Blocks proper site functionality

## Current Problems

### 1. Data Quality Issues
- ❌ Titles with hashtags: "Gem.coop #Gem.coop #technology #innovation"
- ❌ Non-English titles (Japanese, Italian, etc.) without translation
- ❌ Inconsistent ID fields: `topic_id`, `id`, `slug`, `url` - unclear ownership
- ❌ URLs don't match filenames (404 errors)
- ❌ No clear title length limits (SEO best practice: 50-60 chars)

### 2. Architecture Problems
- ❌ URL generation scattered across multiple files
- ❌ Filename generation != URL generation
- ❌ No single source of truth for article identity
- ❌ Patching symptoms instead of fixing root cause

### 3. SEO & UX Problems
- ❌ Poor URL structure for search engines
- ❌ No dates in URLs (harder to assess content freshness)
- ❌ URLs too long (some >100 chars)
- ❌ Non-ASCII characters in URLs
- ❌ Redundant "article-" prefix

## Proposed Solution: Processor-Generated Metadata

### Philosophy
**The content-processor should be the SINGLE SOURCE OF TRUTH for article metadata.**

The processor already has AI capabilities - let's use them properly:

### Stage 1: Content Processor Enhancement (REQUIRED)

**Add to content-processor output:**

```json
{
  "id": "uuid-v4-unique-identifier",
  "original_title": "元のタイトル or Original Title",
  "title": "AI-Generated Engaging English Title",
  "slug": "2025-10-06-engaging-title-here",
  "url_slug": "engaging-title-here",
  "published_date": "2025-10-06",
  "language": "ja",
  "translated": true,
  "seo": {
    "title_length": 45,
    "description": "150 char SEO description",
    "keywords": ["ai", "technology", "news"]
  },
  "cost_tracking": {
    "article_cost_usd": 0.0015,
    "article_tokens": 3500,
    "metadata_cost_usd": 0.0001,
    "metadata_tokens": 150,
    "total_cost_usd": 0.0016
  }
}
```

### Stage 2: Filename Convention (SIMPLE & CLEAR)

**Format**: `YYYY-MM-DD-kebab-case-title.html`

**Examples**:
```
articles/2025-10-06-nvidia-breaks-barriers-with-self-funding-ai.html
articles/2025-10-06-uk-deploys-first-hydrogen-powered-digger.html
articles/2025-10-06-japan-signals-concern-over-trump-trade-deals.html
```

**Benefits**:
- ✅ Date visible in URL (SEO + freshness indicator)
- ✅ Short, clean, readable titles
- ✅ ASCII-only (no kanji/emoji issues)
- ✅ Sortable by date naturally
- ✅ No redundant prefixes
- ✅ Max 80 chars total (AWS S3/Azure best practice)

### Stage 3: URL Structure Matches Exactly

**One rule**: `filename === URL path component`

```
Filename: articles/2025-10-06-great-article.html
URL:      https://jablab.dev/articles/2025-10-06-great-article.html
```

No more mismatches!

## Implementation Plan

### Phase 1: Content Processor Updates (CRITICAL PATH)

**Location**: `containers/content-processor/`

**New AI Processing Step** (after content generation, before storage):

```python
async def generate_article_metadata(article_data: dict) -> dict:
    """
    Use GPT-4o-mini to generate proper metadata for article.
    
    Generates:
    - English title (if non-English detected)
    - SEO-optimized title (45-60 chars)
    - URL-safe slug
    - Cleaned description
    
    Cost: ~$0.0001 per article (negligible)
    """
    
    prompt = f"""
    Given this article data, generate SEO-optimized metadata:
    
    Original Title: {article_data.get('title')}
    Content Preview: {article_data.get('content')[:500]}
    
    Generate:
    1. Engaging English title (45-60 chars, no hashtags/emoji)
    2. URL slug (lowercase, hyphens, ASCII only)
    3. SEO description (140-160 chars)
    
    Return JSON format.
    """
    
    # Call OpenAI API
    # Parse response
    # Return enriched metadata
```

**Update ProcessedContent model** to include:
- `slug`: The final URL slug
- `seo_title`: AI-generated optimized title
- `original_title`: Preserve source title
- `translated`: Boolean flag
- `language`: ISO language code

### Phase 2: Site Generator Simplification

**Location**: `containers/site-generator/content_utility_functions.py`

**Simple filename generation**:

```python
def generate_article_filename(article: dict) -> str:
    """
    Generate filename from processor-provided metadata.
    
    Simple rule: Use the slug from processor, add date prefix.
    No AI, no complex logic - just assembly.
    """
    
    # Processor MUST provide these fields
    published_date = article['published_date']  # ISO format
    slug = article['slug']  # Already cleaned, translated, optimized
    
    # Simple date prefix
    date_prefix = datetime.fromisoformat(published_date).strftime('%Y-%m-%d')
    
    # Filename = date + slug
    filename = f"articles/{date_prefix}-{slug}.html"
    
    # Validate length (Azure blob name limit: 1024, but keep sensible)
    if len(filename) > 100:
        raise ValueError(f"Filename too long: {filename}")
    
    return filename
```

**Template context**:

```python
enriched_article = {
    **article,
    "url": f"/articles/{date_prefix}-{slug}.html",
    "filename": f"{date_prefix}-{slug}.html"
}
```

### Phase 3: URL Utils Update

**Location**: `containers/site-generator/url_utils.py`

```python
def get_article_url(article: dict, base_url: str = "") -> str:
    """
    Generate article URL from processor metadata.
    
    Args:
        article: Must have 'published_date' and 'slug' fields
        base_url: Optional base URL for full URLs
    
    Returns:
        Relative or absolute URL
    """
    date_prefix = datetime.fromisoformat(article['published_date']).strftime('%Y-%m-%d')
    slug = article['slug']
    
    relative_url = f"/articles/{date_prefix}-{slug}.html"
    
    if base_url:
        return urljoin(base_url, relative_url)
    
    return relative_url
```

### Phase 4: Sitemap/RSS Updates

Use the same `get_article_url()` function everywhere. No special logic.

## Migration Strategy

### Step 1: Update Content Processor (1-2 hours)
- Add AI metadata generation function
- Update ProcessedContent model
- Add translation detection
- Test with sample articles

### Step 2: Update Site Generator (30 mins)
- Simplify filename generation
- Remove all complex slug logic
- Use processor-provided metadata only

### Step 3: Regenerate All Content (5 mins)
- Trigger processor to re-process existing articles
- Generate new metadata for all
- Site generator creates new clean filenames

### Step 4: Cleanup (optional)
- Delete old files with "article-" prefix
- Or leave them (will 404 naturally as they age out)

## Data Contract (CRITICAL)

### Processor Output Schema

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "original_title": "米政権内の対中強硬派に焦り",
  "title": "US China Hawks Grow Anxious Over Trump Trade Deals",
  "slug": "us-china-hawks-anxious-trump-trade-deals",
  "published_date": "2025-10-06T09:30:00Z",
  "language": "ja",
  "translated": true,
  "content": "...",
  "seo": {
    "title": "US China Hawks Grow Anxious Over Trump Trade Deals",
    "description": "Senior officials in the US administration express concern over Trump's potential trade agreements with China, signaling internal policy tensions.",
    "keywords": ["trade", "china", "trump", "policy"]
  }
}
```

### Site Generator Requirements

**MUST have from processor:**
- `slug`: URL-safe, ASCII-only, kebab-case
- `published_date`: ISO 8601 format
- `title`: English, 45-60 chars, no special chars

**Site generator does NOT:**
- ❌ Generate slugs
- ❌ Translate titles
- ❌ Clean up hashtags
- ❌ Make SEO decisions

**Site generator ONLY:**
- ✅ Combines date + slug
- ✅ Generates HTML
- ✅ Writes to storage

## Benefits of This Approach

### 1. Clear Separation of Concerns
- **Processor**: AI-powered content intelligence
- **Generator**: Dumb template rendering

### 2. Better Content Quality
- AI-optimized titles for engagement
- Proper translation (not just romanization)
- SEO best practices built-in
- Consistent length/format

### 3. Simpler Generator
- No complex logic
- No fallbacks or guessing
- Easy to test
- Hard to break

### 4. Better URLs
- Clean, readable, shareable
- Date-based (good for SEO)
- ASCII-only (universal compatibility)
- Short and memorable

### 5. Easier Debugging
- One place to fix title issues (processor)
- URLs always match filenames
- Clear data lineage

## Testing Strategy

### Processor Tests
```python
def test_generate_metadata_japanese_title():
    article = {"title": "米政権内の対中強硬派に焦り", "content": "..."}
    result = await generate_article_metadata(article)
    
    assert result["translated"] == True
    assert result["language"] == "ja"
    assert len(result["title"]) <= 60
    assert result["title"].isascii()
    assert "-" in result["slug"]
    assert result["slug"].islower()

def test_generate_metadata_hashtag_title():
    article = {"title": "Gem.coop #technology #blockchain", "content": "..."}
    result = await generate_article_metadata(article)
    
    assert "#" not in result["title"]
    assert len(result["title"]) <= 60
    assert result["slug"].replace("-", "").isalnum()
```

### Generator Tests
```python
def test_generate_filename_from_processor_metadata():
    article = {
        "slug": "nvidia-breaks-barriers-ai",
        "published_date": "2025-10-06T12:00:00Z"
    }
    filename = generate_article_filename(article)
    
    assert filename == "articles/2025-10-06-nvidia-breaks-barriers-ai.html"

def test_url_matches_filename():
    article = {
        "slug": "great-article",
        "published_date": "2025-10-06"
    }
    
    filename = generate_article_filename(article)
    url = get_article_url(article)
    
    assert filename.replace("articles/", "") == url.replace("/articles/", "")
```

## Cost Analysis

### AI Title Generation
- **Model**: GPT-4o-mini
- **Tokens**: ~200 input, ~100 output per article
- **Cost**: ~$0.0001 per article
- **Volume**: 10 articles/day = $0.001/day = $0.03/month

**Verdict**: Negligible cost for massive quality improvement

## Timeline

- **Phase 1** (Processor): 2 hours development + testing
- **Phase 2** (Generator): 30 mins simplification
- **Phase 3** (Integration): 1 hour testing
- **Phase 4** (Deployment): 15 mins

**Total**: ~4 hours for complete solution

## Open Questions

1. **URL Length Limit**: Set at 80 chars total, or allow 100?
2. **Date Format**: YYYY-MM-DD vs YYYYMMDD vs YYYY/MM/DD?
3. **Slug Max Length**: 50 chars? 60 chars?
4. **Translation Service**: OpenAI only, or add DeepL as backup?
5. **Backward Compatibility**: Keep old URLs? Add redirects?

## Decision Points

### Recommended Decisions
- ✅ Use YYYY-MM-DD format (readable, sortable)
- ✅ Max slug length: 50 chars (leaves room for date)
- ✅ OpenAI only (already integrated)
- ✅ No redirects (old URLs can 404, content is ephemeral news)
- ✅ Max total URL: 80 chars (conservative)

## Next Steps

1. **Review & Approve** this design
2. **Update content-processor** to generate metadata
3. **Simplify site-generator** to use metadata
4. **Test** with sample articles
5. **Deploy** and regenerate all content
6. **Monitor** for any issues

---

**Key Principle**: Move intelligence upstream (processor), keep generation dumb (generator).
