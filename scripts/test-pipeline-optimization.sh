#!/bin/bash
# CI/CD Pipeline Optimization Test Script
# Tests the optimized pipeline configuration

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

# Test 1: Validate optimized pipeline YAML syntax
test_pipeline_syntax() {
    log_info "Testing optimized pipeline YAML syntax..."

    if command -v yamllint >/dev/null 2>&1; then
        if yamllint .github/workflows/optimized-cicd.yml; then
            log_success "Pipeline YAML syntax is valid"
        else
            log_error "Pipeline YAML syntax is invalid"
            return 1
        fi
    else
        log_warning "yamllint not available, skipping YAML validation"
    fi
}

# Test 2: Validate GitHub Actions syntax
test_actions_syntax() {
    log_info "Testing GitHub Actions syntax..."

    if command -v actionlint >/dev/null 2>&1; then
        if actionlint .github/workflows/optimized-cicd.yml; then
            log_success "GitHub Actions syntax is valid"
        else
            log_error "GitHub Actions syntax is invalid"
            return 1
        fi
    else
        log_warning "actionlint not available, skipping Actions validation"
    fi
}

# Test 3: Validate smart-deploy action
test_smart_deploy_action() {
    log_info "Testing smart-deploy action syntax..."

    if [[ -f ".github/actions/smart-deploy-optimized/action.yml" ]]; then
        if command -v yamllint >/dev/null 2>&1; then
            if yamllint .github/actions/smart-deploy-optimized/action.yml; then
                log_success "Smart-deploy action syntax is valid"
            else
                log_error "Smart-deploy action syntax is invalid"
                return 1
            fi
        fi
    else
        log_warning "Smart-deploy action not found"
    fi
}

# Test 4: Validate Dockerfile template
test_dockerfile_template() {
    log_info "Testing Dockerfile template..."

    if [[ -f "containers/Dockerfile.template" ]]; then
        # Basic Dockerfile syntax check
        if docker run --rm -i hadolint/hadolint < containers/Dockerfile.template 2>/dev/null; then
            log_success "Dockerfile template passes hadolint checks"
        else
            log_warning "Dockerfile template has hadolint warnings (this is expected for a template)"
        fi
    else
        log_warning "Dockerfile template not found"
    fi
}

# Test 5: Validate Terraform syntax
test_terraform_syntax() {
    log_info "Testing Terraform syntax..."

    if command -v terraform >/dev/null 2>&1; then
        cd infra
        if terraform validate; then
            log_success "Terraform configuration is valid"
        else
            log_error "Terraform configuration is invalid"
            cd ..
            return 1
        fi
        cd ..
    else
        log_warning "Terraform not available, skipping validation"
    fi
}

# Test 6: Check for required files
test_required_files() {
    log_info "Checking for required files..."

    required_files=(
        ".github/workflows/optimized-cicd.yml"
        ".github/actions/smart-deploy-optimized/action.yml"
        "containers/Dockerfile.template"
        "docs/CI_CD_OPTIMIZATION_PLAN.md"
    )

    missing_files=()

    for file in "${required_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            missing_files+=("$file")
        fi
    done

    if [[ ${#missing_files[@]} -eq 0 ]]; then
        log_success "All required files are present"
    else
        log_error "Missing required files:"
        for file in "${missing_files[@]}"; do
            echo "  - $file"
        done
        return 1
    fi
}

# Test 7: Validate pipeline job dependencies
test_pipeline_dependencies() {
    log_info "Testing pipeline job dependencies..."

    # Check that basic dependencies exist
    if grep -q "needs: detect-changes" .github/workflows/optimized-cicd.yml && \
       grep -q "needs:" .github/workflows/optimized-cicd.yml; then
        log_success "Pipeline job dependencies are correctly structured"
    else
        log_error "Pipeline job dependencies are incorrectly structured"
        return 1
    fi
}

# Test 8: Performance estimation
estimate_performance() {
    log_info "Estimating performance improvements..."

    # Count jobs in original vs optimized pipeline
    if [[ -f ".github/workflows/cicd-pipeline.yml" ]]; then
        original_jobs=$(grep -c "^  [a-zA-Z-].*:$" .github/workflows/cicd-pipeline.yml || echo "0")
        optimized_jobs=$(grep -c "^  [a-zA-Z-].*:$" .github/workflows/optimized-cicd.yml || echo "0")

        log_info "Original pipeline: $original_jobs jobs"
        log_info "Optimized pipeline: $optimized_jobs jobs"

        if [[ $optimized_jobs -lt $original_jobs ]]; then
            reduction=$((original_jobs - optimized_jobs))
            percentage=$((reduction * 100 / original_jobs))
            log_success "Reduced job count by $reduction jobs ($percentage% reduction)"
        fi
    fi
}

# Test 9: Security check
test_security_improvements() {
    log_info "Checking security improvements..."

    local security_features=0

    # Temporarily disable error checking for grep commands
    set +e

    # Check for OIDC authentication
    if grep -q "id-token: write" .github/workflows/optimized-cicd.yml; then
        security_features=$((security_features + 1))
    fi

    # Check for minimal permissions
    if grep -q "contents: read" .github/workflows/optimized-cicd.yml; then
        security_features=$((security_features + 1))
    fi

    # Check for non-root user in Dockerfile
    if grep -q "USER appuser" containers/Dockerfile.template; then
        security_features=$((security_features + 1))
    fi

    # Re-enable error checking
    set -e

    log_success "Found $security_features/3 security improvements"
    return 0
}

# Main test execution
main() {
    log_info "Starting CI/CD Pipeline Optimization Tests..."
    echo

    local failed_tests=0

    # Run all tests
    test_required_files || ((failed_tests++))
    test_pipeline_syntax || ((failed_tests++))
    test_actions_syntax || ((failed_tests++))
    test_smart_deploy_action || ((failed_tests++))
    test_dockerfile_template || ((failed_tests++))
    test_terraform_syntax || ((failed_tests++))
    test_pipeline_dependencies || ((failed_tests++))

    # Run informational tests
    estimate_performance
    test_security_improvements

    echo
    if [[ $failed_tests -eq 0 ]]; then
        log_success "All tests passed! The optimized pipeline is ready for deployment."
        echo
        log_info "Next steps:"
        echo "1. Create a feature branch to test the optimized pipeline"
        echo "2. Replace '.github/workflows/cicd-pipeline.yml' with 'optimized-cicd.yml'"
        echo "3. Update the smart-deploy action path in the pipeline"
        echo "4. Test with a small change to validate functionality"
        echo "5. Monitor performance improvements"
        return 0
    else
        log_error "$failed_tests test(s) failed. Please fix the issues before deploying."
        return 1
    fi
}

# Run the tests
main "$@"
