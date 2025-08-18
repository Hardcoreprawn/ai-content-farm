# Container Migration Guide

This document outlines the steps to migrate existing AI Content Farm containers to the new standards.

## Migration Overview

We need to standardize the following containers:
- `content-collector`
- `content-processor` 
- `content-enricher`
- `content-ranker`
- `markdown-generator` (✓ mostly compliant)
- `ssg` (needs major refactoring)
- `markdown-converter` (needs major refactoring)

## Migration Priority

1. **High Priority**: SSG (critical for deliverable website)
2. **High Priority**: Content Collector (pipeline entry point)
3. **Medium Priority**: Content Processor (data transformation)
4. **Medium Priority**: Content Enricher (value addition)
5. **Low Priority**: Content Ranker (mostly working)
6. **Low Priority**: Markdown Generator (already compliant)

## SSG Container Migration

### Current Issues
- Volume mounting conflicts
- Filesystem-based operation
- Missing blob storage integration
- Non-standard API structure

### Migration Steps

1. **Refactor to blob storage**:
   ```python
   # OLD: Reading from filesystem
   with open('/app/data/processed/articles.json', 'r') as f:
       content = json.load(f)
   
   # NEW: Reading from blob storage
   content = await blob_client.download_json(
       BlobContainers.PROCESSED_CONTENT,
       blob_name
   )
   ```

2. **Implement standard endpoints**:
   ```python
   @app.get("/generate")
   async def generate_site(background_tasks: BackgroundTasks):
       """Generate static site from processed content."""
       
   @app.get("/preview/{site_id}")
   async def preview_site(site_id: str):
       """Preview generated site."""
   ```

3. **Add blob-based site storage**:
   ```python
   # Deploy site to blob storage for hosting
   await blob_client.upload_html_site(
       BlobContainers.PUBLISHED_SITES,
       site_files,
       site_id
   )
   ```

### Expected Outcome
- SSG generates sites from blob storage
- Sites are deployed to blob containers
- Preview URLs work reliably
- Standard health/status endpoints

## Content Collector Migration

### Current State
- Working but needs standardization
- Manual execution only
- Filesystem output

### Migration Steps

1. **Standardize API structure**:
   ```python
   @app.post("/collect")
   async def collect_content(
       request: CollectionRequest,
       background_tasks: BackgroundTasks
   ) -> StandardResponse:
   ```

2. **Implement blob output**:
   ```python
   # Save collected content to blob storage
   blob_name = get_timestamped_blob_name("reddit", "collected")
   await blob_client.upload_json(
       BlobContainers.COLLECTED_CONTENT,
       blob_name,
       collected_data
   )
   ```

3. **Add event-driven triggers**:
   ```python
   # Notify next stage
   await notify_next_stage("content-processor", blob_name)
   ```

## Content Processor Migration

### Current State
- Basic functionality exists
- Needs event-driven integration

### Migration Steps

1. **Watch for collected content**:
   ```python
   async def _find_unprocessed_blobs(self) -> List[Dict[str, Any]]:
       """Find new collected content to process."""
       return await self.blob_client.list_blobs_by_prefix(
           BlobContainers.COLLECTED_CONTENT,
           prefix="reddit_"
       )
   ```

2. **Standardize processing output**:
   ```python
   # Process and save to processed content container
   processed_data = await self.process_content(raw_content)
   blob_name = get_timestamped_blob_name("processed", "content")
   await blob_client.upload_json(
       BlobContainers.PROCESSED_CONTENT,
       blob_name,
       processed_data
   )
   ```

## Content Enricher Migration

### Migration Steps

1. **Implement AI enrichment**:
   ```python
   async def enrich_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
       """Enrich content with AI analysis."""
       # Add sentiment analysis, categorization, etc.
       return enriched_content
   ```

2. **Save enriched results**:
   ```python
   blob_name = get_timestamped_blob_name("enriched", "content")
   await blob_client.upload_json(
       BlobContainers.ENRICHED_CONTENT,
       blob_name,
       enriched_data
   )
   ```

## Markdown Converter Migration

### Current Issues
- File watching implementation
- Non-standard structure

### Migration Steps

1. **Refactor to blob watching**:
   ```python
   async def _watch_for_new_content(self):
       """Watch for new markdown files in blob storage."""
       while self.is_running:
           # Check for new markdown files
           new_blobs = await self._find_new_markdown()
           
           for blob_info in new_blobs:
               await self._trigger_ssg(blob_info)
   ```

2. **Implement standard service communication**:
   ```python
   async def _trigger_ssg(self, blob_info: Dict[str, Any]):
       """Trigger SSG to generate site."""
       async with httpx.AsyncClient() as client:
           response = await client.post(
               "http://ssg:8000/generate",
               json={"source_blob": blob_info["name"]}
           )
   ```

## Migration Implementation Plan

### Phase 1: Critical Containers (Week 1)
1. Migrate SSG to blob storage
2. Fix volume mounting issues
3. Implement preview functionality
4. Test end-to-end site generation

### Phase 2: Pipeline Integration (Week 2)
1. Migrate Content Collector
2. Implement event-driven triggers
3. Test collector → processor flow
4. Validate blob storage operations

### Phase 3: Processing Chain (Week 3)
1. Migrate Content Processor
2. Migrate Content Enricher
3. Test processor → enricher → ranker flow
4. Implement monitoring and logging

### Phase 4: Site Generation (Week 4)
1. Migrate Markdown Converter
2. Test markdown → SSG flow
3. Implement automated publishing
4. Performance testing and optimization

## Testing Migration

### Before Migration
```bash
# Test current functionality
./test-pipeline.sh

# Document current behavior
./scripts/audit-containers.sh
```

### During Migration
```bash
# Test each container individually
pytest containers/{container-name}/tests/

# Test container integration
pytest tests/test_migration_integration.py

# Validate blob storage operations
pytest tests/test_blob_storage_migration.py
```

### After Migration
```bash
# Full pipeline test
pytest tests/test_complete_pipeline.py

# Performance benchmarks
./scripts/benchmark-pipeline.sh

# Deployment validation
./scripts/validate-deployment.sh
```

## Migration Checklist

### For Each Container

- [ ] **Structure**: Follows standard directory structure
- [ ] **APIs**: Implements required endpoints (`/`, `/health`, `/status`)
- [ ] **Storage**: Uses blob storage exclusively (no filesystem dependencies)
- [ ] **Events**: Implements event-driven processing
- [ ] **Logging**: Comprehensive logging with proper levels
- [ ] **Errors**: Proper error handling and reporting
- [ ] **Tests**: Unit and integration tests passing
- [ ] **Config**: Environment-based configuration
- [ ] **Health**: Health checks validate dependencies
- [ ] **Docs**: Updated documentation and API specs

### Pipeline Integration

- [ ] **Flow**: Content flows through blob containers correctly
- [ ] **Triggers**: Services trigger each other properly
- [ ] **Monitoring**: All services report health status
- [ ] **Scaling**: Services can be scaled independently
- [ ] **Deployment**: Works with both Azurite and Azure Storage
- [ ] **Performance**: Meets latency and throughput requirements

## Rollback Plan

If migration fails:

1. **Immediate**: Revert to previous working containers
2. **Investigate**: Analyze logs and error reports
3. **Fix**: Address specific issues found
4. **Test**: Validate fixes in isolation
5. **Retry**: Attempt migration with fixes

### Rollback Commands
```bash
# Revert to previous docker-compose
git checkout HEAD~1 docker-compose.yml

# Restart with old containers
docker-compose down
docker-compose up -d

# Verify functionality
./test-pipeline.sh
```

## Success Criteria

Migration is successful when:

1. **Functional**: All containers start and respond to health checks
2. **Integrated**: Complete pipeline processes content end-to-end
3. **Observable**: Comprehensive logging and monitoring
4. **Performant**: Meets or exceeds current performance
5. **Maintainable**: Code follows standards and is well-documented
6. **Deployable**: Works in all environments (local, staging, production)

## Post-Migration Tasks

1. **Documentation**: Update all documentation to reflect new architecture
2. **Training**: Create developer onboarding materials
3. **Monitoring**: Set up production monitoring and alerts
4. **Optimization**: Identify and implement performance improvements
5. **Security**: Conduct security review of new architecture

This migration ensures the AI Content Farm becomes a robust, scalable, and maintainable system following industry best practices.
