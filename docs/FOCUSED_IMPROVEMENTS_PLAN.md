# Focused Improvements Plan
**Created**: October 13, 2025  
**Status**: Active Development Roadmap  
**Based on**: User priorities post-infrastructure completion

---

## Executive Summary

System is **operational and deployed** with working collection, processing, and publishing pipeline. Focus now shifts from infrastructure to **content quality, security, and feature enhancements**.

### Priority Order
1. **Security** - Quick dependency updates (HIGH severity fixes)
2. **Reddit Recovery** - Get locked-out content source working again
3. **Content Quality** - Fix dry writing with multi-prompt approach
4. **Images** - Visual enhancement for articles and index
5. **Audio** - Multi-voice transcripts for accessibility/convenience

---

## 1. Security Updates (Quick Win) 🔒

**Timeline**: 1-2 days  
**Priority**: CRITICAL  
**Effort**: Low

### Current Vulnerabilities
- **authlib 1.6.4** → 1.6.5 (HIGH: CVE-2025-61920 - DoS via oversized JOSE segments)
- **aiohttp <3.12.14** → 3.12.14+ (LOW: HTTP request smuggling)

### Files to Update
```
containers/content-collector/requirements.txt    (aiohttp~=3.11.11)
containers/content-processor/requirements.txt    (aiohttp~=3.13.0)
containers/markdown-generator/requirements.txt   (aiohttp>=3.9.0,<4.0.0)
containers/site-publisher/requirements.txt       (aiohttp~=3.11.11)
```

### Action Items
- [ ] Update all aiohttp to `aiohttp>=3.12.14,<4.0.0` (consistent across containers)
- [ ] Add authlib to any containers using OAuth/JWT (check if needed)
- [ ] Run tests in each container: `PYTHONPATH=/workspaces/ai-content-farm python -m pytest tests/ -v`
- [ ] Update CI/CD to catch dependency vulnerabilities earlier (Dependabot auto-merge for patches?)

### Success Criteria
- ✅ All Dependabot alerts resolved
- ✅ All container tests passing
- ✅ No breaking changes introduced

---

## 2. Reddit Authentication Recovery 🔄

**Timeline**: 3-5 days  
**Priority**: HIGH  
**Effort**: Medium

### Problem Statement
- Locked out of Reddit API for "over using" or "bad credentials"
- Mastodon content is better aligned with goals than RSS/web sources
- Reddit still valuable for specific tech subreddits

### Investigation Steps
1. **Review existing Reddit client**: `/workspaces/ai-content-farm/containers/content-collector/reddit_client.py`
2. **Check configuration**: What credentials are stored in Key Vault?
3. **PRAW rate limiting**: Default PRAW has conservative limits - are we respecting them?
4. **Lockout cause**: Was it rate limiting or credential issues?

### Implementation Plan
- [ ] **Audit current Reddit integration**
  - Review `reddit_client.py` for rate limiting implementation
  - Check Key Vault for Reddit credentials (client_id, client_secret, user_agent)
  - Review logs for Reddit API error messages
  
- [ ] **Implement sustainable Reddit collection**
  - Use `sustainable-reddit.json` template as baseline
  - Add exponential backoff on rate limit errors (PRAW handles this, but verify)
  - Implement request throttling: Max 60 requests/minute (Reddit limit)
  - Add retry logic with proper error handling
  
- [ ] **Test Reddit re-authentication**
  - Create fresh Reddit app credentials at https://www.reddit.com/prefs/apps
  - Update Key Vault secrets
  - Test with small subreddit collection (r/Python, r/programming)
  - Monitor for 24 hours to ensure no lockout

### Files to Modify
```
containers/content-collector/reddit_client.py           (rate limiting, auth)
containers/content-collector/collectors/reddit_collector.py  (if exists)
collection-templates/sustainable-reddit.json            (tune parameters)
infra/terraform/secrets.tf                              (verify Key Vault config)
```

### Success Criteria
- ✅ Reddit API authentication working
- ✅ Successfully collect from 3-5 subreddits over 24 hours
- ✅ No rate limit errors or lockouts
- ✅ Reddit content appears in pipeline alongside Mastodon

---

## 3. Content Quality Improvements 📝

**Timeline**: 1-2 weeks  
**Priority**: HIGH  
**Effort**: Medium-High

### Problem Statement
Current articles are "quite dry" - single prompt generates everything (title, body, metadata) in one pass, resulting in formulaic, unengaging content.

### Solution: Multi-Prompt Article Generation

#### Current Flow (Single Prompt)
```
Topic → OpenAI (one call) → Complete Article (title + body + metadata)
```

#### Proposed Flow (Multi-Prompt)
```
Topic + Sources → 
  1. Content Brief (outline, key points, angle) →
  2. Article Body (deep writing focus) →
  3. Title Generation (multiple options, pick best) →
  4. Metadata Generation (SEO, description, tags)
```

### Implementation Strategy

#### Phase 1: Separate Prompts (Week 1)
- [ ] **Create new prompt functions** in `containers/content-processor/openai_operations.py`:
  ```python
  build_content_brief_prompt(topic, sources, target_length)
  build_article_body_prompt(topic, brief, sources, target_length)
  build_title_generation_prompt(article_body, variants=5)
  build_metadata_prompt(title, article_body, sources)
  ```

- [ ] **Update ArticleGenerationService** (`services/article_generation.py`):
  ```python
  async def generate_article_from_topic_v2(topic_metadata):
      # Step 1: Generate content brief
      brief = await openai_client.generate_completion(
          prompt=build_content_brief_prompt(...)
      )
      
      # Step 2: Generate article body with brief as context
      article_body = await openai_client.generate_article(
          prompt=build_article_body_prompt(topic, brief, ...)
      )
      
      # Step 3: Generate multiple title options, pick best
      titles = await openai_client.generate_completion(
          prompt=build_title_generation_prompt(article_body, variants=5)
      )
      best_title = select_best_title(titles, article_body)
      
      # Step 4: Generate metadata with final title and body
      metadata = await metadata_generator.generate_metadata(
          title=best_title, content=article_body
      )
      
      return assemble_article(title, article_body, metadata)
  ```

- [ ] **Add writer personalities** (already exists in `content_generation.py` - leverage this):
  - **Enthusiast**: Excited, engaging, highlights innovation and possibilities
  - **Skeptic**: Critical thinking, challenges assumptions, balanced analysis
  - **Explainer**: Clear, educational, breaks down complex topics for accessibility
  
  Rotate between personalities or assign based on topic type.

#### Phase 2: Content Depth Variants (Week 2)
- [ ] **Implement two article lengths**:
  - **Highlights** (500-800 words): Quick overview, key takeaways, 5-min read
  - **In-Depth** (2500-3500 words): Comprehensive analysis, detailed sections, 15-min read

- [ ] **Update data model** to support article variants:
  ```python
  class ArticleVariant(str, Enum):
      HIGHLIGHTS = "highlights"
      IN_DEPTH = "in-depth"
  
  # Generate both variants for high-priority topics
  if topic.priority_score > 0.8:
      highlights_article = await generate_article(..., variant="highlights")
      indepth_article = await generate_article(..., variant="in-depth")
  ```

- [ ] **Update markdown-generator** to handle both variants:
  - Generate separate markdown files: `{slug}-highlights.md`, `{slug}-indepth.md`
  - Link between variants in frontmatter
  - Site navigation shows both options

### Files to Modify
```
containers/content-processor/openai_operations.py      (new prompt builders)
containers/content-processor/openai_client.py          (multi-call orchestration)
containers/content-processor/services/article_generation.py  (pipeline update)
containers/content-processor/content_generation.py     (leverage personalities)
containers/content-processor/models.py                 (ArticleVariant enum)
containers/markdown-generator/article_generator.py     (handle variants)
```

### Testing Strategy
- [ ] Compare old vs new article quality (sample 10 topics)
- [ ] Measure engagement: reading time, bounce rate (if analytics added)
- [ ] Cost analysis: Multi-prompt vs single-prompt (expect 2-3x token cost)
- [ ] A/B test personalities with sample readers

### Success Criteria
- ✅ Articles no longer feel formulaic or dry
- ✅ Clear distinction between highlights and in-depth variants
- ✅ Multiple title options generated and best selected
- ✅ Writer personalities add variety and engagement
- ✅ Cost per article remains acceptable (<$0.50/article including variants)

---

## 4. Image Integration 🎨

**Timeline**: 1-2 weeks  
**Priority**: MEDIUM-HIGH  
**Effort**: Medium

### Goal
Add visual appeal to articles and index page with hero images and thumbnails.

### Option A: AI-Generated Images (DALL-E 3)
**Pros**: Unique, customized to content, no licensing issues  
**Cons**: Cost (~$0.04/image), may not always look professional

**Implementation**:
```python
# In content-processor or markdown-generator
from openai import AsyncAzureOpenAI

async def generate_article_image(article_title: str, article_summary: str):
    """Generate hero image using DALL-E 3."""
    prompt = f"Professional editorial illustration for article titled '{article_title}'. {article_summary[:200]}. Modern, clean, tech-focused style."
    
    response = await openai_client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1792x1024",  # Hero image aspect ratio
        quality="standard",
        n=1
    )
    
    image_url = response.data[0].url
    # Download and store in blob storage
    return await download_and_store_image(image_url, article_slug)
```

### Option B: Stock Photos (Unsplash/Pexels API)
**Pros**: Free, professional quality, large selection  
**Cons**: Not unique, may not perfectly match content

**Implementation**:
```python
import aiohttp

async def fetch_stock_image(keywords: List[str]):
    """Fetch relevant stock image from Unsplash."""
    UNSPLASH_ACCESS_KEY = await get_secret("unsplash-api-key")
    query = " ".join(keywords[:3])
    
    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://api.unsplash.com/search/photos",
            params={"query": query, "per_page": 5},
            headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"}
        ) as resp:
            data = await resp.json()
            # Pick highest quality image
            return data["results"][0]["urls"]["regular"]
```

### Integration Points

#### 1. Markdown Frontmatter
```yaml
---
title: "Understanding Quantum Computing"
date: 2025-10-13
hero_image: "/images/2025/10/understanding-quantum-computing-hero.jpg"
thumbnail: "/images/2025/10/understanding-quantum-computing-thumb.jpg"
image_alt: "Quantum computing visualization with qubits"
image_credit: "Generated by DALL-E 3" # or "Photo by John Doe on Unsplash"
---
```

#### 2. Hugo Template Updates
```html
<!-- In site-publisher Hugo theme -->
{{ if .Params.hero_image }}
<div class="article-hero">
  <img src="{{ .Params.hero_image }}" alt="{{ .Params.image_alt }}" />
  {{ if .Params.image_credit }}
  <span class="image-credit">{{ .Params.image_credit }}</span>
  {{ end }}
</div>
{{ end }}
```

#### 3. Index Page Thumbnails
```html
<!-- Article list with thumbnails -->
{{ range .Pages }}
<article class="article-card">
  {{ if .Params.thumbnail }}
  <img src="{{ .Params.thumbnail }}" alt="{{ .Title }}" class="article-thumbnail" />
  {{ end }}
  <h2>{{ .Title }}</h2>
  <p>{{ .Summary }}</p>
</article>
{{ end }}
```

### Files to Modify
```
containers/content-processor/services/image_generation.py  (NEW)
containers/markdown-generator/article_generator.py         (add image generation)
containers/site-publisher/themes/PaperMod/layouts/...      (template updates)
infra/terraform/storage.tf                                 (blob container for images)
```

### Action Items
- [ ] Choose approach: DALL-E 3 vs Stock photos (or hybrid)
- [ ] If DALL-E: Add to Azure OpenAI deployment, test generation
- [ ] If Stock: Get Unsplash API key, implement search/download
- [ ] Create image storage blob container (`images` or `article-images`)
- [ ] Update markdown-generator to generate images during article creation
- [ ] Update Hugo templates to display hero images and thumbnails
- [ ] Add image optimization (resize, compress) before storing
- [ ] Test with 10+ articles to ensure quality and performance

### Success Criteria
- ✅ Every article has a hero image and thumbnail
- ✅ Images are relevant to article content
- ✅ Images display correctly on article pages and index
- ✅ Image generation/fetching doesn't significantly slow pipeline
- ✅ Cost per image is acceptable (~$0.04 DALL-E or $0 stock)

---

## 5. Audio Transcripts 🎧

**Timeline**: 2-3 weeks  
**Priority**: MEDIUM  
**Effort**: High

### Goal
Provide audio versions of articles in different voices for accessibility and convenience (listening while walking, driving, etc.).

### Azure Speech Service Integration

#### Setup Requirements
1. **Azure Resource**: Create Speech Service resource in Azure
2. **Voices**: Select 3-5 neural voices representing different personalities
3. **Storage**: Store audio files in blob storage, link from article metadata

#### Implementation

##### 1. Speech Generation Service
```python
# containers/markdown-generator/audio_generation.py (NEW)

from azure.cognitiveservices.speech import (
    SpeechConfig,
    SpeechSynthesizer,
    AudioConfig
)

class AudioGenerator:
    """Generate audio transcripts using Azure Speech Service."""
    
    VOICE_PROFILES = {
        "professional": "en-US-JennyNeural",  # Clear, professional female
        "casual": "en-US-GuyNeural",          # Friendly, casual male
        "technical": "en-US-AriaNeural",      # Precise, technical female
    }
    
    def __init__(self, speech_key: str, region: str):
        self.speech_config = SpeechConfig(
            subscription=speech_key,
            region=region
        )
    
    async def generate_audio(
        self,
        article_text: str,
        voice_profile: str = "professional",
        output_path: str = None
    ) -> str:
        """Generate audio file from article text."""
        
        # Set voice
        voice_name = self.VOICE_PROFILES.get(voice_profile, "en-US-JennyNeural")
        self.speech_config.speech_synthesis_voice_name = voice_name
        
        # Configure output
        audio_config = AudioConfig(filename=output_path)
        synthesizer = SpeechSynthesizer(
            speech_config=self.speech_config,
            audio_config=audio_config
        )
        
        # Clean article text for TTS (remove markdown, format properly)
        clean_text = self._prepare_text_for_tts(article_text)
        
        # Generate audio
        result = synthesizer.speak_text_async(clean_text).get()
        
        if result.reason == ResultReason.SynthesizingAudioCompleted:
            return output_path
        else:
            raise Exception(f"Speech synthesis failed: {result.reason}")
    
    def _prepare_text_for_tts(self, markdown_text: str) -> str:
        """Clean markdown for natural speech synthesis."""
        import re
        
        # Remove markdown syntax
        text = re.sub(r'#{1,6}\s+', '', markdown_text)  # Headers
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)  # Links
        text = re.sub(r'[*_]{1,2}([^*_]+)[*_]{1,2}', r'\1', text)  # Bold/italic
        text = re.sub(r'`([^`]+)`', r'\1', text)  # Code
        
        # Add pauses at section breaks
        text = text.replace('\n\n', '. ')
        
        return text.strip()
```

##### 2. Integration with Markdown Generator
```python
# In containers/markdown-generator/main.py

async def generate_article_with_audio(article_data: dict):
    """Generate markdown article and audio transcript."""
    
    # Generate markdown (existing)
    markdown_content = generate_markdown(article_data)
    markdown_file = save_markdown(markdown_content, article_data['slug'])
    
    # Generate audio transcripts in multiple voices
    audio_generator = AudioGenerator(
        speech_key=await get_secret("azure-speech-key"),
        region="eastus"
    )
    
    audio_files = {}
    for voice_profile in ["professional", "casual", "technical"]:
        audio_path = f"/tmp/{article_data['slug']}-{voice_profile}.mp3"
        
        audio_file = await audio_generator.generate_audio(
            article_text=article_data['content'],
            voice_profile=voice_profile,
            output_path=audio_path
        )
        
        # Upload to blob storage
        blob_url = await upload_audio_to_blob(audio_file, article_data['slug'], voice_profile)
        audio_files[voice_profile] = blob_url
    
    # Add audio URLs to frontmatter
    article_data['audio_transcripts'] = audio_files
    
    return update_markdown_frontmatter(markdown_file, article_data)
```

##### 3. Markdown Frontmatter
```yaml
---
title: "Understanding Quantum Computing"
date: 2025-10-13
audio_transcripts:
  professional: "https://storage.blob.core.windows.net/audio/2025/10/quantum-computing-professional.mp3"
  casual: "https://storage.blob.core.windows.net/audio/2025/10/quantum-computing-casual.mp3"
  technical: "https://storage.blob.core.windows.net/audio/2025/10/quantum-computing-technical.mp3"
audio_duration_seconds: 720
---
```

##### 4. Hugo Template Audio Player
```html
<!-- In site-publisher Hugo theme -->
{{ if .Params.audio_transcripts }}
<div class="audio-player">
  <h3>Listen to this article</h3>
  <div class="voice-selector">
    {{ range $voice, $url := .Params.audio_transcripts }}
    <button onclick="playAudio('{{ $url }}', '{{ $voice }}')">
      {{ $voice | humanize }}
    </button>
    {{ end }}
  </div>
  <audio id="article-audio" controls></audio>
</div>

<script>
function playAudio(url, voice) {
  const audio = document.getElementById('article-audio');
  audio.src = url;
  audio.play();
}
</script>
{{ end }}
```

### Infrastructure Changes

```hcl
# infra/terraform/speech.tf (NEW)

resource "azurerm_cognitive_account" "speech" {
  name                = "ai-content-prod-speech"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  kind                = "SpeechServices"
  sku_name            = "S0"  # Standard tier
  
  tags = local.common_tags
}

# Grant markdown-generator managed identity access
resource "azurerm_role_assignment" "markdown_gen_speech" {
  scope                = azurerm_cognitive_account.speech.id
  role_definition_name = "Cognitive Services Speech User"
  principal_id         = azurerm_container_app.markdown_generator.identity[0].principal_id
}

# Add audio blob container
resource "azurerm_storage_container" "audio" {
  name                  = "audio"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "blob"  # Public read for audio files
}
```

### Cost Estimation
- **Azure Speech Service**: ~$1 per 1 million characters
- **Average article**: 3000 words ≈ 18,000 characters
- **Cost per article** (3 voices): ~$0.054
- **Monthly** (100 articles): ~$5.40

### Files to Modify
```
containers/markdown-generator/audio_generation.py         (NEW)
containers/markdown-generator/main.py                     (integrate audio)
containers/markdown-generator/requirements.txt            (add azure-cognitiveservices-speech)
containers/site-publisher/themes/PaperMod/layouts/...     (audio player)
infra/terraform/speech.tf                                 (NEW)
infra/terraform/storage.tf                                (audio container)
```

### Action Items
- [ ] Create Azure Speech Service resource via Terraform
- [ ] Implement AudioGenerator service
- [ ] Test with 3-5 articles across different voice profiles
- [ ] Integrate into markdown-generator pipeline
- [ ] Add audio player to Hugo theme
- [ ] Test audio playback on mobile and desktop
- [ ] Optimize audio file size (bitrate, format)
- [ ] Add duration calculation for UX

### Success Criteria
- ✅ Articles have audio transcripts in 3 voice profiles
- ✅ Audio quality is clear and natural-sounding
- ✅ Audio player works on article pages
- ✅ Audio files stored efficiently in blob storage
- ✅ Cost per article remains under $0.10 for all voices
- ✅ Generation doesn't significantly slow pipeline

---

## Cost Impact Summary

| Feature | Monthly Cost Estimate | Notes |
|---------|----------------------|-------|
| Security Updates | $0 | Free, just maintenance |
| Reddit Recovery | $0 | No additional cost |
| Multi-Prompt Articles | +$15-25 | 2-3x tokens per article, ~100 articles/month |
| Images (DALL-E) | +$4-8 | ~$0.04/image, 100-200 images/month |
| Images (Stock) | $0 | Free tier (Unsplash/Pexels) |
| Audio Transcripts | +$5-10 | ~$0.05/article for 3 voices |
| **Total Impact** | **+$24-43** | Assuming AI images + audio |

### Current Budget vs New Features
- **Current**: ~$30-40/month baseline
- **With All Features**: ~$54-83/month
- **Still within acceptable range** for portfolio project with rich features

---

## Implementation Timeline

### Week 1 (Oct 13-20)
- [x] Create this planning document
- [ ] Security: Update all dependencies, test, deploy
- [ ] Reddit: Investigate lockout, create fresh credentials

### Week 2 (Oct 21-27)
- [ ] Reddit: Implement sustainable collection, test over 24 hours
- [ ] Content: Design multi-prompt architecture
- [ ] Content: Implement separate prompt functions

### Week 3 (Oct 28 - Nov 3)
- [ ] Content: Integrate multi-prompt flow into ArticleGenerationService
- [ ] Content: Add writer personalities rotation
- [ ] Images: Choose approach (DALL-E vs Stock)

### Week 4 (Nov 4-10)
- [ ] Content: Implement highlights/in-depth variants
- [ ] Images: Implement image generation/fetching
- [ ] Images: Update markdown-generator and Hugo templates

### Week 5 (Nov 11-17)
- [ ] Audio: Create Azure Speech Service resource
- [ ] Audio: Implement AudioGenerator service
- [ ] Audio: Test with sample articles

### Week 6 (Nov 18-24)
- [ ] Audio: Integrate into markdown-generator pipeline
- [ ] Audio: Add audio player to Hugo theme
- [ ] Testing: End-to-end pipeline with all features

### Week 7 (Nov 25 - Dec 1)
- [ ] Polish: Bug fixes, performance optimization
- [ ] Documentation: Update README, architecture docs
- [ ] Monitoring: Track costs, quality metrics
- [ ] Deploy: Roll out all features to production

---

## Success Metrics

### Security
- ✅ Zero high/critical vulnerabilities in dependencies
- ✅ All containers passing security scans

### Content Sources
- ✅ Reddit + Mastodon + RSS all actively collecting
- ✅ No API lockouts for 30+ days
- ✅ 50+ new topics collected daily

### Content Quality
- ✅ Articles feel engaging and varied (subjective but measurable via feedback)
- ✅ Clear distinction between highlights and in-depth
- ✅ Multiple writer voices add personality

### Visual & Audio
- ✅ 100% of articles have hero images
- ✅ 100% of articles have audio transcripts
- ✅ Audio player functional on all devices

### Cost
- ✅ Total monthly cost under $100
- ✅ Cost per article under $1 (including all features)

### Pipeline Performance
- ✅ End-to-end latency: Topic → Published article < 30 minutes
- ✅ No failed articles due to feature additions

---

## Next Steps

1. **Start with security** - Quick win, no debate needed
2. **Reddit investigation** - Unblock important content source
3. **Multi-prompt prototype** - Test if it actually improves quality
4. **Decide on images** - DALL-E vs Stock (or both?)
5. **Audio as final feature** - Most complex, save for when others are stable

**Ready to begin?** Let's start with the security updates and Reddit recovery. Both are practical, achievable, and unblock higher-value work.
