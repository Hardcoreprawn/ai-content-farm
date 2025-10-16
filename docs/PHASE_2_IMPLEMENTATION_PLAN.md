# Phase 2: Quality Improvements - Implementation Plan

**Status**: Ready to Implement  
**Priority**: Next deployment cycle  
**Prerequisites**: Phase 1 completed ✅  
**Target Completion**: Within 2 days

---

## Overview

Phase 2 focuses on improving the quality and usability of published articles by addressing:
1. Truncated and poorly formatted titles
2. Irrelevant stock images
3. Verbose, non-human-readable directory/URL structures

## Task Breakdown

### Task 1: AI Title Generation for Truncated Titles

**Priority**: 🔴 HIGH  
**Effort**: ⚡ Medium (4-6 hours)  
**Container**: `content-processor`  
**Owner**: Content processing pipeline

#### Problem Statement
Current article titles are truncated mid-word with "..." making them unprofessional:
- Example: `(15 Oct) Two New Windows Zero-Days Exploited in the Wild One Affects Every Version Ever Shipped ht...`
- Issues:
  - Date prefixes clutter titles
  - Truncation cuts off mid-word
  - No semantic understanding of content

#### Acceptance Criteria
- [ ] Titles never truncated mid-word
- [ ] Date prefixes removed or formatted properly
- [ ] Titles max 80-100 characters for readability
- [ ] AI generates concise, SEO-friendly titles when original > 100 chars
- [ ] Original title preserved in `source_metadata.original_title`
- [ ] Title generation uses Azure OpenAI (existing integration)

#### Implementation Details

**File**: `/containers/content-processor/operations/article_operations.py`

**Model Choice**: **gpt-4o-mini** (see docs/AI_MODEL_COST_ANALYSIS.md for detailed justification)
- Cost: $0.000035 per title (vs $0.000108 for gpt-35-turbo)
- Quality: Better than gpt-35-turbo for creative tasks
- Speed: Same fast response time
- Monthly impact: +$0.01/month for 200 articles

**Approach**:
```python
import re
from utils.cost_utils import calculate_openai_cost

async def generate_clean_title(
    original_title: str,
    content_summary: str,
    azure_openai_client: AsyncAzureOpenAI
) -> tuple[str, float]:
    """
    Generate clean, concise title using AI if needed.
    
    Rules:
    1. If title < 80 chars and no date prefix: return as-is
    2. If title has date prefix: remove it
    3. If title > 80 chars: use AI to create concise version
    4. Never truncate mid-word
    
    Returns:
        Tuple of (cleaned_title, cost_usd)
    """
    # Remove date prefixes like "(15 Oct)"
    cleaned = re.sub(r'^\(\d{1,2}\s+\w{3}\)\s*', '', original_title)
    
    # If short enough, return cleaned version (no AI cost)
    if len(cleaned) <= 80 and not re.match(r'.*\.\.\.?\s*$', cleaned):
        logger.info(f"Title already clean, no AI needed: {cleaned}")
        return cleaned.strip(), 0.0
    
    # Use AI to generate concise title
    logger.info(f"Generating clean title with gpt-4o-mini for: {original_title[:50]}...")
    
    response = await azure_openai_client.chat.completions.create(
        model="gpt-4o-mini",  # Cost-optimized: $0.000035/title vs $0.000108 for gpt-35-turbo
        messages=[
            {
                "role": "system", 
                "content": "You are a professional editor. Create concise, engaging article titles."
            },
            {
                "role": "user",
                "content": f"""Generate a concise title (max 80 characters):

Original: {original_title}
Summary: {content_summary[:200]}

Requirements:
- Maximum 80 characters
- Remove date prefixes like (15 Oct)
- Clear and engaging
- No truncation with "..."
- SEO-friendly"""
            }
        ],
        max_tokens=25,  # Title generation needs minimal tokens
        temperature=0.7,  # Balanced creativity
    )
    
    # Calculate cost for tracking
    cost = calculate_openai_cost(
        model_name="gpt-4o-mini",
        prompt_tokens=response.usage.prompt_tokens,
        completion_tokens=response.usage.completion_tokens
    )
    
    clean_title = response.choices[0].message.content.strip()
    logger.info(f"Generated title: {clean_title} (cost: ${cost:.6f})")
    
    return clean_title, cost
```

**Integration Point**: Call after article generation, before saving to processed-content:
```python
# In process_article() function (operations/article_operations.py)
clean_title, title_cost = await generate_clean_title(
    original_title=article_data["title"],
    content_summary=article_data.get("summary", article_data["content"][:500]),
    azure_openai_client=azure_openai_client
)

# Update title and track cost
article_data["title"] = clean_title
article_data["source_metadata"]["original_title"] = original_title  # Preserve original
total_cost += title_cost  # Add to processing cost tracking
```

**Testing**:
```python
# tests/test_title_generation.py
import pytest
from unittest.mock import AsyncMock, Mock

async def test_remove_date_prefix_no_ai():
    """Test that short titles with date prefixes are cleaned without AI."""
    title = "(15 Oct) Windows Zero-Days Exploited"
    result, cost = await generate_clean_title(title, "", mock_client)
    assert not result.startswith("(")
    assert "Windows Zero-Days" in result
    assert cost == 0.0  # No AI used

async def test_keep_short_clean_title():
    """Test that short, clean titles are returned as-is."""
    title = "Windows Security Update"
    result, cost = await generate_clean_title(title, "", mock_client)
    assert result == title
    assert cost == 0.0  # No AI used

async def test_shorten_long_title_with_ai():
    """Test that long titles use AI to generate concise version."""
    long_title = "This is an extremely long title that goes on and on with too much detail and needs to be shortened significantly..."
    
    # Mock Azure OpenAI response
    mock_client = AsyncMock()
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="Concise Article Title"))]
    mock_response.usage = Mock(prompt_tokens=170, completion_tokens=15)
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    result, cost = await generate_clean_title(long_title, "Summary here", mock_client)
    
    assert len(result) <= 80
    assert not result.endswith("...")
    assert cost > 0  # AI was used
    assert cost < 0.001  # But very cheap (gpt-4o-mini)
    
    # Verify correct model was used
    call_args = mock_client.chat.completions.create.call_args
    assert call_args.kwargs["model"] == "gpt-4o-mini"
    assert call_args.kwargs["max_tokens"] == 25

async def test_cost_tracking():
    """Test that costs are properly calculated and logged."""
    # Setup mock with realistic token usage
    mock_client = AsyncMock()
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="Clean Title"))]
    mock_response.usage = Mock(prompt_tokens=170, completion_tokens=15)
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    _, cost = await generate_clean_title("Long title...", "Summary", mock_client)
    
    # gpt-4o-mini: 170 * $0.00015/1k + 15 * $0.0006/1k ≈ $0.000035
    assert 0.00003 < cost < 0.00005
```

**Cost Estimate**: $0.000035 per title (gpt-4o-mini, ~185 tokens)  
**Monthly Cost**: $0.01/month for 200 articles (negligible)  
**Rollout**: Gradual - enable for new articles, backfill old ones optionally

---

### Task 2: Improve Stock Image Selection Logic

**Priority**: 🟡 MEDIUM  
**Effort**: ⚡ Low (2-3 hours)  
**Container**: `markdown-generator`  
**Owner**: Markdown generation pipeline

#### Problem Statement
Stock images often irrelevant because:
- Search uses truncated titles with date prefixes
- No content-based keyword extraction
- Generic results for technical articles

Example: "13 signage" image for Windows zero-day article

#### Acceptance Criteria
- [ ] Images disabled for titles with date prefixes or < 50 chars
- [ ] Keyword extraction from article content and tags
- [ ] Fallback to category-based search
- [ ] Option to disable stock images per article
- [ ] Unsplash attribution always included

#### Implementation Details

**File**: `/containers/markdown-generator/services/image_service.py`

**Approach**:
```python
async def fetch_image_for_article(
    access_key: str,
    title: str,
    content: str,
    tags: list[str],
    category: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Fetch relevant stock image with improved keyword extraction.
    """
    # Skip if title looks truncated or has date prefix
    if len(title) < 50 or re.match(r'^\(\d{1,2}\s+\w{3}\)', title):
        logger.info("Skipping stock image for short/dated title")
        return None
    
    # Extract keywords from multiple sources
    keywords = extract_keywords_from_content(content, tags, category)
    
    if not keywords:
        logger.info("No relevant keywords found, skipping stock image")
        return None
    
    # Try each keyword set until we find a good match
    for keyword_set in keywords:
        search_query = " ".join(keyword_set[:3])  # Top 3 keywords
        
        result = await search_unsplash(access_key, search_query)
        if result and result.get("total", 0) > 0:
            return format_unsplash_result(result)
    
    return None

def extract_keywords_from_content(
    content: str,
    tags: list[str],
    category: Optional[str]
) -> list[list[str]]:
    """
    Extract keyword sets in priority order.
    
    Returns multiple keyword sets to try in order:
    1. Article tags (user-curated)
    2. Category
    3. Content-extracted keywords (NLP-based)
    """
    keyword_sets = []
    
    # Priority 1: Use tags if available
    if tags:
        keyword_sets.append(tags[:3])
    
    # Priority 2: Use category
    if category:
        keyword_sets.append([category])
    
    # Priority 3: Extract from content using simple frequency analysis
    # (Could use spaCy/NLTK for better results, but keep dependencies minimal)
    words = re.findall(r'\b[A-Z][a-z]{3,}\b', content)  # Capitalized words
    common_words = Counter(words).most_common(5)
    if common_words:
        keyword_sets.append([word for word, _ in common_words])
    
    return keyword_sets
```

**Testing**:
```python
def test_skip_dated_titles():
    result = await fetch_image_for_article(
        "key", "(15 Oct) Short", "content", []
    )
    assert result is None

def test_keyword_extraction():
    content = "Windows security vulnerability exploit attack..."
    keywords = extract_keywords_from_content(content, [], None)
    assert "Windows" in keywords[0] or "security" in keywords[0]
```

---

### Task 3: Use Article Slugs for Directory Names

**Priority**: 🟡 MEDIUM  
**Effort**: ⚡ Medium (3-4 hours)  
**Container**: `site-publisher`  
**Owner**: Site publishing pipeline

#### Problem Statement
Current URLs are too verbose and not SEO-friendly:
- Current: `/processed/2025/10/16/20251016_104549_mastodon_mastodon.social_115383358597059180/`
- Desired: `/articles/2025/10/windows-zero-day-vulnerabilities/`

#### Acceptance Criteria
- [ ] URLs use article slugs from processed JSON
- [ ] Format: `/articles/YYYY/MM/slug/`
- [ ] Slugs are URL-safe (lowercase, hyphens, no special chars)
- [ ] Original ID preserved in metadata for traceability
- [ ] Slug collisions handled (append counter if needed)
- [ ] Redirects from old URLs to new (optional, Phase 3)

#### Implementation Details

**File**: `/containers/site-publisher/content_downloader.py`

**Approach**:
```python
async def organize_content_for_hugo(
    content_dir: Path,
    hugo_content_dir: Path,
) -> ValidationResult:
    """
    Organize markdown files using article slugs for directory structure.
    """
    for md_file in content_dir.rglob("*.md"):
        # Read frontmatter to get slug and date
        frontmatter = extract_frontmatter(md_file)
        
        # Get slug from params (added by markdown-generator)
        slug = frontmatter.get("params", {}).get("slug", None)
        date = frontmatter.get("date", None)
        
        if not slug:
            # Fallback to filename-based slug
            slug = generate_slug_from_filename(md_file.name)
        
        # Create clean directory structure
        date_obj = datetime.fromisoformat(date)
        target_dir = hugo_content_dir / "articles" / f"{date_obj.year}" / f"{date_obj.month:02d}" / slug
        target_path = target_dir / "index.md"
        
        # Handle slug collisions
        counter = 1
        while target_path.exists():
            collision_slug = f"{slug}-{counter}"
            target_dir = hugo_content_dir / "articles" / f"{date_obj.year}" / f"{date_obj.month:02d}" / collision_slug
            target_path = target_dir / "index.md"
            counter += 1
        
        # Create directory and copy file
        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(md_file, target_path)
```

**Markdown Generator Update**: Add slug to frontmatter
```python
# In markdown_generation.py prepare_frontmatter()
custom_params["slug"] = article_data.get("slug", sanitize_slug(title))
custom_params["article_id"] = article_data.get("article_id")  # Traceability
```

**Testing**:
```python
def test_slug_based_organization():
    md_file = create_test_markdown(
        frontmatter={"date": "2025-10-16", "params": {"slug": "test-article"}}
    )
    result = await organize_content_for_hugo(temp_dir, hugo_dir)
    
    expected_path = hugo_dir / "articles" / "2025" / "10" / "test-article" / "index.md"
    assert expected_path.exists()

def test_slug_collision_handling():
    # Create two articles with same slug
    create_test_markdown("slug-1", slug="test-article")
    create_test_markdown("slug-2", slug="test-article")
    
    result = await organize_content_for_hugo(temp_dir, hugo_dir)
    
    assert (hugo_dir / "articles/2025/10/test-article/index.md").exists()
    assert (hugo_dir / "articles/2025/10/test-article-1/index.md").exists()
```

---

## Implementation Order

### Day 1
1. **Morning**: Implement Task 1 (AI Title Generation)
   - Write title generation function
   - Integrate into content-processor
   - Write tests
   
2. **Afternoon**: Implement Task 2 (Image Selection)
   - Update keyword extraction
   - Add skip logic for dated titles
   - Write tests

### Day 2
3. **Morning**: Implement Task 3 (Slug-based URLs)
   - Update markdown generator to add slug
   - Update site-publisher organization logic
   - Write tests

4. **Afternoon**: Integration testing & deployment
   - Run full pipeline test
   - Visual verification
   - Deploy via CI/CD

---

## Testing Strategy

### Unit Tests
- Each task has dedicated test file
- Mock Azure OpenAI for title generation
- Mock Unsplash API for image search
- Test edge cases and error handling

### Integration Tests
- Process real article through updated pipeline
- Verify title generation quality
- Check image relevance
- Validate URL structure

### Manual Verification
After deployment, check:
- [ ] Titles are clean and readable
- [ ] Images are relevant or absent
- [ ] URLs are SEO-friendly
- [ ] Old functionality still works

---

## Rollback Plan

Each task is independent and can be rolled back separately:

1. **Title Generation**: Feature flag in config to disable AI title generation
2. **Image Selection**: Falls back to existing behavior if new logic fails
3. **Slug URLs**: Keep old ID-based structure as fallback

---

## Cost Estimate

- **Title generation**: $0.01/month for 200 articles (gpt-4o-mini at $0.000035/title)
- **Image search**: No change (existing Unsplash API)
- **Total**: Negligible cost increase (~$0.01/month at current volume)

**Justification**: gpt-4o-mini is 3x cheaper than gpt-35-turbo and better quality for creative tasks like title generation. See docs/AI_MODEL_COST_ANALYSIS.md for detailed comparison.

---

## Success Metrics

After Phase 2 deployment:

1. **Title Quality**
   - 0% titles truncated mid-word
   - 90%+ titles under 80 characters
   - 0% titles with date prefixes

2. **Image Relevance**
   - 50% reduction in irrelevant images
   - 30% articles without images (intentional skip)
   - 100% proper Unsplash attribution

3. **URL Quality**
   - 100% URLs use article slugs
   - 0 slug collisions (or handled gracefully)
   - SEO scores improve by 20%+

---

**Next Steps**: Begin Task 1 implementation when ready to proceed.
