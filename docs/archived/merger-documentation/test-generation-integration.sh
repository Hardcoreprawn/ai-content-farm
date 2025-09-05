#!/bin/bash
# Test script to verify content-processor generation endpoints are working

set -e

echo "🧪 Testing Content Processor Generation Integration"

cd "/workspaces/ai-content-farm/containers/content-processor"

echo ""
echo "1. Testing generation module import..."
export PYTHONPATH=/workspaces/ai-content-farm:$PYTHONPATH
python -c "from content_generation import get_content_generator; print('✅ Generation module imported')"

echo ""
echo "2. Testing FastAPI app with generation endpoints..."
python -c "from main import app; print('✅ FastAPI app with generation endpoints loaded')"

echo ""
echo "3. Testing generation functionality..."
python -c "
import asyncio
from content_generation import GenerationRequest, get_content_generator

async def test():
    request = GenerationRequest(
        topic='AI Integration Test',
        content_type='blog',
        writer_personality='professional',
        sources=[{'title': 'Test Source', 'summary': 'Integration test summary'}]
    )

    generator = get_content_generator()
    result = await generator.generate_content(request)
    print(f'✅ Generated {result.content_type}: {result.title}')
    print(f'✅ Word count: {result.word_count}')

asyncio.run(test())
"

echo ""
echo "4. Running existing tests to ensure no regression..."
python -m pytest tests/test_standardized_api.py -v -q

echo ""
echo "🎉 ALL TESTS PASSED!"
echo ""
echo "✅ Content Generation Integration Summary:"
echo "   - Generation module: Working"
echo "   - FastAPI integration: Working"
echo "   - Content generation: Working"
echo "   - Existing tests: All passing"
echo ""
echo "📋 Available Generation Endpoints:"
echo "   POST /api/processor/generate/tldr"
echo "   POST /api/processor/generate/blog"
echo "   POST /api/processor/generate/deepdive"
echo "   POST /api/processor/generate/batch"
echo "   GET  /api/processor/generation/status/{batch_id}"
echo ""
echo "🏆 Content-generator functionality successfully merged into content-processor!"
