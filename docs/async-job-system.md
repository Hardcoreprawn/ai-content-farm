# Async Job System Implementation

*Implementation Date: August 11, 2025*

## Overview

The AI Content Farm now uses an asynchronous job processing system for content collection, replacing the previous synchronous approach that was prone to timeouts and provided limited visibility.

## Architecture

### Before: Synchronous Processing
```
Timer → HTTP Request → Wait 5 minutes → Response/Timeout
```
**Problems:**
- Long response times (up to 5 minutes)
- Timeout failures
- No visibility into progress
- Poor user experience

### After: Async Job Tickets
```
Timer → HTTP Request → Immediate Job Ticket → Background Processing
       ↓
Status Check API → Real-time Progress Updates
```

## Implementation Details

### Job Ticket System

When a request is made to SummaryWomble, it:

1. **Generates unique job ID** using UUID4
2. **Returns immediate response** (HTTP 202) with job ticket
3. **Starts background processing** in separate thread
4. **Updates job status** in blob storage throughout lifecycle

### Job Status Lifecycle

| Status | Description | Progress Tracking |
|--------|-------------|-------------------|
| `queued` | Job ticket issued, about to start | Initial state |
| `running` | Background thread processing | Step-by-step progress |
| `completed` | All processing finished successfully | Final results |
| `failed` | Error occurred during processing | Error details |

### Storage Pattern

Job status is stored in blob storage using this pattern:
```
hot-topics/
├── jobs/
│   └── {job-id}/
│       └── status.json
└── {timestamp}_{source}_{subreddit}.json
```

### API Usage

#### Starting a Job
```bash
curl -X POST https://func.azurewebsites.net/api/summarywomble \
  -H "x-functions-key: KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "reddit",
    "topics": ["technology", "programming"],
    "limit": 10
  }'
```

**Response:**
```json
{
  "job_id": "6ce324a8-0502-4b0c-b729-12e10f0f22f6",
  "status": "queued",
  "message": "Content processing started. Use job_id to check status.",
  "timestamp": "2025-08-11T13:52:21.355702",
  "status_check_example": {
    "method": "POST",
    "url": "https://func.azurewebsites.net/api/summarywomble",
    "body": {
      "action": "status",
      "job_id": "6ce324a8-0502-4b0c-b729-12e10f0f22f6"
    }
  }
}
```

#### Checking Job Status
```bash
curl -X POST https://func.azurewebsites.net/api/summarywomble \
  -H "x-functions-key: KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "status",
    "job_id": "6ce324a8-0502-4b0c-b729-12e10f0f22f6"
  }'
```

**Response (Running):**
```json
{
  "job_id": "6ce324a8-0502-4b0c-b729-12e10f0f22f6",
  "status": "running",
  "updated_at": "2025-08-11T13:52:21.456789",
  "progress": {
    "step": "processing r/technology",
    "completed": 1,
    "total": 2
  }
}
```

**Response (Completed):**
```json
{
  "job_id": "6ce324a8-0502-4b0c-b729-12e10f0f22f6",
  "status": "completed",
  "updated_at": "2025-08-11T13:52:21.771167",
  "progress": {
    "step": "finished",
    "completed": 2,
    "total": 2
  },
  "results": {
    "total_topics": 20,
    "total_subreddits": 2,
    "results": [
      {
        "subreddit": "technology",
        "topics_count": 10,
        "blob_name": "20250811_135221_reddit_technology.json",
        "status": "success"
      }
    ]
  }
}
```

## Code Changes

### SummaryWomble Function

1. **Added async processing function** (`process_reddit_data_async`)
2. **Added status update helper** (`update_job_status`)
3. **Modified main handler** to return job tickets immediately
4. **Added status check endpoint** via `action=status` parameter

### GetHotTopics Timer Function

1. **Updated to handle job tickets** instead of waiting for completion
2. **Added status checking logic** with 10-second delay
3. **Enhanced logging** for job progress tracking
4. **Backward compatibility** with legacy synchronous responses

## Benefits

### Performance
- **Instant response** - No more 5-minute waits
- **Reduced timeouts** - Background processing eliminates HTTP timeout issues
- **Better resource usage** - Functions can handle more concurrent requests

### Visibility
- **Real-time progress** - See exactly what's happening
- **Detailed status** - Step-by-step progress tracking
- **Persistent history** - Job status stored for later reference
- **Error details** - Specific error information when jobs fail

### Reliability
- **Fault isolation** - Failed jobs don't affect function availability
- **Retry capability** - Easy to retry failed jobs with same parameters
- **Monitoring** - Can track job success rates and performance metrics

## Integration with Timer Function

The GetHotTopics timer function (runs every 6 hours) now:

1. **Submits job request** and gets immediate ticket
2. **Logs job ID** for reference
3. **Checks status** after 10 seconds to see initial progress
4. **Continues** without waiting for completion

This ensures the timer function completes quickly and doesn't get stuck waiting for content collection.

## Future Enhancements

### Planned Improvements
- **Job queueing** with Azure Service Bus for high-volume periods
- **Job priority levels** for urgent vs normal processing
- **Notification system** for job completion (email/webhook)
- **Job cancellation** capability
- **Retry logic** with exponential backoff
- **Performance metrics** and monitoring dashboards

### Extension to Other Stages
This async pattern can be extended to:
- **Content enrichment** stage (AI processing)
- **Content publishing** stage (website generation)
- **Cross-stage dependencies** (job chains)

## Monitoring

### Key Metrics to Track
- Job success/failure rates
- Average processing times
- Queue depth (when implemented)
- Error patterns by subreddit/topic

### Azure Integration
- Application Insights custom metrics
- Blob storage monitoring
- Function execution metrics
- Cost tracking per job

## Testing

### Manual Testing
```bash
# Start a job
JOB_ID=$(curl -s -X POST "https://func.azurewebsites.net/api/summarywomble" \
  -H "x-functions-key: KEY" \
  -d '{"source": "reddit", "topics": ["technology"], "limit": 2}' | jq -r '.job_id')

# Check status
curl -X POST "https://func.azurewebsites.net/api/summarywomble" \
  -H "x-functions-key: KEY" \
  -d "{\"action\": \"status\", \"job_id\": \"$JOB_ID\"}"
```

### Automated Testing
- Unit tests for job status updates
- Integration tests for full job lifecycle
- Load testing for concurrent job handling
- Timer function integration tests

## Troubleshooting

### Common Issues
1. **Job stuck in 'queued' status** - Check function app health, threading issues
2. **Status not updating** - Verify blob storage permissions
3. **Background thread failures** - Check function app logs for thread exceptions
4. **Job ID not found** - Verify job was actually created, check blob storage

### Debugging
- Check Application Insights for function execution traces
- Monitor blob storage for status file creation
- Review function app logs for background thread errors
- Verify Key Vault access for Reddit API credentials

---

*This implementation significantly improves the reliability and user experience of the content collection pipeline while maintaining backward compatibility and providing a foundation for future enhancements.*
