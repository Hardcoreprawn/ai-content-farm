# Site Generator Split - Implementation Package

**Created:** October 7, 2025  
**Status:** Ready for Implementation  
**Branch:** `feature/split-site-generator`

---

## 📦 What's in This Package

This implementation package contains everything needed to split the monolithic `site-generator` container into two specialized containers with proper testing, documentation, and infrastructure.

### Core Documents

1. **[Architecture Decision](./SITE_GENERATOR_ARCHITECTURE_DECISION.md)**
   - Problem analysis and architectural options
   - Cost/benefit comparison
   - Recommendation and justification
   - 📍 **Start here** to understand WHY we're doing this

2. **[Implementation Plan](./SITE_GENERATOR_SPLIT_IMPLEMENTATION_PLAN.md)**
   - Complete 2-week implementation schedule
   - Detailed code examples for both containers
   - Phase-by-phase breakdown
   - Testing strategy
   - Migration and cleanup procedures
   - 📍 **Main reference** during implementation

3. **[Code Standards](./CODE_STANDARDS_SITE_GENERATOR_SPLIT.md)**
   - PEP8 compliance rules
   - Type hint requirements
   - File organization patterns
   - Outcome-based testing guidelines
   - Tooling and automation
   - 📍 **Keep open** while writing code

4. **[Quick Start Guide](./QUICKSTART_SITE_GENERATOR_SPLIT.md)**
   - Step-by-step setup instructions
   - Ready-to-paste code snippets
   - Daily progress checklist
   - Troubleshooting guide
   - 📍 **Use this** to start coding immediately

5. **[GitHub Issue Template](./GITHUB_ISSUE_SITE_GENERATOR_SPLIT.md)**
   - Pre-formatted issue with all tasks
   - Acceptance criteria checklist
   - Success metrics
   - Risk mitigation
   - 📍 **Create issue** from this template

---

## 🎯 Project Goals

### Primary Objectives
✅ Split `site-generator` into two specialized containers:
- `markdown-generator`: Fast per-article conversion (JSON → Markdown)
- `site-builder`: Batched full-site generation (Markdown → HTML)

✅ Achieve 63% cost reduction ($1.08 → $0.40/month)

✅ Reduce article processing latency by 85% (40s → 7s)

✅ Maintain 100% backward compatibility during migration

✅ Implement comprehensive unit tests (90%+ coverage)

✅ Follow PEP8 standards with type hints (<500 lines per file)

### Success Criteria
- ✅ All unit tests pass with 90%+ coverage
- ✅ KEDA scaling works correctly for each container
- ✅ Zero data loss during migration
- ✅ Performance targets met (5s/article, 60s/site)
- ✅ Cost reduction validated

---

## 📐 High-Level Architecture

### Current (Single Container)
```
[content-processor] → [site-generation-requests] → [site-generator]
                                                           ↓
                                      (JSON → Markdown → HTML - all in one)
                                                           ↓
                                              [markdown-content, $web]
```

**Problems:**
- ❌ Inefficient: Full site rebuild for each article
- ❌ Conflicting KEDA patterns (individual vs batch)
- ❌ Slow: 40s per article (mostly wasted on regenerating unchanged content)
- ❌ Complex logic mixing two workflows

### Proposed (Two Containers)
```
[content-processor] → [markdown-generation-requests] → [markdown-generator]
                                                               ↓
                                                    [markdown-content]
                                                               ↓
                                                    (triggers after N files)
                                                               ↓
                           [site-build-requests] → [site-builder]
                                                               ↓
                                                           [$web]
```

**Benefits:**
- ✅ Efficient: Separate per-article and batch operations
- ✅ Optimal KEDA: Different scaling rules for each pattern
- ✅ Fast: 7s per article + batched site builds
- ✅ Clean: Each container has ONE responsibility

---

## 🏗️ Implementation Timeline

### Week 1: Development
- **Day 1**: Markdown-generator scaffolding
- **Day 2**: Site-builder scaffolding  
- **Day 3**: Unit tests for markdown-generator
- **Day 4**: Unit tests for site-builder
- **Day 5**: Infrastructure (Terraform)

### Week 2: Deployment
- **Day 6**: CI/CD integration
- **Day 7**: Parallel deployment
- **Day 8**: Traffic cutover and validation
- **Day 9**: Deprecate old container
- **Day 10**: Cleanup and documentation

---

## 📋 Quick Reference

### Container Specifications

#### markdown-generator
- **Purpose**: Convert JSON articles to markdown
- **Scaling**: KEDA queue (`queueLength=1`), 0→5 replicas
- **Resources**: 0.25 CPU, 0.5Gi RAM
- **Processing Time**: ~5s per article
- **API Endpoints**:
  - `POST /api/markdown/generate` - Single article
  - `POST /api/markdown/batch` - Multiple articles
  - `GET /api/markdown/status` - Metrics
  - `GET /health` - Health check

#### site-builder
- **Purpose**: Generate complete static HTML site
- **Scaling**: KEDA queue (`queueLength=5`) + cron (hourly), 0→1 replicas
- **Resources**: 0.5 CPU, 1Gi RAM
- **Processing Time**: ~30-60s for full site (100 articles)
- **API Endpoints**:
  - `POST /api/site/build-full` - Full rebuild
  - `POST /api/site/build-incremental` - Add page + update index
  - `POST /api/site/regenerate-index` - Index only
  - `GET /api/site/status` - Metrics
  - `GET /health` - Health check

### File Structure

```
containers/
├── markdown-generator/
│   ├── main.py                 # FastAPI app (~150 lines)
│   ├── markdown_processor.py  # Core logic (~250 lines)
│   ├── models.py               # Pydantic models (~100 lines)
│   ├── config.py               # Configuration (~100 lines)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── tests/
│       ├── conftest.py
│       ├── test_outcomes.py
│       ├── test_api_endpoints.py
│       └── test_queue_processing.py
│
├── site-builder/
│   ├── main.py                 # FastAPI app (~150 lines)
│   ├── site_builder.py         # Core logic (~300 lines)
│   ├── index_manager.py        # Index management (~150 lines)
│   ├── models.py               # Pydantic models (~100 lines)
│   ├── config.py               # Configuration (~100 lines)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── tests/
│       ├── conftest.py
│       ├── test_outcomes.py
│       ├── test_index_management.py
│       └── test_api_endpoints.py
│
└── site-generator/             # DEPRECATED
    └── README.md (deprecation notice)
```

### Infrastructure Changes

**New Resources:**
- Container App: `ai-content-prod-markdown-gen`
- Container App: `ai-content-prod-site-builder`
- Storage Queue: `markdown-generation-requests`
- Storage Queue: `site-build-requests`

**Removed Resources:**
- Container App: `ai-content-prod-site-generator`
- Storage Queue: `site-generation-requests`

---

## 🚀 Getting Started

### Prerequisites
```bash
# Required tools
python 3.11+
docker
terraform
azure-cli
git

# Development dependencies
pip install black flake8 mypy pytest pytest-cov pytest-asyncio
```

### Create Feature Branch
```bash
git checkout -b feature/split-site-generator
```

### Follow Quick Start Guide
See **[QUICKSTART_SITE_GENERATOR_SPLIT.md](./QUICKSTART_SITE_GENERATOR_SPLIT.md)** for step-by-step instructions.

### Create GitHub Issue
```bash
gh issue create \
  --title "Split site-generator into specialized containers" \
  --body-file docs/GITHUB_ISSUE_SITE_GENERATOR_SPLIT.md \
  --label "enhancement,infrastructure,containers"
```

---

## 📊 Expected Outcomes

### Performance Improvements
| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| Article Processing | 40s | 7s | 82% faster |
| Site Build | 30s (per article) | 60s (batched) | 80% reduction |
| Queue Latency | Variable | <2s | Consistent |
| Cold Start | 10s | 10s (markdown), 10s (site) | Same |

### Cost Improvements
| Component | Current | Target | Savings |
|-----------|---------|--------|---------|
| site-generator | $1.08/month | - | Removed |
| markdown-generator | - | $0.25/month | New |
| site-builder | - | $0.15/month | New |
| **Total** | **$1.08/month** | **$0.40/month** | **63% reduction** |

### Quality Improvements
- ✅ 90%+ test coverage (vs current ~60%)
- ✅ PEP8 compliant (enforced with tooling)
- ✅ Complete type hints (mypy --strict passes)
- ✅ All files <500 lines (better maintainability)
- ✅ Outcome-based tests (clearer intent)

---

## 🛡️ Risk Mitigation

### Identified Risks

1. **Data Loss During Migration**
   - **Mitigation**: Parallel deployment, comprehensive testing, rollback plan
   - **Impact**: High → Low

2. **Cost Increase Instead of Reduction**
   - **Mitigation**: Monitor costs daily during migration, immediate rollback if >2x target
   - **Impact**: Medium → Low

3. **KEDA Scaling Issues**
   - **Mitigation**: Extensive testing of scale rules, alerts on scaling failures
   - **Impact**: Medium → Low

4. **Breaking Changes for Downstream**
   - **Mitigation**: Maintain backward compatibility during migration, clear communication
   - **Impact**: Low → Negligible

### Rollback Plan

If issues detected during migration:

```bash
# 1. Stop traffic to new containers
az containerapp update --name ai-content-prod-markdown-gen \
  --min-replicas 0 --max-replicas 0

# 2. Restart old container
az containerapp update --name ai-content-prod-site-generator \
  --min-replicas 0 --max-replicas 2

# 3. Revert queue routing in content-processor
# (Update config to send to site-generation-requests)

# 4. Monitor for stability

# 5. Investigate and fix issues

# 6. Retry migration when ready
```

---

## 📈 Monitoring & Validation

### Key Metrics to Track

**During Development:**
- Test coverage (target: 90%+)
- Code quality scores (black, flake8, mypy)
- File line counts (target: <500 lines)

**During Migration:**
- Queue depths (both old and new)
- Container scaling events
- Processing latencies
- Error rates
- Cost per operation

**Post-Migration:**
- Total monthly cost
- Average processing time
- KEDA scaling efficiency
- User-reported issues

### Success Indicators

✅ **Week 1**: All tests passing, code quality checks pass  
✅ **Week 2 Day 7**: Parallel deployment successful  
✅ **Week 2 Day 8**: New containers handling 100% of traffic  
✅ **Week 2 Day 10**: Old container removed, costs reduced

---

## 🤝 Support & Questions

### During Implementation

**Technical Questions**: Check implementation plan or code standards docs  
**Architecture Questions**: Review architecture decision doc  
**Getting Stuck**: Refer to troubleshooting section in quick start guide

### After Implementation

**Production Issues**: Follow runbooks (to be created)  
**Performance Problems**: Check monitoring dashboards  
**Cost Concerns**: Review cost tracking in Azure portal

---

## 📚 Document Index

All documents in this package:

1. **SITE_GENERATOR_ARCHITECTURE_DECISION.md** - Why split? (Architecture analysis)
2. **SITE_GENERATOR_SPLIT_IMPLEMENTATION_PLAN.md** - How to implement? (Complete guide)
3. **CODE_STANDARDS_SITE_GENERATOR_SPLIT.md** - What standards? (PEP8, testing, etc.)
4. **QUICKSTART_SITE_GENERATOR_SPLIT.md** - How to start? (Step-by-step)
5. **GITHUB_ISSUE_SITE_GENERATOR_SPLIT.md** - Issue template (Task tracking)
6. **README_IMPLEMENTATION_PACKAGE.md** - This document (Overview)

---

## ✅ Pre-Implementation Checklist

Before you begin coding:

- [ ] Read architecture decision document
- [ ] Understand the two-container approach
- [ ] Review code standards (PEP8, type hints, file size)
- [ ] Install all development tools (black, flake8, mypy, pytest)
- [ ] Create feature branch
- [ ] Create GitHub issue from template
- [ ] Review quick start guide
- [ ] Understand migration strategy

---

## 🎉 Ready to Start?

**Next Action:** Open **[QUICKSTART_SITE_GENERATOR_SPLIT.md](./QUICKSTART_SITE_GENERATOR_SPLIT.md)** and begin Phase 1!

**Questions before starting?** Review the architecture decision document or ask for clarification.

**Good luck! This is going to be great!** 🚀

---

*Package Created: October 7, 2025*  
*Last Updated: October 7, 2025*  
*Version: 1.0*
