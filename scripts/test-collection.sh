#!/bin/bash

# Simple test script for pre-baked collection templates
# Demonstrates how easy it is to trigger collections with templates

COLLECTOR_URL="${1:-http://localhost:8001}"
TEMPLATE="${2:-quick-pulse}"

echo "🚀 Testing Collection with Template: $TEMPLATE"
echo "📍 Target URL: $COLLECTOR_URL"

# Load the template
TEMPLATE_FILE="sample_data/collection-templates/${TEMPLATE}.json"

if [ ! -f "$TEMPLATE_FILE" ]; then
    echo "❌ Template file not found: $TEMPLATE_FILE"
    echo "Available templates:"
    ls sample_data/collection-templates/*.json | sed 's/.*\//- /' | sed 's/\.json$//'
    exit 1
fi

echo "📄 Loading template: $TEMPLATE_FILE"

# Extract just the collection_request part (the actual API payload)
COLLECTION_REQUEST=$(cat "$TEMPLATE_FILE" | jq '.collection_request')

echo "🎯 Collection Request:"
echo "$COLLECTION_REQUEST" | jq '.'

echo ""
echo "🚀 Triggering collection..."

# Send to content-collector
curl -X POST "${COLLECTOR_URL}/collections" \
  -H "Content-Type: application/json" \
  -d "$COLLECTION_REQUEST" \
  --verbose

echo ""
echo "✅ Collection triggered!"
echo ""
echo "💡 Usage examples:"
echo "  ./test-collection.sh http://localhost:8001 technology-comprehensive"
echo "  ./test-collection.sh https://your-collector-url.azurecontainerapps.io ai-ml-focused"
echo "  ./test-collection.sh http://localhost:8001 science-research"
