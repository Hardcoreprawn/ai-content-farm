# Site Publisher Container - Design Document

**Status**: Design Phase  
**Date**: October 10, 2025  
**Purpose**: Design for new container that converts markdown articles to static website

## Executive Summary

The site-publisher container will be the final stage of our content pipeline, responsible for taking generated markdown articles and building a complete static website. This design explores two SSG options (Hugo vs Pelican), recommends an approach, and defines the architecture for safe, reliable site publishing.

## Current Pipeline Context

### Existing Architecture
```
KEDA Cron (8hrs) → content-collector → [Storage Queue] → content-processor → [Storage Queue] → markdown-generator → site-publisher → $web
                         ↓                                        ↓                              ↓
                    collected-content                     processed-content              markdown-content
                    (Raw JSON)                           (Enriched JSON)                (Markdown .md)
```

### What We Have Working
- ✅ **content-collector**: Gathers content from approved sources every 8 hours
- ✅ **content-processor**: Enhances content with AI, produces enriched JSON
- ✅ **markdown-generator**: Converts JSON to markdown using Jinja2 templates
- 🚧 **site-publisher**: NEW - Will build static site from markdown files

### Triggering Strategy
**Proposed**: Queue message when markdown-requests queue becomes empty

The markdown-generator processes messages from `markdown-generation-requests` queue. When the queue becomes empty (all markdown articles generated), it signals completion by sending a message to a new `site-publishing-requests` queue. This triggers the site-publisher to rebuild the entire site.

**Benefits**:
- ✅ Clean separation of concerns
- ✅ Batch-oriented (rebuild whole site once per collection cycle)
- ✅ KEDA-compatible scaling (0 replicas when idle)
- ✅ Resilient to failures (message retry logic)

## SSG Technology Comparison

### Option 1: Hugo (Go-based) - RECOMMENDED ⭐

**Pros**:
- 🚀 **Performance**: Extremely fast builds (1000s of pages in seconds)
- 📦 **Single Binary**: No runtime dependencies, easy to containerize
- 🎨 **Rich Ecosystem**: 300+ themes, extensive plugin system
- 📱 **Modern Features**: Built-in image processing, multilingual support, RSS
- 🌍 **Industry Standard**: Most popular SSG globally (65k+ GitHub stars)
- 🔧 **Simple Setup**: Configuration via TOML/YAML, clear structure
- 🏗️ **Content Organization**: Built-in taxonomies, sections, content types
- 💰 **Resource Efficient**: Minimal memory footprint, fast startup

**Cons**:
- 📚 **Learning Curve**: Go templates (but we'd learn it)
- 🐍 **Not Python**: Different from our stack (but very simple to use)
- 🛠️ **Customization**: Requires Go knowledge for complex plugins

**Docker Container Size**: ~50-80 MB (Hugo binary + Alpine base)

**Example Build Command**:
```bash
hugo --minify --destination /output/public
```

### Option 2: Pelican (Python-based)

**Pros**:
- 🐍 **Python Native**: Aligns with our existing stack
- 🔧 **Extensible**: Plugin system in Python
- 📖 **Good Documentation**: Clear Python-centric docs
- 🎨 **Theme Support**: Decent selection of themes

**Cons**:
- 🐌 **Slower**: 10-100x slower than Hugo for large sites
- 📦 **Dependencies**: Requires Python runtime + pip packages
- 🏗️ **Less Active**: Smaller community, fewer updates
- ⚙️ **Complex Setup**: More configuration needed
- 💾 **Resource Heavy**: Larger container, more memory

**Docker Container Size**: ~200-400 MB (Python + dependencies)

**Example Build Command**:
```bash
pelican content -o output -s pelicanconf.py
```

### Recommendation: Hugo ✅

**Rationale**:
1. **Performance**: Orders of magnitude faster, critical as site grows
2. **Simplicity**: Single binary, no dependency management
3. **Industry Standard**: Better long-term support and ecosystem
4. **Container Efficiency**: Smaller images, faster startup, lower costs
5. **Learning Investment**: Worth learning Go templates for the benefits

**Trade-off**: We're comfortable with Python, but Hugo's performance and simplicity outweigh language preference. Hugo is designed specifically for static site generation, while Pelican is a Python project that happens to generate sites.

## Architecture Design

### Container Structure

```
site-publisher/
├── Dockerfile                 # Multi-stage build
├── app.py                     # FastAPI application
├── config.py                  # Configuration management
├── models.py                  # Pydantic models
├── site_builder.py            # Core build orchestration
├── hugo_wrapper.py            # Hugo integration
├── content_sync.py            # Markdown download from blob
├── requirements.txt           # Python dependencies
├── hugo-config/              # Hugo configuration
│   ├── config.toml           # Main Hugo config
│   ├── archetypes/           # Content templates
│   └── layouts/              # Custom layouts (if needed)
├── theme/                    # Chosen Hugo theme
└── tests/
    ├── test_site_builder.py
    ├── test_content_sync.py
    └── conftest.py
```

### Key Components

#### 1. Queue Message Handler
```python
async def handle_publish_request(queue_message: QueueMessageModel) -> Dict[str, Any]:
    """
    Process site publishing request from queue.
    
    Triggered when markdown-generation-requests queue becomes empty.
    """
    # 1. Download all markdown from markdown-content blob container
    # 2. Organize into Hugo content structure
    # 3. Run Hugo build
    # 4. Upload generated HTML/CSS/JS to $web container
    # 5. Return success/failure status
```

#### 2. Content Synchronization
```python
async def sync_markdown_from_blob(
    blob_client: BlobServiceClient,
    container: str = "markdown-content",
    output_dir: Path = Path("/tmp/content")
) -> SyncResult:
    """
    Download all markdown files from blob storage.
    
    Returns:
        SyncResult with file count, size, and any errors
    """
    # Download all .md files
    # Organize by category/date structure for Hugo
    # Preserve frontmatter metadata
```

#### 3. Hugo Build Wrapper
```python
async def build_site_with_hugo(
    content_dir: Path,
    output_dir: Path,
    config_file: Path
) -> BuildResult:
    """
    Execute Hugo build process.
    
    Returns:
        BuildResult with build status, output location, errors
    """
    # Run: hugo --source content_dir --destination output_dir --config config_file
    # Capture stdout/stderr
    # Validate output exists
    # Return structured result
```

#### 4. Site Deployment
```python
async def deploy_to_web_container(
    build_dir: Path,
    blob_client: BlobServiceClient,
    container: str = "$web"
) -> DeploymentResult:
    """
    Upload built site to Azure Storage static website.
    
    Returns:
        DeploymentResult with uploaded file count, URLs, errors
    """
    # Upload all HTML/CSS/JS/assets
    # Set correct content types
    # Validate deployment
```

### Dockerfile Strategy (Multi-stage)

```dockerfile
# Stage 1: Get Hugo binary
FROM golang:1.23-alpine AS hugo-builder
RUN apk add --no-cache git
ARG HUGO_VERSION=0.138.0
RUN go install github.com/gohugoio/hugo@v${HUGO_VERSION}

# Stage 2: Python runtime (using 3.13 for 4 years security support)
FROM python:3.13-slim

# Install Hugo from builder stage
COPY --from=hugo-builder /go/bin/hugo /usr/local/bin/hugo

# Security: Non-root user
RUN useradd --create-home --shell /bin/bash app

# Install Python dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY --chown=app:app . .

USER app

# Run FastAPI application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
```

**Container Size Estimate**: ~300-400 MB (Python + Hugo binary + dependencies)

### Configuration Management

#### Environment Variables
```bash
# Azure Storage
AZURE_STORAGE_ACCOUNT_NAME=aicontentprodstkwakpx
AZURE_SUBSCRIPTION_ID=<subscription-id>

# Queue Configuration
QUEUE_NAME=site-publishing-requests
QUEUE_POLLING_INTERVAL_SECONDS=30

# Blob Containers
MARKDOWN_CONTAINER=markdown-content
OUTPUT_CONTAINER=$web

# Hugo Configuration
HUGO_THEME=paper  # Example: clean, minimal theme
HUGO_BASE_URL=https://aicontentprodstkwakpx.z33.web.core.windows.net
SITE_TITLE=AI Content Farm
SITE_DESCRIPTION=Curated content from the internet
```

#### Hugo Configuration (config.toml)
```toml
baseURL = "https://aicontentprodstkwakpx.z33.web.core.windows.net"
languageCode = "en-us"
title = "AI Content Farm"
theme = "paper"

[params]
  description = "Curated content about technology, science, and more"
  author = "AI Content Farm"

[taxonomies]
  tag = "tags"
  category = "categories"
  source = "sources"

[markup]
  [markup.goldmark]
    [markup.goldmark.renderer]
      unsafe = true  # Allow HTML in markdown

[outputs]
  home = ["HTML", "RSS", "JSON"]
  section = ["HTML", "RSS"]
```

### Hugo Theme Recommendation

**Suggested Theme**: [Hugo PaperMod](https://github.com/adityatelange/hugo-PaperMod)

**Why**:
- ✅ Clean, minimal design (matches project vision)
- ✅ Fast, responsive, accessibility-focused
- ✅ SEO optimized out of box
- ✅ Search functionality built-in
- ✅ Archive/tags/categories support
- ✅ Dark mode support
- ✅ Active maintenance (3k+ stars)

**Alternative**: Hugo Paper (even more minimal, 2k+ stars)

### Markdown Frontmatter Integration

Our markdown-generator creates files with frontmatter that Hugo understands:

```markdown
---
title: "Understanding AI Safety Research"
date: 2025-10-10T14:30:00Z
author: "BBC Technology"
url: "https://bbc.com/article"
source: "rss"
tags: ["AI", "Safety", "Research"]
category: "Technology"
draft: false
---

# Article content here...
```

Hugo automatically parses this frontmatter for:
- Page metadata
- Taxonomy organization (tags, categories)
- URL routing
- RSS feed generation
- Search indexing

## Queue-Based Triggering Design

### Message Flow

```
markdown-generator (last message processed)
    ↓
Check queue depth
    ↓
If queue empty → Send completion message
    ↓
site-publishing-requests queue
    ↓
KEDA scales site-publisher (0 → 1)
    ↓
site-publisher processes batch
    ↓
Rebuild entire site
    ↓
Scale back to 0
```

### Queue Message Structure

**Outgoing from markdown-generator**:
```json
{
  "message_id": "uuid",
  "correlation_id": "uuid",
  "timestamp": "2025-10-10T14:30:00Z",
  "service_name": "markdown-generator",
  "operation": "site_publish_request",
  "payload": {
    "batch_id": "collection-20251010-143000",
    "markdown_count": 42,
    "collection_start": "2025-10-10T08:00:00Z",
    "collection_end": "2025-10-10T14:30:00Z"
  },
  "metadata": {
    "trigger": "queue_empty",
    "queue_name": "markdown-generation-requests"
  }
}
```

### Markdown-Generator Enhancement

Add to markdown-generator's queue processing logic:

```python
async def check_and_signal_completion(queue_client, logger):
    """
    Check if markdown queue is empty and signal site-publisher.
    
    Called after processing each message.
    """
    properties = await queue_client.get_queue_properties()
    message_count = properties.approximate_message_count
    
    if message_count == 0:
        logger.info("Markdown queue empty - signaling site-publisher")
        
        # Send completion message to site-publishing queue
        publish_message = QueueMessageModel(
            service_name="markdown-generator",
            operation="site_publish_request",
            payload={
                "batch_id": f"collection-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                "markdown_count": app_state["total_processed"],
                "trigger": "queue_empty"
            }
        )
        
        await send_queue_message(
            queue_name="site-publishing-requests",
            message=publish_message
        )
```

## Infrastructure Requirements

### Terraform Changes

#### 1. New Storage Queue
```terraform
resource "azurerm_storage_queue" "site_publishing_requests" {
  name               = "site-publishing-requests"
  storage_account_id = azurerm_storage_account.main.id

  metadata = {
    purpose     = "site-publisher-keda-scaling"
    description = "Triggers site-publisher to rebuild entire site"
  }
}
```

#### 2. Container App Definition
```terraform
resource "azurerm_container_app" "site_publisher" {
  name                         = "${local.resource_prefix}-site-publisher"
  resource_group_name          = azurerm_resource_group.main.name
  container_app_environment_id = azurerm_container_app_environment.main.id
  revision_mode                = "Single"

  identity {
    type = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.containers.id]
  }

  template {
    min_replicas = 0
    max_replicas = 1

    container {
      name   = "site-publisher"
      image  = local.container_images["site-publisher"]
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "AZURE_STORAGE_ACCOUNT_NAME"
        value = azurerm_storage_account.main.name
      }
      env {
        name  = "QUEUE_NAME"
        value = azurerm_storage_queue.site_publishing_requests.name
      }
      env {
        name  = "HUGO_BASE_URL"
        value = "https://${azurerm_storage_account.main.name}.z33.web.core.windows.net"
      }
    }

    # KEDA Queue Scaler
    scale_rule {
      name = "site-publish-queue-scaler"
      
      azure_queue_scale_rule {
        queueName   = azurerm_storage_queue.site_publishing_requests.name
        accountName = azurerm_storage_account.main.name
        queueLength = 1  # Process immediately when message arrives
        
        authentication {
          secret_ref = "queue-connection-string"
          trigger_parameter = "connection"
        }
      }
    }
  }
}
```

### RBAC Permissions

Site-publisher needs:
- ✅ **Storage Blob Data Contributor**: Read markdown-content, write to $web
- ✅ **Storage Queue Data Contributor**: Process site-publishing-requests queue

Already configured via shared user-assigned identity.

## API Design

### REST Endpoints

```python
# Health & Monitoring
GET  /health                    # Container health check
GET  /status                    # Current build status
GET  /metrics                   # Build metrics

# Manual Triggering (for testing)
POST /publish                   # Manually trigger site rebuild
POST /preview                   # Build preview without deployment

# Information
GET  /info                      # Site configuration info
GET  /theme                     # Current theme details
```

### Response Models

```python
class SitePublishRequest(BaseModel):
    """Request to publish site."""
    force_rebuild: bool = Field(default=False, description="Force rebuild even if no changes")
    preview_mode: bool = Field(default=False, description="Build but don't deploy")

class SitePublishResult(BaseModel):
    """Result of site publishing operation."""
    status: ProcessingStatus
    build_time_seconds: float
    markdown_files_processed: int
    html_pages_generated: int
    assets_deployed: int
    site_url: str
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
```

## Safety & Reliability Considerations

### 1. Full Site Rebuild Strategy ✅

**Approach**: Always rebuild the entire site from scratch

**Benefits**:
- ✅ **Consistency**: Guarantees site matches current markdown state
- ✅ **Simplicity**: No complex diff logic, no partial update bugs
- ✅ **Clean State**: No orphaned files or stale content
- ✅ **Reliable**: Predictable behavior, easy to debug

**Performance**: Hugo builds 1000+ pages in seconds, so full rebuild is fast enough

### 2. Error Handling

```python
class BuildError(Exception):
    """Raised when Hugo build fails."""
    pass

class DeploymentError(Exception):
    """Raised when deployment to $web fails."""
    pass

# Always clean up temp directories
# Always log errors with context
# Always update metrics on failure
# Always retry transient failures (blob upload)
```

### 3. Rollback Strategy

**Approach**: Keep previous successful build in separate container

```python
# Before deploying new build
async def backup_current_site():
    """Copy current $web to $web-backup before deploying."""
    # Copy all blobs from $web to $web-backup
    pass

async def rollback_to_previous():
    """Restore $web from $web-backup if deployment fails."""
    # Copy all blobs from $web-backup to $web
    pass
```

### 4. Validation

```python
async def validate_build_output(build_dir: Path) -> ValidationResult:
    """Validate Hugo build output before deployment."""
    checks = []
    
    # Check index.html exists
    checks.append(check_file_exists(build_dir / "index.html"))
    
    # Check no broken internal links
    checks.append(await check_internal_links(build_dir))
    
    # Check required assets present
    checks.append(check_assets_present(build_dir))
    
    return ValidationResult(all(checks), checks)
```

### 5. Monitoring

```python
# Metrics to track
app_state = {
    "total_builds": 0,
    "successful_builds": 0,
    "failed_builds": 0,
    "last_build_time": None,
    "last_build_duration": None,
    "average_build_time": None,
    "markdown_files_tracked": 0,
    "html_pages_generated": 0
}
```

## Implementation Phases

### Phase 1: Hugo Integration (Week 1)
- [ ] Create site-publisher container structure
- [ ] Implement Hugo wrapper functions
- [ ] Test Hugo builds locally
- [ ] Create multi-stage Dockerfile
- [ ] Choose and integrate Hugo theme

### Phase 2: Content Pipeline (Week 1-2)
- [ ] Implement markdown download from blob
- [ ] Implement content organization for Hugo
- [ ] Implement site deployment to $web
- [ ] Add error handling and validation

### Phase 3: Queue Integration (Week 2)
- [ ] Add site-publishing-requests queue to Terraform
- [ ] Implement queue message handler in site-publisher
- [ ] Enhance markdown-generator with completion signaling
- [ ] Configure KEDA scaling for site-publisher

### Phase 4: Testing & Hardening (Week 2-3)
- [ ] Unit tests for all components
- [ ] Integration tests with real blob storage
- [ ] End-to-end pipeline test
- [ ] Performance testing (build time, deployment time)
- [ ] Error scenario testing

### Phase 5: Deployment & Monitoring (Week 3)
- [ ] Deploy to production via CI/CD
- [ ] Monitor first automated build
- [ ] Verify site accessibility
- [ ] Set up alerting for build failures
- [ ] Document operational procedures

## Cost Estimation

### Container Resources
- **CPU**: 0.5 vCPU (Hugo is CPU-efficient)
- **Memory**: 1 GiB (room for large sites)
- **Runtime**: ~2-5 minutes per build (download + build + upload)
- **Frequency**: ~3 times per day (8-hour collection cycles)

### Cost Breakdown
- **Compute**: ~$0.02/month (0-replica scaling, short runtimes)
- **Storage**: Included in existing storage account
- **Egress**: Minimal (internal Azure traffic)

**Total Additional Cost**: ~$0.02-0.05/month

## Open Questions & Decisions Needed

### 1. Hugo Theme Selection
**Options**:
- PaperMod (feature-rich, popular)
- Paper (minimal, clean)
- Terminal (developer-focused)
- Custom theme (most control, more work)

**Decision Needed**: Choose theme based on desired aesthetic

### 2. Preview Builds
**Question**: Should we support preview builds before deploying?

**Options**:
- A) Deploy preview to separate container ($web-preview)
- B) Only support production deployments
- C) Local preview only (manual testing)

**Recommendation**: Start with B (production only), add A later if needed

### 3. Incremental vs Full Rebuild
**Question**: Should we optimize for incremental builds?

**Decision**: Start with full rebuild (simpler, reliable), optimize later if needed

### 4. Content Archival
**Question**: Should old content be archived/removed after a period?

**Options**:
- A) Keep all content forever
- B) Archive content older than X days
- C) Manual archival process

**Recommendation**: Start with A, add B when site grows large

### 5. Search Functionality
**Question**: How should users search the site?

**Options**:
- A) Hugo's built-in search (JSON index)
- B) Third-party search (Algolia, etc.)
- C) No search initially

**Recommendation**: Start with C, add A when site has significant content

## Success Criteria

### Functional Requirements
- ✅ Successfully builds site from all markdown files
- ✅ Deploys to Azure Storage static website ($web)
- ✅ Triggered automatically when markdown generation completes
- ✅ Handles errors gracefully with rollback capability
- ✅ Provides clear status/metrics endpoints

### Performance Requirements
- ✅ Build completes in < 5 minutes for typical batch (~50 articles)
- ✅ Deployment completes in < 2 minutes
- ✅ Site accessible immediately after deployment
- ✅ No broken links or missing assets

### Reliability Requirements
- ✅ Zero-replica scaling (no idle costs)
- ✅ Automatic retry on transient failures
- ✅ Clear error reporting and logging
- ✅ Rollback on deployment failure

## Next Steps

1. **Review & Approve Design**: Get feedback on Hugo vs Pelican decision
2. **Create GitHub Issue**: Break down implementation into tasks
3. **Set Up Development Environment**: Install Hugo, test themes locally
4. **Create Container Skeleton**: Basic FastAPI app with Hugo integration
5. **Implement Core Functions**: Content sync, Hugo build, deployment
6. **Add Queue Integration**: Message handling, KEDA scaling
7. **Testing**: Comprehensive unit and integration tests
8. **Deploy**: Via CI/CD pipeline to production

## References

- [Hugo Documentation](https://gohugo.io/documentation/)
- [Hugo PaperMod Theme](https://github.com/adityatelange/hugo-PaperMod)
- [Azure Storage Static Website](https://learn.microsoft.com/en-us/azure/storage/blobs/storage-blob-static-website)
- [KEDA Azure Queue Scaler](https://keda.sh/docs/2.11/scalers/azure-storage-queue/)
- Project Architecture: `/workspaces/ai-content-farm/AGENTS.md`
- Current Pipeline Status: `/workspaces/ai-content-farm/README.md`

---

**Document Owner**: AI Agent  
**Last Updated**: October 10, 2025  
**Status**: Draft - Awaiting Review & Approval
