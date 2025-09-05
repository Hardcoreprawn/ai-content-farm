# Content Generator Container

A containerized microservice that generates original articles from ranked topics in the AI Content Farm pipeline, with multiple writer personalities and intelligent content verification.

## 🎯 Purpose

Transform ranked topics into original, high-quality written content with:

- **TL;DR Articles** (200-400 words): Quick, focused pieces for busy readers
- **Blog Articles** (600-1000 words): Comprehensive coverage when sufficient source material exists
- **Deep Dives** (1500-2500 words): Analytical pieces for substantial topics only
- **Multiple Writer Personalities**: Varying voices to keep content engaging
- **Source Verification**: Real-time checking that sources are accessible and legitimate

## � Writer Personalities

- **Professional**: Authoritative, balanced, fact-focused business tone
- **Analytical**: Data-driven, technical, research-oriented perspective
- **Casual**: Conversational, accessible, everyday language
- **Expert**: Deep technical knowledge, industry insider perspective
- **Skeptical**: Critical thinking, question assumptions, devil's advocate
- **Enthusiast**: Excited, optimistic, focused on possibilities

## 🔍 Content Intelligence

### Adaptive Generation
- Only generates longer content when sufficient source material exists
- Automatically determines if a topic warrants blog or deep-dive treatment
- Falls back to tl;dr format for topics with limited source coverage

### Source Verification
- Real-time verification that source URLs are accessible
- Fact-checking notes included in output
- Explicit source attribution in generated content
- Verification status tracking (verified/partial/unverified)

## 📡 API Endpoints

### Content Generation
```http
POST /generate/tldr?writer_personality=professional
POST /generate/blog?writer_personality=analytical
POST /generate/deepdive?writer_personality=expert
POST /generate/batch
```

### Status & Management
```http
GET /health
GET /status
GET /generation/status/{batch_id}
```

## 🚀 Quick Start

```bash
# Build container
cd containers/content-generator
docker build -t content-generator .

# Run locally
docker run -p 10005:8000 content-generator

# Test health endpoint
curl http://localhost:10005/health
```

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test types
python -m pytest tests/test_service.py -v       # Content generation tests
python -m pytest tests/test_integration.py -v  # Pipeline integration tests
```

## 📊 Pipeline Data Flow

### Input (from Content Ranker)
```json
{
  "batch_id": "ranker_20250819_123000_batch_001",
  "ranked_topics": [
    {
      "topic": "AI Infrastructure Investment",
      "sources": [...],
      "rank": 1,
      "ai_score": 0.891
    }
  ]
}
```

### Output (to Markdown Generator)
```json
{
  "batch_id": "generator_20250819_123030_batch_001", 
  "generated_content": [
    {
      "topic": "AI Infrastructure Investment",
      "content_type": "shortform",
      "title": "UK's £2bn AI Investment: Game Changer or Catch-Up?",
      "content": "...",
      "word_count": 742,
      "generation_time": "2025-08-19T12:30:30Z"
    }
  ]
}
```

## 🔧 Configuration

### Environment Variables
```bash
OPENAI_API_KEY=your_openai_key
CLAUDE_API_KEY=your_anthropic_key
BLOB_CONNECTION_STRING=your_azure_storage
RANKED_CONTENT_CONTAINER=ranked-content
GENERATED_CONTENT_CONTAINER=generated-content
```

### Content Templates
- `templates/shortform.prompt` - 500-800 word article template
- `templates/briefing.prompt` - 3000 word comprehensive template  
- `templates/deepdive.prompt` - 5000+ word analytical template

## ⚡ Performance & Reliability

- **Concurrent Generation**: Process multiple articles simultaneously
- **Quality Gates**: Content validation before output
- **Retry Logic**: Handle API failures gracefully
- **Cost Optimization**: Intelligent model selection (GPT-3.5 vs GPT-4)

## 🔗 Integration Points

### Reads From
- **Blob Container**: `ranked-content`
- **Blob Pattern**: `ranker_{timestamp}_{batch_id}.json`

### Writes To  
- **Blob Container**: `generated-content`
- **Blob Pattern**: `generator_{timestamp}_{content_type}_{batch_id}.json`

### Triggers
- **Event**: New blob in `ranked-content` container
- **Notification**: Blob storage event triggers generation
- **Downstream**: Writes trigger Markdown Generator

## 📁 Files Overview

```
content-generator/
├── main.py                 # FastAPI application entry point
├── service_logic.py        # Core content generation logic
├── models.py              # Pydantic models for requests/responses
├── config.py              # Configuration management
├── generators/            # Content generation modules
│   ├── shortform.py       # 500-800 word article generator
│   ├── briefing.py        # 3000 word briefing generator
│   └── deepdive.py        # 5000+ word deep dive generator
├── templates/             # AI prompts and content templates
├── tests/                 # Comprehensive test suite
├── requirements.txt       # Python dependencies
├── Dockerfile             # Container configuration
└── README.md             # This file
```

## 🎯 Current Status: **Phase 2F-bis - In Development**

- ⚠️ **Status**: New container - implementation needed
- 🎯 **Goal**: Bridge the gap between topic curation and content delivery
- 📝 **Next**: Implement core content generation logic with AI integration

---

**Part of AI Content Farm Pipeline** - Automated content generation for personal curation platform
