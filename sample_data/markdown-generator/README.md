# Markdown Generator Sample Data

This directory contains real production samples from Azure blob storage for testing the markdown generation pipeline.

## Purpose

These samples are used for:
- Integration testing with real-world data
- CI/CD pipeline validation without Azure credentials
- Edge case validation (special characters, missing fields)
- Regression testing against production data

## Sample Files

### RSS Samples (Working Well)
- **`sample_rss_1.json`** - WIRED article about cat water fountains
  - Source: RSS feed
  - Word count: 713
  - Contains: title, url, source, article_content, metadata
  - Good example: Clean article structure, standard metadata

- **`sample_rss_2.json`** - Additional RSS article sample
  - Source: RSS feed
  - Provides variety for testing edge cases

### Mastodon Samples (Historically Problematic)
- **`sample_mastodon_1.json`** - Trade show announcement
  - Source: mastodon.social
  - Contains special characters: `[#TRADESHOW]`, `#Offshore`, colons
  - Edge case: Title with hashtags and special formatting
  - Good example: Tests YAML escaping and Hugo frontmatter compliance

- **`sample_mastodon_2.json`** - Second Mastodon post
  - Source: mastodon.social
  - Additional edge cases and formatting variations

## Data Structure

All samples follow the processed content schema:

```json
{
  "topic_id": "source_identifier",
  "original_title": "Original title with formatting",
  "title": "Cleaned title for use",
  "slug": "url-safe-slug",
  "filename": "articles/2025-10-12-slug.html",
  "url": "/articles/2025-10-12-slug.html",
  "article_content": "Full article markdown content...",
  "word_count": 713,
  "quality_score": 0.7,
  "cost": 0.00157,
  "source": "rss|mastodon|reddit",
  "original_url": "https://source.com/article",
  "generated_at": "2025-10-12T20:42:28.262571+00:00",
  "metadata": {
    "processor_id": "hash",
    "session_id": "uuid",
    "openai_model": "gpt-35-turbo",
    "content_type": "generated_article"
  }
}
```

## Usage in Tests

### Integration Tests
```python
from pathlib import Path
import json

SAMPLE_DATA_DIR = Path(__file__).parent.parent.parent.parent / "sample_data" / "markdown-generator"

def test_with_real_data():
    with open(SAMPLE_DATA_DIR / "sample_rss_1.json") as f:
        data = json.load(f)
    # Test frontmatter generation...
```

### CI/CD Pipeline
The GitHub Actions workflow automatically uses these samples:
```yaml
- name: Run integration tests
  run: |
    cd containers/markdown-generator
    pytest tests/test_markdown_processor_integration.py -v
```

## Updating Samples

To download fresh samples from Azure:

```bash
# Authenticate
az login

# List recent processed content
az storage blob list \
  --account-name aicontentprodstkwakpx \
  --container-name processed-content \
  --auth-mode login \
  --query "[?contains(name, 'processed/2025')].name" \
  --output table

# Download specific sample
az storage blob download \
  --account-name aicontentprodstkwakpx \
  --container-name processed-content \
  --name "processed/2025/10/12/20251012_204235_rss_675939.json" \
  --file sample_data/markdown-generator/sample_rss_1.json \
  --auth-mode login
```

## Edge Cases Covered

### Special Characters
- Hashtags in titles: `[#TRADESHOW]`
- Colons in titles: `"Title: A Deep Dive"`
- URL query parameters: `?param=value&test=true`
- Unicode characters in content

### Missing Fields
- Articles without author
- Articles without published_date
- Articles without category
- Empty tags arrays

### Data Variations
- RSS feeds (structured, clean)
- Mastodon posts (social, informal)
- Different word counts
- Various quality scores

## Hugo Frontmatter Compliance

All samples are tested to ensure generated frontmatter:
- ✅ Has required fields: `title`, `date`, `draft`
- ✅ Places custom fields under `params` key
- ✅ Uses RFC3339 date formatting
- ✅ Properly escapes special characters
- ✅ Validates as valid YAML

## Maintenance

- **Update Frequency**: When new edge cases discovered
- **Source**: Production Azure blob storage
- **Validation**: All samples must pass integration tests
- **Size Limit**: Keep samples < 10KB each (trim large article_content if needed)

---

Last Updated: October 13, 2025
Total Samples: 4 (2 RSS, 2 Mastodon)
