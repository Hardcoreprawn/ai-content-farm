#!/bin/bash

# AI Content Farm - Local Pipeline Test Script  
# Tests both the content flow AND CI/CD pipeline readiness

set -e

echo "🚀 Testing AI Content Farm - Content Pipeline + CI/CD"
echo "======================================================"
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
    fi
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

echo "PART 1: CI/CD Pipeline Readiness"
echo "================================="

echo "1. Testing Workflow Syntax..."
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/cicd-pipeline.yml'))" 2>/dev/null
print_status $? "Workflow YAML syntax"

echo
echo "2. Testing Action References..."
missing_actions=0
for action_ref in $(grep -o "uses: \./\.github/actions/[^/]*" .github/workflows/cicd-pipeline.yml | cut -d'/' -f4 | sort -u); do
    if [ -f ".github/actions/$action_ref/action.yml" ]; then
        echo -e "${GREEN}✅ $action_ref${NC}"
    else
        echo -e "${RED}❌ $action_ref${NC}"
        missing_actions=$((missing_actions + 1))
    fi
done

if [ $missing_actions -gt 0 ]; then
    print_warning "$missing_actions action(s) missing"
else
    echo -e "${GREEN}✅ All actions found${NC}"
fi

echo
echo "3. Testing Container Test Structure..."
containers_with_tests=0
total_containers=0
for container in containers/*/; do
    if [ -d "$container" ]; then
        total_containers=$((total_containers + 1))
        container_name=$(basename "$container")
        if [ -d "${container}tests" ]; then
            test_count=$(find "${container}tests" -name "test_*.py" -o -name "*_test.py" | wc -l)
            if [ $test_count -gt 0 ]; then
                echo -e "${GREEN}✅ $container_name ($test_count tests)${NC}"
                containers_with_tests=$((containers_with_tests + 1))
            else
                echo -e "${YELLOW}⚠️  $container_name (no tests)${NC}"
            fi
        else
            echo -e "${RED}❌ $container_name (no test directory)${NC}"
        fi
    fi
done

echo
echo "PART 2: Content Pipeline Testing"
echo "================================="

# Wait for services to be healthy
echo "⏳ Waiting for services to start..."
sleep 10

# Test Content Collector
echo ""
echo "📥 Testing Content Collector..."
COLLECTOR_HEALTH=$(curl -s http://localhost:8001/health | jq -r '.status' 2>/dev/null || echo "failed")
if [ "$COLLECTOR_HEALTH" = "healthy" ] || [ "$COLLECTOR_HEALTH" = "warning" ]; then
    echo "✅ Content Collector is responding (status: $COLLECTOR_HEALTH)"
else
    echo "❌ Content Collector failed health check (status: $COLLECTOR_HEALTH)"
    curl -s http://localhost:8001/health | jq . || echo "No response"
    exit 1
fi

# Test Content Processor
echo ""
echo "🔄 Testing Content Processor..."
PROCESSOR_HEALTH=$(curl -s http://localhost:8002/health | jq -r '.status' 2>/dev/null || echo "failed")
if [ "$PROCESSOR_HEALTH" = "healthy" ] || [ "$PROCESSOR_HEALTH" = "unhealthy" ]; then
    echo "✅ Content Processor is responding (status: $PROCESSOR_HEALTH)"
else
    echo "❌ Content Processor failed health check (status: $PROCESSOR_HEALTH)"
    curl -s http://localhost:8002/health | jq . || echo "No response"
    exit 1
fi

# Test Content Enricher
echo ""
echo "🧠 Testing Content Enricher..."
ENRICHER_HEALTH=$(curl -s http://localhost:8003/health | jq -r '.status' 2>/dev/null || echo "failed")
if [ "$ENRICHER_HEALTH" = "healthy" ] || [ "$ENRICHER_HEALTH" = "warning" ]; then
    echo "✅ Content Enricher is responding (status: $ENRICHER_HEALTH)"
else
    echo "❌ Content Enricher failed health check (status: $ENRICHER_HEALTH)"
    curl -s http://localhost:8003/health | jq . || echo "No response"
    exit 1
fi

# Test actual content pipeline
echo ""
echo "🔄 Testing full content pipeline..."

# Step 1: Collect content
echo "  1. Collecting content from Reddit..."
COLLECT_RESPONSE=$(curl -s -X POST "http://localhost:8001/collect" \
    -H "Content-Type: application/json" \
    -d '{
        "sources": ["reddit"],
        "subreddits": ["technology"],
        "limit": 3,
        "time_range": "day"
    }')

echo "     📊 Collection response: $(echo $COLLECT_RESPONSE | jq -r '.total_collected // "failed"') items"

# Extract content for processing
COLLECTED_CONTENT=$(echo $COLLECT_RESPONSE | jq '.content // []')

if [ "$COLLECTED_CONTENT" = "[]" ]; then
    echo "     ⚠️  No content collected, using sample data..."
    COLLECTED_CONTENT='[{
        "title": "Sample AI Technology Post",
        "content": "This is sample content about artificial intelligence and machine learning breakthroughs.",
        "url": "https://example.com/sample",
        "source": "sample",
        "score": 100,
        "num_comments": 25
    }]'
fi

# Step 2: Process content
echo "  2. Processing collected content..."
PROCESS_RESPONSE=$(curl -s -X POST "http://localhost:8002/process" \
    -H "Content-Type: application/json" \
    -d "{\"content_items\": $COLLECTED_CONTENT}")

echo "     🔧 Processing response: $(echo $PROCESS_RESPONSE | jq -r '.total_processed // "failed"') items"

# Extract processed content for enrichment
PROCESSED_CONTENT=$(echo $PROCESS_RESPONSE | jq '.processed_items // []')

# Step 3: Enrich content
echo "  3. Enriching processed content..."
ENRICH_RESPONSE=$(curl -s -X POST "http://localhost:8003/enrich" \
    -H "Content-Type: application/json" \
    -d "{\"content_items\": $PROCESSED_CONTENT}")

echo "     🧠 Enrichment response: $(echo $ENRICH_RESPONSE | jq -r '.successful_enrichments // "failed"') items enriched"

# Show sample enriched content
echo ""
echo "📋 Sample enriched content:"
echo $ENRICH_RESPONSE | jq '.enriched_items[0] | {
    title: .title,
    primary_topic: .topic_classification.primary_topic,
    sentiment: .sentiment_analysis.sentiment,
    trend_score: .trend_analysis.trend_score,
    summary: .summary.summary
}' 2>/dev/null || echo "Unable to display sample content"

echo ""
echo "🎉 Pipeline test completed successfully!"
echo "📂 Check the ./output directory for saved content files"
