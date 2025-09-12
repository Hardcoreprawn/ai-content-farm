#!/bin/bash
#
# Azure PKI Infrastructure Deployment Script
#
# Deploys and validates the complete PKI infrastructure including:
# - Let's Encrypt certificate automation
# - Azure DNS zones for jablab.dev and jablab.com
# - mTLS certificate management
# - KEDA + Cosmos DB work queue (budget optimized)
#

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
INFRA_DIR="$PROJECT_ROOT/infra"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "🔍 Checking deployment prerequisites..."

    # Check Azure CLI
    if ! command -v az >/dev/null 2>&1; then
        log_error "Azure CLI not found. Please install Azure CLI."
        exit 1
    fi

    # Check if logged in
    if ! az account show >/dev/null 2>&1; then
        log_error "Not logged into Azure. Please run 'az login'"
        exit 1
    fi

    # Check terraform
    if ! command -v terraform >/dev/null 2>&1; then
        log_error "Terraform not found. Please install Terraform."
        exit 1
    fi

    # Verify we're in the right directory
    if [[ ! -f "$INFRA_DIR/main.tf" ]]; then
        log_error "Infrastructure directory not found. Run from project root."
        exit 1
    fi

    log_success "Prerequisites check passed"
}

# Validate Terraform configuration
validate_terraform() {
    log_info "🔧 Validating Terraform configuration..."

    cd "$INFRA_DIR"

    # Initialize if needed or if providers changed
    if [[ ! -f ".terraform.lock.hcl" ]] || ! terraform providers lock -platform=linux_amd64 -platform=darwin_amd64 -platform=windows_amd64 2>/dev/null; then
        log_info "Initializing Terraform with new providers..."
        terraform init -upgrade
    fi

    # Validate configuration
    terraform validate

    # Format check
    if ! terraform fmt -check=true >/dev/null 2>&1; then
        log_warning "Terraform files need formatting. Running terraform fmt..."
        terraform fmt
    fi

    log_success "Terraform configuration validated"
}

# Plan PKI infrastructure deployment
plan_pki_deployment() {
    log_info "📋 Planning PKI infrastructure deployment..."

    cd "$INFRA_DIR"

    # Plan with PKI enabled
    terraform plan \
        -var="enable_pki=true" \
        -var="enable_mtls=true" \
        -var="primary_domain=jablab.dev" \
        -var="certificate_email=admin@jablab.dev" \
        -out=pki-deployment.tfplan

    log_success "PKI deployment plan created"
}

# Deploy PKI infrastructure
deploy_pki() {
    log_info "🚀 Deploying PKI infrastructure..."

    cd "$INFRA_DIR"

    # Apply the plan
    terraform apply pki-deployment.tfplan

    # Clean up plan file
    rm -f pki-deployment.tfplan

    log_success "PKI infrastructure deployed"
}

# Validate PKI deployment
validate_pki_deployment() {
    log_info "✅ Validating PKI deployment..."

    # Get Key Vault name
    local key_vault_url
    key_vault_url=$(cd "$INFRA_DIR" && terraform output -raw certificate_key_vault_url 2>/dev/null || echo "")

    if [[ -z "$key_vault_url" ]]; then
        log_error "Could not get Key Vault URL from Terraform output"
        return 1
    fi

    local key_vault_name
    key_vault_name=$(echo "$key_vault_url" | sed 's|https://||' | sed 's|\.vault\.azure\.net/||')

    log_info "Checking certificates in Key Vault: $key_vault_name"

    # Check if certificates were created
    local services=("content-collector" "content-processor" "site-generator")

    for service in "${services[@]}"; do
        local cert_name="${service}-certificate"

        if az keyvault certificate show \
            --vault-name "$key_vault_name" \
            --name "$cert_name" \
            --output none 2>/dev/null; then
            log_success "Certificate found: $cert_name"
        else
            log_warning "Certificate not found: $cert_name (may still be provisioning)"
        fi
    done

    # Check DNS zones
    log_info "Checking DNS zones..."

    local dns_zones=("jablab.dev" "jablab.com")
    local resource_group
    resource_group=$(cd "$INFRA_DIR" && terraform output -json | jq -r '.resource_group_name.value' 2>/dev/null || echo "ai-content-dev-rg")

    for zone in "${dns_zones[@]}"; do
        if az network dns zone show \
            --resource-group "$resource_group" \
            --name "$zone" \
            --output none 2>/dev/null; then
            log_success "DNS zone found: $zone"
        else
            log_warning "DNS zone not found: $zone"
        fi
    done

    log_success "PKI deployment validation completed"
}

# Plan KEDA + Cosmos DB deployment
plan_keda_deployment() {
    log_info "📋 Planning KEDA + Cosmos DB deployment..."

    cd "$INFRA_DIR"

    # Plan KEDA infrastructure
    terraform plan \
        -var="enable_pki=true" \
        -var="enable_mtls=true" \
        -var="primary_domain=jablab.dev" \
        -var="certificate_email=admin@jablab.dev" \
        -target=azurerm_cosmosdb_account.keda_state \
        -target=azurerm_cosmosdb_sql_database.keda_state \
        -target=azurerm_cosmosdb_sql_container.work_queue \
        -out=keda-deployment.tfplan

    log_success "KEDA deployment plan created"
}

# Deploy KEDA infrastructure
deploy_keda() {
    log_info "🚀 Deploying KEDA + Cosmos DB infrastructure..."

    cd "$INFRA_DIR"

    # Apply the plan
    terraform apply keda-deployment.tfplan

    # Clean up plan file
    rm -f keda-deployment.tfplan

    log_success "KEDA infrastructure deployed"
}

# Show cost estimation
show_cost_estimation() {
    log_info "💰 Cost estimation for new infrastructure..."

    echo ""
    echo "=== PKI Infrastructure Costs ==="
    echo "DNS Zones (2x):           ~$1.00/month"
    echo "Key Vault operations:     ~$0.50/month"
    echo "Logic Apps (monitoring):  ~$0.50/month"
    echo "Let's Encrypt certs:      $0.00/month (free)"
    echo ""
    echo "=== KEDA Infrastructure Costs ==="
    echo "Cosmos DB (serverless):   ~$5.00/month"
    echo "Container Apps scaling:   $0.00/month (only when running)"
    echo ""
    echo "=== Total Estimated Cost ==="
    echo "New Infrastructure:       ~$7.00/month"
    echo "Service Bus (current):    ~$50.00/month"
    echo "NET SAVINGS:              ~$43.00/month (86% reduction)"
    echo ""
}

# Show deployment status
show_deployment_status() {
    log_info "📊 Deployment Status Summary"
    echo ""

    cd "$INFRA_DIR"

    # Show Terraform outputs
    echo "=== Terraform Outputs ==="
    terraform output 2>/dev/null || log_warning "No Terraform outputs available"
    echo ""

    # Show resource group resources
    local resource_group
    resource_group=$(terraform output -json 2>/dev/null | jq -r '.resource_group_name.value' 2>/dev/null || echo "ai-content-dev-rg")

    echo "=== Azure Resources in $resource_group ==="
    az resource list \
        --resource-group "$resource_group" \
        --query "[].{Name:name, Type:type, Location:location}" \
        --output table 2>/dev/null || log_warning "Could not list resources"

    echo ""
}

# Main command handling
main() {
    local command="${1:-help}"

    case "$command" in
        "validate")
            check_prerequisites
            validate_terraform
            log_success "Validation completed successfully"
            ;;
        "plan-pki")
            check_prerequisites
            validate_terraform
            plan_pki_deployment
            show_cost_estimation
            ;;
        "deploy-pki")
            check_prerequisites
            validate_terraform
            plan_pki_deployment
            deploy_pki
            validate_pki_deployment
            ;;
        "plan-keda")
            check_prerequisites
            validate_terraform
            plan_keda_deployment
            ;;
        "deploy-keda")
            check_prerequisites
            validate_terraform
            plan_keda_deployment
            deploy_keda
            ;;
        "deploy-all")
            check_prerequisites
            validate_terraform
            plan_pki_deployment
            deploy_pki
            validate_pki_deployment
            plan_keda_deployment
            deploy_keda
            show_deployment_status
            show_cost_estimation
            ;;
        "status")
            show_deployment_status
            ;;
        "cost")
            show_cost_estimation
            ;;
        "help"|*)
            echo "Azure PKI + KEDA Infrastructure Deployment"
            echo ""
            echo "Usage: $0 <command>"
            echo ""
            echo "Commands:"
            echo "  validate     - Validate Terraform configuration"
            echo "  plan-pki     - Plan PKI infrastructure deployment"
            echo "  deploy-pki   - Deploy PKI infrastructure (DNS + certificates)"
            echo "  plan-keda    - Plan KEDA + Cosmos DB deployment"
            echo "  deploy-keda  - Deploy KEDA infrastructure"
            echo "  deploy-all   - Deploy complete infrastructure"
            echo "  status       - Show deployment status"
            echo "  cost         - Show cost estimation"
            echo "  help         - Show this help message"
            echo ""
            echo "Prerequisites:"
            echo "  - Azure CLI installed and authenticated"
            echo "  - Terraform installed"
            echo "  - Run from project root directory"
            echo ""
            echo "Example deployment:"
            echo "  $0 validate"
            echo "  $0 plan-pki"
            echo "  $0 deploy-all"
            echo ""
            exit 0
            ;;
    esac
}

# Run main function
main "$@"
