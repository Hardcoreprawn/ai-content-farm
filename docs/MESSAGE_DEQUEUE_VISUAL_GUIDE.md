# Message Dequeue Timing - Visual Architecture & Flows

## Current Problem Flow (❌ What's Broken)

```
┌─────────────────────────────────────────────────────────────────┐
│ CURRENT: Message Processing with Long Visibility Timeout         │
└─────────────────────────────────────────────────────────────────┘

Message Lifecycle:
  
  0s  ├─ Message arrives in queue
      │
  1s  ├─ Container receives message
      │   └─ Visibility timeout: 600s (10 MINUTES!) ⚠️
      │   └─ Message now INVISIBLE to other instances
      │
  45s ├─ Processing completes
      │   └─ Message should be deleted now
      │
 100s ├─ Delete message (may fail silently)
      │   └─ If deletion FAILS: message stays in queue
      │   └─ If deletion SUCCEEDS: message removed
      │
 550s ├─ ⚠️ STILL INVISIBLE (timeout hasn't expired yet)
      │   └─ If another instance restarts during this time...
      │   └─ It might REPROCESS the message!
      │
 600s ├─ Visibility timeout EXPIRES
      │   └─ Message reappears in queue (if not deleted)
      │   └─ Available for reprocessing!
      │
 601s ├─ Another instance picks up message AGAIN
      │   └─ DUPLICATE PROCESSING! ❌
      │
 650s └─ Article processed twice → duplicate published

┌─────────────────────────────────────────────────────────────────┐
│ ROOT CAUSES OF DUPLICATE PROCESSING:                             │
├─────────────────────────────────────────────────────────────────┤
│ 1. Timeout too long (600s) for processing time (45s)            │
│    → Message invisible for 550+ seconds AFTER processing done   │
│                                                                  │
│ 2. Deletion may fail silently                                   │
│    → No verification that message was actually deleted          │
│    → Message reappears at timeout expiry                        │
│                                                                  │
│ 3. No deduplication                                              │
│    → If message reappears, no way to detect it's a duplicate    │
│    → Will process it again                                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Proposed Solution Flow (✅ What We'll Fix)

```
┌─────────────────────────────────────────────────────────────────┐
│ PROPOSED: Optimized Visibility Timeout with Safeguards          │
└─────────────────────────────────────────────────────────────────┘

Message Lifecycle (content-processor example):

  0s  ├─ Message arrives in queue
      │
  1s  ├─ Container receives message
      │   └─ CALCULATE visibility timeout:
      │   │   • Avg processing time: 45s
      │   │   • Safety buffer: +75% = 34s
      │   │   • Timeout = 90s (NOT 600s!)
      │   │
      │   └─ Visibility timeout: 90s ✅
      │   └─ Message now INVISIBLE
      │   └─ Mark message_id for deduplication tracking
      │
 10s  ├─ Processing underway
      │   └─ Check: is this a duplicate? (check cache)
      │   │   └─ NO → proceed with processing
      │   │
      │   └─ Processing continues...
      │
 50s  ├─ Processing completes successfully
      │   └─ Article generated successfully
      │   └─ Mark message as processed (store message_id)
      │   └─ Add to deduplication cache (1 hour TTL)
      │
 51s  ├─ DELETE message with RETRY LOGIC
      │   │   Attempt 1: Delete fails (network error)
      │   │             → Wait 500ms
      │   │   Attempt 2: Delete fails (transient error)
      │   │             → Wait 500ms
      │   │   Attempt 3: Delete SUCCEEDS ✅
      │   │
      │   └─ Verify deletion (peek at queue)
      │   │   └─ Message not found → Confirmed deleted ✅
      │   │
      │   └─ Log deletion success to Application Insights
      │
 52s  ├─ Message successfully processed and deleted
      │   └─ Processing duration: 52s (< 90s timeout) ✅
      │   └─ No reappearance risk ✅
      │
 90s  ├─ Visibility timeout WOULD have expired
      │   └─ But message is already deleted!
      │   └─ No reappearance possible
      │
────────────────────────────────────────────────────────────────────
    If deletion had SOMEHOW FAILED (caught by safeguard):

 90s  ├─ Visibility timeout expires
      │   └─ Message reappears in queue
      │
 91s  ├─ Another instance receives message AGAIN
      │   └─ Check deduplication cache:
      │   │   └─ "Have we seen message_id before?"
      │   │   └─ YES! → Skip processing ✅
      │   │
      │   └─ Delete message anyway (it shouldn't be here)
      │   └─ Log duplicate detection alert
      │   └─ Alert sent to monitoring

┌─────────────────────────────────────────────────────────────────┐
│ KEY IMPROVEMENTS:                                                │
├─────────────────────────────────────────────────────────────────┤
│ ✅ Timeout: 600s → 90s (6.7x reduction)                         │
│    → Processing time 50s vs timeout 90s = only 56% utilization  │
│    → Safe margin to complete before timeout                     │
│                                                                  │
│ ✅ Deletion: Fire-and-forget → Retry + verify                  │
│    → Catches and retries transient failures                     │
│    → Confirms message actually deleted                          │
│                                                                  │
│ ✅ Deduplication: None → In-memory + blob storage               │
│    → Fast in-memory cache for recent messages                   │
│    → Persistent blob log for cross-instance dedup               │
│    → Safety net catches reappearing messages                    │
│                                                                  │
│ ✅ Monitoring: Unknown → Full observability                     │
│    → Track processing duration per operation                    │
│    → Alert on duplicate detection (should be 0%)                │
│    → Alert on deletion failures (should be <1%)                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Architecture: Components & Integration

```
┌──────────────────────────────────────────────────────────────────┐
│                        libs/ (Shared)                            │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─ visibility_timeout.py                                       │
│  │   └─ calculate_visibility_timeout(container_name)            │
│  │   └─ validate_visibility_timeout(timeout, processing_time)   │
│  │   └─ PROCESSING_TIME_ESTIMATES (per container)              │
│  │                                                              │
│  ┌─ queue_message_handling.py                                   │
│  │   └─ delete_message_with_retry()  [retry logic]             │
│  │   └─ verify_message_deletion()    [verification]            │
│  │   └─ MessageDeletionTracker       [statistics]              │
│  │                                                              │
│  ┌─ message_deduplication.py                                    │
│  │   └─ MessageDeduplicator          [main class]              │
│  │   │   ├─ mark_processed()         [record message]          │
│  │   │   ├─ check_duplicate()        [detect duplicate]        │
│  │   │   └─ get_stats()              [metrics]                 │
│  │   └─ DeduplicationRecord          [data model]              │
│  │                                                              │
│  ┌─ queue_client.py (MODIFIED)                                  │
│  │   └─ receive_messages()                                      │
│  │       ├─ Use calculate_visibility_timeout() [NEW]            │
│  │       └─ Receive with optimized timeout                      │
│  │                                                              │
│  └─ storage_queue_client.py (MODIFIED)                          │
│      └─ StorageQueueConfig                                      │
│          └─ Container-aware visibility_timeout defaults [NEW]   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘

                            ▼

┌──────────────────────────────────────────────────────────────────┐
│              containers/ (Each Container)                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─ content-processor/                                          │
│  │   └─ queue_processor.py (MODIFIED)                           │
│  │       ├─ message_handler()                                   │
│  │       │   ├─ deduplicator.check_duplicate() [NEW]           │
│  │       │   ├─ process_content()                               │
│  │       │   ├─ deduplicator.mark_processed() [NEW]            │
│  │       │   └─ delete_message_with_retry() [NEW]              │
│  │       │                                                      │
│  │       └─ Uses: visibility_timeout, deletion, dedup          │
│  │                                                              │
│  ├─ markdown-generator/                                         │
│  │   └─ queue_processor.py (MODIFIED)                           │
│  │       └─ Similar integration                                 │
│  │                                                              │
│  └─ site-publisher/, content-collector/                         │
│      └─ All containers follow same pattern                      │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘

                            ▼

┌──────────────────────────────────────────────────────────────────┐
│            Azure Storage Queue / Application Insights           │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─ Azure Storage Queue                                         │
│  │   └─ Messages with optimized visibility timeout              │
│  │   └─ Fewer reappearances                                     │
│  │   └─ Faster deletion (less timeout waste)                    │
│  │                                                              │
│  ├─ Azure Blob Storage (message-logs/)                          │
│  │   └─ Persistent deduplication log (cross-instance)           │
│  │   └─ 7-day retention for duplicate detection                 │
│  │                                                              │
│  └─ Application Insights                                        │
│      ├─ customMetrics: processing_duration_ms                   │
│      ├─ customEvents: message_received, message_deleted         │
│      ├─ Queries: duplicate_rate, deletion_success_rate          │
│      └─ Alerts: high_duplicate_rate, deletion_failures          │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Timeout Calculation Logic

```
┌─────────────────────────────────────────────────────────────────┐
│ Container: content-processor                                    │
│ Operation: Process article (LLM analysis, enrichment)           │
└─────────────────────────────────────────────────────────────────┘

Step 1: Collect Processing Time Estimates
  ┌─────────────────┐
  │  Fast track     │  (1st percentile)     10s
  │  Typical        │  (50th percentile)    45s  ← Use this
  │  Slow track     │  (95th percentile)    90s
  │  Worst case     │  (99.9th percentile) 120s
  └─────────────────┘

Step 2: Add Safety Buffer
  Base time (typical):        45s
  Safety buffer:               × 1.75 (75% of base time)
                              ───────
  Required timeout:           45 + 34 = 79s
  
  → Rounded up: 90s ✅

Step 3: Validation
  Processing duration:  45s
  Visibility timeout:   90s
  Utilization:         45/90 = 50% ← Good (< 80%)
  
  ✅ Timeout is adequate

┌─────────────────────────────────────────────────────────────────┐
│ TIMEOUT RECOMMENDATIONS (Per Container)                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ content-collector:       180s  (batch collection, variable)     │
│ content-processor:        90s  (stable processing time)         │
│ markdown-generator:       60s  (fast, predictable)              │
│ site-publisher:          180s  (Hugo builds, variable)          │
│                                                                  │
│ OLD (hardcoded):         600s  (10 minutes, excessive)          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Message Deletion Flow (with Retry)

```
┌─ delete_message_with_retry(queue_client, message)
│
├─ Attempt #1
│   ├─ Try: await queue_client.delete_message(message)
│   │
│   ├─ SUCCESS ✅
│   │   └─ Return (True, None)
│   │
│   └─ FAILURE ❌
│       ├─ Log: "Deletion attempt 1/3 failed: Network error"
│       ├─ Wait: 500ms
│       └─ Continue to Attempt #2
│
├─ Attempt #2
│   ├─ Try: await queue_client.delete_message(message)
│   │
│   ├─ SUCCESS ✅
│   │   └─ Return (True, None)
│   │
│   └─ FAILURE ❌
│       ├─ Log: "Deletion attempt 2/3 failed: Transient error"
│       ├─ Wait: 500ms
│       └─ Continue to Attempt #3
│
├─ Attempt #3 (FINAL)
│   ├─ Try: await queue_client.delete_message(message)
│   │
│   ├─ SUCCESS ✅
│   │   └─ Return (True, None)
│   │
│   └─ FAILURE ❌ (give up)
│       ├─ Log: "Failed to delete after 3 attempts: Permission error"
│       ├─ Alert: "MESSAGE DELETION FAILURE"
│       └─ Return (False, "Permission error")
│
└─ After deletion (success)
    ├─ Verify deletion (optional)
    │   ├─ Peek at queue: Is message still there?
    │   ├─ YES  → Log warning: "Deletion verification failed"
    │   └─ NO   → Log success: "Deletion verified"
    │
    └─ Record success to Application Insights
        ├─ customEvent: "message_deletion"
        ├─ success: true/false
        ├─ duration_ms: 250
        └─ retry_attempts: 1-3
```

---

## Deduplication Logic (Multi-Tier)

```
┌─ check_duplicate(message_id, correlation_id)
│
├─ TIER 1: In-Memory Cache (FAST)
│   ├─ _processed_messages_cache.get(message_id)
│   │
│   ├─ FOUND ✅
│   │   ├─ Check TTL: is record expired? (1 hour)
│   │   │
│   │   ├─ NOT EXPIRED
│   │   │   ├─ duplicates_detected += 1
│   │   │   └─ Return (True, "Duplicate in cache")
│   │   │
│   │   └─ EXPIRED
│   │       └─ Remove from cache, continue to Tier 2
│   │
│   └─ NOT FOUND
│       └─ Continue to Tier 2
│
├─ TIER 2: Blob Storage Log (PERSISTENT)
│   ├─ Read: message-logs/{container}/{date}/processed.jsonl
│   │
│   ├─ FOUND in log ✅
│   │   ├─ duplicates_detected += 1
│   │   └─ Return (True, "Duplicate in blob log (3 days ago)")
│   │
│   └─ NOT FOUND
│       └─ Continue to Tier 3
│
├─ TIER 3: Cross-Instance Coordination (DISTRIBUTED)
│   └─ (Future: Could use Redis, Cosmos DB, etc.)
│
└─ RESULT
    ├─ DUPLICATE DETECTED ✅
    │   ├─ Skip processing
    │   ├─ Delete message anyway
    │   └─ Alert monitoring
    │
    └─ NOT DUPLICATE ✅
        ├─ Proceed with processing
        ├─ After success: mark_processed(message_id)
        │   ├─ Add to in-memory cache
        │   └─ Append to blob storage log
        └─ Continue
```

---

## Processing Time Utilization Analysis

```
Current (❌ BROKEN):
┌──────────────────────────────────────────────────────────────────┐
│ content-processor                                                │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│ Processing time:  [======45s======]                             │
│ Timeout:          [====================600s=====================]
│                                                                  │
│ Utilization: 45s / 600s = 7.5% ⚠️ WASTED TIMEOUT!              │
│                                                                  │
│ Risk: Message invisible for 555s AFTER processing complete      │
│       High chance of reappearance if something crashes          │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘

Optimized (✅ PROPOSED):
┌──────────────────────────────────────────────────────────────────┐
│ content-processor                                                │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│ Processing time:  [====45s====]                                 │
│ Timeout:          [========90s========]                          │
│                                                                  │
│ Utilization: 45s / 90s = 50% ✅ BALANCED                        │
│                                                                  │
│ Safety margin: 45s (time from finish to timeout)                │
│                └─ Enough for retries and cleanup                │
│                └─ Not so long that reappearance is likely       │
│                                                                  │
│ Result: Processing completes → Delete → Done                    │
│         Message deleted WELL BEFORE timeout expiry              │
│         Zero reappearance risk ✅                               │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘

All Containers:
┌────────────────────────────────────────────────────────────────────┐
│ Avg Time    Timeout    Utilization    Safety Margin    Status      │
├────────────────────────────────────────────────────────────────────┤
│ 30s  →  60s    50%          30s          ✅ Good                   │
│ 45s  →  90s    50%          45s          ✅ Good                   │
│ 90s  → 180s    50%          90s          ✅ Good                   │
│ 60s  → 120s    50%          60s          ✅ Good                   │
│                                                                    │
│ OLD: All     600s       <10%        500+s ❌ Way too high!        │
└────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Dependency Graph

```
Phase 1: Audit & Measurement
  └─ Collect baseline data
     └─ Processing time estimates
     └─ Current timeout usage
     └─ Output: Recommendations

Phase 2: Optimize Timeouts (Depends on: Phase 1)
  ├─ Create: libs/visibility_timeout.py
  ├─ Update: libs/queue_client.py (use calculated timeout)
  ├─ Update: libs/storage_queue_client.py (config defaults)
  └─ Deploy: Test in dev environment
     └─ Phase 3 can start in parallel

Phase 3: Deletion Verification (Depends on: Phase 1)
  ├─ Create: libs/queue_message_handling.py
  ├─ Update: content-processor queue operations
  ├─ Update: markdown-generator queue processor
  └─ Deploy: Test in dev environment
     └─ Phase 4 can start after this

Phase 4: Deduplication (Depends on: Phase 2 + Phase 3)
  ├─ Create: libs/message_deduplication.py
  ├─ Update: All container message handlers
  ├─ Setup: Blob storage for message logs
  └─ Deploy: Test with production workload
     └─ Phase 5 can start immediately

Phase 5: Monitoring (Depends on: Phase 4)
  ├─ Create: Application Insights queries
  ├─ Setup: Alert rules
  ├─ Create: Monitoring dashboard
  └─ Deploy: Monitor production
```

---

## Success Indicators (What to Watch)

```
GOOD SIGNS ✅:
┌──────────────────────────────────────────────────────────────────┐
│ • Processing duration < 80% of visibility timeout                │
│ • Duplicate detection rate = 0%                                  │
│ • Message deletion success rate > 99%                            │
│ • No requeue detection (dequeue_count = 1)                       │
│ • Average processing time < average timeout                      │
└──────────────────────────────────────────────────────────────────┘

BAD SIGNS ⚠️ (Tune Timeout UP):
┌──────────────────────────────────────────────────────────────────┐
│ • Processing duration > 90% of visibility timeout                │
│   → Increase timeout by 50%                                      │
│                                                                  │
│ • Messages timing out (reappearing):                             │
│   → Increase timeout                                             │
│   → Or optimize processing                                       │
└──────────────────────────────────────────────────────────────────┘

CRITICAL SIGNS 🔴 (Investigate):
┌──────────────────────────────────────────────────────────────────┐
│ • Duplicate detection rate > 5%                                  │
│   → Messages are reappearing too often                           │
│   → Increase timeout or fix processing time                      │
│   → Check: Is deduplication working?                             │
│                                                                  │
│ • Message deletion failure rate > 2%                             │
│   → Retry logic may not be enough                                │
│   → Check: Queue permissions, account connectivity               │
│   → Investigate: Application Insights logs                       │
│                                                                  │
│ • dequeue_count > 1 in production:                               │
│   → Messages are being reprocessed                               │
│   → Check: Was deletion successful?                              │
│   → Check: Did timeout expire mid-processing?                    │
└──────────────────────────────────────────────────────────────────┘
```

---

This visual guide is meant to be printed/referenced during implementation.
See `MESSAGE_DEQUEUE_IMPLEMENTATION_PLAN.md` for detailed code examples.
