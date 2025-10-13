# Stock Images Implementation Plan
**Created**: October 13, 2025  
**Priority**: HIGH - Visual appeal for articles and site  
**Approach**: Stock photos (Unsplash/Pexels) - FREE, fast, professional

---

## Goal
Add relevant, professional images to:
1. **Article pages** - Hero image at top of each article
2. **Index page** - Thumbnail for each article card
3. **Site-wide** - Featured images, backgrounds where appropriate

---

## Stock Photo API Comparison

### Unsplash API ⭐ RECOMMENDED
- **Free tier**: 50 requests/hour
- **Quality**: Exceptional - professional photography
- **Library**: 3+ million high-res photos
- **License**: Free to use, attribution required (can waive for premium)
- **Search**: Keyword-based, very relevant results
- **API**: Simple REST API, well-documented

**Example**:
```bash
# Search for "artificial intelligence"
GET https://api.unsplash.com/search/photos?query=artificial+intelligence&per_page=1

# Returns: High-res photo URL, photographer credit, etc.
```

### Pexels API (Alternative)
- **Free tier**: Unlimited requests (rate limited)
- **Quality**: Good - mix of professional and stock
- **Library**: 3+ million photos + videos
- **License**: Free to use, attribution optional
- **Search**: Keyword-based
- **API**: Simple REST API

### Pixabay API (Alternative)
- **Free tier**: 100 requests/minute
- **Quality**: Variable - user-submitted content
- **Library**: 2.7+ million images
- **License**: Public domain (CC0)
- **API**: Simple REST API

**Recommendation**: **Unsplash** for best quality + professional look

---

## Architecture: Where Images Get Added

### Current Pipeline
```
content-collector → content-processor → markdown-generator → site-publisher
                         ↓                      ↓                  ↓
                    [processes JSON]    [creates markdown]    [builds HTML]
```

### Where to Add Images
**Option 1: In markdown-generator** ⭐ RECOMMENDED
```
markdown-generator:
  1. Receive processed article JSON
  2. Extract keywords/topic for image search
  3. Fetch image from Unsplash
  4. Download and store in blob storage
  5. Add image URLs to frontmatter
  6. Generate markdown with image metadata
```

**Why here?**
- ✅ Separation of concerns (markdown gen = content preparation)
- ✅ Images stored with markdown (atomic operation)
- ✅ Easy to retry if image fetch fails
- ✅ Doesn't slow down content processing

**Option 2: In content-processor** (Not recommended)
- ❌ Couples image fetching with content analysis
- ❌ Slows down processor (images = I/O bound)
- ❌ Harder to debug/retry

**Option 3: In site-publisher** (Too late)
- ❌ Site publisher should only build, not fetch external data
- ❌ Slows down site builds
- ❌ Violates functional boundaries

---

## Implementation Plan

### Phase 1: Unsplash Client (markdown-generator)
**Time estimate**: 2-3 hours

Create new service for image fetching:

```python
# containers/markdown-generator/services/image_service.py

import aiohttp
import logging
from typing import Optional, Dict, Any
from urllib.parse import quote

logger = logging.getLogger(__name__)

class StockImageService:
    """Fetch stock images from Unsplash API."""
    
    def __init__(self, access_key: str):
        """
        Initialize Unsplash client.
        
        Args:
            access_key: Unsplash API access key from Key Vault
        """
        self.access_key = access_key
        self.base_url = "https://api.unsplash.com"
    
    async def search_image(
        self,
        query: str,
        orientation: str = "landscape"
    ) -> Optional[Dict[str, Any]]:
        """
        Search for relevant image by keywords.
        
        Args:
            query: Search query (article topic, keywords)
            orientation: "landscape" (hero), "portrait", "squarish" (thumbnail)
        
        Returns:
            {
                "url": "https://images.unsplash.com/...",
                "url_regular": "1080px wide",
                "url_small": "400px wide (thumbnail)",
                "photographer": "Jane Doe",
                "photographer_url": "https://unsplash.com/@janedoe",
                "description": "Photo of...",
                "color": "#C0FFEE"  # Dominant color
            }
        """
        try:
            # Clean query for search
            clean_query = query[:100]  # Limit length
            
            async with aiohttp.ClientSession() as session:
                params = {
                    "query": clean_query,
                    "per_page": 1,  # Only need top result
                    "orientation": orientation,
                    "content_filter": "high"  # Family-friendly only
                }
                headers = {
                    "Authorization": f"Client-ID {self.access_key}"
                }
                
                url = f"{self.base_url}/search/photos"
                
                async with session.get(url, params=params, headers=headers) as resp:
                    if resp.status != 200:
                        logger.error(f"Unsplash API error: {resp.status}")
                        return None
                    
                    data = await resp.json()
                    
                    if not data.get("results"):
                        logger.warning(f"No images found for query: {query}")
                        return None
                    
                    # Extract first result
                    photo = data["results"][0]
                    
                    return {
                        "url": photo["urls"]["raw"],  # Full resolution
                        "url_regular": photo["urls"]["regular"],  # 1080px
                        "url_small": photo["urls"]["small"],  # 400px
                        "photographer": photo["user"]["name"],
                        "photographer_url": photo["user"]["links"]["html"],
                        "description": photo.get("description") or photo.get("alt_description", ""),
                        "color": photo.get("color", "#808080"),
                        "unsplash_url": photo["links"]["html"]
                    }
        
        except Exception as e:
            logger.error(f"Failed to fetch image: {e}")
            return None
    
    async def download_image(
        self,
        image_url: str,
        output_path: str
    ) -> bool:
        """
        Download image to local file.
        
        Args:
            image_url: Full image URL from Unsplash
            output_path: Local file path to save image
        
        Returns:
            True if successful, False otherwise
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as resp:
                    if resp.status != 200:
                        logger.error(f"Failed to download image: {resp.status}")
                        return False
                    
                    content = await resp.read()
                    
                    with open(output_path, "wb") as f:
                        f.write(content)
                    
                    logger.info(f"Downloaded image to {output_path}")
                    return True
        
        except Exception as e:
            logger.error(f"Failed to download image: {e}")
            return False
    
    def extract_keywords_from_article(
        self,
        title: str,
        content: str,
        tags: list[str] = None
    ) -> str:
        """
        Extract search keywords from article metadata.
        
        Prioritizes:
        1. Tags (if available)
        2. First 3 words of title
        3. Fallback to generic tech terms
        
        Args:
            title: Article title
            content: Article content (first 200 chars)
            tags: Article tags/categories
        
        Returns:
            Search query string
        """
        # Use tags if available
        if tags:
            return " ".join(tags[:2])  # Max 2 tags for relevance
        
        # Extract meaningful words from title
        stopwords = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for"}
        words = [w.lower() for w in title.split() if w.lower() not in stopwords]
        
        if words:
            return " ".join(words[:3])  # First 3 meaningful words
        
        # Fallback
        return "technology"
```

**Usage in markdown generator**:
```python
# In containers/markdown-generator/main.py or article_generator.py

async def generate_article_with_images(article_data: dict):
    """Generate markdown with hero image and thumbnail."""
    
    # Initialize image service
    unsplash_key = await get_secret("unsplash-access-key")
    image_service = StockImageService(unsplash_key)
    
    # Extract keywords for image search
    query = image_service.extract_keywords_from_article(
        title=article_data["title"],
        content=article_data.get("content", "")[:200],
        tags=article_data.get("tags", [])
    )
    
    # Fetch hero image (landscape)
    hero_image = await image_service.search_image(
        query=query,
        orientation="landscape"
    )
    
    if hero_image:
        # Store image URLs in frontmatter
        article_data["hero_image"] = hero_image["url_regular"]
        article_data["thumbnail"] = hero_image["url_small"]
        article_data["image_alt"] = hero_image["description"]
        article_data["image_credit"] = hero_image["photographer"]
        article_data["image_credit_url"] = hero_image["photographer_url"]
        
        logger.info(f"Added image for article: {article_data['title']}")
    else:
        logger.warning(f"No image found for: {article_data['title']}")
    
    # Generate markdown with image metadata
    return generate_markdown(article_data)
```

---

### Phase 2: Frontmatter Schema (markdown-generator)
**Time estimate**: 30 minutes

Update markdown frontmatter to include image fields:

```yaml
---
title: "Understanding Quantum Computing"
date: 2025-10-13T14:30:00Z
slug: understanding-quantum-computing
tags: ["quantum", "computing", "technology"]

# Image metadata (NEW)
hero_image: "https://images.unsplash.com/photo-xyz?w=1080"
thumbnail: "https://images.unsplash.com/photo-xyz?w=400"
image_alt: "Quantum computer in laboratory setting"
image_credit: "John Photographer"
image_credit_url: "https://unsplash.com/@johnphoto"
image_dominant_color: "#2C5F8D"

# Existing fields
description: "An introduction to quantum computing concepts..."
author: "AI Content Farm"
---
```

---

### Phase 3: Hugo Template Updates (site-publisher)
**Time estimate**: 1-2 hours

Update PaperMod theme templates to display images:

#### Article Page (single.html)
```html
<!-- containers/site-publisher/themes/PaperMod/layouts/_default/single.html -->

<article class="post-single">
  <header class="post-header">
    <!-- Hero Image (NEW) -->
    {{ if .Params.hero_image }}
    <div class="post-hero-image">
      <img 
        src="{{ .Params.hero_image }}" 
        alt="{{ .Params.image_alt | default .Title }}"
        loading="lazy"
        style="width: 100%; height: auto; border-radius: 8px;"
      />
      {{ if .Params.image_credit }}
      <p class="image-credit" style="font-size: 0.85em; color: #666; margin-top: 0.5em;">
        Photo by 
        <a href="{{ .Params.image_credit_url }}" target="_blank" rel="noopener">
          {{ .Params.image_credit }}
        </a>
        on 
        <a href="https://unsplash.com" target="_blank" rel="noopener">Unsplash</a>
      </p>
      {{ end }}
    </div>
    {{ end }}
    
    <h1 class="post-title">{{ .Title }}</h1>
    <!-- ... rest of header ... -->
  </header>
  
  <div class="post-content">
    {{ .Content }}
  </div>
</article>
```

#### Index Page (list.html)
```html
<!-- containers/site-publisher/themes/PaperMod/layouts/_default/list.html -->

<div class="post-entry">
  {{ if .Params.thumbnail }}
  <div class="post-thumbnail">
    <a href="{{ .Permalink }}">
      <img 
        src="{{ .Params.thumbnail }}" 
        alt="{{ .Title }}"
        loading="lazy"
        style="width: 100%; height: 200px; object-fit: cover; border-radius: 8px;"
      />
    </a>
  </div>
  {{ end }}
  
  <header class="entry-header">
    <h2>
      <a href="{{ .Permalink }}">{{ .Title }}</a>
    </h2>
  </header>
  
  <div class="entry-content">
    {{ .Summary }}
  </div>
  
  <footer class="entry-footer">
    <time>{{ .Date.Format "January 2, 2006" }}</time>
  </footer>
</div>
```

---

### Phase 4: Infrastructure (Terraform + Key Vault)
**Time estimate**: 30 minutes

#### Add Unsplash API Key to Key Vault
```bash
# Get Unsplash API key from https://unsplash.com/developers
# Create app, get "Access Key"

az keyvault secret set \
  --vault-name "ai-content-prod-kv" \
  --name "unsplash-access-key" \
  --value "YOUR_ACCESS_KEY_HERE"
```

#### Update markdown-generator to read secret
```terraform
# infra/container_app_markdown_generator.tf

resource "azurerm_container_app" "markdown_generator" {
  # ... existing config ...
  
  secret {
    name  = "unsplash-access-key"
    value = azurerm_key_vault_secret.unsplash_access_key.value
  }
  
  template {
    container {
      # ... existing config ...
      
      env {
        name        = "UNSPLASH_ACCESS_KEY"
        secret_name = "unsplash-access-key"
      }
    }
  }
}
```

```terraform
# infra/key_vault.tf

resource "azurerm_key_vault_secret" "unsplash_access_key" {
  name         = "unsplash-access-key"
  value        = var.unsplash_access_key  # Set via GitHub secrets
  key_vault_id = azurerm_key_vault.main.id
  
  content_type = "api-key"
  
  tags = merge(local.common_tags, {
    purpose = "Stock image API access"
  })
}
```

---

## Testing Strategy

### Local Testing
```python
# Test image service locally
import asyncio
from services.image_service import StockImageService

async def test_image_search():
    service = StockImageService(access_key="YOUR_TEST_KEY")
    
    # Test search
    result = await service.search_image("artificial intelligence")
    print(f"Found image: {result['url_regular']}")
    print(f"Photographer: {result['photographer']}")
    
    # Test keyword extraction
    keywords = service.extract_keywords_from_article(
        title="The Future of AI in Healthcare",
        content="",
        tags=["AI", "healthcare"]
    )
    print(f"Keywords: {keywords}")

asyncio.run(test_image_search())
```

### Integration Testing
1. Process one article through markdown-generator
2. Check markdown frontmatter has image URLs
3. Build site with site-publisher
4. Verify hero image displays on article page
5. Verify thumbnail displays on index page

---

## Quick Wins Timeline

### Day 1 (Today): Setup & Prototype
- [ ] Sign up for Unsplash API (5 min)
- [ ] Create `image_service.py` in markdown-generator (1 hour)
- [ ] Test image search locally (30 min)
- [ ] Add Unsplash key to Key Vault (15 min)

### Day 2: Integration
- [ ] Update markdown-generator to fetch images (1 hour)
- [ ] Update frontmatter schema (30 min)
- [ ] Test with 3-5 sample articles (1 hour)

### Day 3: Hugo Templates
- [ ] Update single.html for hero images (1 hour)
- [ ] Update list.html for thumbnails (30 min)
- [ ] CSS tweaks for responsive images (30 min)
- [ ] Test on mobile and desktop (30 min)

### Day 4: Deploy & Verify
- [ ] Deploy updated containers via CI/CD
- [ ] Generate 10+ articles with images
- [ ] Verify images load correctly
- [ ] Check attribution links work
- [ ] Monitor API usage (should be <50 req/hour)

**Total time**: ~8 hours spread over 4 days

---

## Cost & Rate Limits

### Unsplash Free Tier
- **50 requests/hour** = ~1,200 requests/day
- **No cost** for API usage
- **Attribution required** (automated in template)

### Expected Usage
- **Article generation**: ~10-20 articles/day
- **Image requests**: 1 per article = 10-20 req/day
- **Well within limits**: <5% of daily quota

### Fallback Strategy
If API limit hit (unlikely):
1. Use cached generic images per topic category
2. Queue image fetching for later retry
3. Generate articles without images (still functional)

---

## Future Enhancements (Not Now)

### Phase 5: Image Optimization (Later)
- Resize images to optimal dimensions
- Convert to WebP format for faster loading
- Generate multiple sizes (srcset) for responsive images
- Cache images in CDN

### Phase 6: Smarter Image Selection (Later)
- Use AI to analyze article content for better keywords
- Select images based on dominant colors (theme matching)
- A/B test image relevance (click-through rates)

### Phase 7: Image Storage (Later)
- Download and store images in blob storage (reduce Unsplash dependency)
- Create image blob container
- Serve via CDN for faster loading

**For now**: Direct Unsplash URLs are fine (fast, reliable, free CDN)

---

## Next Steps

**Ready to start?** I can:

1. **Create the image service** (`image_service.py`) right now
2. **Sign up for Unsplash API** (you do this - takes 5 min)
3. **Test locally** with sample article
4. **Deploy** once proven

**Want me to start coding the image service?** It's a clean, self-contained module that won't break anything existing.
