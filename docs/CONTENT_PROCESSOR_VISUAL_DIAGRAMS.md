# Content Processor Visual Architecture Diagrams

## 1. Current Class Hierarchy (Stateful OOP)

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Application                  │
│                         (main.py)                       │
└───────────────┬─────────────────────────────────────────┘
                │
    ┌───────────┼───────────┐
    │           │           │
    ▼           ▼           ▼
┌────────┐  ┌────────┐  ┌────────────┐
│Diagnos-│  │Process-│  │StorageQueue│
│tics    │  │ing     │  │Router      │
│Router  │  │Router  │  │(Singleton!)│
└────────┘  └────────┘  └─────┬──────┘
                              │
                      ┌───────▼──────────────────────┐
                      │   ContentProcessor Instance  │
                      │   ─────────────────────────  │
                      │   • processor_id: str        │
                      │   • session_id: str          │
                      │   • blob_client: Client      │
                      │   • openai_client: Client    │
                      │   • 7 service instances      │
                      └───────┬──────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐   ┌───────────────┐   ┌──────────────┐
│TopicDiscovery │   │ArticleGenerat-│   │LeaseCoordina-│
│Service        │   │ionService     │   │tor           │
│─────────────  │   │─────────────  │   │────────────  │
│• blob_client  │   │• openai_client│   │• processor_id│
│• container    │   │• metadata_gen │   └──────────────┘
└───────────────┘   └───────┬───────┘
                            │
                    ┌───────▼───────┐
                    │ OpenAIClient  │
                    │ ────────────  │
                    │• client: Async│
                    │• pricing_svc  │
                    └───────┬───────┘
                            │
                    ┌───────▼───────┐
                    │PricingService │
                    │────────────── │
                    │• blob_client  │
                    │• cache_data   │
                    └───────────────┘

🔴 PROBLEMS:
- Circular dependencies (MetadataGenerator ↔ OpenAIClient)
- Shared mutable state (blob_client in 3 places)
- Singleton pattern (StorageQueueRouter)
- Deep nesting (5 levels)
- Manual cleanup required
```

---

## 2. Proposed Functional Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Application                  │
│                    (Dependency Injection)               │
└───────────────┬─────────────────────────────────────────┘
                │
    ┌───────────┼───────────┐
    │           │           │
    ▼           ▼           ▼
┌────────┐  ┌────────┐  ┌────────────┐
│Diagnos-│  │Process-│  │StorageQueue│
│tics    │  │ing     │  │Handler     │
│Handler │  │Handler │  │(Stateless) │
└────────┘  └────────┘  └─────┬──────┘
                              │
                      ┌───────▼──────────────────────┐
                      │  create_processing_context() │
                      │  [Pure Function]             │
                      │  Returns: ProcessingContext  │
                      │  (Immutable Dataclass)       │
                      └───────┬──────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ProcessingContext│
                    │ (frozen=True)   │
                    │─────────────────│
                    │• processor_id   │
                    │• blob_accessor  │
                    │• openai_config  │
                    │• queue_client   │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐  ┌──────────────┐  ┌─────────────┐
│find_topics()  │  │generate_     │  │save_article()│
│[Pure Function]│  │article()     │  │[Pure Func]   │
│               │  │[Pure Func]   │  └─────────────┘
└───────────────┘  └──────────────┘

✅ BENEFITS:
- No circular dependencies
- No shared mutable state
- No singletons
- Flat structure (2 levels max)
- Automatic cleanup via context managers
- Easy to test (just pass different functions)
```

---

## 3. Data Flow Comparison

### CURRENT (Stateful):

```
HTTP Request
    │
    ▼
┌─────────────────────────────────────────────┐
│ StorageQueueRouter.process_message()        │
│ [Singleton Instance with State]             │
│                                             │
│ self.processor = ContentProcessor()  ◄──────┼─── Stored!
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│ ContentProcessor.process_available_work()   │
│ [Instance Method with Mutable State]        │
│                                             │
│ Uses self.topic_discovery  ◄────────────────┼─── Reference
│ Uses self.article_generation  ◄─────────────┼─── Reference
│ Uses self.session_tracker  ◄────────────────┼─── Reference
│ Mutates self.session_tracker.counters ◄─────┼─── MUTATION!
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│ TopicDiscoveryService.find_topics()         │
│ [Instance Method with Shared State]         │
│                                             │
│ Uses self.blob_client  ◄────────────────────┼─── Shared!
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│ ArticleGenerationService.generate_article() │
│ [Instance Method with Nested State]         │
│                                             │
│ Uses self.openai_client  ◄──────────────────┼─── Nested
│   └─> Uses self.pricing_service  ◄──────────┼─── Deeper
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│ OpenAIClient.generate_article()             │
│ [Instance Method with Connection State]     │
│                                             │
│ Uses self.client (AsyncAzureOpenAI)  ◄──────┼─── Stateful!
│ Must call self.close() manually  ◄──────────┼─── Cleanup!
└─────────────────────────────────────────────┘

🔴 5 LEVELS DEEP, SHARED MUTABLE STATE, MANUAL CLEANUP
```

### PROPOSED (Functional):

```
HTTP Request
    │
    ▼
┌─────────────────────────────────────────────┐
│ process_request_handler()                   │
│ [Pure Function - No State]                  │
│                                             │
│ context = create_processing_context()  ◄────┼─── Fresh!
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│ process_available_work(context, ...)        │
│ [Pure Function - Immutable Params]          │
│                                             │
│ Receives context.blob_accessor  ◄───────────┼─── Injected
│ Receives context.openai_config  ◄───────────┼─── Injected
│ Returns ProcessingResult  ◄─────────────────┼─── New Object
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│ find_available_topics(blob_accessor, ...)   │
│ [Pure Function - No Side Effects]           │
│                                             │
│ Returns List[TopicMetadata]  ◄──────────────┼─── New List
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│ generate_article_from_topic(topic, config)  │
│ [Pure Function - No State]                  │
│                                             │
│ async with openai_client(config):  ◄────────┼─── Context Mgr
│     result = await generate(...)            │
│ # Automatic cleanup!  ◄─────────────────────┼─── Auto!
│                                             │
│ Returns ArticleResult  ◄────────────────────┼─── New Object
└─────────────────────────────────────────────┘

✅ 3 LEVELS MAX, NO SHARED STATE, AUTO CLEANUP
```

---

## 4. Dependency Graph

### CURRENT (Tangled):

```
                    ┌──────────────┐
            ┌──────►│SimplifiedBlob│◄────┐
            │       │Client        │     │
            │       └──────────────┘     │
            │                            │
            │                            │
┌───────────┴──────┐          ┌─────────┴────────┐
│TopicDiscovery    │          │ProcessorStorage  │
│Service           │          │Service           │
└──────────────────┘          └──────────────────┘
                                       ▲
                                       │
                                       │
                    ┌──────────────────┴───────┐
                    │ContentProcessor          │
                    │  (Holds All Services)    │
                    └──────────┬───────────────┘
                               │
                    ┌──────────▼───────────┐
                    │ArticleGeneration     │
                    │Service               │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │OpenAIClient          │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │PricingService        │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
            ┌──────►│SimplifiedBlob        │
            │       │Client (AGAIN!)       │
            │       └──────────────────────┘
            │
┌───────────┴──────┐
│MetadataGenerator │
│   (Circular!)    │
└───────┬──────────┘
        │
        │      ┌──────────────┐
        └─────►│OpenAIClient  │
               │(Circular!)   │
               └──────────────┘

🔴 CIRCULAR DEPENDENCIES
🔴 SHARED MUTABLE STATE (SimplifiedBlobClient used 3x)
🔴 5+ LEVEL NESTING
```

### PROPOSED (Clean):

```
                    ┌──────────────┐
                    │HTTP Request  │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │Request Handler│
                    └──────┬───────┘
                           │
                    ┌──────▼────────────────┐
                    │create_context()       │
                    │Returns ProcessingCtx  │
                    └──────┬────────────────┘
                           │
                           ├─────► blob_accessor
                           ├─────► openai_config
                           └─────► queue_client
                           
                    ┌──────▼────────────────┐
                    │process_work(context)  │
                    │[Pure Function]        │
                    └──────┬────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
┌───────────────┐  ┌──────────────┐  ┌──────────────┐
│find_topics()  │  │generate_     │  │save_article()│
│               │  │article()     │  │              │
│[Uses accessor]│  │[Uses config] │  │[Uses accessor]│
└───────────────┘  └──────────────┘  └──────────────┘

✅ NO CIRCULAR DEPENDENCIES
✅ NO SHARED STATE (each function gets what it needs)
✅ FLAT STRUCTURE (2 levels max)
✅ EASY TO TEST (mock individual functions)
```

---

## 5. State Management Comparison

### CURRENT (Mutable State Everywhere):

```
┌─────────────────────────────────────────────┐
│ ContentProcessor Instance                   │
│                                             │
│ processor_id = "abc123"          ◄──────────┼─── Mutable
│ session_id = "xyz789"            ◄──────────┼─── Mutable
│                                             │
│ session_tracker:                            │
│   ├─ topics_processed = 0        ◄──────────┼─── MUTATED!
│   ├─ topics_failed = 0           ◄──────────┼─── MUTATED!
│   ├─ total_cost = 0.0            ◄──────────┼─── MUTATED!
│   └─ session_start = datetime    ◄──────────┼─── Mutable
│                                             │
│ blob_client:                                │
│   ├─ (shared reference)          ◄──────────┼─── SHARED!
│   └─ connection_string           ◄──────────┼─── Mutable
│                                             │
│ openai_client:                              │
│   ├─ client = AsyncAzureOpenAI   ◄──────────┼─── Stateful!
│   └─ endpoint = "..."            ◄──────────┼─── Mutable
│                                             │
└─────────────────────────────────────────────┘

        ▼ CALLED FROM MULTIPLE THREADS ▼

┌─────────────────────────────────────────────┐
│ process_available_work()                    │
│                                             │
│ self.session_tracker.topics_processed += 1  │◄─ RACE CONDITION!
│ self.session_tracker.total_cost += cost     │◄─ RACE CONDITION!
│                                             │
└─────────────────────────────────────────────┘

🔴 MUTABLE STATE → RACE CONDITIONS
🔴 SHARED REFERENCES → UNPREDICTABLE BEHAVIOR
🔴 MANUAL TRACKING → HARD TO DEBUG
```

### PROPOSED (Immutable State):

```
┌─────────────────────────────────────────────┐
│ ProcessingContext (frozen dataclass)        │
│                                             │
│ processor_id: str = "abc123"     ◄──────────┼─── IMMUTABLE
│ openai_config: OpenAIConfig      ◄──────────┼─── FROZEN
│ blob_accessor: BlobAccessor      ◄──────────┼─── FUNCTIONS
│ queue_client: QueueClient        ◄──────────┼─── FUNCTIONS
│                                             │
└─────────────────────────────────────────────┘

        ▼ PASSED TO PURE FUNCTIONS ▼

┌─────────────────────────────────────────────┐
│ process_available_work(context, ...)        │
│                                             │
│ # No mutation!                              │
│ result = ProcessingResult(                  │
│     topics_processed=5,          ◄──────────┼─── NEW OBJECT
│     total_cost=0.123,            ◄──────────┼─── NEW OBJECT
│     processing_time=12.3         ◄──────────┼─── NEW OBJECT
│ )                                           │
│ return result                    ◄──────────┼─── RETURN NEW
│                                             │
└─────────────────────────────────────────────┘

        ▼ CALLER AGGREGATES RESULTS ▼

┌─────────────────────────────────────────────┐
│ Request Handler                             │
│                                             │
│ results = []                                │
│ for batch in batches:                       │
│     result = await process_work(context)    │
│     results.append(result)       ◄──────────┼─── COLLECT
│                                             │
│ total_metrics = aggregate(results)◄─────────┼─── AGGREGATE
│                                             │
└─────────────────────────────────────────────┘

✅ NO RACE CONDITIONS (immutable)
✅ NO SHARED STATE (fresh objects)
✅ CLEAR DATA FLOW (function returns)
```

---

## 6. Testing Complexity Comparison

### CURRENT (Hard to Test):

```
┌─────────────────────────────────────────────┐
│ Test ContentProcessor.process_work()        │
│                                             │
│ # Must mock 7+ dependencies!                │
│ processor = ContentProcessor()              │
│ processor.topic_discovery = Mock()  ◄───────┼─── Mock
│ processor.article_generation = Mock() ◄─────┼─── Mock
│ processor.article_generation             │
│     .openai_client = Mock()          ◄──────┼─── Nested Mock
│ processor.article_generation             │
│     .openai_client                       │
│         .pricing_service = Mock()    ◄──────┼─── Deeper Mock
│ processor.lease_coordinator = Mock()  ◄─────┼─── Mock
│ processor.storage = Mock()           ◄──────┼─── Mock
│ processor.queue_coordinator = Mock()  ◄─────┼─── Mock
│ processor.session_tracker = Mock()   ◄──────┼─── Mock
│                                             │
│ # Must setup lifecycle                      │
│ await processor.initialize_config() ◄───────┼─── Setup
│                                             │
│ # Test                                      │
│ result = await processor.process_work()     │
│                                             │
│ # Must cleanup                              │
│ await processor.cleanup()           ◄───────┼─── Teardown
│                                             │
└─────────────────────────────────────────────┘

🔴 12+ LINES OF MOCKING
🔴 NESTED MOCK SETUP
🔴 LIFECYCLE MANAGEMENT
```

### PROPOSED (Easy to Test):

```
┌─────────────────────────────────────────────┐
│ Test process_available_work()               │
│                                             │
│ # Mock dependencies as simple functions     │
│ async def mock_find_topics(...):            │
│     return [TopicMetadata(...)]  ◄──────────┼─── Simple!
│                                             │
│ async def mock_generate_article(...):       │
│     return ArticleResult(...)    ◄──────────┼─── Simple!
│                                             │
│ # Create context with mocks                 │
│ context = ProcessingContext(                │
│     blob_accessor=mock_find_topics,◄────────┼─── Inject
│     openai_config=mock_config,   ◄──────────┼─── Inject
│     processor_id="test-123"                 │
│ )                                           │
│                                             │
│ # Test - just call the function             │
│ result = await process_available_work(      │
│     context=context,                        │
│     batch_size=5                            │
│ )                                           │
│                                             │
│ # Assert - no cleanup needed!               │
│ assert result.topics_processed == 5         │
│                                             │
└─────────────────────────────────────────────┘

✅ 6 LINES OF MOCKING (vs 12+)
✅ SIMPLE FUNCTION MOCKS (no nesting)
✅ NO LIFECYCLE MANAGEMENT
✅ NO CLEANUP NEEDED
```

---

## 7. Refactoring Roadmap

```
┌─────────────────────────────────────────────────────────┐
│ PHASE 1: Extract Pure Functions (Weeks 1-2)            │
│                                                         │
│ TopicConversionService  ──┐                            │
│ (Already stateless)       │                            │
│                           ▼                            │
│                    functional/                          │
│                    topic_conversion.py                  │
│                    ✅ Pure functions                    │
│                                                         │
│ PricingService.calc_cost()──┐                          │
│                              ▼                          │
│                    functional/pricing.py                │
│                    ✅ Cost calculation logic            │
│                                                         │
│ MetadataGenerator.generate_slug()──┐                   │
│                                     ▼                   │
│                    functional/metadata.py               │
│                    ✅ String transformations            │
│                                                         │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 2: Replace Client Classes (Weeks 3-4)            │
│                                                         │
│ OpenAIClient (class)  ──┐                              │
│                         │                              │
│                         ▼                              │
│              functional/openai_integration.py          │
│              ✅ Async context managers                 │
│              ✅ OpenAIConfig frozen dataclass          │
│              ✅ Pure API functions                     │
│                                                         │
│ SimplifiedBlobClient ──┐                               │
│ (Already mostly good)  │                               │
│                        ▼                               │
│              Remove singleton pattern                   │
│              ✅ Use FastAPI Depends()                  │
│                                                         │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 3: Decompose ContentProcessor (Weeks 5-6)        │
│                                                         │
│ ContentProcessor.process_work() ──┐                    │
│                                    │                    │
│                                    ▼                    │
│              functional/orchestration.py                │
│              ✅ Pure function workflows                │
│              ✅ Dependency injection                   │
│              ✅ Immutable context                      │
│                                                         │
│ Delete processor.py                                     │
│              ✅ Remove all service classes             │
│              ✅ Move to pure functions                 │
│                                                         │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 4: Refactor Endpoints (Week 7)                   │
│                                                         │
│ StorageQueueRouter (singleton) ──┐                     │
│                                   │                     │
│                                   ▼                     │
│              endpoints/storage_queue.py                 │
│              ✅ Stateless handler                      │
│              ✅ FastAPI dependency injection           │
│              ✅ Request-scoped context                 │
│                                                         │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 5: Documentation & Cleanup (Week 8)              │
│                                                         │
│ • Update all docstrings (Google style)                 │
│ • Run black, isort, mypy                               │
│ • Generate API documentation                           │
│ • Write functional programming guide                   │
│ • Delete deprecated class files                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 8. Before/After Code Examples

### Example 1: Topic Processing

**BEFORE (OOP)**:
```python
class ContentProcessor:
    def __init__(self):
        self.processor_id = str(uuid4())
        self.blob_client = SimplifiedBlobClient()
        self.topic_discovery = TopicDiscoveryService(self.blob_client)
        self.article_generation = ArticleGenerationService()
        self.session_tracker = SessionTracker()
    
    async def process_available_work(self, batch_size: int):
        topics = await self.topic_discovery.find_available_topics(
            batch_size, 0.5
        )
        
        for topic in topics:
            article = await self.article_generation.generate_article(topic)
            self.session_tracker.topics_processed += 1  # Mutation!
            self.session_tracker.total_cost += article.cost  # Mutation!
        
        return self.session_tracker.get_stats()  # Returns mutable state
```

**AFTER (Functional)**:
```python
@dataclass(frozen=True)
class ProcessingContext:
    processor_id: str
    blob_accessor: Callable
    openai_config: OpenAIConfig
    
async def process_available_work(
    context: ProcessingContext,
    batch_size: int,
    priority_threshold: float
) -> ProcessingResult:
    """Pure function - no side effects."""
    topics = await find_available_topics(
        context.blob_accessor,
        batch_size,
        priority_threshold
    )
    
    results = []
    for topic in topics:
        result = await generate_article_from_topic(
            topic,
            context.openai_config
        )
        results.append(result)
    
    return aggregate_results(results)  # Returns new immutable object
```

### Example 2: OpenAI API Call

**BEFORE (OOP)**:
```python
class OpenAIClient:
    def __init__(self):
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.model = "gpt-35-turbo"
        self.client = AsyncAzureOpenAI(...)  # Stored as instance var
    
    async def generate_article(self, topic: str):
        response = await self.client.chat.completions.create(...)
        return response.choices[0].message.content
    
    async def close(self):
        await self.client.close()  # Must remember to call!

# Usage requires cleanup
client = OpenAIClient()
try:
    article = await client.generate_article("topic")
finally:
    await client.close()  # Manual cleanup!
```

**AFTER (Functional)**:
```python
@dataclass(frozen=True)
class OpenAIConfig:
    endpoint: str
    model: str
    api_version: str

@asynccontextmanager
async def openai_client(config: OpenAIConfig):
    """Automatic resource cleanup."""
    client = AsyncAzureOpenAI(
        azure_endpoint=config.endpoint,
        api_version=config.api_version
    )
    try:
        yield client
    finally:
        await client.close()  # Automatic cleanup!

async def generate_article(
    config: OpenAIConfig,
    topic: str
) -> str:
    """Pure function with automatic cleanup."""
    async with openai_client(config) as client:
        response = await client.chat.completions.create(
            model=config.model,
            messages=[{"role": "user", "content": topic}]
        )
        return response.choices[0].message.content
    # Cleanup happens automatically!

# Usage is simple and safe
config = OpenAIConfig(endpoint="...", model="gpt-4")
article = await generate_article(config, "topic")
# No cleanup needed!
```

---

**End of Visual Diagrams Document**
