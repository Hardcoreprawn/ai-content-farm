# Site Publisher Container - Executive Summary

**Date**: October 10, 2025  
**Decision Required**: Hugo (Go) vs Pelican (Python) for Static Site Generation  
**Recommendation**: Hugo ⭐  
**Full Design**: See `docs/SITE_PUBLISHER_DESIGN.md`

## Quick Decision Matrix

| Criterion | Hugo (Go) | Pelican (Python) |
|-----------|-----------|------------------|
| **Build Speed** | ⭐⭐⭐⭐⭐ (1000s pages/sec) | ⭐⭐ (10-100x slower) |
| **Container Size** | ⭐⭐⭐⭐⭐ (~50-80 MB) | ⭐⭐ (~200-400 MB) |
| **Language Fit** | ⭐⭐⭐ (New, but simple) | ⭐⭐⭐⭐⭐ (Python native) |
| **Ecosystem** | ⭐⭐⭐⭐⭐ (300+ themes, huge community) | ⭐⭐⭐ (Smaller ecosystem) |
| **Simplicity** | ⭐⭐⭐⭐⭐ (Single binary) | ⭐⭐⭐ (Python + deps) |
| **Industry Adoption** | ⭐⭐⭐⭐⭐ (#1 SSG globally) | ⭐⭐⭐ (Less popular) |
| **Cost Efficiency** | ⭐⭐⭐⭐⭐ (Fast = cheaper) | ⭐⭐⭐ (Slower = pricier) |

## Recommendation: Hugo ✅

### Why Hugo Despite Python Stack?

**Performance is King**: Hugo's build speed (orders of magnitude faster) means:
- Lower Azure compute costs
- Faster deployments
- Better scalability as content grows
- Minimal resource usage (0.5 vCPU, 1 GiB memory sufficient)

**Simplicity**: Single binary with no dependency management:
```dockerfile
# Just copy Hugo binary - that's it!
COPY --from=hugo-builder /go/bin/hugo /usr/local/bin/hugo
```

**Industry Standard**: Most popular SSG means:
- Better long-term support
- More themes and plugins
- Larger community for help
- More examples and tutorials

**Learning Go Templates**: Minimal investment for massive benefits
- Template syntax is straightforward
- We only need basic templates (theme handles most)
- One-time learning curve

### The Trade-off We're Making

**Giving Up**: Python language consistency across all containers  
**Gaining**: 10-100x performance, 50% smaller containers, industry-standard tooling

**Verdict**: Worth it. Hugo is purpose-built for static sites; Pelican is a Python project that happens to generate sites.

## Architecture Overview

### Pipeline Flow
```
markdown-generation-requests queue becomes empty
    ↓
markdown-generator sends completion message
    ↓
site-publishing-requests queue
    ↓
KEDA scales site-publisher (0 → 1)
    ↓
1. Download all markdown from markdown-content container
2. Build complete site with Hugo
3. Deploy HTML/CSS/JS to $web container
4. Site live at static website URL
    ↓
Scale back to 0 (cost efficiency)
```

### Key Design Decisions

#### 1. Full Site Rebuild (Not Incremental) ✅
**Why**: Simplicity, consistency, reliability  
**Performance**: Hugo builds 1000+ pages in seconds, so full rebuild is fast enough

#### 2. Queue-Triggered (Not Timer) ✅
**Why**: Efficient - only rebuild when new content available  
**Trigger**: markdown-generator signals when its queue empties

#### 3. Multi-Stage Docker Build ✅
```dockerfile
# Stage 1: Get Hugo binary from Go image
FROM golang:1.23-alpine AS hugo-builder
RUN go install github.com/gohugoio/hugo@v0.138.0

# Stage 2: Python runtime + Hugo (using 3.13 for 4 years security support)
FROM python:3.13-slim
COPY --from=hugo-builder /go/bin/hugo /usr/local/bin/hugo
```

#### 4. Hugo Theme: PaperMod ✅
**Why**: Clean, minimal, SEO-optimized, search built-in, active maintenance

## Implementation Plan

### Phase 1: Foundation (Week 1)
```bash
# Tasks
- [ ] Create container structure (app.py, models.py, site_builder.py)
- [ ] Implement Hugo wrapper functions
- [ ] Create multi-stage Dockerfile
- [ ] Test Hugo builds locally with sample markdown
- [ ] Integrate PaperMod theme
```

### Phase 2: Pipeline Integration (Week 1-2)
```bash
# Tasks
- [ ] Implement markdown download from blob storage
- [ ] Implement site deployment to $web container
- [ ] Add error handling and validation
- [ ] Add rollback capability ($web-backup)
```

### Phase 3: Queue & KEDA (Week 2)
```bash
# Infrastructure
- [ ] Add site-publishing-requests queue (Terraform)
- [ ] Add site-publisher container app (Terraform)
- [ ] Configure KEDA scaling

# Code
- [ ] Implement queue message handler
- [ ] Enhance markdown-generator to signal completion
```

### Phase 4: Testing (Week 2-3)
```bash
# Tests
- [ ] Unit tests (Hugo wrapper, content sync, deployment)
- [ ] Integration tests (real blob storage)
- [ ] End-to-end pipeline test (collection → site live)
- [ ] Performance testing (build/deploy times)
```

### Phase 5: Production (Week 3)
```bash
# Deployment
- [ ] Deploy via CI/CD pipeline
- [ ] Monitor first automated build
- [ ] Verify site accessibility
- [ ] Set up alerting
```

## Cost Impact

### Additional Monthly Costs
- **Compute**: ~$0.02-0.05/month
  - 0-replica scaling (only runs when needed)
  - ~3 builds per day (8-hour collection cycles)
  - ~2-5 minutes per build
- **Storage**: $0 (using existing storage account)
- **Egress**: $0 (internal Azure traffic)

**Total**: ~$0.02-0.05/month (negligible)

## Quick Start Commands

### Local Hugo Testing
```bash
# Install Hugo
brew install hugo  # macOS
# or
wget https://github.com/gohugoio/hugo/releases/download/v0.138.0/hugo_extended_0.138.0_Linux-64bit.tar.gz

# Create test site
hugo new site mysite
cd mysite
git clone https://github.com/adityatelange/hugo-PaperMod themes/PaperMod
echo 'theme = "PaperMod"' >> config.toml

# Add content
hugo new posts/my-first-post.md

# Build
hugo

# Serve locally
hugo server
```

### Container Development
```bash
# Build container
cd /workspaces/ai-content-farm/containers/site-publisher
docker build -t site-publisher:test .

# Run locally
docker run -p 8080:8080 \
  -e AZURE_STORAGE_ACCOUNT_NAME=test \
  site-publisher:test
```

## Open Questions for Review

### 1. Theme Choice
**Question**: PaperMod vs Paper vs custom theme?  
**Recommendation**: PaperMod (feature-rich, well-maintained)

### 2. Search Functionality
**Question**: Add search now or later?  
**Recommendation**: Later (PaperMod has built-in JSON search when needed)

### 3. Preview Builds
**Question**: Support preview deployments ($web-preview)?  
**Recommendation**: Not initially (add if needed)

### 4. Content Archival
**Question**: Archive old content?  
**Recommendation**: Not initially (Hugo handles thousands of posts easily)

## Technical Specifications

### Container Resources
```yaml
CPU: 0.5 vCPU
Memory: 1 GiB
Min Replicas: 0
Max Replicas: 1
Expected Runtime: 2-5 minutes per build
```

### Environment Variables
```bash
AZURE_STORAGE_ACCOUNT_NAME=aicontentprodstkwakpx
QUEUE_NAME=site-publishing-requests
MARKDOWN_CONTAINER=markdown-content
OUTPUT_CONTAINER=$web
HUGO_THEME=PaperMod
HUGO_BASE_URL=https://aicontentprodstkwakpx.z33.web.core.windows.net
```

### Blob Containers Used
- **Input**: `markdown-content` (read markdown files)
- **Output**: `$web` (deploy built site)
- **Backup**: `$web-backup` (rollback capability)

## Success Metrics

### Functional
- ✅ Builds complete site from markdown
- ✅ Deploys to static website successfully
- ✅ Triggered automatically by queue message
- ✅ Zero broken links or missing assets

### Performance
- ✅ Build time < 5 minutes for ~50 articles
- ✅ Deploy time < 2 minutes
- ✅ Site accessible immediately

### Reliability
- ✅ Zero-replica scaling (no idle costs)
- ✅ Automatic retry on failures
- ✅ Rollback on deployment errors

## Next Steps

1. **Decision**: Approve Hugo vs Pelican recommendation
2. **Create Issue**: Break down implementation tasks
3. **Start Phase 1**: Set up container structure and Hugo integration
4. **Parallel Work**: Can start while markdown-generator continues running

## Questions?

- **"Why not stay with Python?"**: Performance and ecosystem benefits outweigh language consistency
- **"Will we maintain Go code?"**: No! Hugo is just a binary we call, no Go code to maintain
- **"What if we outgrow Hugo?"**: Extremely unlikely - Hugo powers huge sites (Kubernetes docs, etc.)
- **"Can we switch later?"**: Yes, but Hugo's performance makes switching unnecessary

---

**Full Design Document**: `docs/SITE_PUBLISHER_DESIGN.md`  
**Ready to Proceed**: Awaiting approval to start Phase 1 implementation
