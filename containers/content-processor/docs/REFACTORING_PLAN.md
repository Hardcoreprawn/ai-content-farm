# OpenAI Client Refactoring: OOP → Functional Programming

## Goal
Replace OOP `OpenAIClient` class with functional `openai_operations.py` + rate limiting.

## Why
- Project follows functional programming paradigm (pure functions, no classes except Pydantic models)
- `openai_operations.py` already exists with pure functions and comprehensive tests (21 tests)
- Rate limiting added with `libs/openai_rate_limiter.py` (9 tests passing)
- All 30 tests passing with functional approach

## Files to Refactor

### 1. `processor.py`
**Current**: Instantiates `OpenAIClient(rate_limiter=rate_limiter)`
**Change to**: Use functional operations with rate limiter passed as parameter

### 2. `services/article_generation.py`
**Current**: Instantiates `OpenAIClient()` and calls methods
**Change to**: Use functional operations with rate limiter

### 3. `metadata_generator.py`
**Current**: Instantiates `OpenAIClient()` and calls methods  
**Change to**: Use functional operations with rate limiter

## Functional Approach Pattern

```python
# OLD (OOP):
client = OpenAIClient(rate_limiter=limiter)
content, cost, tokens = await client.generate_article(title="...", ...)

# NEW (Functional):
from openai_operations import create_openai_client, generate_article_content
from libs.openai_rate_limiter import call_with_rate_limit
from pricing_service import PricingService

openai_client = await create_openai_client(endpoint, api_version)
pricing = PricingService()

content, prompt_tokens, completion_tokens = await call_with_rate_limit(
    limiter,
    generate_article_content,
    client=openai_client,
    model_name=model,
    topic_title=title,
    research_content=research,
    target_word_count=3000
)

cost = await pricing.calculate_cost(model, prompt_tokens, completion_tokens)
```

## Steps

1. ✅ **Write tests** for rate-limited functional operations
2. ✅ **Verify tests pass** (30/30 passing)
3. 🔄 **Refactor processor.py** to use functional operations
4. 🔄 **Refactor article_generation.py** to use functional operations
5. 🔄 **Refactor metadata_generator.py** to use functional operations
6. 🔄 **Run all tests** to verify nothing broke
7. 🔄 **Deprecate/remove openai_client.py** (OOP class file)
8. 🔄 **Update any remaining imports**

## Test Coverage
- `test_openai_operations.py`: 21 tests for pure functions ✅
- `test_openai_rate_limiting.py`: 9 tests for rate limiting ✅
- Total: 30 tests covering all functionality

## Benefits
- **Consistency**: All code follows functional programming
- **Testability**: Pure functions easier to test
- **No state**: No hidden state in objects
- **Rate limiting**: Built-in from the start
- **Composability**: Functions can be easily composed
