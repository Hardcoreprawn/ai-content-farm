# Collection Templates

This directory contains JSON templates for different types of content collection. These templates define **approved sources only** and are the exclusive way to trigger content collection for security reasons.

## 🔒 Security Policy

**IMPORTANT**: Collection templates are the ONLY way to define content sources. The collection API does NOT accept arbitrary URLs to prevent:
- DDoS attacks on third-party sites
- Malware downloads
- Data exfiltration
- Resource abuse

All templates must be:
1. Committed to this repository
2. Security reviewed before deployment
3. Deployed to Azure Blob Storage via CI/CD only

See Issue #580 for security rationale.

## 📚 Available Templates

### Production Templates (High Quality)

**quality-tech.json** - Substantive technical content
- Focus: Systems engineering, architecture, research papers
- Sources: arXiv CS, company engineering blogs (Netflix, Spotify, Facebook), practitioner blogs
- Philosophy: Technical depth over consumer gadget reviews
- **Recommended for regular collection**

**ai-research.json** - Cutting-edge AI/ML research
- Focus: Research papers, frontier AI developments
- Sources: arXiv (AI/ML/CL/CV), research labs (Google, OpenAI, Anthropic, DeepMind)
- Philosophy: Research-quality content with mathematical depth
- **Recommended for AI-focused collection**

### Legacy Templates (Under Review)

**default.json** - Original broad collection (⚠️ DEPRECATED)
- Contains consumer tech sources (WIRED, Engadget, etc.)
- Too many listicles and product reviews
- **DO NOT USE - being phased out**

**tech-rss.json** - RSS-only collection
- Mix of quality and consumer sources
- Needs curation and filtering improvement

**tech-news.json** - Reddit-focused (currently disabled)
- Reddit sources temporarily disabled
- Awaiting cooldown period

## Template Structure

Each template is a JSON file that follows the CollectionRequest schema:

```json
{
  "sources": [
    {
      "type": "reddit",
      "subreddits": ["technology", "programming"],
      "limit": 15,
      "criteria": {
        "min_score": 10,
        "time_filter": "day"
      }
    },
    {
      "type": "rss", 
      "feed_urls": [
        "https://feeds.feedburner.com/TechCrunch",
        "https://www.wired.com/feed/rss"
      ],
      "limit": 10,
      "criteria": {
        "topics": ["AI", "machine learning"],
        "exclude_keywords": ["review", "deal"]
      }
    },
    {
      "type": "mastodon",
      "instances": ["mastodon.social", "fosstodon.org"],
      "hashtags": ["technology", "programming", "AI"],
      "limit": 15,
      "criteria": {
        "min_favorites": 2,
        "published_within_hours": 24,
        "language": "en"
      }
    }
  ],
  "deduplicate": true,
  "similarity_threshold": 0.8,
  "save_to_storage": true
}
```

## Usage

### Via KEDA Cron Scheduler (Automated)
The content-collector automatically runs every 8 hours using the configured template. To change which template is used:

1. Update the KEDA cron scaler environment variable in `/infra/container_apps.tf`
2. Deploy via CI/CD pipeline

### Via API (Manual/Testing)
```bash
# Trigger collection with specific template
curl -X POST https://ai-content-prod-collector.whitecliff-6844954b.uksouth.azurecontainerapps.io/collections \
  -H "Content-Type: application/json" \
  -d '{"template_name": "quality-tech"}'

# List available templates
curl https://ai-content-prod-collector.whitecliff-6844954b.uksouth.azurecontainerapps.io/templates

# Get template details
curl https://ai-content-prod-collector.whitecliff-6844954b.uksouth.azurecontainerapps.io/templates/quality-tech
```

## Content Philosophy

### ✅ What We Want
- **Research papers** and technical analysis
- **Systems engineering** posts from companies at scale
- **Deep dives** into architecture and performance
- **Novel algorithms** and techniques
- **Infrastructure** challenges and solutions
- **Security research** and formal methods
- **Programming language** theory and compilers

### ❌ What We Avoid
- Consumer gadget reviews ("Best iPhone cases")
- Product unboxing videos
- Shopping guides and deals
- Listicles ("Top 10 programmer productivity hacks")
- Crypto hype and speculation
- Generic startup advice
- Celebrity tech gossip

## Available Templates

### 🌟 Recommended Production Templates

**quality-tech.json** - High-quality technical content
- Engineering blogs: Netflix, Spotify, Dropbox, Facebook, GitHub, Cloudflare
- Research: arXiv CS papers, ACM Queue, Google Research
- Practitioners: Martin Fowler, Dan Luu, Julia Evans, Xe Iaso
- HN: High-score threshold (100+) for community curation
- **Use this for general technical content collection**

**ai-research.json** - AI/ML research focus
- arXiv: AI, ML, CL (NLP), CV, NE, stat.ML categories
- Research labs: Google, OpenAI, Anthropic, DeepMind, Meta
- Frameworks: TensorFlow, PyTorch, HuggingFace
- Analysis: Distill, The Gradient, researcher blogs
- **Use this for AI-specific research collection**

### 📦 Legacy/Deprecated Templates

- `default.json` - **DEPRECATED** - Too much consumer content (WIRED, Engadget)
- `tech-rss.json` - Needs curation review
- `tech-news.json` - Reddit sources (currently disabled)
- `mastodon.json` - General Mastodon collection
- `mastodon-social.json` - Mastodon.social specific
- `discovery.json` - Experimental discovery mode
- `sustainable-reddit.json` - Sustainable Reddit collection strategy
- `adaptive-multi-source.json` - Multi-source adaptive collection
- `web-overlap-test.json` - Deduplication testing

## Adding New Templates

1. Create a new JSON file in this directory
2. Follow the CollectionRequest schema (see API documentation)
3. Update the GitHub Actions workflow to reference your new template
4. Test manually before committing

## Template Fields

### Sources Configuration
- **sources**: Array of source configurations
  - **type**: Source type - "reddit", "rss", "web", or "mastodon"
  - **subreddits**: List of subreddit names (for reddit sources)
  - **feed_urls**: List of RSS feed URLs (for rss sources)
  - **websites**: List of website URLs (for web sources)
  - **instances**: List of Mastodon instance URLs (for mastodon sources)
  - **hashtags**: List of hashtags to search for (for mastodon sources)
  - **limit**: Maximum items to collect per source
  - **criteria**: Additional filtering criteria (optional)
    - **min_score**: Minimum score for reddit posts
    - **time_filter**: Time filter for reddit (hour, day, week, month, year, all)
    - **min_favorites**: Minimum number of favorites for mastodon posts
    - **min_reblogs**: Minimum number of reblogs for mastodon posts
    - **published_within_hours**: Only collect posts published within this timeframe
    - **language**: Language code for content filtering (e.g., "en")
    - **topics**: List of topics to focus on (used for content relevance)
    - **exclude_keywords**: Keywords to exclude from collection

### Collection Settings
- **deduplicate**: Whether to remove duplicate content (default: true)
- **similarity_threshold**: Threshold for similarity detection (0.0-1.0, default: 0.8)
- **save_to_storage**: Whether to save to blob storage (default: true)

### Testing Deduplication
The `web-overlap-test.json` template is specifically designed to test the deduplication system by:
- **Intentional overlaps**: Multiple sources include the same websites (techcrunch.com, arstechnica.com, theverge.com)
- **Cross-category topics**: Similar topics across different source groups to test topic-based deduplication
- **Stress testing**: High-volume sources to see how the system handles large amounts of potentially duplicate content

This template helps validate that the deduplication algorithm correctly identifies and removes duplicate articles from the same sources, even when they're requested through different collection configurations.

### Metadata (Optional)
- **metadata**: Additional information about the template
  - **template_name**: Identifier for the template
  - **description**: Human-readable description
  - **focus_areas**: Array of focus areas
  - **update_frequency**: Suggested update frequency
  - **content_types**: Types of content this template collects
