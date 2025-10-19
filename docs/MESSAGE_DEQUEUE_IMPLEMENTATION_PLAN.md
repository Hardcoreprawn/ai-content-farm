# Message Dequeue Timing Implementation Plan

**Status**: Implementation Planning  
**Created**: October 19, 2025  
**Priority**: HIGH IMPACT  
**Goal**: Ensure reliable message processing without duplicates, message loss, or unnecessary requeuing

---

## Executive Summary

The content pipeline relies on Azure Storage Queue message visibility timeouts to prevent duplicate processing. **Current visibility timeout is hardcoded to 10 minutes (600 seconds) across all operations**, which is excessive for most workloads and risks message reappearance while still processing.

**Key Issues**:
1. ❌ **10-minute visibility timeout** - Too long for most operations (markdown generation ~15-30s, content processing ~45-60s)
2. ❌ **No deduplication safeguards** - If a message reappears due to timeout expiry, it will be processed again
3. ❌ **No visibility timeout tuning per container** - Same timeout for fast operations (markdown gen) and slow ones (content processing)
4. ❌ **Missing deletion verification** - No confirmation that messages are actually deleted after processing
5. ❌ **No monitoring for duplicate processing** - Can't detect if duplicate processing is happening

**Success Criteria**:
- ✅ Zero duplicate message processing
- ✅ Zero message loss
- ✅ Appropriate visibility timeouts per container (operations complete well before timeout)
- ✅ Automated monitoring and alerts for anomalies
- ✅ Clear deduplication and retry strategies documented

---

## Current State Analysis

### Visibility Timeout Hardcoding

**Problem Location 1**: `libs/queue_client.py:229`
```python
message_pager = self._queue_client.receive_messages(
    messages_per_page=max_msgs,
    visibility_timeout=600,  # 10 minutes - allows for site builds taking 3-5 minutes
)
```

**Problem Location 2**: `libs/storage_queue_client.py:282`
```python
async for message in self._queue_client.receive_messages(
    messages_per_page=max_msgs,
    visibility_timeout=self.config.visibility_timeout,  # Config-driven but default unclear
)
```

**Problem Location 3**: Container-specific configs

| Container | Current Config | Status |
|-----------|----------------|--------|
| content-processor | Not specified (defaults to Azure SDK default ~30s?) | ⚠️ Inconsistent |
| markdown-generator | 72 seconds (config.py:72) | ✅ Better but not optimized |
| site-publisher | Unknown - needs investigation | ❓ Unknown |
| content-collector | Unknown - needs investigation | ❓ Unknown |

### Message Deletion Verification

**Current Pattern** (content-processor):
```python
messages = await receive_queue_messages(queue_client, max_messages=5, visibility_timeout=30)

for msg in messages:
    try:
        # Process message
        result = await process_content(msg['content'])
        
        # Delete if successful
        if result.success:
            await delete_queue_message(queue_client, msg['id'], msg['pop_receipt'])
    except Exception as e:
        # No explicit requeue - message reappears after timeout
        logger.error(f"Failed to process: {e}")
```

**Issues**:
1. ✅ Message deletion is called on success
2. ❌ No verification that deletion succeeded
3. ❌ No tracking of messages that fail deletion
4. ❌ Partial failures could leave messages in uncertain state

### Deduplication Safeguards

**Current State**: None implemented
- ❌ No correlation ID tracking across processing steps
- ❌ No deduplication cache/database
- ❌ No duplicate detection in message handlers
- ❌ No Application Insights tracking of message IDs

---

## Implementation Plan

### Phase 1: Audit & Measurement (Week 1)

**Goal**: Establish current baseline and identify exact issues

#### 1.1 Audit All Queue Operations
- [ ] **File**: `libs/queue_client.py` (lines 200-280)
  - Document actual visibility timeout value
  - Check if it's being overridden anywhere
  - Verify deletion success path

- [ ] **File**: `libs/storage_queue_client.py` (lines 260-330)
  - Check default visibility timeout in StorageQueueConfig
  - Audit all receive_messages() calls
  - Verify delete_message() error handling

- [ ] **Container configs**:
  - `containers/markdown-generator/config.py` - Check `queue_visibility_timeout_seconds`
  - `containers/content-processor/queue_operations_pkg/queue_client_operations.py` - Check defaults
  - `containers/content-collector/` - Find and document timeout settings
  - `containers/site-publisher/` - Find and document timeout settings

#### 1.2 Measure Processing Times
Add Application Insights logging to track actual processing duration by container:

```python
# Track actual processing time
import time

async def measure_processing(container_name, operation_type):
    """Decorator to track operation timing."""
    start_time = time.time()
    
    # ... process message ...
    
    duration_ms = (time.time() - start_time) * 1000
    
    logger.info(
        f"Operation completed",
        extra={
            "container": container_name,
            "operation": operation_type,
            "duration_ms": duration_ms,
            "visibility_timeout": current_timeout,
            # If duration > 80% of visibility_timeout, that's a problem
            "timeout_risk": "HIGH" if duration_ms > current_timeout * 800 else "OK"
        }
    )
```

**Measurement Points**:
- content-collector: From fetch → deduplicate → queue message (track: time per item, total batch time)
- content-processor: From dequeue → process → enqueue markdown (track: time per article)
- markdown-generator: From dequeue → generate → upload markdown (track: time per article)
- site-publisher: From dequeue → build → deploy (track: time per build)

#### 1.3 Baseline Monitoring Dashboard
Create Application Insights queries to track:

```kusto
// Query 1: Processing duration distribution by container
customMetrics
| where name == "processing_duration_ms"
| summarize 
    Avg = avg(value),
    P50 = percentile(value, 50),
    P95 = percentile(value, 95),
    P99 = percentile(value, 99),
    Max = max(value)
    by container = tostring(customDimensions.container)

// Query 2: Timeout risk detection
customMetrics
| where customDimensions.timeout_risk == "HIGH"
| summarize
    risk_count = count(),
    affected_messages = dcount(customDimensions.message_id)
    by container = tostring(customDimensions.container)

// Query 3: Deletion success rate
customEvents
| where name == "message_deletion"
| summarize
    total_deletions = count(),
    successful = count(deletions where success == true),
    failed = count(deletions where success == false),
    success_rate = (todouble(count(deletions where success == true)) / count()) * 100
    by container = tostring(customDimensions.container)
```

**Output**: Initial visibility timeout recommendations based on actual data

---

### Phase 2: Implement Optimized Visibility Timeouts (Week 1-2)

**Goal**: Set appropriate visibility timeouts per container based on actual processing times

#### 2.1 Update StorageQueueConfig with Container-Specific Defaults

**File**: `libs/storage_queue_client.py` - Modify `StorageQueueConfig`

```python
class StorageQueueConfig(BaseModel):
    """Storage Queue configuration model."""
    
    storage_account_name: str
    queue_name: str
    max_wait_time: int = 1
    max_messages: int = 10
    retry_attempts: int = 3
    visibility_timeout: int = Field(
        default=30,
        description="Message visibility timeout in seconds"
    )
    
    @classmethod
    def from_environment(cls, queue_name: Optional[str] = None) -> "StorageQueueConfig":
        """Create config from environment variables with container-aware defaults."""
        storage_account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME", "").strip()
        env_queue_name = os.getenv("STORAGE_QUEUE_NAME", "").strip()
        container_name = os.getenv("CONTAINER_NAME", "").strip()
        
        final_queue_name = queue_name or env_queue_name or "content-processing-requests"
        
        # Container-specific visibility timeout recommendations
        # (processing_time + safety_buffer)
        CONTAINER_TIMEOUT_DEFAULTS = {
            "content-collector": 180,      # 3 min: collection can take 1-2 min per batch
            "content-processor": 90,       # 1.5 min: processing takes 45-60s per article
            "markdown-generator": 60,      # 1 min: generation takes 15-30s per article
            "site-publisher": 180,         # 3 min: Hugo build takes 60-120s
        }
        
        timeout = CONTAINER_TIMEOUT_DEFAULTS.get(container_name, 30)
        
        return cls(
            storage_account_name=storage_account_name,
            queue_name=final_queue_name,
            visibility_timeout=timeout,
        )
```

#### 2.2 Implement Timeout Calculation Helper

**File**: New file `libs/visibility_timeout.py`

```python
"""
Visibility timeout calculation and management for queue operations.

Ensures message processing completes before visibility timeout expires,
preventing duplicate processing due to message reappearance.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Processing time estimates (in seconds) from operational data
PROCESSING_TIME_ESTIMATES = {
    "content-collector": {
        "min": 30,      # Collecting from single source
        "max": 300,     # Full collection batch (50+ articles)
        "average": 120,
    },
    "content-processor": {
        "min": 10,      # Fastest article processing
        "max": 120,     # Slowest article processing
        "average": 45,
    },
    "markdown-generator": {
        "min": 5,       # Simple markdown generation
        "max": 60,      # With image search and retry
        "average": 15,
    },
    "site-publisher": {
        "min": 30,      # Fast Hugo build
        "max": 300,     # Large site with 1000+ articles
        "average": 90,
    },
}

# Safety buffer as percentage of processing time
# Accounts for network delays, retries, temporary slowdowns
SAFETY_BUFFER_PERCENT = 0.75  # 75% buffer

def calculate_visibility_timeout(
    container_name: str,
    use_max: bool = False,
    custom_duration_ms: Optional[float] = None,
) -> int:
    """
    Calculate appropriate visibility timeout for a container.
    
    Strategy:
    1. Use custom duration if provided (actual measured time)
    2. Otherwise use container estimate with safety buffer
    3. Never go below 30s (Azure SDK minimum)
    4. Never go above 7 days (Azure Storage Queue maximum)
    
    Args:
        container_name: Name of container/service
        use_max: Use max processing time instead of average
        custom_duration_ms: Custom measured duration in milliseconds
    
    Returns:
        Visibility timeout in seconds (int)
    """
    
    if container_name not in PROCESSING_TIME_ESTIMATES:
        logger.warning(
            f"Unknown container {container_name}, using safe default 30s"
        )
        return 30
    
    # Determine base processing time in seconds
    if custom_duration_ms is not None:
        base_seconds = custom_duration_ms / 1000
    else:
        estimates = PROCESSING_TIME_ESTIMATES[container_name]
        base_seconds = estimates["max"] if use_max else estimates["average"]
    
    # Apply safety buffer
    timeout_seconds = base_seconds * (1 + SAFETY_BUFFER_PERCENT)
    
    # Enforce bounds
    timeout_seconds = max(30, min(timeout_seconds, 7 * 24 * 3600))  # 7 days max
    
    return int(timeout_seconds)


def validate_visibility_timeout(
    timeout_seconds: int,
    processing_time_ms: float,
) -> bool:
    """
    Validate that visibility timeout is adequate for processing time.
    
    Returns False if processing time is > 80% of visibility timeout
    (high risk of timeout expiry during processing).
    
    Args:
        timeout_seconds: Configured visibility timeout
        processing_time_ms: Actual processing time
    
    Returns:
        True if timeout is adequate, False if risky
    """
    processing_seconds = processing_time_ms / 1000
    utilization_percent = (processing_seconds / timeout_seconds) * 100
    
    if utilization_percent > 80:
        logger.warning(
            f"Processing utilization {utilization_percent:.1f}% of visibility timeout. "
            f"Risk of message reappearance. Increase timeout or optimize processing."
        )
        return False
    
    return True


def get_recommended_timeout(
    container_name: str,
    processing_times_ms: Optional[list] = None,
) -> dict:
    """
    Get recommended visibility timeout with explanation.
    
    Args:
        container_name: Container name
        processing_times_ms: List of recent processing times in milliseconds
    
    Returns:
        Dict with recommended timeout and reasoning
    """
    
    if processing_times_ms:
        # Use actual measured times if available
        avg_ms = sum(processing_times_ms) / len(processing_times_ms)
        recommended = calculate_visibility_timeout(
            container_name,
            custom_duration_ms=avg_ms
        )
        reasoning = f"Based on {len(processing_times_ms)} measured operations (avg: {avg_ms/1000:.1f}s)"
    else:
        # Use estimates
        recommended = calculate_visibility_timeout(container_name, use_max=False)
        estimates = PROCESSING_TIME_ESTIMATES[container_name]
        reasoning = f"Based on estimates (avg: {estimates['average']}s, max: {estimates['max']}s)"
    
    return {
        "container": container_name,
        "recommended_timeout_seconds": recommended,
        "reasoning": reasoning,
        "safety_buffer_percent": SAFETY_BUFFER_PERCENT * 100,
    }
```

#### 2.3 Update Queue Client to Use Calculated Timeouts

**File**: `libs/queue_client.py` - Modify `receive_messages()`

```python
from libs.visibility_timeout import calculate_visibility_timeout, validate_visibility_timeout

async def receive_messages(self, max_messages: Optional[int] = None) -> List[Any]:
    """Receive messages from the Storage Queue with optimized visibility timeout."""
    
    if not self._queue_client:
        await self.connect()
    
    if not self._queue_client:
        raise RuntimeError("Queue client not connected")
    
    max_msgs = max_messages or 10
    
    try:
        messages = []
        
        # Calculate appropriate visibility timeout based on queue/container
        visibility_timeout = calculate_visibility_timeout(
            container_name=os.getenv("CONTAINER_NAME", "unknown")
        )
        
        logger.info(
            f"Receiving messages with {visibility_timeout}s visibility timeout",
            extra={"visibility_timeout": visibility_timeout}
        )
        
        # Get the async iterator with calculated timeout
        message_pager = self._queue_client.receive_messages(
            messages_per_page=max_msgs,
            visibility_timeout=visibility_timeout,  # CHANGED from hardcoded 600
        )
        
        try:
            count = 0
            async for message in message_pager:
                messages.append(message)
                count += 1
                if count >= max_msgs:
                    break
        finally:
            if hasattr(message_pager, "aclose"):
                await message_pager.aclose()
            elif hasattr(message_pager, "close"):
                await message_pager.close()
        
        logger.info(
            f"Received {len(messages)} messages from queue '{self.queue_name}'"
        )
        return messages
    
    except Exception as e:
        logger.error(
            f"Failed to receive messages from queue '{self.queue_name}': {e}"
        )
        raise
```

---

### Phase 3: Implement Deletion Verification & Error Handling (Week 2)

**Goal**: Ensure messages are actually deleted and track deletion failures

#### 3.1 Enhance Message Deletion with Verification

**File**: New helper in `libs/queue_message_handling.py`

```python
"""
Message handling utilities with reliability safeguards.

Provides deletion verification, retry logic, and failure tracking
to ensure messages are reliably removed from queues.
"""

import asyncio
import logging
import time
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


async def delete_message_with_retry(
    queue_client: Any,
    message: Any,
    max_retries: int = 3,
    retry_delay: float = 0.5,
) -> Tuple[bool, Optional[str]]:
    """
    Delete a message from queue with retry logic.
    
    Args:
        queue_client: Azure Queue client
        message: Message to delete
        max_retries: Number of retry attempts
        retry_delay: Delay between retries (seconds)
    
    Returns:
        Tuple of (success: bool, error_message: Optional[str])
    """
    
    last_error = None
    
    for attempt in range(max_retries):
        try:
            await queue_client.delete_message(message)
            
            logger.info(
                f"Message deleted successfully",
                extra={
                    "message_id": message.id,
                    "attempt": attempt + 1,
                    "pop_receipt": message.pop_receipt[:20],  # First 20 chars
                }
            )
            return True, None
        
        except Exception as e:
            last_error = str(e)
            
            if attempt < max_retries - 1:
                logger.warning(
                    f"Deletion attempt {attempt + 1}/{max_retries} failed: {e}. "
                    f"Retrying in {retry_delay}s",
                    extra={
                        "message_id": message.id,
                        "attempt": attempt + 1,
                        "error": str(e),
                    }
                )
                await asyncio.sleep(retry_delay)
            else:
                logger.error(
                    f"Failed to delete message after {max_retries} attempts",
                    extra={
                        "message_id": message.id,
                        "final_error": str(e),
                    }
                )
    
    return False, last_error


async def verify_message_deletion(
    queue_client: Any,
    message_id: str,
    container_name: str,
) -> bool:
    """
    Verify that a message was actually deleted.
    
    Uses peek_messages to check if message still exists.
    
    Args:
        queue_client: Azure Queue client
        message_id: Message ID that should be deleted
        container_name: For logging context
    
    Returns:
        True if message is gone, False if still in queue
    """
    
    try:
        # Peek at messages without removing them
        messages = []
        async for msg in queue_client.peek_messages(messages_per_page=32):
            messages.append(msg)
        
        # Check if our message still exists
        for msg in messages:
            if msg.id == message_id:
                logger.warning(
                    f"Deleted message still in queue - deletion may have failed",
                    extra={
                        "message_id": message_id,
                        "container": container_name,
                        "dequeue_count": msg.dequeue_count,
                    }
                )
                return False
        
        logger.debug(
            f"Verified message deletion",
            extra={"message_id": message_id}
        )
        return True
    
    except Exception as e:
        logger.warning(
            f"Could not verify deletion: {e}",
            extra={
                "message_id": message_id,
                "error": str(e),
            }
        )
        # Assume success if we can't verify (don't block processing)
        return True


class MessageDeletionTracker:
    """Track message deletion attempts and failures for monitoring."""
    
    def __init__(self, container_name: str):
        self.container_name = container_name
        self.total_deletions = 0
        self.successful_deletions = 0
        self.failed_deletions = 0
        self.unverified_deletions = 0
        self.deletion_failures = {}  # message_id -> error
    
    async def delete_and_track(
        self,
        queue_client: Any,
        message: Any,
        max_retries: int = 3,
    ) -> bool:
        """Delete message and track result."""
        
        self.total_deletions += 1
        
        # Attempt deletion with retries
        success, error = await delete_message_with_retry(
            queue_client,
            message,
            max_retries=max_retries,
        )
        
        if success:
            self.successful_deletions += 1
            
            # Verify deletion (optional, adds latency)
            verified = await verify_message_deletion(
                queue_client,
                message.id,
                self.container_name,
            )
            
            if not verified:
                self.unverified_deletions += 1
                logger.warning(
                    f"Deletion verification failed",
                    extra={"message_id": message.id}
                )
        else:
            self.failed_deletions += 1
            self.deletion_failures[message.id] = error
            logger.error(
                f"Permanent deletion failure",
                extra={
                    "message_id": message.id,
                    "error": error,
                    "container": self.container_name,
                }
            )
        
        return success
    
    def get_stats(self) -> dict:
        """Get deletion statistics for monitoring."""
        success_rate = (
            (self.successful_deletions / self.total_deletions * 100)
            if self.total_deletions > 0
            else 0
        )
        
        return {
            "container": self.container_name,
            "total_deletions": self.total_deletions,
            "successful": self.successful_deletions,
            "failed": self.failed_deletions,
            "unverified": self.unverified_deletions,
            "success_rate_percent": success_rate,
            "first_failures": list(self.deletion_failures.items())[:5],
        }
    
    def log_stats(self):
        """Log current statistics."""
        stats = self.get_stats()
        logger.info(
            f"Message deletion statistics",
            extra=stats
        )
```

#### 3.2 Update Container Message Processing

**File**: `containers/content-processor/queue_operations_pkg/queue_client_operations.py`

```python
from libs.queue_message_handling import delete_message_with_retry, MessageDeletionTracker

async def delete_queue_message_safe(
    queue_client: QueueClient,
    message_id: str,
    pop_receipt: str,
    max_retries: int = 3,
) -> Tuple[bool, Optional[str]]:
    """
    Delete message from Azure Queue Storage with retry logic.
    
    CHANGED: Now includes retry and error reporting.
    """
    last_error = None
    
    for attempt in range(max_retries):
        try:
            await queue_client.delete_message(message_id, pop_receipt)
            logger.info(
                f"Deleted message {message_id} from queue",
                extra={
                    "attempt": attempt + 1,
                    "message_id": message_id,
                }
            )
            return True, None
        
        except Exception as e:
            last_error = str(e)
            
            if attempt < max_retries - 1:
                logger.warning(
                    f"Delete attempt {attempt + 1}/{max_retries} failed for {message_id}: {e}",
                    extra={
                        "attempt": attempt + 1,
                        "error": str(e),
                    }
                )
                await asyncio.sleep(0.5)
            else:
                logger.error(
                    f"Failed to delete message {message_id} after {max_retries} attempts: {e}",
                    extra={
                        "message_id": message_id,
                        "final_error": str(e),
                    }
                )
    
    return False, last_error
```

---

### Phase 4: Implement Deduplication Safeguards (Week 2-3)

**Goal**: Detect and prevent duplicate message processing

#### 4.1 Message Tracking & Deduplication

**File**: New file `libs/message_deduplication.py`

```python
"""
Message deduplication and duplicate detection.

Tracks processed messages to prevent duplicate processing
in case of visibility timeout expiry or requeuing.
"""

import asyncio
import hashlib
import json
import logging
import time
from typing import Optional, Set, Tuple

from azure.storage.blob.aio import BlobContainerClient

logger = logging.getLogger(__name__)

# In-memory cache of recently processed messages (last 1 hour)
_processed_messages_cache: dict = {}


class DeduplicationRecord:
    """Record of a processed message for deduplication."""
    
    def __init__(self, message_id: str, correlation_id: str, timestamp: float):
        self.message_id = message_id
        self.correlation_id = correlation_id
        self.timestamp = timestamp
        self.ttl_seconds = 3600  # 1 hour
    
    def is_expired(self) -> bool:
        """Check if record has expired."""
        return (time.time() - self.timestamp) > self.ttl_seconds


class MessageDeduplicator:
    """
    Track and detect duplicate messages.
    
    Uses three-tier approach:
    1. In-memory cache (fast, per-instance)
    2. Blob storage log (persistent, cross-instance)
    3. Correlation ID tracking (optional, for debugging)
    """
    
    def __init__(
        self,
        container_name: str,
        blob_container_client: Optional[BlobContainerClient] = None,
    ):
        self.container_name = container_name
        self.blob_container_client = blob_container_client
        self.duplicates_detected = 0
        self.false_positives = 0
    
    async def mark_processed(
        self,
        message_id: str,
        correlation_id: str,
        payload_hash: Optional[str] = None,
    ) -> None:
        """
        Mark a message as processed.
        
        Args:
            message_id: Unique message ID
            correlation_id: Correlation ID for tracking
            payload_hash: Optional hash of payload for deduplication
        """
        
        record = DeduplicationRecord(
            message_id=message_id,
            correlation_id=correlation_id,
            timestamp=time.time(),
        )
        
        # In-memory cache
        _processed_messages_cache[message_id] = record
        
        # Blob storage (if available)
        if self.blob_container_client:
            try:
                await self._log_to_blob_storage(
                    message_id,
                    correlation_id,
                    payload_hash,
                    "processed",
                )
            except Exception as e:
                logger.warning(
                    f"Failed to log processed message to blob: {e}",
                    extra={"message_id": message_id}
                )
        
        logger.debug(
            f"Marked message as processed",
            extra={
                "message_id": message_id,
                "correlation_id": correlation_id,
            }
        )
    
    async def check_duplicate(
        self,
        message_id: str,
        correlation_id: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if message was already processed.
        
        Args:
            message_id: Message ID to check
            correlation_id: Correlation ID
        
        Returns:
            Tuple of (is_duplicate: bool, reason: Optional[str])
        """
        
        # Check in-memory cache first (fast)
        if message_id in _processed_messages_cache:
            record = _processed_messages_cache[message_id]
            
            if not record.is_expired():
                self.duplicates_detected += 1
                reason = f"Duplicate in-memory cache (correlation: {correlation_id})"
                logger.warning(
                    f"Duplicate message detected: {reason}",
                    extra={
                        "message_id": message_id,
                        "correlation_id": correlation_id,
                    }
                )
                return True, reason
            else:
                # Expired record - remove from cache
                del _processed_messages_cache[message_id]
        
        # Check blob storage (if available)
        if self.blob_container_client:
            try:
                is_dup, reason = await self._check_blob_storage(
                    message_id,
                    correlation_id,
                )
                if is_dup:
                    return True, reason
            except Exception as e:
                logger.warning(
                    f"Failed to check blob storage: {e}",
                    extra={"message_id": message_id}
                )
        
        return False, None
    
    async def _log_to_blob_storage(
        self,
        message_id: str,
        correlation_id: str,
        payload_hash: Optional[str],
        status: str,
    ) -> None:
        """Log processed message to blob storage."""
        
        if not self.blob_container_client:
            return
        
        log_entry = {
            "message_id": message_id,
            "correlation_id": correlation_id,
            "payload_hash": payload_hash,
            "status": status,
            "timestamp": time.time(),
            "container": self.container_name,
        }
        
        # Append to daily log file
        today = time.strftime("%Y-%m-%d")
        blob_name = f"message-logs/{self.container_name}/{today}/processed.jsonl"
        
        try:
            blob_client = self.blob_container_client.get_blob_client(blob_name)
            
            # Append to existing file or create new
            try:
                existing = await blob_client.download_blob()
                content = await existing.readall()
                content += f"\n{json.dumps(log_entry)}".encode()
            except:
                content = json.dumps(log_entry).encode()
            
            await blob_client.upload_blob(content, overwrite=True)
        
        except Exception as e:
            logger.error(
                f"Failed to write message log to blob: {e}",
                extra={"blob_name": blob_name}
            )
    
    async def _check_blob_storage(
        self,
        message_id: str,
        correlation_id: str,
    ) -> Tuple[bool, Optional[str]]:
        """Check if message was logged to blob storage."""
        
        if not self.blob_container_client:
            return False, None
        
        try:
            # Check last 7 days of logs
            for day_offset in range(7):
                from datetime import datetime, timedelta
                
                date = (datetime.utcnow() - timedelta(days=day_offset)).strftime("%Y-%m-%d")
                blob_name = f"message-logs/{self.container_name}/{date}/processed.jsonl"
                
                try:
                    blob_client = self.blob_container_client.get_blob_client(blob_name)
                    content = await blob_client.download_blob()
                    data = await content.readall()
                    
                    # Search for message_id in log
                    for line in data.decode().split("\n"):
                        if not line.strip():
                            continue
                        
                        log_entry = json.loads(line)
                        if log_entry.get("message_id") == message_id:
                            self.duplicates_detected += 1
                            return (
                                True,
                                f"Duplicate in blob storage {date} "
                                f"(correlation: {correlation_id})",
                            )
                
                except:
                    # Blob doesn't exist for this day
                    continue
        
        except Exception as e:
            logger.warning(
                f"Error checking blob storage for duplicates: {e}"
            )
        
        return False, None
    
    def get_stats(self) -> dict:
        """Get deduplication statistics."""
        
        # Clean expired cache entries
        now = time.time()
        expired_count = 0
        for msg_id, record in list(_processed_messages_cache.items()):
            if record.is_expired():
                del _processed_messages_cache[msg_id]
                expired_count += 1
        
        return {
            "container": self.container_name,
            "duplicates_detected": self.duplicates_detected,
            "cache_size": len(_processed_messages_cache),
            "expired_removed": expired_count,
        }
    
    def log_stats(self):
        """Log current statistics."""
        stats = self.get_stats()
        logger.info(
            f"Message deduplication statistics",
            extra=stats
        )
```

#### 4.2 Integration with Container Message Processing

Example integration in `containers/content-processor/queue_processor.py`:

```python
from libs.message_deduplication import MessageDeduplicator

# Initialize deduplicator
deduplicator = MessageDeduplicator(
    container_name="content-processor",
    blob_container_client=blob_service_client.get_container_client("message-logs"),
)

async def message_handler(queue_message, message) -> Dict[str, Any]:
    """Process queue message with deduplication."""
    
    # Check for duplicate
    is_duplicate, reason = await deduplicator.check_duplicate(
        message_id=message.id,
        correlation_id=queue_message.correlation_id,
    )
    
    if is_duplicate:
        logger.warning(
            f"Skipping duplicate message: {reason}",
            extra={
                "message_id": message.id,
                "correlation_id": queue_message.correlation_id,
            }
        )
        
        # Still delete the message to prevent re-queuing
        try:
            await delete_message_with_retry(queue_client, message)
        except:
            logger.error(
                f"Failed to delete duplicate message",
                extra={"message_id": message.id}
            )
        
        return {"status": "skipped", "reason": "duplicate"}
    
    try:
        # Process message normally
        result = await process_content(queue_message)
        
        # Mark as processed for future deduplication
        await deduplicator.mark_processed(
            message_id=message.id,
            correlation_id=queue_message.correlation_id,
            payload_hash=hashlib.sha256(
                json.dumps(queue_message.payload).encode()
            ).hexdigest(),
        )
        
        # Delete message only after successful processing
        success, error = await delete_message_with_retry(queue_client, message)
        
        if not success:
            logger.error(
                f"Failed to delete processed message: {error}",
                extra={"message_id": message.id}
            )
        
        return {"status": "processed", "result": result}
    
    except Exception as e:
        logger.error(
            f"Error processing message: {e}",
            extra={
                "message_id": message.id,
                "error": str(e),
            }
        )
        # Let message reappear for retry
        raise
```

---

### Phase 5: Monitoring & Alerting (Week 3)

**Goal**: Real-time visibility into message processing health

#### 5.1 Application Insights Queries

**File**: New file `docs/MONITORING_QUERIES.md`

```kusto
// Query 1: Message Processing Timeline
customEvents
| where name in ("message_received", "message_processed", "message_deleted")
| project
    timestamp,
    message_id = tostring(customDimensions.message_id),
    event = name,
    container = tostring(customDimensions.container),
    duration_ms = todouble(customDimensions.duration_ms)
| order by message_id, timestamp asc
| summarize
    received = min_of(timestamp),
    deleted = max_of(timestamp),
    total_time_ms = max(timestamp) - min_of(timestamp)
    by message_id, container

// Query 2: Duplicate Detection Rate
customEvents
| where name == "duplicate_detected"
| summarize
    duplicates_count = count(),
    unique_messages = dcount(customDimensions.message_id)
    by container = tostring(customDimensions.container),
       bin(timestamp, 1h)
| order by timestamp desc

// Query 3: Visibility Timeout Risk
customMetrics
| where name == "processing_duration_ms"
| extend
    timeout_seconds = todouble(customDimensions.visibility_timeout),
    duration_seconds = value / 1000,
    utilization_percent = (value / 1000) / todouble(customDimensions.visibility_timeout) * 100
| where utilization_percent > 80
| summarize
    at_risk_count = count(),
    max_utilization = max(utilization_percent),
    avg_utilization = avg(utilization_percent)
    by container = tostring(customDimensions.container)
| order by max_utilization desc

// Query 4: Deletion Success Rate
customEvents
| where name == "message_deletion"
| summarize
    total = count(),
    successful = count(result == "success"),
    failed = count(result == "failed"),
    success_rate = (todouble(count(result == "success")) / count()) * 100
    by container = tostring(customDimensions.container),
       bin(timestamp, 1h)
| order by timestamp desc

// Query 5: Message Requeue Detection (dequeue_count > 1)
customEvents
| where name == "message_received"
| where todouble(customDimensions.dequeue_count) > 1
| summarize
    requeue_count = count(),
    max_dequeues = max(todouble(customDimensions.dequeue_count)),
    containers_affected = dcount(tostring(customDimensions.container))
    by bin(timestamp, 1h)
| order by timestamp desc
```

#### 5.2 Alerts Configuration

**File**: `infra/monitoring_alerts.tf` (Terraform)

```hcl
# Alert: High duplicate message detection rate
resource "azurerm_monitor_metric_alert" "high_duplicate_rate" {
  name                = "ai-content-high-duplicate-rate"
  resource_group_name = azurerm_resource_group.main.name
  scopes              = [azurerm_application_insights.main.id]
  
  criteria {
    metric_namespace = "Microsoft.Insights/components"
    metric_name      = "customMetrics/duplicate_detection_rate"
    operator         = "GreaterThan"
    threshold        = 5  # >5% duplicate rate
    aggregation      = "Average"
  }
  
  action {
    action_group_id = azurerm_monitor_action_group.alerts.id
  }
}

# Alert: Message deletion failures
resource "azurerm_monitor_metric_alert" "deletion_failures" {
  name                = "ai-content-message-deletion-failures"
  resource_group_name = azurerm_resource_group.main.name
  scopes              = [azurerm_application_insights.main.id]
  
  criteria {
    metric_namespace = "Microsoft.Insights/components"
    metric_name      = "customMetrics/deletion_failure_rate"
    operator         = "GreaterThan"
    threshold        = 2  # >2% failure rate
    aggregation      = "Average"
  }
  
  action {
    action_group_id = azurerm_monitor_action_group.alerts.id
  }
}

# Alert: Visibility timeout risk (processing > 80% of timeout)
resource "azurerm_monitor_metric_alert" "timeout_risk" {
  name                = "ai-content-visibility-timeout-risk"
  resource_group_name = azurerm_resource_group.main.name
  scopes              = [azurerm_application_insights.main.id]
  
  criteria {
    metric_namespace = "Microsoft.Insights/components"
    metric_name      = "customMetrics/timeout_utilization_high"
    operator         = "GreaterThan"
    threshold        = 10  # >10 events with high utilization
    aggregation      = "Count"
  }
  
  action {
    action_group_id = azurerm_monitor_action_group.alerts.id
  }
}
```

---

## Implementation Checklist

### Phase 1: Audit & Measurement
- [ ] Audit all queue operation code files
- [ ] Document current visibility timeout values by container
- [ ] Measure actual processing times (add logging)
- [ ] Create baseline Application Insights queries
- [ ] Generate initial recommendations report

### Phase 2: Optimize Visibility Timeouts
- [ ] Create `libs/visibility_timeout.py` with calculation logic
- [ ] Update `StorageQueueConfig` with container-aware defaults
- [ ] Update `libs/queue_client.py` to use calculated timeouts
- [ ] Remove hardcoded 600s timeout from all files
- [ ] Test timeout values with development workload
- [ ] Document timeout values per container in README

### Phase 3: Deletion Verification
- [ ] Create `libs/queue_message_handling.py` with retry logic
- [ ] Implement `MessageDeletionTracker` class
- [ ] Update `container/content-processor/` to use safe deletion
- [ ] Update markdown-generator to use safe deletion
- [ ] Add deletion failure alerting
- [ ] Test deletion verification with simulated failures

### Phase 4: Deduplication
- [ ] Create `libs/message_deduplication.py` with deduplication logic
- [ ] Implement `MessageDeduplicator` class with blob storage
- [ ] Integrate deduplicator into container message handlers
- [ ] Test duplicate detection with simulated requeues
- [ ] Add duplicate detection metrics
- [ ] Document deduplication strategy

### Phase 5: Monitoring
- [ ] Create Application Insights queries
- [ ] Setup monitoring dashboard
- [ ] Configure metric alerts
- [ ] Document alert thresholds
- [ ] Create runbooks for common alerts

---

## Risk Mitigation

### Risk 1: Visibility Timeout Too Short
**Problem**: Messages timeout and reappear while still processing
**Mitigation**:
- Start with conservative timeouts (avg_time * 2)
- Monitor processing duration distribution
- Alert if processing > 80% of timeout
- Gradually reduce as confidence grows

### Risk 2: Visibility Timeout Too Long
**Problem**: Duplicate processing if queue fails (e.g., restart)
**Mitigation**:
- Use deduplication for all messages
- Keep timeout as low as safely possible
- Monitor message dequeue count

### Risk 3: Deletion Failures Accumulate
**Problem**: Failed deletes cause message requeuing and duplicates
**Mitigation**:
- Implement retry logic (3 attempts with backoff)
- Log all deletion failures
- Alert on >2% deletion failure rate
- Manual intervention procedure for stuck messages

### Risk 4: Cross-Instance Race Conditions
**Problem**: Multiple container instances process same message
**Mitigation**:
- Use distributed deduplication (blob storage)
- Implement pop_receipt validation
- Test with multi-instance scaling

---

## Testing Strategy

### Unit Tests
```python
# tests/test_visibility_timeout.py
def test_calculate_visibility_timeout_content_processor():
    assert calculate_visibility_timeout("content-processor") >= 90
    assert calculate_visibility_timeout("content-processor") <= 180

def test_calculate_visibility_timeout_with_custom_duration():
    # If processing took 10s, timeout should be ~17.5s (10 + 75% buffer)
    assert calculate_visibility_timeout("test", custom_duration_ms=10000) >= 17

def test_validate_visibility_timeout_pass():
    # 45s processing, 90s timeout = 50% utilization (OK)
    assert validate_visibility_timeout(90, 45000) == True

def test_validate_visibility_timeout_fail():
    # 75s processing, 90s timeout = 83% utilization (HIGH RISK)
    assert validate_visibility_timeout(90, 75000) == False

# tests/test_deduplication.py
@pytest.mark.asyncio
async def test_duplicate_detection():
    dedup = MessageDeduplicator("test-container")
    
    await dedup.mark_processed("msg-1", "corr-1")
    
    is_dup, reason = await dedup.check_duplicate("msg-1", "corr-1")
    assert is_dup == True
    assert "duplicate" in reason.lower()

@pytest.mark.asyncio
async def test_deletion_retry_success():
    mock_client = AsyncMock()
    success, error = await delete_message_with_retry(mock_client, msg)
    
    assert success == True
    assert error is None
    mock_client.delete_message.assert_called_once()

@pytest.mark.asyncio
async def test_deletion_retry_failure_then_success():
    mock_client = AsyncMock()
    mock_client.delete_message.side_effect = [
        Exception("Network error"),
        Exception("Network error"),
        None  # Success on 3rd attempt
    ]
    
    success, error = await delete_message_with_retry(
        mock_client, msg, max_retries=3
    )
    
    assert success == True
    assert mock_client.delete_message.call_count == 3
```

### Integration Tests
```python
# tests/test_queue_operations_integration.py
@pytest.mark.integration
async def test_end_to_end_message_processing():
    """Test complete message lifecycle: send → receive → process → delete"""
    
    # Send message
    msg_id = await send_test_message(queue_client, test_data)
    
    # Receive message
    messages = await receive_queue_messages(queue_client, max_messages=1)
    assert len(messages) == 1
    assert messages[0]['id'] == msg_id
    
    # Process message (simulate)
    await asyncio.sleep(5)
    
    # Verify message is still invisible (before timeout)
    peeked = await peek_queue_messages(queue_client)
    assert not any(m.id == msg_id for m in peeked)
    
    # Delete message
    success, error = await delete_message_with_retry(
        queue_client,
        messages[0],
        max_retries=3
    )
    assert success == True
    
    # Verify deletion
    peeked = await peek_queue_messages(queue_client)
    assert not any(m.id == msg_id for m in peeked)
```

---

## Success Metrics

### Primary Metrics
- ✅ **Zero duplicate processing**: Duplicate detection rate = 0%
- ✅ **Zero message loss**: All messages either processed or deleted
- ✅ **Appropriate timeouts**: Processing time < 80% of visibility timeout
- ✅ **High deletion success**: Deletion success rate > 99%

### Secondary Metrics
- ✅ **Processing efficiency**: Processing time distribution tracked and optimized
- ✅ **Alert coverage**: All critical failure modes have alerts
- ✅ **Observability**: Complete message lifecycle tracking in Application Insights

### Monitoring Dashboard Metrics
- Message processing time (p50, p95, p99)
- Duplicate detection rate (daily/hourly)
- Deletion success rate (daily/hourly)
- Visibility timeout utilization (% of timeout used)
- Message requeue count (dequeue_count distribution)
- Failed deletion attempts (daily/hourly)

---

## Timeline & Dependencies

```
Week 1:
  Day 1-2: Phase 1 - Audit & Measurement
  Day 3-5: Phase 2 - Optimize Timeouts
  
Week 2:
  Day 1-3: Phase 3 - Deletion Verification
  Day 4-5: Phase 4 - Deduplication Start
  
Week 3:
  Day 1-3: Phase 4 - Deduplication Complete
  Day 4-5: Phase 5 - Monitoring & Alerts

Post-Implementation:
  Ongoing: Monitor metrics, tune timeouts based on production data
```

---

## Questions for Review

1. **Timeout values**: Are the recommended timeouts (90s content-processor, 60s markdown-generator, 180s site-publisher) appropriate?
2. **Deduplication scope**: Should we implement blob-based deduplication, or is in-memory sufficient?
3. **Deletion verification**: Is the additional latency of verification acceptable, or should it be optional?
4. **Alert thresholds**: What duplicate rate (%) should trigger alerts? Currently set to 5%, is that right?
5. **Testing**: Should we add chaos engineering tests (simulate queue failures, timeouts)?

---

_Last Updated: October 19, 2025_  
_Status: Ready for Implementation_
