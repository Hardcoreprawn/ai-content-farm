# Collection Templates

This directory contains JSON templates for different types of content collection. These templates are used by the GitHub Actions workflow to trigger content collection with predefined configurations.

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
    }
  ],
  "deduplicate": true,
  "similarity_threshold": 0.8,
  "save_to_storage": true
}
```

## Available Templates

- `default.json` - Basic Reddit collection from popular tech subreddits
- `discovery.json` - Discovery-focused collection from emerging tech subreddits  
- `tech-rss.json` - RSS feeds from prominent technology websites with topic filtering
- `web-overlap-test.json` - **Deduplication test template** with overlapping web sources across multiple categories to stress-test the deduplication system

## Adding New Templates

1. Create a new JSON file in this directory
2. Follow the CollectionRequest schema (see API documentation)
3. Update the GitHub Actions workflow to reference your new template
4. Test manually before committing

## Template Fields

### Sources Configuration
- **sources**: Array of source configurations
  - **type**: Source type - "reddit", "rss", or "web"
  - **subreddits**: List of subreddit names (for reddit sources)
  - **feed_urls**: List of RSS feed URLs (for rss sources)
  - **websites**: List of website URLs (for web sources)
  - **limit**: Maximum items to collect per source
  - **criteria**: Additional filtering criteria (optional)
    - **min_score**: Minimum score for reddit posts
    - **time_filter**: Time filter for reddit (hour, day, week, month, year, all)
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
