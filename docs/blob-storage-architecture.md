# Blob Storage Architecture Design

*Created: August 12, 2025*

## **Standardized Container Structure**

### **Core Principle: Clear Input/Output Flow**
Each processing stage has dedicated input and output containers, enabling:
- ✅ **Clear data lineage**: Easy to track content through pipeline
- ✅ **Scalable processing**: Multiple function instances can process different files
- ✅ **Error isolation**: Failed processing doesn't block other items
- ✅ **Restart capability**: Reprocess from any stage
- ✅ **Monitoring**: Clear visibility into pipeline bottlenecks

### **Container Naming Convention**
```
{stage-name}-{status}/
```
Where:
- `stage-name`: Descriptive process name (kebab-case)
- `status`: `queue` (input) or `complete` (output)

## **Container Structure**

### **1. Topic Collection Stage**
```
topic-collection-queue/     # Input for TopicCollectorWorker
├── reddit-technology.trigger     # Trigger files for processing
├── reddit-programming.trigger
└── reddit-machinelearning.trigger

topic-collection-complete/  # Output from TopicCollectorWorker
├── 20250812_140000_reddit_technology.json
├── 20250812_140000_reddit_programming.json
└── 20250812_140000_reddit_machinelearning.json
```

### **2. Content Ranking Stage**
```
content-ranking-queue/      # Input for ContentRankerWorker
├── 20250812_140000_reddit_technology.json    # Copied from topic-collection-complete
├── 20250812_140000_reddit_programming.json
└── 20250812_140000_reddit_machinelearning.json

content-ranking-complete/   # Output from ContentRankerWorker
├── ranked_20250812_140500_technology.json
├── ranked_20250812_140500_programming.json
└── ranked_20250812_140500_machinelearning.json
```

### **3. Content Enrichment Stage**
```
content-enrichment-queue/   # Input for ContentEnricherWorker
├── ranked_20250812_140500_technology.json    # Copied from content-ranking-complete
├── ranked_20250812_140500_programming.json
└── ranked_20250812_140500_machinelearning.json

content-enrichment-complete/ # Output from ContentEnricherWorker
├── enriched_20250812_141000_technology.json
├── enriched_20250812_141000_programming.json
└── enriched_20250812_141000_machinelearning.json
```

### **4. Content Publishing Stage**
```
content-publishing-queue/   # Input for ContentPublisherWorker
├── enriched_20250812_141000_technology.json  # Copied from content-enrichment-complete
├── enriched_20250812_141000_programming.json
└── enriched_20250812_141000_machinelearning.json

published-articles/         # Output from ContentPublisherWorker
├── ai-trends-2025-breakthrough-technology.md
├── python-performance-optimization-guide.md
└── machine-learning-industry-adoption.md
```

### **5. Job Processing & Status**
```
job-status/                 # Async job tracking
├── jobs/
│   ├── {job-id}/
│   │   ├── status.json
│   │   ├── progress.json
│   │   └── results.json
│   └── ...
└── processing-logs/        # Detailed processing logs
    ├── topic-collection/
    ├── content-ranking/
    ├── content-enrichment/
    └── content-publishing/
```

### **6. Error Handling & Dead Letter**
```
processing-errors/          # Failed processing items
├── topic-collection-errors/
├── content-ranking-errors/
├── content-enrichment-errors/
└── content-publishing-errors/

dead-letter-queue/          # Items that failed multiple times
├── failed_20250812_reddit_technology.json
└── retry_count_exceeded/
```

## **Worker Function Input/Output Contracts**

### **Standard Worker API Pattern**
```http
POST /api/{worker-name}/process
```

**Request Body**:
```json
{
  "input_blob": "content-ranking-queue/ranked_20250812_140500_technology.json",
  "output_blob": "content-enrichment-queue/enriched_20250812_141000_technology.json",
  "processing_options": {
    "batch_size": 1,
    "timeout_seconds": 300,
    "retry_count": 3
  }
}
```

**Response**:
```json
{
  "status": "success|processing|error",
  "message": "Processing completed successfully",
  "data": {
    "input_blob": "content-ranking-queue/ranked_20250812_140500_technology.json",
    "output_blob": "content-enrichment-queue/enriched_20250812_141000_technology.json",
    "items_processed": 15,
    "processing_time_ms": 2350
  },
  "metadata": {
    "timestamp": "2025-08-12T14:15:00Z",
    "function": "ContentEnricherWorker",
    "execution_time_ms": 2350,
    "version": "1.0.0"
  }
}
```

### **Batch Processing Pattern**
```http
POST /api/{worker-name}/process-batch
```

**Request Body**:
```json
{
  "input_container": "content-ranking-queue",
  "output_container": "content-enrichment-queue",
  "processing_options": {
    "max_files": 10,
    "parallel_processing": true
  }
}
```

## **Scheduler Function Behavior**

### **1. Container Monitoring Pattern**
Each scheduler monitors its designated input container:

```python
# Example: ContentRankerScheduler
@blob_trigger(path="topic-collection-complete/{name}", connection="AzureWebJobsStorage")
def content_ranker_scheduler(blob: func.InputStream):
    """
    Triggered when new content appears in topic-collection-complete/
    Copies file to content-ranking-queue/ and calls ContentRankerWorker
    """
    
    # 1. Copy blob to input queue
    source_blob = blob.name
    target_blob = f"content-ranking-queue/{source_blob}"
    copy_blob(source_blob, target_blob)
    
    # 2. Call worker with explicit paths
    worker_response = call_worker(
        worker_url="/api/ContentRankerWorker/process",
        input_blob=target_blob,
        output_blob=f"content-ranking-complete/ranked_{timestamp}_{topic}.json"
    )
    
    # 3. Log and monitor result
    log_processing_result(worker_response)
```

### **2. Error Handling & Retry Logic**
```python
def handle_processing_error(input_blob, error, retry_count=0):
    """Standard error handling for all schedulers"""
    
    if retry_count < MAX_RETRIES:
        # Retry with exponential backoff
        schedule_retry(input_blob, retry_count + 1)
    else:
        # Move to dead letter queue
        move_to_dead_letter(input_blob, error)
        alert_operations_team(input_blob, error)
```

## **Migration Plan from Current Structure**

### **Current State**
```
hot-topics/
├── 20250807_093142_reddit_technology.json
├── 20250807_093306_reddit_MachineLearning.json
├── jobs/{job-id}/status.json
└── ...
```

### **Migration Steps**
1. **Create new container structure** in staging storage account
2. **Migrate existing data** to appropriate new containers
3. **Update scheduler triggers** to monitor new containers
4. **Update worker functions** to use new input/output paths
5. **Test end-to-end pipeline** with new structure
6. **Deploy to production** after validation

### **Backward Compatibility**
- Keep `hot-topics` container during transition
- Gradually migrate processing to new structure
- Maintain monitoring on both old and new containers
- Clean up old structure after successful migration

## **Benefits of New Structure**

### **For Development**
- ✅ **Clear testing**: Easy to test individual stages
- ✅ **Debugging**: Obvious place to look for failed processing
- ✅ **Data lineage**: Complete audit trail of content transformation

### **For Operations**
- ✅ **Monitoring**: Clear metrics per processing stage
- ✅ **Scaling**: Independent scaling per stage based on queue depth
- ✅ **Error handling**: Isolated error recovery per stage

### **For Business**
- ✅ **Reliability**: Robust pipeline with automatic retry
- ✅ **Transparency**: Clear visibility into content processing status
- ✅ **Scalability**: Handle increased content volume efficiently

---
*Next: Implement ContentRankerWorker as template for standardized pattern*
