# Phase 2: Test Update Strategy

## Current Test Issues

The functional refactoring has replaced the OOP patterns with functional ones:

### Old Pattern (OOP):
- `main.SiteGenerator` class
- `main.get_site_generator()` function  
- Instance methods like `generate_markdown()`, `generate_site()`

### New Pattern (Functional):
- `functional_config.create_generator_context()` function
- `main.get_generator_context()` dependency injection
- Pure functions: `generate_markdown_batch()`, `generate_static_site()`

## Test Update Plan

1. **Replace `get_site_generator` mocks** with `get_generator_context` mocks
2. **Mock functional modules** instead of class instances  
3. **Update test assertions** to expect functional responses
4. **Preserve test coverage** while adapting to functional architecture

## Implementation Strategy

- Update all `patch("main.get_site_generator")` to `patch("main.get_generator_context")`
- Mock functional modules: `content_processing_functions`, `html_page_generation`
- Ensure mock return values match functional signatures
- Validate that API contracts remain unchanged

This maintains 100% test coverage while validating the new functional architecture.