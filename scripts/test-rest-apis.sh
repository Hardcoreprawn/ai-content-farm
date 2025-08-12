#!/bin/bash
# Test REST API endpoints for ContentRanker and ContentEnricher worker functions
# Usage: ./test-rest-apis.sh

STAGING_BASE="https://ai-content-staging-func.azurewebsites.net/api"

echo "🧪 Testing Worker Function REST APIs..."
echo "======================================"

# Get function keys
echo -e "\n🔑 Getting function keys..."
RANKER_KEY=$(az functionapp function keys list \
  --name ai-content-staging-func \
  --resource-group ai-content-staging-rg \
  --function-name ContentRanker \
  --query "default" -o tsv 2>/dev/null)

ENRICHER_KEY=$(az functionapp function keys list \
  --name ai-content-staging-func \
  --resource-group ai-content-staging-rg \
  --function-name ContentEnricher \
  --query "default" -o tsv 2>/dev/null)

if [ -z "$RANKER_KEY" ]; then
    echo "❌ Could not get ContentRanker key"
    exit 1
fi

if [ -z "$ENRICHER_KEY" ]; then
    echo "❌ Could not get ContentEnricher key"
    exit 1
fi

echo "✅ Got function keys"

# Test ContentRanker with valid input
echo -e "\n📊 Testing ContentRanker - Valid Input:"
curl -X POST "${STAGING_BASE}/ContentRanker?code=${RANKER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "input_blob_path": "hot-topics/20250811_135221_reddit_technology.json",
    "output_blob_path": "content-pipeline/ranked-topics/ranked_test_20250812.json"
  }' \
  -w "\nHTTP Status: %{http_code}\n" \
  -s | jq '.'

# Test ContentRanker - Missing input_blob_path
echo -e "\n📊 Testing ContentRanker - Missing Input Path:"
curl -X POST "${STAGING_BASE}/ContentRanker?code=${RANKER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"output_blob_path": "content-pipeline/ranked-topics/test.json"}' \
  -w "\nHTTP Status: %{http_code}\n" \
  -s | jq '.'

# Test ContentRanker - Invalid method
echo -e "\n📊 Testing ContentRanker - Invalid Method:"
curl -X GET "${STAGING_BASE}/ContentRanker?code=${RANKER_KEY}" \
  -w "\nHTTP Status: %{http_code}\n" \
  -s | jq '.'

# Test ContentRanker - No auth
echo -e "\n📊 Testing ContentRanker - No Authentication:"
curl -X POST "${STAGING_BASE}/ContentRanker" \
  -H "Content-Type: application/json" \
  -d '{
    "input_blob_path": "hot-topics/test.json",
    "output_blob_path": "content-pipeline/ranked-topics/test.json"
  }' \
  -w "\nHTTP Status: %{http_code}\n" \
  -s

# Test ContentEnricher with valid input (assuming ranked topics exist)
echo -e "\n🔬 Testing ContentEnricher - Valid Input:"
curl -X POST "${STAGING_BASE}/ContentEnricher?code=${ENRICHER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "input_blob_path": "content-pipeline/ranked-topics/ranked_test_20250812.json",
    "output_blob_path": "content-pipeline/enriched-topics/enriched_test_20250812.json"
  }' \
  -w "\nHTTP Status: %{http_code}\n" \
  -s | jq '.'

# Test ContentEnricher - Missing output_blob_path  
echo -e "\n🔬 Testing ContentEnricher - Missing Output Path:"
curl -X POST "${STAGING_BASE}/ContentEnricher?code=${ENRICHER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"input_blob_path": "content-pipeline/ranked-topics/test.json"}' \
  -w "\nHTTP Status: %{http_code}\n" \
  -s | jq '.'

# Test ContentEnricher - Invalid method
echo -e "\n🔬 Testing ContentEnricher - Invalid Method:"
curl -X GET "${STAGING_BASE}/ContentEnricher?code=${ENRICHER_KEY}" \
  -w "\nHTTP Status: %{http_code}\n" \
  -s | jq '.'

echo -e "\n✅ Worker Function REST API Testing Complete!"
