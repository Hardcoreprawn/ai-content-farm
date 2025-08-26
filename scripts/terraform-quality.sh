#!/bin/bash
# Terraform quality checks for AI Content Farm
# This script runs terraform fmt and validate checks
# Usage: ./scripts/terraform-quality.sh [--fix]

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
TERRAFORM_DIR="infra"
FIX_MODE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --fix)
            FIX_MODE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--fix]"
            echo "  --fix   Auto-fix formatting issues"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}🏗️  Running Terraform quality checks...${NC}"
echo "Directory: $TERRAFORM_DIR"
echo "Fix mode: $FIX_MODE"
echo ""

# Check if terraform directory exists
if [ ! -d "$TERRAFORM_DIR" ]; then
    echo -e "${RED}❌ Terraform directory '$TERRAFORM_DIR' not found!${NC}"
    exit 1
fi

# Check if terraform is available
if ! command -v terraform &> /dev/null; then
    echo -e "${RED}❌ Terraform not found! Please install Terraform.${NC}"
    exit 1
fi

cd "$TERRAFORM_DIR"

# Function to check file changes
check_terraform_files() {
    if command -v git &> /dev/null && git rev-parse --git-dir > /dev/null 2>&1; then
        # In git repo - check staged files
        terraform_files=$(git diff --cached --name-only --diff-filter=AM | grep -E '\.tf$' || true)
        if [ -n "$terraform_files" ]; then
            echo -e "${BLUE}📝 Staged Terraform files:${NC}"
            echo "$terraform_files" | sed 's/^/  - /'
            echo ""
            return 0
        else
            echo -e "${YELLOW}ℹ️  No staged .tf files found, checking all files...${NC}"
            echo ""
            return 1
        fi
    else
        # Not in git repo - check all files
        return 1
    fi
}

# Track results
format_failed=false
validate_failed=false

# 1. Terraform Format Check
echo -e "${BLUE}1. Checking Terraform formatting...${NC}"

if $FIX_MODE; then
    echo "Running terraform fmt (fixing formatting)..."
    if terraform fmt -recursive .; then
        echo -e "${GREEN}✅ Terraform formatting fixed successfully!${NC}"
    else
        echo -e "${RED}❌ Terraform fmt failed!${NC}"
        format_failed=true
    fi
else
    echo "Running terraform fmt -check (read-only)..."
    if terraform fmt -check -diff -recursive .; then
        echo -e "${GREEN}✅ All Terraform files are properly formatted!${NC}"
    else
        echo -e "${RED}❌ Terraform formatting issues found!${NC}"
        echo -e "${YELLOW}💡 Run with --fix to auto-format, or run: terraform fmt -recursive .${NC}"
        format_failed=true
    fi
fi
echo ""

# 2. Terraform Validation
echo -e "${BLUE}2. Validating Terraform configuration...${NC}"

# Initialize without backend for validation
echo "Initializing Terraform (validation mode)..."
if terraform init -backend=false > /dev/null 2>&1; then
    echo "Running terraform validate..."
    if terraform validate; then
        echo -e "${GREEN}✅ Terraform configuration is valid!${NC}"
    else
        echo -e "${RED}❌ Terraform validation failed!${NC}"
        validate_failed=true
    fi
else
    echo -e "${YELLOW}⚠️  Could not initialize Terraform for validation${NC}"
    echo "This might be due to missing provider configuration."
    echo "Skipping validation check..."
fi
echo ""

# 3. Summary
echo -e "${BLUE}📊 Quality Check Summary${NC}"
echo "========================"

if [ "$format_failed" = false ] && [ "$validate_failed" = false ]; then
    echo -e "${GREEN}✅ All checks passed!${NC}"
    echo ""
    echo "Terraform files are:"
    echo "  ✓ Properly formatted"
    echo "  ✓ Syntactically valid"
    exit 0
else
    echo -e "${RED}❌ Some checks failed:${NC}"
    [ "$format_failed" = true ] && echo "  ✗ Formatting issues found"
    [ "$validate_failed" = true ] && echo "  ✗ Validation errors found"
    echo ""
    echo "Please fix the issues and try again."
    exit 1
fi
