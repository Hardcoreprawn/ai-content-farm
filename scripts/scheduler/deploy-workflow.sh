#!/bin/bash
# Deploy Logic App workflow for content scheduler
# This script deploys the Logic App workflow definition to Azure

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
RESOURCE_GROUP="${RESOURCE_GROUP:-ai-content-dev-rg}"
LOGIC_APP_NAME="${LOGIC_APP_NAME:-}"
WORKFLOW_FILE="$(dirname "$0")/../../docs/scheduler/logic-app-workflow.json"

echo -e "${BLUE}🚀 Deploying Logic App Scheduler Workflow...${NC}"

# Function to check if Azure CLI is logged in
check_azure_login() {
    if ! az account show >/dev/null 2>&1; then
        echo -e "${RED}❌ Not logged into Azure. Please run 'az login' first.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Azure CLI authenticated${NC}"
}

# Function to get Logic App name dynamically
get_logic_app_name() {
    local logic_app
    logic_app=$(az logic workflow list --resource-group "$RESOURCE_GROUP" --query "[?contains(name, 'scheduler')].name" -o tsv 2>/dev/null | head -1)
    if [[ -n "$logic_app" ]]; then
        LOGIC_APP_NAME="$logic_app"
        echo -e "${GREEN}✅ Found Logic App: $LOGIC_APP_NAME${NC}"
    else
        echo -e "${RED}❌ No Logic App found in resource group $RESOURCE_GROUP${NC}"
        echo -e "${YELLOW}💡 Deploy the infrastructure first with: cd infra && terraform apply${NC}"
        exit 1
    fi
}

# Function to validate workflow JSON
validate_workflow() {
    if [[ ! -f "$WORKFLOW_FILE" ]]; then
        echo -e "${RED}❌ Workflow file not found: $WORKFLOW_FILE${NC}"
        exit 1
    fi

    echo -e "${BLUE}🔍 Validating workflow JSON...${NC}"
    if jq . "$WORKFLOW_FILE" >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Workflow JSON is valid${NC}"
    else
        echo -e "${RED}❌ Workflow JSON is invalid${NC}"
        exit 1
    fi
}

# Function to check if Logic App exists
check_logic_app_exists() {
    echo -e "${BLUE}🔍 Checking Logic App status...${NC}"

    local state
    state=$(az logic workflow show --name "$LOGIC_APP_NAME" --resource-group "$RESOURCE_GROUP" --query "state" -o tsv 2>/dev/null)

    if [[ -n "$state" ]]; then
        echo -e "${GREEN}✅ Logic App exists with state: $state${NC}"
        return 0
    else
        echo -e "${RED}❌ Logic App not found: $LOGIC_APP_NAME${NC}"
        return 1
    fi
}

# Function to deploy workflow definition
deploy_workflow() {
    echo -e "${BLUE}📦 Deploying workflow definition...${NC}"

    # Create a temporary file with the workflow definition only
    local temp_workflow="/tmp/scheduler-workflow-definition.json"
    jq '.definition' "$WORKFLOW_FILE" > "$temp_workflow"

    # Deploy the workflow
    if az logic workflow update \
        --name "$LOGIC_APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --definition "@$temp_workflow" >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Workflow deployed successfully${NC}"
        rm -f "$temp_workflow"
        return 0
    else
        echo -e "${RED}❌ Failed to deploy workflow${NC}"
        rm -f "$temp_workflow"
        return 1
    fi
}

# Function to enable the Logic App
enable_logic_app() {
    echo -e "${BLUE}⚡ Enabling Logic App...${NC}"

    if az logic workflow update \
        --name "$LOGIC_APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --state "Enabled" >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Logic App enabled${NC}"
        return 0
    else
        echo -e "${RED}❌ Failed to enable Logic App${NC}"
        return 1
    fi
}

# Function to test workflow deployment
test_deployment() {
    echo -e "${BLUE}🧪 Testing workflow deployment...${NC}"

    # Get workflow details
    local trigger_name="Recurrence"
    local workflow_state
    workflow_state=$(az logic workflow show --name "$LOGIC_APP_NAME" --resource-group "$RESOURCE_GROUP" --query "state" -o tsv 2>/dev/null)

    if [[ "$workflow_state" == "Enabled" ]]; then
        echo -e "${GREEN}✅ Workflow is enabled and ready${NC}"

        # Check if we can see the trigger
        local triggers
        triggers=$(az logic workflow trigger list --name "$LOGIC_APP_NAME" --resource-group "$RESOURCE_GROUP" --query "length(@)" -o tsv 2>/dev/null)

        if [[ "$triggers" -gt 0 ]]; then
            echo -e "${GREEN}✅ Found $triggers trigger(s)${NC}"
            return 0
        else
            echo -e "${YELLOW}⚠️  No triggers found${NC}"
            return 1
        fi
    else
        echo -e "${RED}❌ Workflow is not enabled: $workflow_state${NC}"
        return 1
    fi
}

# Function to show next steps
show_next_steps() {
    echo -e "${GREEN}"
    echo "🎉 Logic App Workflow Deployment Complete!"
    echo ""
    echo "📋 Next Steps:"
    echo "1. Configure topics:"
    echo "   ./scripts/scheduler/configure-topics.sh"
    echo ""
    echo "2. Test the scheduler:"
    echo "   ./scripts/scheduler/test-scheduler.sh"
    echo ""
    echo "3. Manual trigger (optional):"
    echo "   az logic workflow trigger run \\"
    echo "     --name $LOGIC_APP_NAME \\"
    echo "     --resource-group $RESOURCE_GROUP \\"
    echo "     --trigger-name Recurrence"
    echo ""
    echo "4. Monitor in Azure Portal:"
    echo "   https://portal.azure.com/#view/Microsoft_Azure_ERM/LogicAppMenuBlade/~/overview/resourceId/%2Fsubscriptions%2F$(az account show --query id -o tsv)%2FresourceGroups%2F$RESOURCE_GROUP%2Fproviders%2FMicrosoft.Logic%2Fworkflows%2F$LOGIC_APP_NAME"
    echo -e "${NC}"
}

# Main execution
main() {
    echo -e "${BLUE}🎯 Starting Logic App Workflow Deployment...${NC}"
    echo -e "${BLUE}Resource Group: $RESOURCE_GROUP${NC}"
    echo -e "${BLUE}Workflow File: $WORKFLOW_FILE${NC}"
    echo ""

    # Prerequisites
    check_azure_login
    validate_workflow
    get_logic_app_name

    # Deployment steps
    if check_logic_app_exists; then
        if deploy_workflow; then
            if enable_logic_app; then
                if test_deployment; then
                    show_next_steps
                    echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
                    exit 0
                else
                    echo -e "${YELLOW}⚠️  Deployment completed with warnings${NC}"
                    exit 0
                fi
            else
                echo -e "${RED}❌ Failed to enable Logic App${NC}"
                exit 1
            fi
        else
            echo -e "${RED}❌ Failed to deploy workflow${NC}"
            exit 1
        fi
    else
        echo -e "${RED}❌ Logic App not found. Deploy infrastructure first.${NC}"
        exit 1
    fi
}

# Show usage if help requested
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    echo "Usage: $0 [options]"
    echo ""
    echo "Environment variables:"
    echo "  RESOURCE_GROUP    Azure resource group name (default: ai-content-dev-rg)"
    echo "  LOGIC_APP_NAME    Logic App name (auto-detected if not set)"
    echo ""
    echo "This script deploys the Logic App workflow definition for the content scheduler."
    echo "It requires that the Logic App infrastructure has already been deployed with Terraform."
    echo ""
    echo "Prerequisites:"
    echo "  - Azure CLI logged in"
    echo "  - Logic App infrastructure deployed"
    echo "  - Valid workflow JSON file"
    exit 0
fi

# Run main function
main "$@"
