# Content Processing Pipeline

This directory contains the content processing pipeline that transforms collected topics into publication-ready articles.

## Overview

The pipeline consists of three main stages:

1. **Topic Ranking** (`topic_ranker.py`) - Evaluates collected topics for publishing worthiness
2. **Content Enrichment** (`content_enricher.py`) - Researches and fact-checks topics
3. **Content Publishing** (`content_publisher.py`) - Generates polished markdown articles

## Quick Start

### Full Pipeline
```bash
cd content_processor
python3 pipeline.py --mode full --max-articles 5
```

### Individual Stages
```bash
# 1. Rank topics only
python3 pipeline.py --mode rank --hours-back 24 --min-score 0.3

# 2. Enrich specific ranked file
python3 pipeline.py --mode enrich --input-file ranked_topics_20250724_120000.json

# 3. Publish specific enriched file  
python3 pipeline.py --mode publish --input-file enriched_topics_20250724_120000.json --max-articles 3

# 4. Check pipeline status
python3 pipeline.py --mode status
```

## Components

### Topic Ranker
Evaluates topics based on:
- **Engagement metrics** (Reddit scores, comments)
- **Freshness** (recency of content)
- **Monetization potential** (keyword analysis)
- **SEO potential** (title quality, format)

Configuration:
- `min_score_threshold`: Minimum Reddit score (default: 100)
- `min_comments_threshold`: Minimum comments (default: 10)
- `hours_fresh_threshold`: Consider fresh if within N hours (default: 48)

### Content Enricher
Enriches topics with:
- **External content fetching** from source URLs
- **Source credibility assessment**
- **Citation generation**
- **Research notes and fact-checking guidance**

Features:
- Respectful request delays (1 second between requests)
- Domain credibility scoring
- HTML metadata extraction
- Content quality assessment

### Content Publisher
Generates publication-ready content:
- **SEO-optimized markdown** with frontmatter
- **Proper citations** and source attribution
- **Monetization-friendly formatting**
- **Meta tags** for social sharing
- **Reading time estimation**

Output format:
- YAML frontmatter with SEO data
- Structured markdown content
- Citations and references section
- Social media optimization

## Configuration

### Ranking Weights
```python
weights = {
    'engagement': 0.4,    # Reddit scores/comments
    'freshness': 0.2,     # Recency of content  
    'monetization': 0.3,  # Commercial potential
    'seo': 0.1           # SEO optimization potential
}
```

### High-Value Keywords
Topics containing these keywords get higher monetization scores:
- AI, machine learning, crypto, bitcoin
- Technology, startup, innovation
- Investment, market, funding
- Productivity, tools, software

### Content Quality Factors
- Has title and description
- Substantial content (>200 words)
- Domain credibility
- Source availability

## File Structure

```
content_processor/
├── pipeline.py              # Main orchestrator
├── topic_ranker.py         # Topic ranking logic
├── content_enricher.py     # Content research & enrichment
├── content_publisher.py    # Markdown article generation
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## Output Files

### Ranked Topics
```json
{
  "generated_at": "2025-07-24T12:00:00",
  "total_topics": 15,
  "ranking_criteria": {...},
  "topics": [
    {
      "title": "...",
      "ranking_score": 0.85,
      "score_breakdown": {
        "engagement": 0.9,
        "freshness": 0.8,
        "monetization": 0.7,
        "seo": 0.6
      },
      ...
    }
  ]
}
```

### Enriched Topics
```json
{
  "generated_at": "2025-07-24T12:15:00",
  "source_file": "ranked_topics_20250724_120000.json",
  "total_topics": 15,
  "enrichment_process": {...},
  "topics": [
    {
      ..., // Original topic data
      "enrichment": {
        "processed_at": "2025-07-24T12:15:00",
        "external_content": {...},
        "verification_checks": [...],
        "citations": [...],
        "research_notes": [...]
      }
    }
  ]
}
```

### Published Articles
```markdown
---
title: "Article Title"
slug: "article-slug"
date: 2025-07-24
tags: ["technology", "ai"]
readingTime: 3
monetization:
  ads: true
  affiliate: false
---

# Article Title

*This topic is trending on Reddit...*

## What's Happening
...

## Sources and References
1. [Source Article](url) - domain.com (accessed 2025-07-24)
2. [Reddit Discussion](url) - 500 upvotes, 120 comments
```

## Monetization Features

The pipeline includes several monetization-friendly features:

### SEO Optimization
- Meta descriptions and titles
- Structured data in frontmatter
- Reading time estimation
- Tag and category classification

### Content Quality
- Multiple source citations
- Fact-checking guidance
- Professional formatting
- Engagement metrics

### Social Sharing
- Open Graph metadata
- Twitter card optimization
- Facebook sharing optimization
- LinkedIn sharing support

### Ad-Friendly Structure
- Clear content sections
- Proper heading hierarchy
- Reading time for ad placement
- Engagement hooks

## Usage Examples

### Daily Content Generation
```bash
# Run full pipeline daily at 9 AM
0 9 * * * cd /path/to/content_processor && python3 pipeline.py --mode full --max-articles 3
```

### High-Quality Content Only
```bash
python3 pipeline.py --mode full --min-score 0.5 --max-articles 2
```

### Research-Heavy Content
```bash
# Rank topics
python3 pipeline.py --mode rank --min-score 0.4

# Manual review of ranked topics, then enrich
python3 pipeline.py --mode enrich --input-file ranked_topics_latest.json

# Manual fact-checking, then publish
python3 pipeline.py --mode publish --input-file enriched_topics_latest.json
```

## Integration with JAMStack

Published articles are ready for static site generators:

### Next.js
- Frontmatter compatible with next-mdx-remote
- SEO data for next/head integration
- Social sharing metadata

### Gatsby
- Compatible with gatsby-transformer-remark
- GraphQL-ready frontmatter structure
- Image optimization ready

### Hugo
- YAML frontmatter format
- Hugo page bundles compatible
- Taxonomy integration (tags/categories)

## Monitoring and Quality Control

### Pipeline Status
```bash
python3 pipeline.py --mode status
```

Shows:
- Recent files processed
- Configuration settings
- Directory structure
- Processing statistics

### Quality Metrics
Each article includes:
- Source credibility scores
- Content quality assessment
- Engagement metrics
- SEO optimization scores

### Manual Review Points
1. After ranking - review topic selection
2. After enrichment - fact-check sources
3. Before publishing - content quality review
4. After publishing - performance monitoring

## Best Practices

### Content Quality
- Always verify facts from multiple sources
- Include proper attribution and citations
- Maintain editorial standards
- Regular quality audits

### SEO Optimization
- Target 1-2 primary keywords per article
- Use descriptive, engaging titles
- Include meta descriptions under 160 characters
- Add relevant tags and categories

### Monetization
- Balance ad placement with user experience
- Include affiliate disclosures when applicable
- Monitor performance metrics
- Test different content formats

### Legal Compliance
- Respect robots.txt and rate limits
- Include proper source attribution
- Maintain copyright compliance
- Add necessary disclaimers

## Troubleshooting

### Common Issues

**No topics found:**
- Check if wombles have run recently
- Verify output directory path
- Lower min_score threshold

**External content fetch fails:**
- Check internet connectivity
- Verify URL accessibility
- Review rate limiting settings

**Publishing errors:**
- Check site directory permissions
- Verify markdown syntax
- Review frontmatter formatting

### Debug Mode
Add verbose logging by modifying the scripts or running with:
```bash
python3 -u pipeline.py --mode full 2>&1 | tee pipeline.log
```
