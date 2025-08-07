# Makefile for AI Content Farm Project - Updated for Key Vault Separation

.PHONY: help verify bootstrap bootstrap-init bootstrap-apply bootstrap-migrate bootstrap-plan \
        app-init app-apply app-plan setup-keyvault deploy-functions test-functions \
        security-scan check-azure clean dev staging production

ENVIRONMENT ?= staging

# Default target
.DEFAULT_GOAL := help

help:
	@echo "AI Content Farm - Updated Makefile"
	@echo ""
	@echo "🚀 Quick Start:"
	@echo "  verify              - Check all prerequisites"
	@echo "  bootstrap           - Full bootstrap setup (init + apply + migrate)"
	@echo "  deploy              - Full application deployment"
	@echo ""
	@echo "🏗️ Bootstrap Infrastructure (Run Once):"
	@echo "  bootstrap-init      - Initialize bootstrap Terraform"
	@echo "  bootstrap-plan      - Plan bootstrap changes"
	@echo "  bootstrap-apply     - Deploy bootstrap (storage + CI/CD vault)"
	@echo "  bootstrap-migrate   - Migrate bootstrap to remote state"
	@echo ""
	@echo "🔧 Application Infrastructure:"
	@echo "  app-init            - Initialize application Terraform with remote state"
	@echo "  app-plan            - Plan application changes"
	@echo "  app-apply           - Deploy application (functions + app vault)"
	@echo ""
	@echo "🔐 Secret Management:"
	@echo "  setup-keyvault      - Interactive secret configuration"
	@echo ""
	@echo "🚀 Function Deployment:"
	@echo "  deploy-functions    - Deploy Azure Functions"
	@echo "  test-functions      - Test deployed functions"
	@echo ""
	@echo "🔒 Security & Validation:"
	@echo "  security-scan       - Run Checkov security scan"
	@echo "  check-azure         - Verify Azure access"
	@echo ""
	@echo "🧹 Utilities:"
	@echo "  clean              - Remove build artifacts"
	@echo ""
	@echo "🎯 Workflows:"
	@echo "  dev                - Full development setup"
	@echo "  staging            - Deploy to staging environment"
	@echo "  production         - Deploy to production environment"

# Prerequisites Check
verify: check-azure
	@echo "🔍 Verifying prerequisites..."
	@command -v terraform >/dev/null 2>&1 || (echo "❌ Terraform not found. Please install Terraform." && exit 1)
	@command -v az >/dev/null 2>&1 || (echo "❌ Azure CLI not found. Please install Azure CLI." && exit 1)
	@command -v func >/dev/null 2>&1 || (echo "❌ Azure Functions Core Tools not found." && exit 1)
	@echo "✅ All prerequisites verified!"

# Bootstrap Infrastructure (Foundation)
bootstrap: bootstrap-init bootstrap-plan bootstrap-apply bootstrap-migrate
	@echo "🎉 Bootstrap setup complete!"

bootstrap-init:
	@echo "🏗️ Initializing bootstrap infrastructure..."
	cd infra/bootstrap && terraform init

bootstrap-plan:
	@echo "📋 Planning bootstrap changes..."
	cd infra/bootstrap && terraform plan -var="environment=$(ENVIRONMENT)"

bootstrap-apply:
	@echo "🚀 Deploying bootstrap infrastructure..."
	cd infra/bootstrap && terraform apply -var="environment=$(ENVIRONMENT)" -auto-approve

bootstrap-migrate:
	@echo "🔄 Migrating bootstrap to remote state..."
	@echo "⚠️  This will migrate bootstrap state to the storage account it created"
	@read -p "Continue? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	cd infra/bootstrap && terraform init -backend-config=backend.hcl -migrate-state

# Application Infrastructure  
deploy: app-init app-plan app-apply
	@echo "🎉 Application deployment complete!"

app-init:
	@echo "🔧 Initializing application infrastructure with remote state..."
	cd infra/application && terraform init -backend-config=backend-$(ENVIRONMENT).hcl

app-plan:
	@echo "📋 Planning application changes..."
	cd infra/application && terraform plan -var-file=$(ENVIRONMENT).tfvars

app-apply:
	@echo "🚀 Deploying application infrastructure..."
	cd infra/application && terraform apply -var-file=$(ENVIRONMENT).tfvars -auto-approve

# Secret Management
setup-keyvault:
	@echo "🔐 Setting up Key Vault secrets..."
	@scripts/setup-keyvault.sh

# Function Deployment and Testing
deploy-functions:
	@echo "🚀 Deploying Azure Functions..."
	cd functions && func azure functionapp publish ai-content-$(ENVIRONMENT)-func

test-functions:
	@echo "🧪 Testing functions..."
	@curl -f https://ai-content-$(ENVIRONMENT)-func.azurewebsites.net/api/GetHotTopics || echo "❌ Function not responding"

# Security and Validation
security-scan:
	@echo "🔒 Running security scan..."
	@checkov --framework terraform --directory infra/ --quiet || echo "⚠️  Security scan completed with findings"

# Utilities  
check-azure:
	@echo "🔍 Checking Azure access..."
	@az account show --output table || (echo "❌ Please run 'az login' first" && exit 1)

clean:
	@echo "🧹 Cleaning build artifacts..."
	@find . -name "*.tfplan" -delete 2>/dev/null || true
	@find . -name ".terraform" -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleanup complete"

# Full Development Workflow
dev: verify bootstrap deploy setup-keyvault deploy-functions test-functions
	@echo "🎯 Full development setup complete!"

# Environment-specific workflows  
staging: ENVIRONMENT=staging
staging: verify bootstrap deploy setup-keyvault
	@echo "🎯 Staging environment ready!"

production: ENVIRONMENT=production  
production: verify bootstrap deploy
	@echo "🎯 Production environment ready!"
	@echo "⚠️  Don't forget to run 'make setup-keyvault' manually for production secrets"
