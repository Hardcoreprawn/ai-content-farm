#!/bin/bash
# Telemetry Verification Script
# Verifies that Log Analytics and Application Insights are properly configured
# and receiving data from containers

set -e

echo "═══════════════════════════════════════════════════════════════"
echo "   Log Analytics & Application Insights Verification"
echo "═══════════════════════════════════════════════════════════════"
echo ""

RESOURCE_GROUP="${1:-ai-content-prod-rg}"
WORKSPACE_NAME="${2:-ai-content-prod-la}"
APPINSIGHTS_NAME="${3:-ai-content-prod-insights}"

echo "📋 Configuration:"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  Log Analytics Workspace: $WORKSPACE_NAME"
echo "  Application Insights: $APPINSIGHTS_NAME"
echo ""

# Check if resources exist
echo "🔍 Checking infrastructure..."

WORKSPACE=$(az monitor log-analytics workspace show \
  --resource-group "$RESOURCE_GROUP" \
  --workspace-name "$WORKSPACE_NAME" \
  -o json 2>/dev/null || echo "{}")

if [ "$WORKSPACE" == "{}" ]; then
  echo "❌ Log Analytics workspace not found"
  exit 1
fi
echo "✅ Log Analytics workspace found"

APPINSIGHTS=$(az monitor app-insights component show \
  --app "$APPINSIGHTS_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  -o json 2>/dev/null || echo "{}")

if [ "$APPINSIGHTS" == "{}" ]; then
  echo "❌ Application Insights not found"
  exit 1
fi
echo "✅ Application Insights found"

# Extract workspace ID and customer ID
WORKSPACE_ID=$(echo "$WORKSPACE" | jq -r '.id')
CUSTOMER_ID=$(echo "$WORKSPACE" | jq -r '.customerId')
INSTRUMENTATION_KEY=$(echo "$APPINSIGHTS" | jq -r '.instrumentationKey')

echo ""
echo "📊 Workspace Details:"
echo "  ID: $WORKSPACE_ID"
echo "  Customer ID: $CUSTOMER_ID"
echo "  Instrumentation Key: $INSTRUMENTATION_KEY"
echo ""

# Check for telemetry data
echo "📈 Checking for telemetry data..."

# Query for custom events (last 24 hours)
echo ""
echo "Querying custom events (last 24 hours)..."

QUERY='
customEvents
| where timestamp > ago(24h)
| summarize EventCount = count(),
            LastEvent = max(timestamp),
            Services = dcount(tostring(customDimensions.service_name))
| project EventCount, LastEvent, Services
'

RESULT=$(az monitor log-analytics query \
  --workspace "$WORKSPACE_ID" \
  --analytics-query "$QUERY" \
  -o json 2>/dev/null || echo "[]")

EVENT_COUNT=$(echo "$RESULT" | jq -r '.[0].EventCount // 0')

if [ "$EVENT_COUNT" -gt 0 ]; then
  echo "✅ Found $EVENT_COUNT custom events"
  echo "$RESULT" | jq '.'
else
  echo "⚠️  No custom events found in last 24 hours"
fi

# Query for traces (errors/warnings)
echo ""
echo "Querying traces and errors (last 24 hours)..."

QUERY2='
traces
| where timestamp > ago(24h)
| summarize TraceCount = count(),
            ErrorCount = countif(severityLevel > 1),
            LastTrace = max(timestamp)
| project TraceCount, ErrorCount, LastTrace
'

RESULT2=$(az monitor log-analytics query \
  --workspace "$WORKSPACE_ID" \
  --analytics-query "$QUERY2" \
  -o json 2>/dev/null || echo "[]")

TRACE_COUNT=$(echo "$RESULT2" | jq -r '.[0].TraceCount // 0')
ERROR_COUNT=$(echo "$RESULT2" | jq -r '.[0].ErrorCount // 0')

if [ "$TRACE_COUNT" -gt 0 ]; then
  echo "✅ Found $TRACE_COUNT traces ($ERROR_COUNT errors)"
  echo "$RESULT2" | jq '.'
else
  echo "⚠️  No traces found in last 24 hours"
fi

# Query for exceptions
echo ""
echo "Querying exceptions (last 24 hours)..."

QUERY3='
exceptions
| where timestamp > ago(24h)
| summarize ExceptionCount = count(),
            UniqueExceptions = dcount(outerMessage),
            LastException = max(timestamp)
| project ExceptionCount, UniqueExceptions, LastException
'

RESULT3=$(az monitor log-analytics query \
  --workspace "$WORKSPACE_ID" \
  --analytics-query "$QUERY3" \
  -o json 2>/dev/null || echo "[]")

EXCEPTION_COUNT=$(echo "$RESULT3" | jq -r '.[0].ExceptionCount // 0')

if [ "$EXCEPTION_COUNT" -gt 0 ]; then
  echo "✅ Found $EXCEPTION_COUNT exceptions"
  echo "$RESULT3" | jq '.'
else
  echo "ℹ️  No exceptions in last 24 hours (good!)"
fi

# Check container app environment variables
echo ""
echo "🐳 Checking container environment..."

CONTAINERS=("ai-content-prod-collector" "ai-content-prod-processor" "ai-content-prod-generator")

for CONTAINER in "${CONTAINERS[@]}"; do
  echo ""
  echo "  Checking $CONTAINER..."

  ENV_VARS=$(az containerapp show \
    --name "$CONTAINER" \
    --resource-group "$RESOURCE_GROUP" \
    -o json 2>/dev/null | jq '.properties.template.containers[0].env' || echo "[]")

  HAS_CONNECTION_STRING=$(echo "$ENV_VARS" | jq 'any(.name == "APPLICATIONINSIGHTS_CONNECTION_STRING")')

  if [ "$HAS_CONNECTION_STRING" == "true" ]; then
    echo "    ✅ Has APPLICATIONINSIGHTS_CONNECTION_STRING"
  else
    echo "    ❌ Missing APPLICATIONINSIGHTS_CONNECTION_STRING"
  fi
done

# Summary
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "📊 Summary"
echo "═══════════════════════════════════════════════════════════════"
echo ""

if [ "$EVENT_COUNT" -gt 0 ] || [ "$TRACE_COUNT" -gt 0 ]; then
  echo "✅ Telemetry is WORKING - data is being collected"
  echo ""
  echo "   Custom Events: $EVENT_COUNT"
  echo "   Traces: $TRACE_COUNT"
  echo "   Exceptions: $EXCEPTION_COUNT"
else
  echo "⚠️  No telemetry data found"
  echo ""
  echo "Common causes:"
  echo "  1. Containers just restarted (wait 2-5 minutes)"
  echo "  2. Missing azure-monitor-opentelemetry dependency"
  echo "  3. No requests hitting the containers yet"
  echo "  4. Data ingestion delay (check again in 5 minutes)"
  echo ""
  echo "To debug:"
  echo "  - Check container logs: az containerapp logs show --name <app-name> --resource-group $RESOURCE_GROUP"
  echo "  - Verify dependency: grep azure-monitor-opentelemetry containers/*/requirements.txt"
  echo "  - Test locally: python -c \"from azure.monitor.opentelemetry import configure_azure_monitor\""
fi

echo ""
