# Site Generator Architecture Decision: One Container vs Two

**Date:** October 7, 2025  
**Status:** 🎯 **ARCHITECTURAL ANALYSIS**  
**Decision Required:** Should site-generator remain as one container or split into markdown-generator + site-builder?

---

## 📊 Current Situation

### Your Requirements
1. **Upstream triggers**: Content processor creates queue message for EACH new article
2. **Immediate conversion**: JSON → Markdown (one-to-one, fast)
3. **Batch site generation**: All markdown → Complete static site (many-to-one, slower)
4. **KEDA scaling**: Queue/Worker pattern for cost optimization
5. **Scale to zero**: Only pay when processing

### Current Implementation Issues
- ✅ KEDA configured correctly (`queueLength=1`, scales 0→2)
- ✅ Queue integration working
- ❌ **Conflicting workflows**: Single article processing vs full site regeneration
- ❌ **Inefficient**: Regenerating entire site for each article
- ❌ **Scaling confusion**: Container doesn't know if it should process one item or regenerate everything

---

## 🏗️ Architecture Options

### Option A: Keep One Container (Current - Needs Fixing)

**Single Container**: `site-generator`
- Handles both markdown conversion AND site generation
- Single queue: `site-generation-requests`

**Pros:**
- ✅ All code already in one place
- ✅ Shared libraries (theme system, blob client, etc.)
- ✅ Simpler deployment (one container to manage)
- ✅ Lower infrastructure overhead

**Cons:**
- ❌ Conflicting scaling patterns (individual items vs batch)
- ❌ Inefficient: Full site rebuild for each article
- ❌ Complex logic: "Should I process one or regenerate all?"
- ❌ Difficult to optimize: Can't tune KEDA for both patterns
- ❌ Wasted resources: Container wakes up for single article, does full rebuild

**Cost Impact:**
```
Each article triggers:
- Container startup: ~10s
- Markdown generation: ~2s (just this article)
- Full site rebuild: ~30s (regenerating 100 articles)
- Total: ~42s per article

10 articles/day × 42s = 420s/day = 0.12 hours/day
0.12 hours × $0.30/hour = $0.036/day = ~$1.08/month

BUT: Mostly wasted on regenerating unchanged articles
```

---

### Option B: Split Into Two Specialized Containers ⭐ **RECOMMENDED**

**Container 1**: `markdown-generator` (Fast, per-item)
- Input: Queue message with JSON article blob path
- Output: Single markdown file
- Scaling: `queueLength=1` (immediate, per-article)
- Duration: ~2-5 seconds per article

**Container 2**: `site-builder` (Slower, batch)
- Input: Queue message triggered after N markdown files OR timer
- Output: Complete HTML site
- Scaling: `queueLength=3` (batch multiple triggers) OR cron schedule
- Duration: ~30-60 seconds per full rebuild

**Flow:**
```
content-processor → [markdown-queue] → markdown-generator → markdown blob
                                             ↓
                                      (after N files OR timer)
                                             ↓
                                      [site-build-queue] → site-builder → HTML site
```

**Pros:**
- ✅ **Clean separation**: Each container has ONE job
- ✅ **Optimal scaling**: Different KEDA rules for each pattern
- ✅ **Efficient**: Markdown generation is instant, site builds are batched
- ✅ **Cost-effective**: Don't regenerate site for every article
- ✅ **Better observability**: Clear metrics per stage
- ✅ **Independent optimization**: Tune each container separately
- ✅ **Code reuse**: Both containers share libs/ folder

**Cons:**
- ⚠️ Additional queue required (`site-build-queue`)
- ⚠️ Two containers to deploy (but same codebase)
- ⚠️ Slightly more Terraform configuration

**Cost Impact:**
```
Markdown Generation (per article):
- Container startup: ~5s
- Markdown conversion: ~2s
- Total: ~7s per article

Site Building (every 5 articles or 1 hour):
- Container startup: ~10s
- Full site rebuild: ~30s
- Total: ~40s per batch

10 articles/day:
- Markdown: 10 × 7s = 70s = 0.019 hours = $0.006/day
- Site builds: 2 × 40s = 80s = 0.022 hours = $0.007/day
- Total: $0.013/day = ~$0.39/month

SAVINGS: $1.08 - $0.39 = $0.69/month (~64% reduction)
```

---

### Option C: One Container with Smart Routing

**Single Container** with two processing modes:
- Same queue, but payload specifies mode: `markdown_only` or `full_rebuild`
- Smart batching: Accumulate markdown requests, trigger rebuild after N items

**Pros:**
- ✅ Single codebase and deployment
- ✅ Can optimize within same container

**Cons:**
- ❌ Complex state management (counting articles)
- ❌ Single KEDA rule can't optimize for both patterns
- ❌ Still inefficient scaling (wakes for each article)
- ❌ Difficult to implement batching correctly
- ❌ Hard to debug and monitor

**Not Recommended** - Adds complexity without solving core scaling issues

---

## 🎯 Recommendation: Option B (Two Containers)

### Why Split Is Better

#### 1. **Perfect Fit for KEDA**
```yaml
# markdown-generator
queueLength: 1          # Immediate, per-item processing
min_replicas: 0
max_replicas: 5         # Can scale up for bursts

# site-builder  
queueLength: 3          # Wait for a few triggers (batch)
min_replicas: 0
max_replicas: 1         # Only need one for full rebuild
```

#### 2. **Clear Responsibility**
- **Markdown-generator**: "I convert ONE JSON article to markdown"
- **Site-builder**: "I rebuild the ENTIRE site from ALL markdown"

#### 3. **Better Cost Control**
- Don't waste compute regenerating entire site for each article
- Batch site builds every N articles or on timer
- Independent scaling means better utilization

#### 4. **Easier to Optimize**
- Markdown-generator: Optimize for speed (minimal startup, quick conversion)
- Site-builder: Optimize for completeness (thorough, can be slower)

#### 5. **Code Reuse Is Easy**
Both containers can share:
```
libs/
  ├── simplified_blob_client.py
  ├── queue_client.py
  ├── shared_models.py
  └── retry_utilities.py

containers/
  ├── markdown-generator/
  │   ├── Dockerfile (same base as site-generator)
  │   ├── main.py (focused on markdown)
  │   └── requirements.txt
  └── site-builder/
      ├── Dockerfile (same base as site-generator)
      ├── main.py (focused on HTML)
      └── requirements.txt
```

---

## 📝 Implementation Plan

### Phase 1: Split the Container (Week 1)

**Step 1: Create markdown-generator**
```bash
cd containers
cp -r site-generator markdown-generator
cd markdown-generator

# Strip out HTML generation code
rm html_page_generation.py
rm sitemap_generation.py
rm rss_generation.py
rm templates/ -rf

# Focus main.py on markdown only
# Remove /generate-site endpoint
# Keep /generate-markdown endpoint
```

**Step 2: Create site-builder**
```bash
cd containers
cp -r site-generator site-builder
cd site-builder

# Strip out markdown generation code (or keep for discovery mode)
# Focus main.py on HTML generation
# Remove /generate-markdown endpoint
# Keep /generate-site endpoint
```

**Step 3: Update Infrastructure**
```terraform
# infra/container_app_markdown_generator.tf
resource "azurerm_container_app" "markdown_generator" {
  name = "${local.resource_prefix}-markdown-gen"
  
  template {
    min_replicas = 0
    max_replicas = 5  # Can scale for bursts
    
    custom_scale_rule {
      name = "markdown-queue-scaler"
      custom_rule_type = "azure-queue"
      metadata = {
        queueName   = "markdown-generation-requests"
        queueLength = "1"  # Immediate processing
      }
    }
  }
}

# infra/container_app_site_builder.tf
resource "azurerm_container_app" "site_builder" {
  name = "${local.resource_prefix}-site-builder"
  
  template {
    min_replicas = 0
    max_replicas = 1  # Only need one
    
    custom_scale_rule {
      name = "site-build-queue-scaler"
      custom_rule_type = "azure-queue"
      metadata = {
        queueName   = "site-build-requests"
        queueLength = "3"  # Batch a few triggers
      }
    }
    
    # Optional: Also add cron scaler for periodic rebuilds
    custom_scale_rule {
      name = "hourly-rebuild"
      custom_rule_type = "cron"
      metadata = {
        timezone = "America/Los_Angeles"
        start    = "0 * * * *"  # Every hour
        end      = "0 * * * *"
        desiredReplicas = "1"
      }
    }
  }
}
```

**Step 4: Update Queue Logic**
```python
# markdown-generator: After saving markdown
await queue_client.send_message(
    queue_name="site-build-requests",
    message={
        "service_name": "markdown-generator",
        "operation": "rebuild_site",
        "payload": {
            "trigger": "new_markdown_file",
            "markdown_file": blob_name,
            "timestamp": datetime.now().isoformat()
        }
    }
)

# site-builder: Smart batching
# Only rebuild if:
# - 3+ messages in queue OR
# - 1 hour since last build OR
# - Forced rebuild flag
```

### Phase 2: Add Batching Intelligence (Week 2)

**Option 2a: Queue-Based Batching (Simpler)**
- Let messages accumulate in `site-build-requests` queue
- KEDA `queueLength=3` means container waits for 3+ messages
- When it wakes, it processes all messages and rebuilds once
- **Downside**: Site might be stale for up to 3 articles

**Option 2b: Cron + Queue Hybrid (Better)**
- Cron trigger: Rebuild site every hour regardless
- Queue trigger: If 5+ messages, rebuild immediately
- Best of both: Fresh site AND responsive to bursts
- **Recommended approach**

```terraform
# Two scaling rules = hybrid trigger
custom_scale_rule {
  name = "urgent-rebuild"  # For bursts
  custom_rule_type = "azure-queue"
  metadata = {
    queueLength = "5"  # Only if many articles queued
  }
}

custom_scale_rule {
  name = "hourly-rebuild"  # For freshness
  custom_rule_type = "cron"
  metadata = {
    start = "0 * * * *"
    desiredReplicas = "1"
  }
}
```

---

## 🔍 Comparison Matrix

| Aspect | One Container | Two Containers | Smart Routing |
|--------|--------------|----------------|---------------|
| **Code Complexity** | Medium | Low (focused) | High |
| **Scaling Efficiency** | Poor | Excellent | Medium |
| **Cost per Month** | $1.08 | $0.39 ⭐ | $0.75 |
| **Processing Latency** | High (40s) | Low (7s) ⭐ | Medium (20s) |
| **Observability** | Unclear | Clear ⭐ | Complex |
| **Maintenance** | Medium | Easy ⭐ | Difficult |
| **Infrastructure** | 1 container | 2 containers | 1 container |
| **KEDA Optimization** | Poor | Excellent ⭐ | Limited |

---

## 💡 Final Recommendation

**Split into two containers** (`markdown-generator` + `site-builder`)

### Why This Is The Right Choice

1. **Aligns with your requirements**: Per-article markdown + batched site builds
2. **Cost-effective**: 64% cost reduction ($1.08 → $0.39/month)
3. **Better user experience**: Articles appear in markdown immediately, site updates within an hour
4. **KEDA-friendly**: Each container has optimal scaling configuration
5. **Future-proof**: Easy to add more stages (e.g., separate RSS generator)
6. **Code reuse**: 80% of code stays shared in libs/
7. **Proven pattern**: This is the standard microservices approach

### Migration Path

**Immediate**: Keep existing site-generator working (fallback)
**Week 1**: Build and deploy markdown-generator (parallel to existing)
**Week 2**: Build and deploy site-builder (parallel to existing)
**Week 3**: Switch queue routing to new containers
**Week 4**: Remove old site-generator once validated

**Risk**: Low - Can run both systems in parallel during migration

---

## 📚 Related Documents

- [KEDA Scaling Strategy](./SITE_REGENERATION_TRIGGER.md)
- [Cost Optimization](./infrastructure/cost-optimization.md)
- [Container Architecture](./CONTENT_PROCESSOR_ARCHITECTURE.md)
- [Queue Patterns](./QUEUE_PROPERTIES_IMPLEMENTATION_SUMMARY.md)

---

**Next Steps:**
1. ✅ Review this analysis
2. ⬜ Decide on approach (recommend: Option B)
3. ⬜ Create GitHub issues for implementation
4. ⬜ Begin Phase 1: Container split
