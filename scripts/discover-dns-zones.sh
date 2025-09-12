#!/bin/bash
#
# Azure DNS Zone Discovery Script
#
# This script discovers existing DNS zones for jablab.dev and jablab.com
# and provides the resource group information needed for PKI setup.
#

set -euo pipefail

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

# Discover DNS zones
discover_dns_zones() {
    log_info "🔍 Discovering existing DNS zones for jablab.dev and jablab.com..."

    # Check if logged into Azure
    if ! az account show >/dev/null 2>&1; then
        log_error "Not logged into Azure. Please run 'az login'"
        exit 1
    fi

    local subscription_id
    subscription_id=$(az account show --query id -o tsv)

    log_info "Using subscription: $subscription_id"
    echo ""

    # Search for jablab.dev
    local jablab_dev_zones
    jablab_dev_zones=$(az network dns zone list --query "[?name=='jablab.dev']" -o table 2>/dev/null || echo "")

    if [[ -n "$jablab_dev_zones" ]] && [[ "$jablab_dev_zones" != *"[]"* ]]; then
        log_success "Found jablab.dev DNS zone:"
        echo "$jablab_dev_zones"

        # Get resource group
        local jablab_dev_rg
        jablab_dev_rg=$(az network dns zone list --query "[?name=='jablab.dev'].resourceGroup" -o tsv)
        log_info "Resource Group: $jablab_dev_rg"
        echo ""
    else
        log_warning "jablab.dev DNS zone not found"
        echo ""
    fi

    # Search for jablab.com
    local jablab_com_zones
    jablab_com_zones=$(az network dns zone list --query "[?name=='jablab.com']" -o table 2>/dev/null || echo "")

    if [[ -n "$jablab_com_zones" ]] && [[ "$jablab_com_zones" != *"[]"* ]]; then
        log_success "Found jablab.com DNS zone:"
        echo "$jablab_com_zones"

        # Get resource group
        local jablab_com_rg
        jablab_com_rg=$(az network dns zone list --query "[?name=='jablab.com'].resourceGroup" -o tsv)
        log_info "Resource Group: $jablab_com_rg"
        echo ""

        # Show existing records (first 10)
        log_info "Existing DNS records in jablab.com (first 10):"
        az network dns record-set list \
            --resource-group "$jablab_com_rg" \
            --zone-name "jablab.com" \
            --query "[].{Name:name, Type:type, TTL:ttl}" \
            --output table 2>/dev/null | head -15 || log_warning "Could not list records"
        echo ""
    else
        log_warning "jablab.com DNS zone not found"
        echo ""
    fi
}

# Generate terraform import commands
generate_import_commands() {
    log_info "📋 Generating Terraform import commands..."
    echo ""

    # Get resource groups for DNS zones
    local jablab_dev_rg jablab_com_rg

    jablab_dev_rg=$(az network dns zone list --query "[?name=='jablab.dev'].resourceGroup" -o tsv 2>/dev/null || echo "")
    jablab_com_rg=$(az network dns zone list --query "[?name=='jablab.com'].resourceGroup" -o tsv 2>/dev/null || echo "")

    if [[ -n "$jablab_dev_rg" ]]; then
        local jablab_dev_id
        jablab_dev_id="/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$jablab_dev_rg/providers/Microsoft.Network/dnszones/jablab.dev"

        echo "# Import jablab.dev DNS zone"
        echo "terraform import 'data.azurerm_dns_zone.jablab_dev[0]' '$jablab_dev_id'"
        echo ""
    fi

    if [[ -n "$jablab_com_rg" ]]; then
        local jablab_com_id
        jablab_com_id="/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$jablab_com_rg/providers/Microsoft.Network/dnszones/jablab.com"

        echo "# Import jablab.com DNS zone"
        echo "terraform import 'data.azurerm_dns_zone.jablab_com[0]' '$jablab_com_id'"
        echo ""
    fi
}

# Generate terraform variables
generate_terraform_vars() {
    log_info "📝 Generating terraform.tfvars configuration..."
    echo ""

    # Get resource groups
    local jablab_dev_rg jablab_com_rg

    jablab_dev_rg=$(az network dns zone list --query "[?name=='jablab.dev'].resourceGroup" -o tsv 2>/dev/null || echo "")
    jablab_com_rg=$(az network dns zone list --query "[?name=='jablab.com'].resourceGroup" -o tsv 2>/dev/null || echo "")

    # Determine if zones are in the same resource group
    if [[ -n "$jablab_dev_rg" ]] && [[ -n "$jablab_com_rg" ]]; then
        if [[ "$jablab_dev_rg" == "$jablab_com_rg" ]]; then
            echo "# DNS zones are in the same resource group"
            echo "dns_zones_resource_group = \"$jablab_dev_rg\""
        else
            log_warning "DNS zones are in different resource groups:"
            log_warning "  jablab.dev: $jablab_dev_rg"
            log_warning "  jablab.com: $jablab_com_rg"
            echo "# Note: Zones in different resource groups - using jablab.dev RG"
            echo "dns_zones_resource_group = \"$jablab_dev_rg\""
        fi
    elif [[ -n "$jablab_dev_rg" ]]; then
        echo "# Only jablab.dev found"
        echo "dns_zones_resource_group = \"$jablab_dev_rg\""
    elif [[ -n "$jablab_com_rg" ]]; then
        echo "# Only jablab.com found"
        echo "dns_zones_resource_group = \"$jablab_com_rg\""
    else
        echo "# No existing DNS zones found - will create new ones"
        echo "# dns_zones_resource_group = \"\""
    fi

    echo ""
    echo "# PKI Configuration"
    echo "enable_pki = true"
    echo "enable_mtls = true"
    echo "primary_domain = \"jablab.dev\""
    echo "certificate_email = \"admin@jablab.dev\""
    echo ""
}

# Show deployment next steps
show_next_steps() {
    log_info "🚀 Next Steps for PKI Deployment"
    echo ""

    echo "1. Update your terraform.tfvars file with the configuration above"
    echo ""
    echo "2. Validate the Terraform configuration:"
    echo "   cd infra && terraform validate"
    echo ""
    echo "3. Plan the PKI deployment:"
    echo "   ./scripts/deploy-pki-infrastructure.sh plan-pki"
    echo ""
    echo "4. Deploy when ready:"
    echo "   ./scripts/deploy-pki-infrastructure.sh deploy-pki"
    echo ""

    log_warning "Important: The existing DNS records in jablab.com will be preserved."
    log_warning "New A records will be added for your services (content-collector, etc.)"
    echo ""
}

# Main function
main() {
    local command="${1:-discover}"

    case "$command" in
        "discover")
            discover_dns_zones
            generate_terraform_vars
            show_next_steps
            ;;
        "import")
            discover_dns_zones
            generate_import_commands
            ;;
        "vars")
            generate_terraform_vars
            ;;
        "help"|*)
            echo "Azure DNS Zone Discovery for PKI Setup"
            echo ""
            echo "Usage: $0 <command>"
            echo ""
            echo "Commands:"
            echo "  discover  - Discover DNS zones and generate configuration (default)"
            echo "  import    - Generate Terraform import commands"
            echo "  vars      - Generate terraform.tfvars configuration"
            echo "  help      - Show this help message"
            echo ""
            exit 0
            ;;
    esac
}

# Run main function
main "$@"
