# Makefile for AI Content Farm Project - Updated for Key Vault Separation

# Testing a new commit

.PHONY: help verify bootstrap bootstrap-init bootstrap-apply bootstrap-migrate bootstrap-plan \
	app-init app-apply app-plan setup-keyvault setup-infracost deploy-functions test-functions \
	security-scan check-azure clean dev staging production \
	lint lint-yaml lint-actions cost-estimate cost-analysis \
	test test-unit test-integration test-functions-local test-all \
	test-coverage test-watch test-setup

ENVIRONMENT ?= staging

# Default target
.DEFAULT_GOAL := help

help:
	@echo "AI Content Farm - Updated Makefile"
	@echo ""
	@echo "Quick Start:"
	@echo "  verify              - Check all prerequisites"
	@echo "  bootstrap           - Full bootstrap setup (init + apply + migrate)"
	@echo "  deploy              - Full application deployment"
	@echo ""
	@echo "Testing (NEW):"
	@echo "  test                - Run all tests (unit + integration + function)"
	@echo "  test-unit           - Run unit tests only (fast, no dependencies)" 
	@echo "  test-integration    - Run integration tests (requires Azure)" 
	@echo "  test-functions-local- Run function tests locally"
	@echo "  test-coverage       - Run tests with coverage report"
	@echo "  test-watch          - Run tests in watch mode during development"
	@echo "  test-setup          - Install test dependencies"
	@echo ""
	@echo "Bootstrap Infrastructure (Run Once):"
	@echo "  bootstrap-init      - Initialize bootstrap Terraform"
	@echo "  bootstrap-plan      - Plan bootstrap changes"
	@echo "  bootstrap-apply     - Deploy bootstrap (storage + CI/CD vault)"
	@echo "  bootstrap-migrate   - Migrate bootstrap to remote state"
	@echo ""
	@echo "Application Infrastructure:"
	@echo "  app-init            - Initialize application Terraform with remote state"
	@echo "  app-plan            - Plan application changes"
	@echo "  app-apply           - Deploy application (functions + app vault)"
	@echo ""
	@echo "Secret Management:"
	@echo "  setup-keyvault      - Interactive secret configuration"
	@echo ""
	@echo "Function Deployment:"
	@echo "  deploy-functions    - Deploy Azure Functions"
	@echo "  test-functions      - Test deployed functions"
	@echo ""
	@echo "Security & Validation:"
	@echo "  security-scan       - Run Checkov security scan"
	@echo "  lint                - Run YAML and GitHub Actions lint checks"
	@echo "  check-azure         - Verify Azure access"
	@echo ""
	@echo "Cost Analysis:"
	@echo "  setup-infracost     - Store/Update Infracost API key in CI/CD Key Vault"
	@echo "  cost-estimate       - Generate local cost estimate using Infracost and usage model"
	@echo "  cost-analysis       - Alias to cost-estimate"
	@echo ""
	@echo "Utilities:"
	@echo "  clean              - Remove build artifacts"
	@echo ""
	@echo "Workflows:"
	@echo "  dev                - Full development setup"
	@echo "  staging            - Deploy to staging environment"
	@echo "  production         - Deploy to production environment"

# Prerequisites Check
verify: check-azure
	@echo "Verifying prerequisites..."
	@command -v terraform >/dev/null 2>&1 || (echo "ERROR: Terraform not found. Please install Terraform." && exit 1)
	@command -v az >/dev/null 2>&1 || (echo "ERROR: Azure CLI not found. Please install Azure CLI." && exit 1)
	@command -v func >/dev/null 2>&1 || (echo "ERROR: Azure Functions Core Tools not found." && exit 1)
	@echo "All prerequisites verified!"

# Bootstrap Infrastructure (Foundation)
bootstrap: bootstrap-init bootstrap-plan bootstrap-apply bootstrap-migrate
	@echo "Bootstrap setup complete!"

bootstrap-init:
	@echo "Initializing bootstrap infrastructure..."
	cd infra/bootstrap && terraform init

bootstrap-plan:
	@echo "Planning bootstrap changes..."
	cd infra/bootstrap && terraform plan -var="environment=$(ENVIRONMENT)"

bootstrap-apply:
	@echo "Deploying bootstrap infrastructure..."
	cd infra/bootstrap && terraform apply -var="environment=$(ENVIRONMENT)" -auto-approve

bootstrap-migrate:
	@echo "Migrating bootstrap to remote state..."
	@echo "WARNING: This will migrate bootstrap state to the storage account it created"
	@read -p "Continue? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	cd infra/bootstrap && terraform init -backend-config=backend.hcl -migrate-state

# Application Infrastructure  
deploy: app-init app-plan app-apply
	@echo "Application deployment complete!"

app-init:
	@echo "Initializing application infrastructure with remote state..."
	cd infra/application && terraform init -backend-config=backend-$(ENVIRONMENT).hcl

app-plan:
	@echo "Planning application changes..."
	cd infra/application && terraform plan -var-file=$(ENVIRONMENT).tfvars

app-apply:
	@echo "Deploying application infrastructure..."
	cd infra/application && terraform apply -var-file=$(ENVIRONMENT).tfvars -auto-approve

# Secret Management
setup-keyvault:
	@echo "Setting up Key Vault secrets..."
	@scripts/setup-keyvault.sh

# Infracost setup (wrapper around setup-keyvault; focuses on the Infracost API key path)
setup-infracost:
	@echo "Setting up Infracost API key in Key Vault..."
	@scripts/setup-keyvault.sh

# Function Deployment and Testing
deploy-functions:
	@echo "Deploying Azure Functions..."
	cd functions && func azure functionapp publish ai-content-$(ENVIRONMENT)-func

test-functions:
	@echo "Testing functions..."
	@curl -f https://ai-content-$(ENVIRONMENT)-func.azurewebsites.net/api/GetHotTopics || echo "ERROR: Function not responding"

# Security and Validation
security-scan:
	@echo "Running security scan..."
	@checkov --framework terraform --directory infra/ --quiet || echo "WARNING: Security scan completed with findings"

# Linters
lint: lint-yaml lint-actions
	@echo "Lint checks complete"

lint-yaml:
	@echo "Running yamllint..."
	@command -v yamllint >/dev/null 2>&1 || (echo "Installing yamllint locally (user site)..." && pip3 install --user yamllint)
	@yamllint -f colored .

.PHONY: fix-yaml
fix-yaml:
	@echo "Auto-fixing YAML whitespace (trailing spaces, CRLF -> LF)..."
	@find . -type f \( -name "*.yml" -o -name "*.yaml" \) -print0 | xargs -0 sed -E -i -e 's/[[:space:]]+$$//' -e 's/\r$$//'
	@echo "Done. Re-run 'make lint' to verify."

lint-actions:
	@echo "Running actionlint (GitHub Actions workflow linter)..."
	@command -v docker >/dev/null 2>&1 || (echo "ERROR: Docker is required to run actionlint locally. Skipping." && exit 0)
	@docker run --rm -v "$(PWD)":/repo -w /repo rhysd/actionlint:latest

# Cost estimation with Infracost (uses infra/* and infracost-usage.yml)
cost-estimate:
	@echo "Running local Infracost cost estimation..."
	@scripts/cost-estimate.sh

# Alias
cost-analysis: cost-estimate

# Utilities  
check-azure:
	@echo "Checking Azure access..."
	@az account show --output table || (echo "ERROR: Please run 'az login' first" && exit 1)

clean:
	@echo "Cleaning build artifacts..."
	@find . -name "*.tfplan" -delete 2>/dev/null || true
	@find . -name ".terraform" -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleanup complete"

# Full Development Workflow
dev: verify bootstrap deploy setup-keyvault deploy-functions test-functions
	@echo "Full development setup complete!"

# Testing Framework (NEW) - Comprehensive test management
test-setup:
	@echo "Installing test dependencies..."
	@pip3 install pytest pytest-cov pytest-html pytest-xdist pytest-watch requests
	@echo "Test dependencies installed"

test: test-setup
	@echo "Running all tests..."
	@pytest --tb=short --maxfail=3 -v

test-unit: test-setup
	@echo "Running unit tests (fast, no external dependencies)..."
	@pytest -m "unit" --tb=short -v

test-integration: test-setup
	@echo "Running integration tests (requires Azure connectivity)..."
	@pytest -m "integration" --tb=short -v

test-functions-local: test-setup
	@echo "Running function-level tests locally..."
	@pytest -m "function" --tb=short -v

test-coverage: test-setup
	@echo "Running tests with coverage analysis..."
	@pytest --cov=functions --cov-report=html --cov-report=term-missing --cov-report=xml

test-watch: test-setup
	@echo "Running tests in watch mode (for development)..."
	@pytest-watch --clear --runner "pytest --tb=short -v"

test-all: test-unit test-integration test-functions-local
	@echo "All test suites completed!"

# Individual function testing
test-content-ranker:
	@echo "Testing ContentRanker function..."
	@pytest functions/ContentRanker/test_content_ranker.py -v

test-content-enricher:
	@echo "Testing ContentEnricher function..."
	@pytest functions/ContentEnricher/test_content_enricher.py -v

test-summary-womble:
	@echo "Testing SummaryWomble function..."
	@pytest functions/SummaryWomble/test_summary_womble.py -v

# Test reporting and analysis
test-report:
	@echo "Generating comprehensive test report..."
	@pytest --html=test-report.html --self-contained-html --junitxml=test-results.xml

test-ci: test-setup
	@echo "Running tests for CI/CD pipeline..."
	@pytest --tb=short --maxfail=1 --junitxml=test-results.xml --cov=functions --cov-report=xml

# Test data management
test-clean:
	@echo "Cleaning test artifacts..."
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@find . -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true
	@rm -f test-report.html test-results.xml .coverage 2>/dev/null || true
	@rm -rf htmlcov/ 2>/dev/null || true
	@echo "Test cleanup complete"

# Environment-specific workflows  
staging: ENVIRONMENT=staging
staging: verify bootstrap deploy setup-keyvault
	@echo "Staging environment ready!"

production: ENVIRONMENT=production  
production: verify bootstrap deploy
	@echo "Production environment ready!"
	@echo "WARNING: Don't forget to run 'make setup-keyvault' manually for production secrets"
