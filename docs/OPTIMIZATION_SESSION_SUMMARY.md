# Pipeline Optimization - Planning Session Summary

**Date**: October 18, 2025  
**Type**: Planning & Research Session  
**Output**: Comprehensive optimization plan with 8 improvement areas

## 📋 What We Created

Created **`docs/PIPELINE_OPTIMIZATION_PLAN.md`** - a detailed roadmap for improving the content pipeline across efficiency, quality, and cost dimensions.

## 🎯 Key Problem Areas Identified

### Critical Issues (High Impact)
1. **Markdown Generator Waste** - Rebuilding site even with no new content (~30-50% unnecessary builds)
2. **Message Deduplication** - Need audit to ensure no duplicate processing
3. **Streaming Collection** - Current "big batch" approach delays first article by 5+ minutes
4. **RSS Quality** - Accepting too much low-quality content (especially Wired)
5. **Research Depth** - Articles lack citations and fact-checking

### Medium Priority
6. **KEDA Scale Tuning** - Can be more aggressive for better throughput
7. **Unsplash Rate Limits** - Hitting API limits, need client-side rate limiting
8. **Homepage Design** - Current index.html needs improvement

## 💡 High-Impact Solutions

### 1. Smart Site Rebuild Signaling
**Problem**: Markdown-generator counts "messages processed" not "files created"  
**Solution**: Only signal site-publisher when NEW content actually generated  
**Impact**: 30-50% cost reduction, fewer unnecessary Hugo builds

### 2. Streaming Collection Architecture
**Problem**: Collect all → dedupe → flood queue (first article waits 5+ minutes)  
**Solution**: Stream items one-by-one to processor as collected  
**Impact**: Time-to-first-article: 5 min → 30 seconds

### 3. RSS Quality Scoring
**Problem**: "Rubbish" content from web/RSS, especially Wired paywalled articles  
**Solution**: Calculate quality scores (content length, keywords, source reputation)  
**Impact**: 30-50% reduction in low-value articles

### 4. Research Pipeline
**Problem**: No fact-checking, citations, or source verification  
**Solution**: Multi-phase research (Wikipedia → Fact-check → Generate with citations)  
**Impact**: 10x improvement in content quality and credibility

## 📊 Implementation Roadmap

### Sprint 1 (Week 1-2): Quick Wins - $10-15/month savings
- ✅ Planning complete
- 🔲 Fix markdown generator unnecessary rebuilds
- 🔲 Tune KEDA parameters (queueLength, cooldown)
- 🔲 Audit message dequeue/deletion

### Sprint 2 (Week 3-4): Streaming & Quality
- 🔲 Implement streaming collector (Reddit first)
- 🔲 Add Unsplash rate limiting (token bucket)
- 🔲 RSS quality filtering and scoring

### Sprint 3 (Week 5-6): Polish
- 🔲 Homepage redesign
- 🔲 Monitoring dashboard
- 🔲 Performance tuning

### Sprint 4 (Week 7-8): Research Pipeline
- 🔲 Wikipedia integration
- 🔲 Basic fact-checking
- 🔲 Citation formatting

## 🎲 Architectural Decisions

### Token Bucket vs Sliding Window (Unsplash Rate Limiting)
**Recommendation**: Token bucket - more sophisticated, handles burst traffic better

### Streaming vs Batch Collection
**Recommendation**: Hybrid approach
- Start with streaming for Reddit (highest volume)
- Keep batch for RSS/Mastodon (simpler, lower volume)
- Evaluate after production testing

### KEDA Scale Parameters
**Recommendations**:
```
content-processor:  queueLength=8 (down from 16), cooldown=45s
site-publisher:     queueLength=1, cooldown=120s (down from 300s)
```

### RSS Quality Threshold
**Recommendation**: Start with min_score=5.0, tune based on results
- Score factors: content length, topic relevance, source reputation
- Wired: Higher threshold (8.0) + paywall detection

## 📈 Expected Outcomes

### Cost Impact
- **Immediate** (Sprint 1): -$10-15/month from reduced Hugo builds
- **Medium-term** (Sprint 2): Unsplash stays in free tier
- **Research Phase**: +$10-15/month for research APIs (net neutral)

### Performance Impact
- **Latency**: 5 minutes → 30 seconds for first article
- **Throughput**: 2x faster during peak collection periods
- **Responsiveness**: Better KEDA scaling behavior

### Quality Impact
- **Content**: 30-50% reduction in low-quality articles
- **Research**: 3+ sources per article with citations
- **Trust**: Fact-checking and references improve credibility

## 🚀 Next Actions

### Immediate (This Week)
1. **Review this plan** - Get stakeholder feedback on priorities
2. **Create GitHub issues** - One issue per work item with acceptance criteria
3. **Start Sprint 1** - Begin with markdown generator fix (highest impact)

### Technical Prep
1. **Set up monitoring** - Add metrics for "files generated" vs "messages processed"
2. **Create test workload** - 50+ article collection for performance testing
3. **Baseline measurements** - Current costs, latency, quality scores

### Decision Points
- [ ] Budget approval for research APIs (~$10-15/month)
- [ ] Timeline expectations for each sprint
- [ ] Which issues are most painful (prioritization)
- [ ] Streaming rollout strategy (phased or full)

## 📚 Related Documentation

- **Full Plan**: `docs/PIPELINE_OPTIMIZATION_PLAN.md` (this session's output)
- **Current Architecture**: `docs/PHASE_2_FANOUT_COMPLETE.md`
- **Deduplication Strategy**: `docs/PIPELINE_DEDUPLICATION_STRATEGY.md`
- **KEDA Configuration**: `infra/container_apps_keda_auth.tf`

## 🤔 Open Questions

### For Discussion:
1. **Streaming complexity** - Worth the implementation effort vs batch simplicity?
2. **Quality vs quantity** - Acceptable trade-off to reject more content?
3. **Research depth** - How many sources per article is "enough"?
4. **Cost sensitivity** - Should we optimize for minimum cost or best quality?

### Technical Investigations:
1. **Message visibility timeouts** - Are we handling correctly? (needs audit)
2. **Index.html issues** - What specifically is "not good"? (needs user feedback)
3. **Wired content** - Is it paywall detection or just poor RSS feeds?
4. **Duplicate processing** - Any evidence in Application Insights logs?

---

## Summary

This planning session produced a comprehensive 8-point optimization plan targeting:
- **Efficiency**: Streaming collection, smarter rebuilds, better scaling
- **Quality**: RSS filtering, research pipeline, fact-checking
- **Cost**: Rate limiting, fewer wasteful operations, monitoring

**Highest ROI items**: Markdown generator fix, streaming collection, RSS quality scoring  
**Timeline**: 8 week roadmap split into 4 sprints  
**Investment**: ~$10-15/month net (savings offset research API costs)

The plan is **conservative and incremental** - each sprint delivers value independently, so we can pause/adjust based on results.

---

_Ready to proceed with Sprint 1 when approved._
