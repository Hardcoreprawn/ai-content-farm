# Content Pipeline Blob Flow Analysis

**Date**: August 12, 2025

## Current Blob Structure

### Stage 1: Topic Collection
- **Function**: SummaryWomble (HTTP triggered by GetHotTopics timer)
- **Output Container**: `hot-topics`
- **File Pattern**: `{timestamp}_{source}_{subreddit}.json`
- **Example**: `20250812_143000_reddit_technology.json`

### Stage 2: Topic Ranking  
- **Function**: ContentRanker (Blob triggered)
- **Input**: `hot-topics/{name}`
- **Output Container**: `content-pipeline`  
- **Output Path**: `ranked-topics/ranked_{DateTime}.json`
- **Example**: `content-pipeline/ranked-topics/ranked_2025-08-12T14:30:00Z.json`

### Stage 3: Content Enrichment
- **Function**: ContentEnricher (Blob triggered)
- **Input**: `content-pipeline/ranked-topics/{name}`
- **Output Container**: `content-pipeline`
- **Output Path**: `enriched-topics/enriched_{datetime}.json`
- **Example**: `content-pipeline/enriched-topics/enriched_2025-08-12_14-30-00.json`

## Recommended Improvements for Visibility

### 1. Separate Containers by Stage
```
hot-topics/           # Raw Reddit data (Stage 1)
ranked-topics/        # Ranked content (Stage 2)  
enriched-topics/      # Research-enriched content (Stage 3)
published-articles/   # Final articles (Stage 4 - Future)
```

### 2. Consistent Naming Convention
```
{YYYY-MM-DD}_{HH-mm-ss}_{stage}_{source}.json

Examples:
hot-topics/2025-08-12_14-30-00_collected_reddit-technology.json
ranked-topics/2025-08-12_14-31-15_ranked_batch-001.json
enriched-topics/2025-08-12_14-32-30_enriched_batch-001.json
```

### 3. Pipeline Status Tracking
- Add status container: `pipeline-status/`
- Track progress: `{timestamp}_pipeline_status.json`

## Benefits of Current Structure
✅ **Automatic flow**: Blob triggers create seamless pipeline
✅ **Clear separation**: Different paths for each stage  
✅ **Timestamp tracking**: Easy to correlate inputs/outputs
✅ **Scalable**: Each stage can process independently

## Immediate Monitoring Commands
```bash
# Watch raw topic collection
az storage blob list --container-name hot-topics --account-name <storage>

# Watch ranked topics
az storage blob list --container-name content-pipeline --prefix ranked-topics/

# Watch enriched topics  
az storage blob list --container-name content-pipeline --prefix enriched-topics/
```
