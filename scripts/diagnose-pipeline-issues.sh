#!/bin/bash
# Pipeline Health Diagnostics
# Checks for known issues: duplicate processing, 429 errors, missing triggers
# Usage: ./diagnose-pipeline-issues.sh

set -euo pipefail

RESOURCE_GROUP="${RESOURCE_GROUP:-ai-content-prod-rg}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  Pipeline Health Diagnostics                          ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""

# Check 1: Queue Authentication
echo -e "${BLUE}[1/6] Checking Queue Access Permissions${NC}"
STORAGE_ACCOUNT=$(az storage account list \
    --resource-group "$RESOURCE_GROUP" \
    --query "[0].name" -o tsv 2>/dev/null)

if [[ -z "$STORAGE_ACCOUNT" ]]; then
    echo -e "${RED}  ❌ Could not find storage account${NC}"
else
    echo -e "${GREEN}  ✓ Storage account: $STORAGE_ACCOUNT${NC}"

    # Try to get connection string
    CONN_STR=$(az storage account show-connection-string \
        --name "$STORAGE_ACCOUNT" \
        --resource-group "$RESOURCE_GROUP" \
        --query "connectionString" -o tsv 2>/dev/null || echo "")

    if [[ -z "$CONN_STR" ]]; then
        echo -e "${RED}  ❌ Cannot get connection string - insufficient permissions${NC}"
        echo -e "${YELLOW}  💡 Grant 'Storage Account Contributor' role:${NC}"
        echo -e "${YELLOW}     az role assignment create --assignee <your-email> \\${NC}"
        echo -e "${YELLOW}       --role 'Storage Account Contributor' \\${NC}"
        echo -e "${YELLOW}       --scope /subscriptions/<sub>/resourceGroups/$RESOURCE_GROUP${NC}"
    else
        echo -e "${GREEN}  ✓ Connection string available${NC}"

        # Test queue access
        QUEUE_COUNT=$(az storage queue list \
            --connection-string "$CONN_STR" \
            --query "length(@)" -o tsv 2>/dev/null || echo "0")

        if [[ "$QUEUE_COUNT" -gt 0 ]]; then
            echo -e "${GREEN}  ✓ Can access $QUEUE_COUNT queues${NC}"
        else
            echo -e "${YELLOW}  ⚠️  Found 0 queues - unexpected${NC}"
        fi
    fi
fi
echo ""

# Check 2: Queue Message Counts and Dead Letters
echo -e "${BLUE}[2/6] Checking Queue Depths and Stuck Messages${NC}"
if [[ -n "$CONN_STR" ]]; then
    for queue in content-collection-requests content-processing-requests markdown-generation-requests site-publishing-requests; do
        COUNT=$(az storage message peek \
            --queue-name "$queue" \
            --connection-string "$CONN_STR" \
            --num-messages 32 \
            --query "length(@)" -o tsv 2>/dev/null || echo "0")

        if [[ "$COUNT" -eq 0 ]]; then
            echo -e "${GREEN}  ✓ $queue: ${COUNT} messages${NC}"
        elif [[ "$COUNT" -lt 5 ]]; then
            echo -e "${YELLOW}  ⚠️  $queue: ${COUNT} messages${NC}"
        else
            echo -e "${RED}  ❌ $queue: ${COUNT} messages (possible backlog!)${NC}"

            # Check for duplicate/stuck messages
            MESSAGES=$(az storage message peek \
                --queue-name "$queue" \
                --connection-string "$CONN_STR" \
                --num-messages 5 \
                --query "[].{id:id, dequeueCount:dequeueCount, insertionTime:insertionTime}" \
                -o json 2>/dev/null || echo "[]")

            echo "$MESSAGES" | jq -r '.[] | "      Message: \(.id) - Attempts: \(.dequeueCount) - Age: \(.insertionTime)"'
        fi
    done
else
    echo -e "${YELLOW}  ⚠️  Skipped - no connection string${NC}"
fi
echo ""

# Check 3: Container App Scaling Configuration
echo -e "${BLUE}[3/6] Checking KEDA Scaling Configuration${NC}"
for app in content-collector content-processor markdown-generator site-publisher; do
    echo -e "${CYAN}  Checking $app...${NC}"

    # Get scale rules
    SCALE_INFO=$(az containerapp show \
        --name "$app" \
        --resource-group "$RESOURCE_GROUP" \
        --query "{minReplicas:properties.template.scale.minReplicas, maxReplicas:properties.template.scale.maxReplicas, rules:properties.template.scale.rules}" \
        -o json 2>/dev/null || echo "{}")

    MIN_REPLICAS=$(echo "$SCALE_INFO" | jq -r '.minReplicas // "N/A"')
    MAX_REPLICAS=$(echo "$SCALE_INFO" | jq -r '.maxReplicas // "N/A"')
    QUEUE_LENGTH=$(echo "$SCALE_INFO" | jq -r '.rules[0].custom.metadata.queueLength // "N/A"')

    echo -e "    Min: $MIN_REPLICAS, Max: $MAX_REPLICAS, QueueLength: $QUEUE_LENGTH"

    # Warnings
    if [[ "$MIN_REPLICAS" != "0" ]]; then
        echo -e "${YELLOW}    ⚠️  Min replicas > 0 increases costs${NC}"
    fi

    if [[ "$QUEUE_LENGTH" =~ ^[0-9]+$ ]] && [[ "$QUEUE_LENGTH" -gt 10 ]]; then
        echo -e "${YELLOW}    ⚠️  Queue length threshold high ($QUEUE_LENGTH) - may delay scale-up${NC}"
    fi
done
echo ""

# Check 4: Recent Error Rates (429 errors, etc.)
echo -e "${BLUE}[4/6] Checking for OpenAI 429 Rate Limit Errors${NC}"

# Get Application Insights workspace ID
APP_INSIGHTS=$(az monitor app-insights component list \
    --resource-group "$RESOURCE_GROUP" \
    --query "[0].name" -o tsv 2>/dev/null || echo "")

if [[ -z "$APP_INSIGHTS" ]]; then
    echo -e "${YELLOW}  ⚠️  No Application Insights found - cannot check error rates${NC}"
else
    echo -e "${GREEN}  ✓ Application Insights: $APP_INSIGHTS${NC}"

    # Query for 429 errors in last 24 hours
    QUERY='requests
    | where timestamp > ago(24h)
    | where resultCode == "429" or customDimensions contains "429"
    | summarize count() by bin(timestamp, 1h), name
    | order by timestamp desc
    | take 10'

    ERRORS=$(az monitor app-insights query \
        --app "$APP_INSIGHTS" \
        --resource-group "$RESOURCE_GROUP" \
        --analytics-query "$QUERY" \
        --query "tables[0].rows" -o json 2>/dev/null || echo "[]")

    ERROR_COUNT=$(echo "$ERRORS" | jq 'length')

    if [[ "$ERROR_COUNT" -eq 0 ]]; then
        echo -e "${GREEN}  ✓ No 429 errors in last 24 hours${NC}"
    else
        echo -e "${RED}  ❌ Found $ERROR_COUNT instances of 429 errors:${NC}"
        echo "$ERRORS" | jq -r '.[] | "      \(.[0]) - \(.[1]): \(.[2]) errors"'
        echo -e "${YELLOW}  💡 Recommendation: Implement rate limiting and reduce concurrency${NC}"
    fi
fi
echo ""

# Check 5: Site Publisher Trigger Chain
echo -e "${BLUE}[5/6] Checking Site Publisher Trigger Chain${NC}"
echo -e "${CYAN}  Verifying markdown-generator → site-publisher connection...${NC}"

# Check markdown-generator environment variables
MD_ENV=$(az containerapp show \
    --name "markdown-generator" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.template.containers[0].env" \
    -o json 2>/dev/null || echo "[]")

SITE_QUEUE_CONFIGURED=$(echo "$MD_ENV" | jq -r '.[] | select(.name == "SITE_PUBLISHING_QUEUE_NAME") | .value')

if [[ -z "$SITE_QUEUE_CONFIGURED" ]]; then
    echo -e "${RED}  ❌ markdown-generator missing SITE_PUBLISHING_QUEUE_NAME env var${NC}"
    echo -e "${YELLOW}  💡 Add environment variable in Terraform or Azure Portal${NC}"
else
    echo -e "${GREEN}  ✓ markdown-generator configured to send to: $SITE_QUEUE_CONFIGURED${NC}"
fi

# Check if site-publisher has messages
if [[ -n "$CONN_STR" ]]; then
    PUBLISHER_MSGS=$(az storage message peek \
        --queue-name "site-publishing-requests" \
        --connection-string "$CONN_STR" \
        --num-messages 1 \
        --query "length(@)" -o tsv 2>/dev/null || echo "0")

    if [[ "$PUBLISHER_MSGS" -gt 0 ]]; then
        echo -e "${YELLOW}  ⚠️  site-publishing-requests has $PUBLISHER_MSGS messages waiting${NC}"
        echo -e "${YELLOW}  💡 Check if site-publisher is scaled up and processing${NC}"
    else
        echo -e "${BLUE}  ℹ️  No messages in site-publishing-requests queue${NC}"
    fi
fi

# Check site-publisher logs for recent activity
echo -e "${CYAN}  Checking recent site-publisher activity...${NC}"
RECENT_LOGS=$(az containerapp logs show \
    --name "site-publisher" \
    --resource-group "$RESOURCE_GROUP" \
    --tail 10 \
    --query "[].{time:TimeGenerated, msg:Log_s}" \
    -o json 2>/dev/null || echo "[]")

LOG_COUNT=$(echo "$RECENT_LOGS" | jq 'length')

if [[ "$LOG_COUNT" -eq 0 ]]; then
    echo -e "${YELLOW}  ⚠️  No recent site-publisher logs - may not have run recently${NC}"
else
    echo -e "${GREEN}  ✓ Found $LOG_COUNT recent log entries${NC}"
    LAST_RUN=$(echo "$RECENT_LOGS" | jq -r '.[0].time')
    echo -e "    Last activity: $LAST_RUN"
fi
echo ""

# Check 6: Cooldown Period Analysis
echo -e "${BLUE}[6/6] Checking Cooldown Period Configuration${NC}"
echo -e "${CYAN}  NOTE: Cooldown periods configured via Azure CLI (not in Terraform)${NC}"
echo -e "${CYAN}  Expected values from config comments:${NC}"
echo -e "    content-collector: 45s"
echo -e "    content-processor: 60s"
echo -e "    markdown-generator: 45s"
echo -e "    site-publisher: 300s (5 minutes - may be too long)"
echo ""
echo -e "${YELLOW}  💡 Recommendation: Reduce site-publisher cooldown to 60-90s${NC}"
echo -e "${YELLOW}     Long cooldown delays final publication unnecessarily${NC}"
echo ""

# Summary
echo -e "${CYAN}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  Diagnostic Summary                                    ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${YELLOW}🔍 Action Items:${NC}"
echo ""
echo -e "1. ${YELLOW}Fix Queue Access:${NC} Grant 'Storage Account Contributor' role"
echo -e "2. ${YELLOW}Fix Message Reprocessing:${NC} Increase visibility timeout to 300s"
echo -e "3. ${YELLOW}Fix Rate Limiting:${NC} Implement rate limiter for OpenAI calls"
echo -e "4. ${YELLOW}Fix Site Publisher:${NC} Verify trigger chain and reduce cooldown"
echo -e "5. ${YELLOW}Monitor Execution Windows:${NC} Use cron-aware monitoring script"
echo ""

echo -e "${BLUE}📚 See docs/PIPELINE_ISSUES_AND_FIXES.md for detailed fixes${NC}"
echo ""
