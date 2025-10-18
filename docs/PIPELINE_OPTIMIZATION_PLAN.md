# Pipeline Optimization Plan - October 2025

**Status**: Planning Session  
**Created**: October 18, 2025  
**Goal**: Improve efficiency, quality, and cost-effectiveness of content pipeline

## Overview

This document outlines optimization opportunities across the content pipeline based on production observations. The focus is on incremental improvements that reduce costs, improve content quality, and optimize processing flow.

---

## 🎯 Priority 1: Quick Wins (1-2 weeks)

### 1. Markdown Generator - Unnecessary Site Rebuild Requests ⚡ HIGH IMPACT

**Problem**:  
Markdown-generator sends site-publisher queue messages even when no new content was produced. This triggers expensive Hugo builds for no reason.

**Current Behavior**:
```python
# queue_processor.py lines 196-212
if stable_empty_seconds >= STABLE_EMPTY_DURATION and total_processed_since_signal > 0:
    await signal_site_publisher(total_processed_since_signal, output_container)
```

**Issue**: `total_processed_since_signal` counts ALL messages processed, not messages that actually resulted in new/updated markdown files.

**Solution**:
```python
# Track ACTUAL new content generation (not just message processing)
new_files_generated = 0  # Initialize counter

# In message_handler, increment when new file created:
if not file_exists or content_hash_changed:
    new_files_generated += 1

# Only signal if actual new files generated:
if stable_empty_seconds >= STABLE_EMPTY_DURATION and new_files_generated > 0:
    await signal_site_publisher(new_files_generated, output_container)
    new_files_generated = 0  # Reset after signaling
```

**Impact**:
- **Cost Reduction**: 30-50% fewer Hugo builds (currently ~$0.10/build)
- **Performance**: Fewer unnecessary KEDA scale-ups of site-publisher
- **Resource Usage**: Lower compute costs

**Implementation**:
- [ ] Modify `queue_processor.py` to track actual file generation
- [ ] Update `message_handler` to return whether new file was created
- [ ] Test with empty queue and duplicate content scenarios
- [ ] Update metrics/logging to show "files generated" vs "messages processed"

---

### 2. KEDA Scale Rules - Aggressive Tuning ⚡ MEDIUM IMPACT

**Problem**:  
Current KEDA parameters are conservative. We can be more aggressive based on workload characteristics.

**Current Configuration**:

| Container | queueLength | activationQueueLength | cooldown | Issues |
|-----------|-------------|----------------------|----------|--------|
| content-collector | 1 | 1 | 45s | Good - fast scaling |
| content-processor | 16 | 1 | 60s | Too high - batches too large |
| markdown-generator | 1 | 1 | 90s | Good - fast response |
| site-publisher | 1 | 1 | 300s | Too long - delays builds |

**Proposed Changes**:

```terraform
# content-processor (infra/container_apps_keda_auth.tf)
queueLength=8              # DOWN from 16 - smaller batches for faster throughput
activationQueueLength=1    # Keep at 1 - quick activation
cooldown=45               # DOWN from 60s - faster scale-down

# site-publisher
queueLength=1             # Keep at 1 - one build at a time
activationQueueLength=1   # Keep at 1
cooldown=120              # DOWN from 300s - 2 min is enough for Hugo
```

**Rationale**:
- **content-processor**: Processing is CPU-bound (~30-45s per item). Smaller batches = more parallelism via multiple container instances
- **site-publisher**: Hugo builds are fast (~15-30s). 5 minute cooldown is excessive, 2 minutes is plenty

**Impact**:
- **Throughput**: 2x faster processing during peak collection times
- **Cost**: Slightly higher (more container instances), but better user experience
- **Responsiveness**: Faster article publication after collection

**Implementation**:
- [ ] Update `infra/container_apps_keda_auth.tf` with new values
- [ ] Test with production-like workload (50+ articles)
- [ ] Monitor container scaling behavior in Azure Portal
- [ ] Adjust based on actual performance data

---

### 3. Message Dequeue Times - Prevent Duplicate Processing ⚡ HIGH IMPACT

**Problem**:  
Need to verify we're not processing messages multiple times due to visibility timeout issues.

**Current State**: Unknown - needs investigation

**Investigation Required**:
```python
# Check visibility timeout settings in queue clients
# libs/queue_client.py - verify visibility_timeout parameter

# Expected behavior:
# - Message invisible for processing duration
# - If processing fails, message reappears after timeout
# - If processing succeeds, message deleted

# Problem scenarios:
# - Timeout too short: message reappears while still processing → duplicate work
# - No deletion after success: message processed multiple times
```

**Action Items**:
- [ ] Audit all `receive_messages()` calls for `visibility_timeout` parameter
- [ ] Check `delete_message()` is called after successful processing
- [ ] Review Application Insights for duplicate processing patterns
- [ ] Add message deduplication tracking (message_id logging)

**Recommended Settings**:
```python
# content-processor: 90s visibility (45s processing + 45s buffer)
# markdown-generator: 60s visibility (15s generation + 45s buffer)
# site-publisher: 180s visibility (60s build + 120s buffer)
```

**Impact**:
- **Cost Reduction**: Eliminate duplicate processing costs
- **Data Quality**: Prevent duplicate articles
- **Reliability**: Better error handling

---

### 4. Content Collector - Streaming Single Items ⚡ HIGH IMPACT

**Problem**:  
Collector does "big grab → check duplicates → flood of queue messages". The next stage (processor) is the bottleneck, so we should stream items one-by-one to processor ASAP.

**Current Flow**:
```
1. Collect ALL items (50+ articles) - 2-3 minutes
2. Deduplicate in memory
3. Save collection blob
4. Send ALL to processing queue in rapid succession
5. Processor wakes up, starts processing batch (queueLength=16)
```

**Issues**:
- First article doesn't start processing until ALL collection completes
- Processor sees huge queue spike, may not scale fast enough
- Topic fanout already works well for parallelism

**Proposed Streaming Architecture**:

```python
# In collectors/simple_*.py - collect_batch()
async def collect_batch_streaming(self, **kwargs) -> AsyncIterator[Dict[str, Any]]:
    """
    Yield items one-by-one as they're collected and validated.
    
    Instead of collecting all → deduplicate → return list,
    we stream items and check against recent collection history.
    """
    
    # Load recent collection history for deduplication
    recent_items = await load_recent_collection_history(hours=24)
    seen_hashes = {item['content_hash'] for item in recent_items}
    
    async for raw_item in self._fetch_items_stream():
        # Immediate validation and deduplication
        if meets_content_criteria(raw_item) and item_hash not in seen_hashes:
            seen_hashes.add(item_hash)
            yield raw_item  # Stream immediately to caller

# In service_logic.py
async def collect_and_stream_to_processor(self, sources_data):
    """Send items to processor queue as soon as collected."""
    
    for source_config in sources_data:
        collector = create_collector(source_config['type'])
        
        async with collector:
            async for item in collector.collect_batch_streaming():
                # Send IMMEDIATELY to processor queue
                await self._send_processing_request_single(item)
                
                # Also append to collection blob for history
                await self._append_to_collection_file(item)
```

**Benefits**:
- ✅ First article starts processing within seconds (not minutes)
- ✅ Smoother queue load (gradual fill vs spike)
- ✅ Better KEDA scaling behavior (ramps up gradually)
- ✅ Maintains deduplication via recent history lookup

**Trade-offs**:
- More complex implementation (streaming vs batch)
- Need persistent deduplication history (blob storage)
- Must handle partial collection failures differently

**Implementation Phases**:
1. **Phase 1**: Add recent collection history loading (read last 24h of collections)
2. **Phase 2**: Implement streaming in one collector (simple_reddit)
3. **Phase 3**: Test end-to-end with small workload
4. **Phase 4**: Roll out to other collectors if successful

**Estimated Impact**:
- Time-to-first-article: 5 minutes → 30 seconds
- Queue load: Spike pattern → smooth ramp
- User experience: Much faster content availability

---

## 🎯 Priority 2: Medium Term (2-4 weeks)

### 5. Index.html Homepage - Improve Quality 📱 MEDIUM IMPACT

**Problem**:  
Current homepage (index.html) is "still not good" - needs investigation and redesign.

**Investigation Required**:
- [ ] Review current Hugo template for homepage
- [ ] Check responsive design on mobile/tablet
- [ ] Verify article listing, pagination, and layout
- [ ] Test accessibility (a11y) compliance
- [ ] Get user feedback on design

**Potential Issues**:
- Poor article discovery (unclear navigation)
- Weak visual design (not engaging)
- Slow performance (large images, unoptimized CSS)
- Missing metadata (SEO issues)

**Action Items**:
- [ ] Audit `site-publisher/templates/` Hugo templates
- [ ] Review Core Web Vitals metrics for homepage
- [ ] Create design mockups for improved layout
- [ ] Implement iterative improvements
- [ ] A/B test if significant changes

---

### 6. Unsplash API Rate Limiting 💰 MEDIUM IMPACT

**Problem**:  
Hitting Unsplash API limits. Need client-side rate limiting to stay within free tier.

**Current Behavior**:
```python
# containers/markdown-generator/services/image_service.py
async def search_unsplash_image(query, access_key, per_page=1):
    url = f"{UNSPLASH_API_BASE_URL}/search/photos"
    # No rate limiting - just makes request
```

**Unsplash Free Tier Limits**:
- 50 requests per hour
- Demo: unlimited requests but throttled
- Production: Must stay within limits or upgrade

**Solution - Implement Token Bucket Rate Limiter**:

```python
# services/rate_limiter.py
import asyncio
import time
from typing import Optional

class TokenBucketRateLimiter:
    """
    Token bucket rate limiter for Unsplash API.
    
    Free tier: 50 requests/hour = ~0.83 requests/minute
    Use conservative limit: 40 requests/hour = ~0.67 requests/minute
    """
    
    def __init__(self, requests_per_hour: int = 40):
        self.tokens = requests_per_hour
        self.capacity = requests_per_hour
        self.refill_rate = requests_per_hour / 3600  # tokens per second
        self.last_refill = time.time()
        self._lock = asyncio.Lock()
    
    async def acquire(self, timeout: Optional[float] = None) -> bool:
        """
        Acquire a token for making a request.
        
        Args:
            timeout: Maximum time to wait for token (None = wait forever)
            
        Returns:
            True if token acquired, False if timeout
        """
        async with self._lock:
            now = time.time()
            
            # Refill tokens based on time elapsed
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now
            
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            
            # Wait for refill if timeout specified
            if timeout:
                wait_time = (1 - self.tokens) / self.refill_rate
                if wait_time <= timeout:
                    await asyncio.sleep(wait_time)
                    self.tokens = 0
                    self.last_refill = time.time()
                    return True
            
            return False

# Global rate limiter instance
_unsplash_limiter = TokenBucketRateLimiter(requests_per_hour=40)

# Modify image_service.py
async def search_unsplash_image(query, access_key, per_page=1):
    # Wait for rate limit token (max 60s timeout)
    if not await _unsplash_limiter.acquire(timeout=60):
        logger.warning("Unsplash rate limit reached, skipping image")
        return None
    
    # Make request
    url = f"{UNSPLASH_API_BASE_URL}/search/photos"
    # ... rest of implementation
```

**Alternative: Simple In-Memory Counter**:
```python
# Simpler but less accurate
import time

_request_times = []

async def check_rate_limit() -> bool:
    """Simple sliding window rate limiter."""
    now = time.time()
    hour_ago = now - 3600
    
    # Remove old requests
    _request_times[:] = [t for t in _request_times if t > hour_ago]
    
    if len(_request_times) < 40:
        _request_times.append(now)
        return True
    
    return False
```

**Impact**:
- **Cost Savings**: Stay within free tier, avoid upgrade to $X/month
- **Reliability**: Graceful degradation when limit reached
- **User Experience**: Articles still publish (just without images when limited)

**Implementation**:
- [ ] Implement token bucket rate limiter
- [ ] Add metrics tracking (requests/hour, limit hits)
- [ ] Test with high-volume workload
- [ ] Add fallback behavior (use default image or skip image)
- [ ] Monitor Unsplash usage in Application Insights

---

### 7. RSS/Web Content Quality - Filter Low-Quality Sources 📊 HIGH IMPACT

**Problem**:  
"A lot of the web/rss content is rubbish. Particularly from Wired."

**Investigation Required**:

```bash
# Check recent collections for quality scores
# containers/content-collector/collectors/web_utilities.py - meets_content_criteria()

# Current quality criteria:
# - points_per_comment (Reddit)
# - engagement_rate (Mastodon)
# - BUT: No quality filtering for RSS/web scraping
```

**Root Causes**:
1. **No content quality filtering on RSS feeds** - accepts everything
2. **Wired specifically** - may be paywalled, short excerpts, or clickbait
3. **No source reputation tracking** - all sources treated equally

**Solutions**:

#### A. Implement RSS Content Quality Scoring
```python
# collectors/web_utilities.py
def calculate_rss_quality_score(item: Dict[str, Any]) -> float:
    """
    Calculate quality score for RSS/web content.
    
    Factors:
    - Content length (penalize very short articles)
    - Presence of actual article body (not just excerpt)
    - Keywords/topics match (tech, science, etc)
    - Source reputation (configurable whitelist/blacklist)
    - Publication date (prefer recent)
    """
    score = 0.0
    
    # Content length scoring
    content = item.get('content', '') or item.get('summary', '')
    word_count = len(content.split())
    
    if word_count < 100:
        score += 0  # Too short, likely excerpt only
    elif word_count < 300:
        score += 3
    elif word_count < 1000:
        score += 5
    else:
        score += 7  # Full article content
    
    # Source reputation (configurable)
    source_url = item.get('url', '')
    if 'wired.com' in source_url and '<paywall>' in content:
        score -= 10  # Penalize Wired paywalled content
    
    # Topic relevance (check title/content for tech keywords)
    tech_keywords = {'ai', 'software', 'technology', 'engineering', 'science'}
    title_lower = item.get('title', '').lower()
    if any(keyword in title_lower for keyword in tech_keywords):
        score += 3
    
    return score

def meets_content_criteria(item: Dict[str, Any], min_score: float = 5.0) -> bool:
    """Enhanced criteria check with RSS quality scoring."""
    source_type = item.get('source_type', '')
    
    if source_type in ['rss', 'web']:
        quality_score = calculate_rss_quality_score(item)
        return quality_score >= min_score
    
    # Existing criteria for Reddit/Mastodon
    # ...
```

#### B. Source-Specific Configuration
```json
// collection-templates/quality-tech.json
{
  "sources": [
    {
      "type": "rss",
      "feeds": [
        {
          "url": "https://feeds.arstechnica.com/arstechnica/index",
          "reputation": 0.9,
          "min_quality_score": 5
        },
        {
          "url": "https://feeds.wired.com/wired/index",
          "reputation": 0.5,
          "min_quality_score": 8,
          "skip_if_paywall": true
        }
      ]
    }
  ]
}
```

#### C. Post-Collection Quality Filtering
```python
# Add quality filtering AFTER collection but BEFORE deduplication
collected_items = await collect_content_batch(sources_data)

# Apply quality filtering
quality_filtered = [
    item for item in collected_items 
    if calculate_rss_quality_score(item) >= min_quality_score
]

logger.info(
    f"Quality filtering: {len(collected_items)} → {len(quality_filtered)} items "
    f"(removed {len(collected_items) - len(quality_filtered)} low-quality)"
)

# Then deduplicate
deduplicated = await deduplicate_content(quality_filtered)
```

**Impact**:
- **Content Quality**: 30-50% reduction in low-value articles
- **Cost Savings**: Fewer articles to process/store/publish
- **User Experience**: Higher quality content on site
- **Processing Efficiency**: Less waste in pipeline

**Implementation**:
- [ ] Implement `calculate_rss_quality_score()` function
- [ ] Add source reputation configuration to templates
- [ ] Test with production Wired RSS feed
- [ ] Tune quality thresholds based on results
- [ ] Add metrics tracking (quality score distribution)

---

## 🎯 Priority 3: Research & Long-Term (4+ weeks)

### 8. Article Research & Referencing 🔬 HIGH VALUE

**Problem**:  
"We need to do more research and referencing on our articles."

**Current State**:
- content-processor generates articles from AI (GPT-4) based on topic only
- No external research or fact-checking
- No citations or references
- No source verification

**Vision**:
Multi-step research pipeline that produces well-researched, referenced content.

**Proposed Architecture**:

```
Topic → Research Phase → Fact-Checking Phase → Article Generation → Citation Formatting
```

#### Phase 1: Research Phase (NEW)
```python
# New service: containers/content-researcher/

async def research_topic(topic: Dict[str, Any]) -> Dict[str, Any]:
    """
    Conduct research on a topic using multiple sources.
    
    Returns:
        {
            "topic_id": "...",
            "research_results": [
                {
                    "source": "wikipedia",
                    "url": "https://en.wikipedia.org/wiki/...",
                    "summary": "...",
                    "key_facts": ["fact1", "fact2"],
                    "credibility_score": 0.95
                },
                {
                    "source": "arxiv",
                    "url": "https://arxiv.org/abs/...",
                    "summary": "...",
                    "key_facts": ["research finding 1"],
                    "credibility_score": 0.99
                }
            ],
            "synthesis": "Overall understanding of topic based on research"
        }
    """
    
    # Research sources:
    # 1. Wikipedia API - general knowledge
    # 2. arXiv API - academic papers (for technical topics)
    # 3. Google Scholar - research citations
    # 4. Perplexity AI API - AI-powered research assistant
    # 5. Original source article (if URL available)
```

#### Phase 2: Fact-Checking Phase (NEW)
```python
async def fact_check_claims(research: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verify key claims against multiple sources.
    
    Returns:
        {
            "verified_facts": ["fact1", "fact2"],
            "disputed_facts": ["fact3"],
            "unchecked_facts": ["fact4"],
            "confidence_score": 0.87
        }
    """
    
    # Cross-reference claims across multiple sources
    # Flag claims that appear in only one source
    # Identify contradictions between sources
```

#### Phase 3: Enhanced Article Generation
```python
# Modify containers/content-processor/services/article_generation.py

async def generate_article_with_research(
    topic: Dict[str, Any],
    research: Dict[str, Any],
    fact_check: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate article using research and fact-checking results.
    
    Prompt includes:
    - Original topic
    - Research summaries
    - Verified facts
    - Citations in proper format
    """
    
    prompt = f"""
    Write a well-researched article on: {topic['title']}
    
    Research Sources:
    {format_research_sources(research)}
    
    Key Verified Facts:
    {format_verified_facts(fact_check)}
    
    Requirements:
    - Include inline citations [1], [2], etc
    - Reference all sources properly
    - Present balanced perspective
    - Highlight disputed claims appropriately
    """
    
    article = await openai_client.generate(prompt)
    
    # Append references section
    article['content'] += format_references_section(research)
    
    return article
```

**Research APIs to Integrate**:

| API | Purpose | Cost | Rate Limits |
|-----|---------|------|-------------|
| Wikipedia API | General knowledge | Free | 200 req/s |
| arXiv API | Academic papers | Free | Unlimited |
| Perplexity AI | AI research | $5/month | 5 req/s |
| Brave Search | Web search | $5/month | 2000 req/month |
| CrossRef | Academic citations | Free | 50 req/s |

**Implementation Phases**:

**Phase A: Wikipedia Integration (Week 1-2)**
- [ ] Create Wikipedia API client
- [ ] Extract relevant sections from articles
- [ ] Add citations to generated content
- [ ] Test with 10-20 topics

**Phase B: Fact-Checking MVP (Week 3-4)**
- [ ] Implement basic cross-reference checking
- [ ] Flag unverified claims
- [ ] Add confidence scores to articles

**Phase C: Academic Sources (Week 5-6)**
- [ ] Integrate arXiv for technical topics
- [ ] Add academic citation formatting
- [ ] Create bibliography generation

**Phase D: AI Research Assistant (Week 7-8)**
- [ ] Integrate Perplexity AI API
- [ ] Combine AI research with traditional sources
- [ ] Fine-tune prompts for best results

**Estimated Costs**:
- Wikipedia: Free
- arXiv: Free
- Perplexity AI: $5-10/month
- Brave Search: $5/month
- **Total**: ~$10-15/month additional

**Impact**:
- **Content Quality**: 10x improvement in depth and accuracy
- **Trust**: Citations and references build credibility
- **SEO**: Better content = better search rankings
- **Unique Value**: Differentiation from other content farms

---

## Implementation Roadmap

### Sprint 1 (Week 1-2): Quick Wins
- [x] Planning session (this document)
- [ ] Issue #1: Markdown generator unnecessary rebuilds
- [ ] Issue #2: KEDA scale rule tuning
- [ ] Issue #3: Message dequeue audit
- [ ] Deploy and monitor changes

### Sprint 2 (Week 3-4): Streaming & Quality
- [ ] Issue #4: Streaming collector implementation
- [ ] Issue #6: Unsplash rate limiting
- [ ] Issue #7: RSS quality filtering
- [ ] A/B test streaming vs batch collection

### Sprint 3 (Week 5-6): Polish & Monitoring
- [ ] Issue #5: Homepage redesign
- [ ] Comprehensive monitoring dashboard
- [ ] Performance optimization based on data
- [ ] Documentation updates

### Sprint 4 (Week 7-8): Research Pipeline
- [ ] Issue #8: Wikipedia integration (Phase A)
- [ ] Basic fact-checking (Phase B)
- [ ] Test with production workload
- [ ] Iterate based on quality metrics

---

## Success Metrics

### Cost Metrics
- [ ] Reduce unnecessary Hugo builds by 40%
- [ ] Stay within Unsplash free tier
- [ ] Overall pipeline cost reduction: $10-15/month savings

### Performance Metrics
- [ ] Time-to-first-article: 5 min → 30 sec
- [ ] Processing throughput: 100+ articles/hour
- [ ] End-to-end latency: <10 minutes for 50 articles

### Quality Metrics
- [ ] RSS content quality score: >7.0 average
- [ ] Article research depth: 3+ sources per article
- [ ] Citation coverage: 80%+ of factual claims referenced

### Operational Metrics
- [ ] Zero duplicate message processing
- [ ] KEDA scaling efficiency: <30s scale-up time
- [ ] Container resource utilization: 70-85% (not over/under)

---

## Next Steps

1. **Review this plan** with stakeholders/users
2. **Prioritize** based on impact vs effort
3. **Create GitHub issues** for each work item
4. **Start with Sprint 1** quick wins
5. **Monitor and iterate** based on results

---

## Questions & Discussion Points

### For User/Stakeholder Review:
- [ ] Which issues are most painful currently?
- [ ] Any other quality/performance concerns not covered?
- [ ] Budget constraints for research API costs?
- [ ] Timeline expectations for each sprint?

### Technical Decisions Needed:
- [ ] Streaming vs batch: Full rollout or hybrid approach?
- [ ] Rate limiting: Token bucket vs simpler sliding window?
- [ ] Research depth: How many sources per article minimum?
- [ ] Quality scoring: What threshold is "good enough"?

---

_Last Updated: October 18, 2025_  
_Next Review: After Sprint 1 completion_
