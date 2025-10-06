#!/bin/bash
# Check current state before clean rebuild

echo "📊 Current State Analysis"
echo "========================="
echo ""

# Static site articles
echo "Static Site Articles:"
STATIC_COUNT=$(az storage blob list \
    --account-name aicontentprodstkwakpx \
    --container-name '$web' \
    --prefix "articles/" \
    --auth-mode login \
    --query "length([])" -o tsv 2>&1 | grep -v "WARNING")

echo "  Total articles: $STATIC_COUNT"
echo ""

# Check for legacy "article-" prefix
LEGACY_COUNT=$(az storage blob list \
    --account-name aicontentprodstkwakpx \
    --container-name '$web' \
    --prefix "articles/article-" \
    --auth-mode login \
    --query "length([])" -o tsv 2>&1 | grep -v "WARNING")

echo "  Legacy 'article-' prefixed: $LEGACY_COUNT"
echo ""

# Check for proper date format
echo "Sample filenames (first 10):"
az storage blob list \
    --account-name aicontentprodstkwakpx \
    --container-name '$web' \
    --prefix "articles/" \
    --auth-mode login \
    --query "[0:10].name" -o tsv 2>&1 | grep -v "WARNING"

echo ""

# Check for non-ASCII filenames (Vietnamese, Japanese, etc.)
echo "Checking for non-English filenames..."
NON_ASCII=$(az storage blob list \
    --account-name aicontentprodstkwakpx \
    --container-name '$web' \
    --prefix "articles/" \
    --auth-mode login \
    --query "[].name" -o tsv 2>&1 | grep -v "WARNING" | grep -P '[^\x00-\x7F]' | wc -l)

echo "  Non-ASCII filenames found: $NON_ASCII"
if [ "$NON_ASCII" -gt 0 ]; then
    echo "  Examples:"
    az storage blob list \
        --account-name aicontentprodstkwakpx \
        --container-name '$web' \
        --prefix "articles/" \
        --auth-mode login \
        --query "[].name" -o tsv 2>&1 | grep -v "WARNING" | grep -P '[^\x00-\x7F]' | head -3
fi

echo ""

# Processed content
echo "Processed Content:"
PROCESSED_COUNT=$(az storage blob list \
    --account-name aicontentprodstkwakpx \
    --container-name processed-content \
    --auth-mode login \
    --query "length([])" -o tsv 2>&1 | grep -v "WARNING")

echo "  Total processed articles: $PROCESSED_COUNT"
echo ""

# Collected content
echo "Collected Content:"
COLLECTED_COUNT=$(az storage blob list \
    --account-name aicontentprodstkwakpx \
    --container-name collected-content \
    --auth-mode login \
    --query "length([])" -o tsv 2>&1 | grep -v "WARNING")

echo "  Total collected items: $COLLECTED_COUNT"
echo ""

echo "========================="
echo "Summary:"
echo "  📄 Static articles: $STATIC_COUNT (including $LEGACY_COUNT legacy)"
echo "  🔄 Processed: $PROCESSED_COUNT"
echo "  📦 Collected: $COLLECTED_COUNT"
echo "  ⚠️  Non-ASCII filenames: $NON_ASCII"
echo ""

if [ "$LEGACY_COUNT" -gt 0 ] || [ "$NON_ASCII" -gt 0 ]; then
    echo "⚠️  Issues detected - clean rebuild recommended!"
else
    echo "✓ No obvious issues found"
fi
