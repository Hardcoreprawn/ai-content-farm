#!/bin/bash
# Test the complete scheduler workflow end-to-end
# This script validates the Logic App scheduler integration with content-collector

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
RESOURCE_GROUP="${RESOURCE_GROUP:-ai-content-dev-rg}"
LOGIC_APP_NAME="${LOGIC_APP_NAME:-ai-content-dev-scheduler}"
KEY_VAULT_NAME="${KEY_VAULT_NAME:-}"
STORAGE_ACCOUNT="${STORAGE_ACCOUNT:-}"

echo -e "${BLUE}🧪 Testing Scheduler End-to-End Workflow...${NC}"

# Function to check if Azure CLI is logged in
check_azure_login() {
    if ! az account show >/dev/null 2>&1; then
        echo -e "${RED}❌ Not logged into Azure. Please run 'az login' first.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Azure CLI authenticated${NC}"
}

# Function to get resource names dynamically
get_resource_names() {
    # Get Logic App name
    local logic_app
    logic_app=$(az logic workflow list --resource-group "$RESOURCE_GROUP" --query "[?contains(name, 'scheduler')].name" -o tsv 2>/dev/null | head -1)
    if [[ -n "$logic_app" ]]; then
        LOGIC_APP_NAME="$logic_app"
        echo -e "${GREEN}✅ Found Logic App: $LOGIC_APP_NAME${NC}"
    else
        echo -e "${YELLOW}⚠️  Using default Logic App name: $LOGIC_APP_NAME${NC}"
    fi

    # Get Key Vault name
    local kv_name
    kv_name=$(az keyvault list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv 2>/dev/null)
    if [[ -n "$kv_name" ]]; then
        KEY_VAULT_NAME="$kv_name"
        echo -e "${GREEN}✅ Found Key Vault: $KEY_VAULT_NAME${NC}"
    fi

    # Get Storage Account name
    local storage_name
    storage_name=$(az storage account list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv 2>/dev/null)
    if [[ -n "$storage_name" ]]; then
        STORAGE_ACCOUNT="$storage_name"
        echo -e "${GREEN}✅ Found Storage Account: $STORAGE_ACCOUNT${NC}"
    fi
}

# Test 1: Verify Logic App exists and is enabled
test_logic_app_status() {
    echo -e "${BLUE}🔍 Test 1: Logic App Status${NC}"

    local state
    state=$(az logic workflow show --name "$LOGIC_APP_NAME" --resource-group "$RESOURCE_GROUP" --query "state" -o tsv 2>/dev/null)

    if [[ "$state" == "Enabled" ]]; then
        echo -e "${GREEN}✅ Logic App is enabled and ready${NC}"
        return 0
    elif [[ "$state" == "Disabled" ]]; then
        echo -e "${YELLOW}⚠️  Logic App is disabled, enabling...${NC}"
        az logic workflow update --name "$LOGIC_APP_NAME" --resource-group "$RESOURCE_GROUP" --state "Enabled"
        echo -e "${GREEN}✅ Logic App enabled${NC}"
        return 0
    else
        echo -e "${RED}❌ Logic App not found or in unknown state: $state${NC}"
        return 1
    fi
}

# Test 2: Verify Key Vault configuration exists
test_key_vault_config() {
    echo -e "${BLUE}🔍 Test 2: Key Vault Configuration${NC}"

    if [[ -z "$KEY_VAULT_NAME" ]]; then
        echo -e "${RED}❌ Key Vault name not found${NC}"
        return 1
    fi

    local config
    config=$(az keyvault secret show --vault-name "$KEY_VAULT_NAME" --name "scheduler-config" --query "value" -o tsv 2>/dev/null)

    if [[ -n "$config" ]]; then
        echo -e "${GREEN}✅ Scheduler configuration found in Key Vault${NC}"

        # Validate JSON structure
        if echo "$config" | jq . >/dev/null 2>&1; then
            echo -e "${GREEN}✅ Configuration is valid JSON${NC}"

            # Check for required fields
            local collector_url
            collector_url=$(echo "$config" | jq -r '.content_collector_url // empty')
            if [[ -n "$collector_url" && "$collector_url" != "null" ]]; then
                echo -e "${GREEN}✅ Content collector URL configured: $collector_url${NC}"
            else
                echo -e "${YELLOW}⚠️  Content collector URL missing or invalid${NC}"
            fi

            # Check for topics
            local topic_count
            topic_count=$(echo "$config" | jq '.initial_topics | length' 2>/dev/null || echo "0")
            if [[ "$topic_count" -gt 0 ]]; then
                echo -e "${GREEN}✅ Found $topic_count configured topics${NC}"
            else
                echo -e "${YELLOW}⚠️  No topics configured${NC}"
            fi
        else
            echo -e "${RED}❌ Configuration is not valid JSON${NC}"
            return 1
        fi
    else
        echo -e "${RED}❌ Scheduler configuration not found in Key Vault${NC}"
        echo -e "${YELLOW}💡 Run ./scripts/scheduler/configure-topics.sh to create it${NC}"
        return 1
    fi
}

# Test 3: Verify Storage Tables exist
test_storage_tables() {
    echo -e "${BLUE}🔍 Test 3: Storage Tables${NC}"

    if [[ -z "$STORAGE_ACCOUNT" ]]; then
        echo -e "${RED}❌ Storage account name not found${NC}"
        return 1
    fi

    local storage_key
    storage_key=$(az storage account keys list --account-name "$STORAGE_ACCOUNT" --resource-group "$RESOURCE_GROUP" --query "[0].value" -o tsv 2>/dev/null)

    local tables=("topicconfigurations" "executionhistory" "sourceanalytics")
    local table_count=0

    for table in "${tables[@]}"; do
        if az storage table exists \
            --name "$table" \
            --account-name "$STORAGE_ACCOUNT" \
            --account-key "$storage_key" \
            --query "exists" -o tsv >/dev/null 2>&1; then
            echo -e "${GREEN}✅ Table exists: $table${NC}"
            ((table_count++))
        else
            echo -e "${RED}❌ Table missing: $table${NC}"
        fi
    done

    if [[ $table_count -eq ${#tables[@]} ]]; then
        echo -e "${GREEN}✅ All required storage tables exist${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  Some storage tables are missing${NC}"
        return 1
    fi
}

# Test 4: Test Content Collector connectivity
test_content_collector() {
    echo -e "${BLUE}🔍 Test 4: Content Collector Connectivity${NC}"

    # Get collector URL from configuration
    local config collector_url
    config=$(az keyvault secret show --vault-name "$KEY_VAULT_NAME" --name "scheduler-config" --query "value" -o tsv 2>/dev/null)
    collector_url=$(echo "$config" | jq -r '.content_collector_url // empty' 2>/dev/null)

    if [[ -z "$collector_url" || "$collector_url" == "null" ]]; then
        echo -e "${RED}❌ Content collector URL not configured${NC}"
        return 1
    fi

    # Test health endpoint
    echo -e "${YELLOW}🔗 Testing: $collector_url/health${NC}"
    local response status_code
    response=$(curl -s -w "HTTPSTATUS:%{http_code}" "$collector_url/health" || echo "HTTPSTATUS:000")
    status_code=$(echo "$response" | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)

    if [[ "$status_code" == "200" ]]; then
        echo -e "${GREEN}✅ Content collector is healthy${NC}"
        return 0
    else
        echo -e "${RED}❌ Content collector health check failed (HTTP $status_code)${NC}"
        return 1
    fi
}

# Test 5: Manual Logic App trigger
test_manual_trigger() {
    echo -e "${BLUE}🔍 Test 5: Manual Logic App Trigger${NC}"

    echo -e "${YELLOW}🚀 Triggering Logic App manually...${NC}"

    # Get the recurrence trigger name
    local trigger_name="Recurrence"

    # Trigger the Logic App
    if az logic workflow trigger run \
        --name "$LOGIC_APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --trigger-name "$trigger_name" >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Logic App triggered successfully${NC}"

        # Wait a moment for execution to start
        sleep 5

        # Check recent run status
        local run_status
        run_status=$(az logic workflow run list \
            --name "$LOGIC_APP_NAME" \
            --resource-group "$RESOURCE_GROUP" \
            --top 1 \
            --query "[0].status" -o tsv 2>/dev/null)

        if [[ -n "$run_status" ]]; then
            echo -e "${GREEN}✅ Latest run status: $run_status${NC}"

            if [[ "$run_status" == "Succeeded" ]]; then
                echo -e "${GREEN}🎉 Logic App execution succeeded!${NC}"
                return 0
            elif [[ "$run_status" == "Running" ]]; then
                echo -e "${YELLOW}⏳ Logic App is still running...${NC}"
                return 0
            else
                echo -e "${YELLOW}⚠️  Logic App run status: $run_status${NC}"
                return 1
            fi
        else
            echo -e "${YELLOW}⚠️  Could not get run status${NC}"
            return 1
        fi
    else
        echo -e "${RED}❌ Failed to trigger Logic App${NC}"
        return 1
    fi
}

# Test 6: Check execution history
test_execution_history() {
    echo -e "${BLUE}🔍 Test 6: Execution History${NC}"

    local runs
    runs=$(az logic workflow run list \
        --name "$LOGIC_APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --top 5 \
        --query "length(@)" -o tsv 2>/dev/null)

    if [[ "$runs" -gt 0 ]]; then
        echo -e "${GREEN}✅ Found $runs recent execution(s)${NC}"

        # Show recent run details
        az logic workflow run list \
            --name "$LOGIC_APP_NAME" \
            --resource-group "$RESOURCE_GROUP" \
            --top 3 \
            --query "[].{Status:status, StartTime:startTime, EndTime:endTime}" \
            --output table

        return 0
    else
        echo -e "${YELLOW}⚠️  No execution history found${NC}"
        return 1
    fi
}

# Test 7: Cost monitoring
test_cost_monitoring() {
    echo -e "${BLUE}🔍 Test 7: Cost Monitoring${NC}"

    # Check if budget exists
    local budget
    budget=$(az consumption budget list --resource-group-name "$RESOURCE_GROUP" --query "[?contains(name, 'scheduler')].name" -o tsv 2>/dev/null | head -1)

    if [[ -n "$budget" ]]; then
        echo -e "${GREEN}✅ Scheduler budget found: $budget${NC}"

        # Get budget details
        local amount threshold
        amount=$(az consumption budget show --budget-name "$budget" --resource-group-name "$RESOURCE_GROUP" --query "amount" -o tsv 2>/dev/null)
        if [[ -n "$amount" ]]; then
            echo -e "${GREEN}✅ Budget amount: \$$amount/month${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  No scheduler budget found${NC}"
    fi
}

# Main test execution
main() {
    echo -e "${BLUE}🎯 Starting Scheduler End-to-End Tests...${NC}"
    echo -e "${BLUE}Resource Group: $RESOURCE_GROUP${NC}"
    echo ""

    # Setup
    check_azure_login
    get_resource_names
    echo ""

    # Run tests
    local test_results=()
    local test_names=(
        "Logic App Status"
        "Key Vault Configuration"
        "Storage Tables"
        "Content Collector Connectivity"
        "Manual Logic App Trigger"
        "Execution History"
        "Cost Monitoring"
    )

    # Execute tests
    test_logic_app_status && test_results+=(0) || test_results+=(1)
    test_key_vault_config && test_results+=(0) || test_results+=(1)
    test_storage_tables && test_results+=(0) || test_results+=(1)
    test_content_collector && test_results+=(0) || test_results+=(1)
    test_manual_trigger && test_results+=(0) || test_results+=(1)
    test_execution_history && test_results+=(0) || test_results+=(1)
    test_cost_monitoring && test_results+=(0) || test_results+=(1)

    # Summary
    echo ""
    echo -e "${BLUE}📊 Test Results Summary${NC}"
    echo "=========================="

    local passed=0
    local total=${#test_results[@]}

    for i in "${!test_results[@]}"; do
        if [[ ${test_results[$i]} -eq 0 ]]; then
            echo -e "${GREEN}✅ ${test_names[$i]}${NC}"
            ((passed++))
        else
            echo -e "${RED}❌ ${test_names[$i]}${NC}"
        fi
    done

    echo ""
    echo -e "${BLUE}Overall: $passed/$total tests passed${NC}"

    if [[ $passed -eq $total ]]; then
        echo -e "${GREEN}🎉 All tests passed! Scheduler is ready for production.${NC}"
        return 0
    elif [[ $passed -gt $((total / 2)) ]]; then
        echo -e "${YELLOW}⚠️  Most tests passed. Review failures and retry.${NC}"
        return 1
    else
        echo -e "${RED}❌ Multiple test failures. Check configuration and infrastructure.${NC}"
        return 1
    fi
}

# Show usage if help requested
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    echo "Usage: $0 [options]"
    echo ""
    echo "Environment variables:"
    echo "  RESOURCE_GROUP    Azure resource group name (default: ai-content-dev-rg)"
    echo "  LOGIC_APP_NAME    Logic App name (auto-detected if not set)"
    echo "  KEY_VAULT_NAME    Key Vault name (auto-detected if not set)"
    echo "  STORAGE_ACCOUNT   Storage account name (auto-detected if not set)"
    echo ""
    echo "This script tests the complete scheduler workflow including:"
    echo "  - Logic App configuration and status"
    echo "  - Key Vault scheduler configuration"
    echo "  - Storage table setup"
    echo "  - Content collector connectivity"
    echo "  - Manual trigger execution"
    echo "  - Execution history validation"
    echo "  - Cost monitoring setup"
    exit 0
fi

# Run main function
main "$@"
