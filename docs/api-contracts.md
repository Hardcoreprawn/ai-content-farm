# API Contracts and Data Formats

## Foundational Principles

### REST-First Architecture
**All functions MUST be HTTP endpoints** with clear REST patterns:
- ✅ **Testable**: Every function accessible via HTTP for manual testing
- ✅ **Observable**: Clear status, error messages, and progress indicators
- ✅ **Controllable**: Manual trigger capability with proper authentication
- ✅ **Debuggable**: Detailed responses explaining what happened and why

### Standard Response Format
All HTTP endpoints MUST return consistent response structure:

```json
{
  "status": "success|error|processing",
  "message": "Human-readable description",
  "data": { /* actual response data */ },
  "errors": [ /* detailed error information */ ],
  "metadata": {
    "timestamp": "2025-08-12T14:30:00Z",
    "function": "ContentRanker",
    "execution_time_ms": 1250
  }
}
```

### Authentication Standards
- **Function-level keys** for manual testing and debugging
- **Clear auth errors**: "401 Unauthorized - Function key required" 
- **Internal calls**: Use managed identity or service-to-service keys

### Error Handling Requirements
- **No silent failures**: Always return meaningful HTTP status codes
- **Detailed error messages**: Explain what went wrong and how to fix it
- **Structured errors**: Include error codes, categories, and suggestions

## Content Processing Pipeline Data Flow

### 1. GetHotTopics → SummaryWomble
**Trigger**: Timer function (every 6 hours)
**Method**: HTTP POST to SummaryWomble
**Authentication**: Internal service-to-service key
**Payload**:
```json
{
  "source": "reddit",
  "topics": ["technology", "MachineLearning", "artificial"],
  "limit": 10,
  "credentials": {
    "source": "keyvault"
  }
}
```

**Expected Response**:
```json
{
  "status": "accepted",
  "message": "Topic collection job started successfully", 
  "data": {
    "job_id": "uuid-string",
    "topics_requested": ["technology", "MachineLearning", "artificial"],
    "estimated_completion": "2025-08-12T14:35:00Z"
  },
  "metadata": {
    "timestamp": "2025-08-12T14:30:00Z",
    "function": "SummaryWomble",
    "execution_time_ms": 250
  }
}
```

## Current Functions Needing REST API Upgrades

### ❌ ContentRanker (Currently blob-trigger only)
**NEEDS**: HTTP endpoint `/api/content-ranker/process`
**Current**: Only `ContentRankerManual` exists but returns 500 errors
**Required**: Proper REST API with clear error messages

### ❌ ContentEnricher (Currently blob-trigger only)  
**NEEDS**: HTTP endpoint `/api/content-enricher/process`
**Current**: Only `ContentEnricherManual` exists but needs testing
**Required**: Proper REST API with authentication and error handling

### ✅ SummaryWomble (HTTP endpoint exists)
**Status**: Has HTTP endpoint but may need response format updates
**Enhancement**: Add `/health` and `/status` endpoints

### 2. SummaryWomble → Blob Storage (Raw Topics)
**Location**: `hot-topics` container
**File Pattern**: `{timestamp}_{source}_{subreddit}.json`
**Example**: `20250811_150000_reddit_technology.json`

**Format**:
```json
{
  "job_id": "uuid-string",
  "source": "reddit",
  "subject": "technology",
  "fetched_at": "20250811_150000",
  "count": 25,
  "topics": [
    {
      "title": "Post Title",
      "external_url": "https://example.com/article",
      "reddit_url": "https://www.reddit.com/r/technology/comments/abc123/",
      "reddit_id": "abc123",
      "score": 1500,
      "created_utc": 1691766000,
      "num_comments": 125,
      "author": "username",
      "subreddit": "technology",
      "fetched_at": "20250811_150000",
      "selftext": "Post content preview..."
    }
  ]
}
```

### 3. ContentRanker Input (Blob Trigger)
**Trigger Path**: `hot-topics/{timestamp}_{source}_{subreddit}.json`
**Input**: Same as SummaryWomble output above

### 4. ContentRanker → Blob Storage (Ranked Topics)
**Location**: `content-pipeline/ranked-topics/` 
**File Pattern**: `ranked_{timestamp}.json`

**Format**:
```json
{
  "generated_at": "2025-08-11T15:05:00.000000",
  "source_files": ["20250811_150000_reddit_technology.json"],
  "total_topics": 20,
  "ranking_criteria": {
    "min_score_threshold": 100,
    "min_comments_threshold": 10,
    "weights": {
      "engagement": 0.4,
      "freshness": 0.2, 
      "monetization": 0.3,
      "seo": 0.1
    }
  },
  "topics": [
    {
      // Original topic data plus:
      "ranking_score": 0.68,
      "score_breakdown": {
        "engagement": 1.0,
        "freshness": 0.8,
        "monetization": 0.4,
        "seo": 0.0,
        "final": 0.68
      }
    }
  ]
}
```

### 5. ContentEnricher Input (Blob Trigger)  
**Trigger Path**: `content-pipeline/ranked-topics/ranked_{timestamp}.json`

### 6. ContentEnricher → Blob Storage (Enriched Topics)
**Location**: `content-pipeline/enriched-topics/`
**File Pattern**: `enriched_{timestamp}.json`

**Format**:
```json
{
  "generated_at": "2025-08-11T15:10:00.000000", 
  "source_file": "ranked_20250811_150500.json",
  "total_topics": 15,
  "topics": [
    {
      // Original ranked topic data plus:
      "enrichment_data": {
        "external_content": {
          "title": "Article Title",
          "description": "Meta description",
          "content_preview": "First 500 chars...",
          "domain": "example.com",
          "credibility_score": 0.8
        },
        "research_notes": "Key points for fact-checking...",
        "citations": ["Source 1", "Source 2"],
        "content_quality": 0.75
      }
    }
  ]
}
```

### 7. ContentPublisher Input (Blob Trigger)
**Trigger Path**: `content-pipeline/enriched-topics/enriched_{timestamp}.json`

### 8. ContentPublisher → Blob Storage (Published Articles)
**Location**: `published-articles/`
**File Pattern**: `{slug}.md`

**Format**: SEO-optimized Markdown with YAML frontmatter
```markdown
---
title: "Article Title"
description: "SEO meta description under 160 chars"
date: "2025-08-11"
author: "AI Content Farm"
tags: ["technology", "ai", "innovation"]
categories: ["tech-news"]
featured_image: "/images/default-tech.jpg"
reading_time: "5 min"
seo:
  canonical_url: "https://example.com/original"
  keywords: ["ai", "technology", "innovation"]
social:
  twitter_card: "summary_large_image"
  og_type: "article"
sources:
  primary: "https://reddit.com/r/technology/comments/abc123/"
  external: "https://example.com/article"
---

# Article Title

Article content with proper markdown formatting...

## Sources and References

- [Primary Discussion](reddit_url)
- [External Source](external_url)
```

## Job Status Tracking

All functions use job tickets stored in:
**Location**: `jobs/{job_id}/status.json`

**Format**:
```json
{
  "job_id": "uuid-string",
  "status": "queued|running|completed|failed",
  "updated_at": "2025-08-11T15:00:00.000000",
  "progress": {
    "step": "processing r/technology",
    "completed": 2,
    "total": 5
  },
  "error": null,
  "results": {
    "status": "completed",
    "timestamp": "20250811_150000",
    "total_topics": 75
  }
}
```
