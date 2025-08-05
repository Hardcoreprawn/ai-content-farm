# Content Processing Workflow Documentation

## Overview

The AI Content Farm now has a complete content processing pipeline that transforms raw Reddit topics into publication-ready articles. This system evaluates, enriches, and publishes content automatically while ensuring quality, accuracy, and monetization potential.

## Workflow Stages

### 1. Topic Collection (Content Wombles)
**Location**: `content_wombles/`
**Purpose**: Collect trending topics from Reddit communities

**Process**:
- Scrapes hot topics from technology-focused subreddits
- Extracts engagement metrics (scores, comments)
- Stores raw data as JSON files in `output/`

**Command**: `make collect-topics`

### 2. Topic Ranking
**Location**: `content_processor/topic_ranker.py`
**Purpose**: Evaluate topics for publishing worthiness

**Deduplication**: 
- Removes duplicate topics by title similarity (>80% word overlap)
- Eliminates duplicate external URLs
- Keeps highest engagement version of duplicates

**Scoring Criteria**:
- **Engagement (40%)**: Reddit scores and comments
- **Freshness (20%)**: How recent the content is
- **Monetization (30%)**: Commercial potential based on keywords
- **SEO (10%)**: Title quality and search optimization potential

**Thresholds**:
- Minimum 100 upvotes
- Minimum 10 comments
- Overall score > 0.3

**Command**: `make rank-topics`

### 3. Content Enrichment
**Location**: `content_processor/content_enricher.py`
**Purpose**: Research and fact-check topics

**Features**:
- Fetches content from external sources
- Assesses domain credibility
- Generates citations and references
- Provides research guidance
- Respectful request rate limiting (1 second delays)

**Command**: `make enrich-content FILE=ranked_topics_file.json`

### 4. Content Publishing
**Location**: `content_processor/content_publisher.py`
**Purpose**: Generate SEO-optimized markdown articles

**Duplicate Prevention**:
- Additional deduplication by slug and URL
- Prevents file naming conflicts
- Ensures unique article generation

**Output Features**:
- YAML frontmatter with SEO metadata
- Social sharing optimization
- Monetization-ready structure
- Proper source attribution
- Reading time estimation
- Tag and category classification

**Command**: `make publish-articles FILE=enriched_topics_file.json`

## Full Pipeline

**Command**: `make process-content`

This runs all stages automatically:
1. Ranks collected topics (last 24 hours)
2. Enriches top-scoring topics
3. Publishes up to 5 articles

## Content Quality Features

### SEO Optimization
- Meta descriptions under 160 characters
- Structured heading hierarchy
- Keyword-rich titles and content
- Internal and external linking
- Reading time for user engagement

### Monetization Ready
- Ad-friendly content structure
- Clear sections for ad placement
- Engagement metrics for targeting
- Social sharing optimization
- Professional formatting

### Source Attribution
- Primary source citations
- Reddit discussion links
- Domain credibility scoring
- Access date tracking
- Fact-checking guidance

### Editorial Standards
- Automated quality scoring
- Content length requirements
- Engagement thresholds
- **Comprehensive deduplication** (title similarity + URL matching)
- Manual review checkpoints
- Plagiarism prevention

## Configuration

### Ranking Weights
```python
weights = {
    'engagement': 0.4,    # Reddit engagement metrics
    'freshness': 0.2,     # Content recency
    'monetization': 0.3,  # Commercial potential  
    'seo': 0.1           # Search optimization
}
```

### Monetization Keywords
High-value topics include: AI, machine learning, crypto, technology, startups, productivity tools, software, investments

### Quality Thresholds
- Minimum 100 Reddit upvotes
- Minimum 10 comments
- Content length > 200 words
- Credible source domains preferred

## Generated Article Structure

```markdown
---
title: "Article Title"
slug: "url-friendly-slug"
date: 2025-08-05
tags: ["technology", "ai"]
readingTime: 3
monetization:
  ads: true
  affiliate: false
seo:
  title: "SEO-optimized title"
  description: "Meta description under 160 chars"
originalSource:
  url: "https://reddit.com/..."
  engagement: "500 upvotes, 120 comments"
---

# Article Title

*Trending context and engagement metrics*

## What's Happening
Main content based on external sources

## Why This Matters
Analysis and implications

## Key Insights
Research notes and findings

## Join the Discussion
Call-to-action and engagement

## Sources and References
1. [Primary Source](url) - domain.com
2. [Reddit Discussion](url) - engagement metrics
```

## File Organization

### Input Files
- `output/YYYYMMDD_HHMMSS_reddit_subreddit.json` - Raw topic data
- `output/ranked_topics_YYYYMMDD_HHMMSS.json` - Ranked topics
- `output/enriched_topics_YYYYMMDD_HHMMSS.json` - Enriched content

### Output Files
- `site/content/articles/YYYYMMDD-slug.md` - Published articles
- `output/publication_summary_YYYYMMDD_HHMMSS.json` - Publishing report
- `output/pipeline_results_YYYYMMDD_HHMMSS.json` - Full pipeline log
- `output/cleanup_report_YYYYMMDD_HHMMSS.json` - Duplicate cleanup report

## Post-Publication Cleanup

### Duplicate Article Detection
The system includes a post-publication cleanup stage to catch any duplicate articles that may have been published:

```bash
# Clean up duplicate articles
make cleanup-articles

# Dry run to see what would be removed
cd content_processor && python3 content_publisher.py --cleanup-only --dry-run

# Custom similarity threshold (default: 0.8)
cd content_processor && python3 content_publisher.py --cleanup-only --similarity-threshold 0.9
```

### Cleanup Algorithm
1. **Exact Slug Matching**: Identifies articles with identical URL slugs
2. **Content Similarity**: Uses word-overlap analysis to detect near-duplicates
3. **Smart Selection**: Keeps the larger/more recent version when duplicates are found
4. **Safe Operation**: Supports dry-run mode for testing before actual removal

### Cleanup Reports
Generated reports include:
- Total articles analyzed
- Duplicate articles identified and removed
- Detailed list of removed files
- Similarity scores for content-based matches

## Integration with Static Sites

### JAMStack Compatibility
- Standard YAML frontmatter
- Markdown content format
- SEO metadata structure
- Social sharing tags

### Next.js Integration
```javascript
// Compatible with next-mdx-remote
import { serialize } from 'next-mdx-remote/serialize'
import { MDXRemote } from 'next-mdx-remote'

// Frontmatter available for meta tags
const { title, description, tags } = frontmatter
```

### Gatsby Integration
```javascript
// Compatible with gatsby-transformer-remark
export const query = graphql`
  query {
    markdownRemark {
      frontmatter {
        title
        date
        tags
        readingTime
      }
      html
    }
  }
`
```

## Monitoring and Analytics

### Pipeline Status
**Command**: `make content-status`

Shows:
- Recent processed files
- Configuration settings
- Processing statistics
- Directory structure

### Quality Metrics
Each article includes:
- Source credibility scores (0.0-1.0)
- Content quality assessment
- Engagement potential
- SEO optimization score

### Performance Tracking
Monitor:
- Topics processed per day
- Publishing success rate
- Source reliability
- User engagement metrics

## Best Practices

### Content Quality
1. Verify facts from multiple sources
2. Include proper attribution
3. Maintain editorial standards
4. Regular quality audits

### SEO Excellence  
1. Target 1-2 keywords per article
2. Optimize meta descriptions
3. Use descriptive titles
4. Include relevant tags

### Monetization
1. Balance ads with user experience
2. Track performance metrics
3. Test content formats
4. Monitor revenue impact

### Legal Compliance
1. Respect source terms of use
2. Include proper disclaimers
3. Maintain copyright compliance
4. Add affiliate disclosures

## Automation and Scheduling

### Daily Content Generation
```bash
# Crontab example - daily at 9 AM
0 9 * * * cd /path/to/ai-content-farm && make collect-topics && make process-content
```

### Quality Control Points
1. **After Ranking**: Review topic selection
2. **After Enrichment**: Fact-check sources  
3. **Before Publishing**: Content quality review
4. **After Publishing**: Performance monitoring

## Troubleshooting

### Common Issues
- **No topics found**: Check wombles execution, adjust time window
- **External fetch fails**: Verify connectivity, check rate limits
- **Publishing errors**: Check directory permissions, markdown syntax
- **Duplicate articles**: Deduplication runs automatically, but check for file conflicts

### Duplicate Prevention
The pipeline includes multi-stage deduplication:
1. **Topic Ranking**: Removes duplicate topics by title similarity (>80%) and URL matching
2. **Content Publishing**: Additional slug and URL checking before file creation
3. **File System**: Automatic filename conflict resolution with numeric suffixes

**Deduplication Metrics Example**:
```
Loaded 300 topics from last 800 hours
After deduplication: 149 unique topics  # 151 duplicates removed
Publishing 5 articles...                # No duplicate articles generated
```

### Debug Commands
```bash
# Check pipeline status
make content-status

# Test individual stages
make rank-topics
make enrich-content FILE=ranked_file.json
make publish-articles FILE=enriched_file.json

# Verbose logging
python3 content_processor/pipeline.py --mode full 2>&1 | tee debug.log
```

## Future Enhancements

### Content Improvements
- Multi-language support
- Image generation and optimization
- Video content integration
- Podcast episode generation

### Advanced Features
- Machine learning topic prediction
- Automated A/B testing
- Advanced fact-checking APIs
- Real-time trend analysis

### Platform Integration
- CMS system integration
- Social media auto-posting
- Email newsletter generation
- Analytics dashboard

---

*This workflow documentation is part of the AI Content Farm project. For technical implementation details, see the README files in each component directory.*
