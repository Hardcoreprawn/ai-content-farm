# Content Ranker

This service ranks and prioritizes enriched content based on multiple factors including engagement scores, recency, and topic relevance.

## API Endpoints

- `POST /rank` - Accept enriched content, return ranked results
- `GET /health` - Health check endpoint

## Features

- **Multi-factor ranking algorithm**: Combines engagement, recency, and topic relevance
- **Configurable weights**: Adjust ranking factors based on needs
- **Batch processing**: Handle multiple content items efficiently
- **Pure functional design**: No side effects, easy to test

## Usage

```bash
# Rank enriched content
curl -X POST "http://localhost:8004/rank" \
  -H "Content-Type: application/json" \
  -d '{"items": [...], "options": {...}}'

# Health check
curl http://localhost:8004/health
```

## Development

See the main project documentation for development setup and testing.
