# TODO - AI Content Farm Refactor

**Status**: Clean refactor in Azure 'prod' environment  
**Goal**: Daily digest at jablab.com with 5 most interesting topics + deep dives

## 🎯 New Refined Vision

**End Goal**: `jablab.com` daily digest featuring:
- **5 most interesting topics** from verified sources (Reddit tech, science, LinkedIn MSP/dev)  
- **Briefing mode**: Quick summaries for daily scan
- **Deep dive mode**: Research-level articles for topics worth exploring
- **Trustworthy sources**: Verifiable content we can safely write about

**Clean Architecture** (4 services):
```
Sources → Collector → Processor → Publisher → jablab.com
         (find leads) (rank/research) (generate site)
```

## 🚀 Current Approach: Develop in Azure Production

**Why**: Eliminate local/cloud complexity, work directly where it matters
**Breaking change**: Acceptable since not live yet, complexity reduction is priority

### Phase 1: Clean Collector (Week 1) - ✅ COMPLETED!
**Goal**: Build the foundation right - standardized content discovery

#### ✅ BREAKTHROUGH: Topic Intelligence Collector Working!
**Achievement**: Built a sophisticated topic intelligence system that:
- **Listens to conversations** across platforms without scraping content
- **Identifies trending topics** worth researching (not content to copy)
- **Scores research potential** based on engagement, novelty, fact-check needs
- **Generates research recommendations** with specific angles and source types
- **Saves topics to blob storage** for pipeline processing

**Example Output**:
```json
{
  "topic_id": "ecb9b37ad49f",
  "title": "Trending: AI reasoning breakthrough", 
  "research_potential": 0.97,
  "fact_check_needed": true,
  "research_angle": "Technical analysis and implications",
  "source_types_needed": ["academic papers", "peer-reviewed studies"],
  "estimated_research_depth": "2-4 hours"
}
```

**Key Innovation**: We're not scraping - we're **listening for what to research**!

#### Week 1 Tasks: ✅ DONE
- [x] **Design Standard API Model**: Clean, consistent FastAPI response format
- [x] **Refactor Collector**: Focused on topic intelligence and trend detection
- [x] **Multi-platform Support**: Reddit, Twitter, LinkedIn, YouTube ready
- [x] **Research Scoring**: Intelligent scoring for research potential
- [x] **Blob Storage Integration**: Topics saved for pipeline processing

### Phase 2: Research Processor (Week 2) - NEXT
**Goal**: Take trending topics and create original research papers

#### Week 2 Tasks:
- [ ] **Research Engine**: Take topic recommendations and build comprehensive research
  - Fact-check claims using authoritative sources
  - Find academic papers and industry reports
  - Interview experts or find expert quotes
  - Build reference lists and citations
- [ ] **Original Analysis**: Create original insights, not just summaries
  - Technical implications and predictions
  - Cross-reference multiple viewpoints
  - Identify gaps in current understanding
- [ ] **Quality Control**: Ensure research meets publication standards
  - Verify all claims with sources
  - Check for bias and balance perspectives
  - Maintain high editorial standards

### Phase 3: Publisher (Week 3)
**Goal**: Generate beautiful static site at jablab.com

- [ ] **Article Generation**: Transform ranked topics into articles
- [ ] **Site Generation**: Create clean, fast static site
- [ ] **Domain Setup**: Configure jablab.com to point to Azure
- [ ] **Content Modes**: Implement briefing vs deep-dive presentation

## 🔧 Technical Implementation

### Standard API Response Format
```json
{
  "status": "success|error|processing",
  "message": "Human-readable description",
  "data": {...},
  "metadata": {
    "timestamp": "2025-08-28T10:00:00Z",
    "service": "collector",
    "version": "2.0.0"
  }
}
```

### Azure Container Strategy
- **External Access**: content-gen, site-gen (for testing/preview)
- **Internal Services**: collector, processor (communicate via blob storage)
- **Development**: Work directly in Azure, test via external endpoints

### Content Pipeline
1. **Collector** → `collected-topics/` blob container
2. **Processor** → `ranked-content/` blob container  
3. **Publisher** → `published-sites/` blob container + jablab.com

## 🎯 Current Azure Status

**Working Containers**:
- ✅ `ai-content-prod-content-gen` (external access)
- ✅ `ai-content-prod-site-gen` (external access)
- ✅ All other containers (internal only)

**Immediate Actions**:
1. **Start with Collector refactor** in Azure
2. **Use content-gen container** for testing new API patterns
3. **Focus on clean, simple implementation** over feature completeness

## 📋 Success Criteria

**Phase 1 Complete When**:
- [ ] Collector finds 20+ quality topics daily from multiple sources
- [ ] Standard API responses work consistently across all endpoints
- [ ] Can trigger collection via external API and see results in blob storage

**Final Success**:
- [ ] jablab.com shows daily digest with 5 best topics
- [ ] Users can switch between briefing and deep-dive modes
- [ ] Content updates automatically without manual intervention
- [ ] Monthly Azure costs under $50

---

**Next Action**: Start refactoring the Collector service in Azure with clean API patterns
