#!/bin/bash
set -e

# Content Processor Azure Deployment and Testing Script
# Tests the Azure deployment and validates API functionality

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="/workspaces/ai-content-farm"

# Configuration
RESOURCE_GROUP_PREFIX="jamil-ai-content"
ENVIRONMENT="${1:-staging}"  # staging or production
REGION="uksouth"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

check_dependencies() {
    log "🔍 Checking dependencies..."

    for cmd in az docker python3; do
        if ! command -v "$cmd" &> /dev/null; then
            error "$cmd is required but not installed"
            exit 1
        fi
    done

    # Check Azure CLI login
    if ! az account show &> /dev/null; then
        error "Azure CLI not logged in. Run 'az login' first."
        exit 1
    fi

    success "All dependencies available"
}

get_azure_urls() {
    local rg_name="${RESOURCE_GROUP_PREFIX}-${ENVIRONMENT}"

    log "🔍 Getting Azure deployment URLs for resource group: $rg_name"

    # Get content processor URL
    local processor_fqdn
    processor_fqdn=$(az containerapp show \
        --name "${RESOURCE_GROUP_PREFIX}-processor" \
        --resource-group "$rg_name" \
        --query "properties.configuration.ingress.fqdn" \
        --output tsv 2>/dev/null || echo "")

    if [ -n "$processor_fqdn" ]; then
        AZURE_PROCESSOR_URL="https://$processor_fqdn"
        success "Found Content Processor: $AZURE_PROCESSOR_URL"
    else
        warning "Content Processor URL not found. Is it deployed?"
        AZURE_PROCESSOR_URL=""
    fi

    # Get other service URLs for context
    local collector_fqdn
    collector_fqdn=$(az containerapp show \
        --name "${RESOURCE_GROUP_PREFIX}-collector" \
        --resource-group "$rg_name" \
        --query "properties.configuration.ingress.fqdn" \
        --output tsv 2>/dev/null || echo "")

    if [ -n "$collector_fqdn" ]; then
        success "Found Content Collector: https://$collector_fqdn"
    fi

    local generator_fqdn
    generator_fqdn=$(az containerapp show \
        --name "${RESOURCE_GROUP_PREFIX}-generator" \
        --resource-group "$rg_name" \
        --query "properties.configuration.ingress.fqdn" \
        --output tsv 2>/dev/null || echo "")

    if [ -n "$generator_fqdn" ]; then
        success "Found Content Generator: https://$generator_fqdn"
    fi
}

check_container_status() {
    local rg_name="${RESOURCE_GROUP_PREFIX}-${ENVIRONMENT}"

    log "📊 Checking container status..."

    # Check content processor status
    local processor_status
    processor_status=$(az containerapp show \
        --name "${RESOURCE_GROUP_PREFIX}-processor" \
        --resource-group "$rg_name" \
        --query "properties.runningStatus" \
        --output tsv 2>/dev/null || echo "Not Found")

    echo "Content Processor Status: $processor_status"

    # Get revision details
    local revision_info
    revision_info=$(az containerapp revision list \
        --name "${RESOURCE_GROUP_PREFIX}-processor" \
        --resource-group "$rg_name" \
        --query "[0].{name:name,active:properties.active,replicas:properties.replicas,createdTime:properties.createdTime}" \
        --output table 2>/dev/null || echo "No revisions found")

    echo ""
    echo "Latest Revision:"
    echo "$revision_info"
}

deploy_to_azure() {
    log "🚀 Deploying Content Processor to Azure ($ENVIRONMENT)..."

    cd "$PROJECT_ROOT"

    # Check if Terraform is initialized
    if [ ! -d "infra/.terraform" ]; then
        log "Initializing Terraform..."
        cd infra
        terraform init
        cd ..
    fi

    # Plan deployment
    log "📋 Planning Terraform deployment..."
    cd infra

    if ! terraform plan -var-file="environments/${ENVIRONMENT}.tfvars" -out="plan.tfplan"; then
        error "Terraform plan failed"
        exit 1
    fi

    # Apply deployment
    log "🚀 Applying Terraform deployment..."
    read -p "Continue with deployment? (y/N): " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if ! terraform apply "plan.tfplan"; then
            error "Terraform apply failed"
            exit 1
        fi
        success "Deployment completed"
    else
        warning "Deployment cancelled"
        return 1
    fi

    cd ..
}

test_azure_api() {
    if [ -z "$AZURE_PROCESSOR_URL" ]; then
        error "No Azure URL found. Cannot test Azure deployment."
        return 1
    fi

    log "🔬 Testing Azure API deployment..."

    cd "$SCRIPT_DIR"

    # Run validation script against Azure
    if python3 validate_api.py --azure --azure-url "$AZURE_PROCESSOR_URL"; then
        success "Azure API tests passed!"
        return 0
    else
        warning "Some Azure API tests failed"
        return 1
    fi
}

show_monitoring_info() {
    local rg_name="${RESOURCE_GROUP_PREFIX}-${ENVIRONMENT}"

    log "📊 Setting up monitoring and logging..."

    # Get Application Insights info
    local app_insights_name
    app_insights_name=$(az monitor app-insights component list \
        --resource-group "$rg_name" \
        --query "[0].name" \
        --output tsv 2>/dev/null || echo "")

    if [ -n "$app_insights_name" ]; then
        success "Application Insights: $app_insights_name"

        local app_insights_key
        app_insights_key=$(az monitor app-insights component show \
            --app "$app_insights_name" \
            --resource-group "$rg_name" \
            --query "instrumentationKey" \
            --output tsv 2>/dev/null || echo "")

        echo "Instrumentation Key: ${app_insights_key:0:8}..."
    fi

    # Show log analytics workspace
    local log_workspace
    log_workspace=$(az monitor log-analytics workspace list \
        --resource-group "$rg_name" \
        --query "[0].name" \
        --output tsv 2>/dev/null || echo "")

    if [ -n "$log_workspace" ]; then
        success "Log Analytics Workspace: $log_workspace"
    fi

    echo ""
    echo "📈 Monitoring URLs:"
    if [ -n "$AZURE_PROCESSOR_URL" ]; then
        echo "• Health Check: $AZURE_PROCESSOR_URL/health"
        echo "• Status Info:  $AZURE_PROCESSOR_URL/status"
        echo "• API Docs:     $AZURE_PROCESSOR_URL/docs"
        echo "• OpenAPI:      $AZURE_PROCESSOR_URL/openapi.json"
    fi

    echo ""
    echo "📋 Azure Portal Links:"
    echo "• Resource Group: https://portal.azure.com/#@jamilabubakar.onmicrosoft.com/resource/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$rg_name"
    if [ -n "$app_insights_name" ]; then
        echo "• App Insights:   https://portal.azure.com/#@jamilabubakar.onmicrosoft.com/resource/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$rg_name/providers/Microsoft.Insights/components/$app_insights_name"
    fi
}

main() {
    echo "🔬 Content Processor Azure Deployment & Testing"
    echo "Environment: $ENVIRONMENT"
    echo "=" * 60

    check_dependencies

    case "${2:-test}" in
        "deploy")
            deploy_to_azure
            get_azure_urls
            check_container_status
            test_azure_api
            show_monitoring_info
            ;;
        "test")
            get_azure_urls
            check_container_status
            test_azure_api
            show_monitoring_info
            ;;
        "status")
            get_azure_urls
            check_container_status
            show_monitoring_info
            ;;
        "logs")
            local rg_name="${RESOURCE_GROUP_PREFIX}-${ENVIRONMENT}"
            log "📋 Fetching recent logs..."

            az containerapp logs show \
                --name "${RESOURCE_GROUP_PREFIX}-processor" \
                --resource-group "$rg_name" \
                --follow=false \
                --tail=50
            ;;
        *)
            echo "Usage: $0 [staging|production] [deploy|test|status|logs]"
            echo ""
            echo "Commands:"
            echo "  deploy  - Deploy to Azure and test"
            echo "  test    - Test existing Azure deployment (default)"
            echo "  status  - Show deployment status"
            echo "  logs    - Show recent container logs"
            exit 1
            ;;
    esac
}

main "$@"
