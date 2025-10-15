#!/bin/bash
# Check Log Analytics logs for Container Apps
# Usage: ./scripts/check-log-analytics.sh [container-name] [hours]

set -e

WORKSPACE_ID="d766c59b-dfcb-43dc-8600-3a3f2d94236e"
CONTAINER_NAME="${1:-}"
HOURS="${2:-1}"

echo "================================================"
echo "Container Apps Log Analytics Query"
echo "================================================"
echo ""

# Check if logs are available
echo "🔍 Checking if logs are being ingested..."
LOG_COUNT=$(az monitor log-analytics query \
  --workspace "$WORKSPACE_ID" \
  --analytics-query "ContainerAppConsoleLogs | where TimeGenerated > ago(24h) | count" \
  --output json | jq -r '.[0].Count')

if [ "$LOG_COUNT" -eq 0 ]; then
    echo "❌ No logs found in Log Analytics yet"
    echo ""
    echo "This is normal if the configuration was just applied."
    echo "Logs typically appear 5-10 minutes after Container App Environment update."
    echo ""
    echo "To check the current environment configuration:"
    echo "  az containerapp env show --name ai-content-prod-env --resource-group ai-content-prod-rg"
    exit 0
fi

echo "✅ Found $LOG_COUNT log entries in the last 24 hours"
echo ""

# Build the query based on parameters
if [ -n "$CONTAINER_NAME" ]; then
    QUERY="ContainerAppConsoleLogs | where TimeGenerated > ago(${HOURS}h) | where ContainerName contains '$CONTAINER_NAME' | project TimeGenerated, ContainerName, Log | order by TimeGenerated desc | take 50"
    echo "📋 Showing last 50 logs from '$CONTAINER_NAME' (last ${HOURS}h):"
else
    QUERY="ContainerAppConsoleLogs | where TimeGenerated > ago(${HOURS}h) | project TimeGenerated, ContainerName, Log | order by TimeGenerated desc | take 50"
    echo "📋 Showing last 50 logs from all containers (last ${HOURS}h):"
fi

echo ""
az monitor log-analytics query \
  --workspace "$WORKSPACE_ID" \
  --analytics-query "$QUERY" \
  --output table

echo ""
echo "================================================"
echo "To query specific containers:"
echo "  ./scripts/check-log-analytics.sh collector 2"
echo "  ./scripts/check-log-analytics.sh processor 1"
echo "  ./scripts/check-log-analytics.sh markdown-gen 4"
echo "================================================"
