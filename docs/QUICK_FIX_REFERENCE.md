# Quick Reference: Markdown Generator Rebuild Fix

## The Problem
Markdown-generator was sending "rebuild signals" to site-publisher even when **no new markdown files were created**. This happened because the container counted **messages processed** instead of **files generated**.

**Impact**: 
- ~60 unnecessary Hugo builds per hour
- ~48 false positive builds per hour (80% waste)
- ~$18/month in wasted compute costs
- Prevents proper container scale-down

## The Solution
Track **file creation** not **message processing**:
1. Detect duplicates by comparing file hashes (SHA256)
2. Only count files where `files_created = True`
3. Only signal site-publisher when files were actually created
4. Site-publisher validates file count before building

## Files Changed

### Container: markdown-generator

#### 1. `models.py`
```python
# Added to MarkdownGenerationResult:
files_created: bool  # Was this a NEW file?
file_created_timestamp: Optional[str]  # When was it created?
file_hash: Optional[str]  # SHA256 hash for dedup detection
```

#### 2. `markdown_processor.py`
```python
# In process_article():
- Added: import hashlib
- Added: SHA256 hash calculation of markdown content
- Added: Check if existing file has same hash
- Changed: Return files_created flag (True/False)
- Changed: Only write if file is new or content differs
```

**Key Logic**:
```python
new_content_hash = hashlib.sha256(markdown_content.encode()).hexdigest()
if existing_hash == new_content_hash and not overwrite:
    files_created = False  # Duplicate - skip
else:
    files_created = True   # New/different - create
```

#### 3. `queue_processor.py`
```python
# Message handler now:
- Returns files_created count (0 or 1)
- Increments app_state["total_files_generated"] on success
- Returns 0 for failed/invalid messages

# startup_queue_processor now:
- Takes app_state parameter
- Tracks files_generated_this_batch (not messages)
- Only signals if files_generated_this_batch > 0
- Skips signals with clear logging when no files
```

**Old Logic** ❌:
```python
if total_processed_since_signal > 0:  # Count of MESSAGES
    await signal_site_publisher(total_processed_since_signal)
```

**New Logic** ✅:
```python
if files_generated_this_batch > 0:  # Count of NEW FILES
    await signal_site_publisher(files_generated_this_batch)
```

#### 4. `main.py`
```python
# Enhanced app_state:
app_state["total_files_generated"] = 0  # Track new files

# Updated startup_queue_processor call:
asyncio.create_task(
    startup_queue_processor(
        ...,
        app_state=app_state,  # NEW: pass state
    )
)
```

### Container: site-publisher

#### 5. `app.py`
```python
# Message handler now:
- Extracts operation type
- Checks content_summary["files_created"]
- Returns "skipped" if files_created == 0
- Only builds if files_created > 0
- Clear logging of skip reasons
```

**New Validation**:
```python
markdown_count = content_summary.get("files_created", 0)
if markdown_count == 0:
    logger.info("Skipping build: 0 markdown files")
    return {"status": "skipped"}
```

## Testing Checklist

- [ ] Local unit tests pass
- [ ] Docker builds successfully
- [ ] Staging deployment works
- [ ] Markdown duplicate detection works
- [ ] Site-publisher builds when files_created > 0
- [ ] Site-publisher skips when files_created = 0
- [ ] Logs show correct file counts
- [ ] No builds with 0 files uploaded

## Deployment

```bash
# Build and push containers
docker build -t markdown-generator:latest containers/markdown-generator/
docker build -t site-publisher:latest containers/site-publisher/

# Deploy via CI/CD (normal flow)
git checkout -b fix/markdown-generator-rebuilds
git add -A
git commit -m "Fix: Track markdown file creation, not message processing

- Add files_created flag to MarkdownGenerationResult
- Detect duplicates using SHA256 hash comparison
- Only signal site-publisher when new files created
- Validate files_created > 0 before building
- Fixes ~80% false positive rebuild signals
- Saves ~$15/month in unnecessary builds"
git push origin fix/markdown-generator-rebuilds
# Create PR, merge to main
```

## Metrics to Monitor

```
Before:
- Builds/hour: ~60
- False positives: ~80%
- Build cost: ~$18/month

After (Target):
- Builds/hour: 2-4
- False positives: 0%
- Build cost: ~$2-3/month
```

## Rollback

If issues arise:
```bash
git revert <commit-hash>
git push origin main
# CI/CD will automatically redeploy
```

## Questions?

See detailed docs:
- `/docs/MARKDOWN_GENERATOR_REBUILD_INVESTIGATION.md` - Root cause analysis
- `/docs/MARKDOWN_GENERATOR_REBUILD_IMPLEMENTATION_COMPLETE.md` - Full implementation details
- `/docs/PIPELINE_OPTIMIZATION_PLAN.md` - Context and roadmap
