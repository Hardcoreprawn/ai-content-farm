# Makefile for AI Content Farm Project

.PHONY: help devcontainer site infra clean deploy-functions verify-functions lint-terraform checkov terraform-init terraform-validate terraform-plan terraform-format apply verify destroy

help:
	@echo "Available targets:"
	@echo "  devcontainer     - Validate devcontainer setup (list installed tools)"
	@echo "  site            - Validate Eleventy static site (build and serve)"
	@echo "  infra           - Validate Terraform setup (init & validate)"
	@echo "  verify-functions - Run full verification pipeline for Functions"
	@echo "  deploy-functions - Deploy Azure Functions after verification"
	@echo "  verify          - Run full verification pipeline (no deploy)"
	@echo "  apply           - Deploy infrastructure after verification"
	@echo "  destroy         - Destroy infrastructure"
	@echo "  clean           - Remove build artifacts"

# Terraform targets
terraform-format:
	@echo "🔧 Formatting Terraform files..."
	cd infra && terraform fmt -recursive

terraform-init:
	@echo "🔧 Initializing Terraform..."
	cd infra && terraform init -upgrade

terraform-validate:
	@echo "✅ Validating Terraform configuration..."
	cd infra && terraform validate

terraform-plan:
	@echo "📋 Planning Terraform changes..."
	cd infra && terraform plan

checkov:
	@echo "🔒 Running Checkov security scan..."
	~/.local/bin/checkov -d infra --quiet --compact
	@echo "🔒 Running Checkov on Azure Functions..."
	~/.local/bin/checkov -d azure-function-deploy --quiet --compact

lint-terraform: terraform-format terraform-validate

# Full verification pipeline for infrastructure (no deploy)
verify: checkov terraform-init lint-terraform terraform-plan
	@echo "✅ Infrastructure verification complete. Ready to deploy."

# Deploy infrastructure after verification
apply: verify
	@echo "🚀 Deploying infrastructure..."
	cd infra && terraform apply

# Destroy infrastructure
destroy:
	@echo "💥 Destroying infrastructure..."
	cd infra && terraform destroy -auto-approve

# Azure Functions targets
verify-functions:
	@echo "🔧 Verifying Azure Functions deployment..."
	@echo "✅ Checking Python syntax..."
	cd azure-function-deploy && python -m py_compile GetHotTopics/__init__.py
	@echo "✅ Validating function.json..."
	cd azure-function-deploy/GetHotTopics && python -c "import json; json.load(open('function.json'))"
	@echo "✅ Checking requirements.txt exists..."
	cd azure-function-deploy && test -f requirements.txt && echo "requirements.txt found" || echo "⚠️  requirements.txt not found"
	@echo "✅ Azure Functions verification complete."

deploy-functions: verify-functions
	@echo "🚀 Deploying Azure Functions..."
	cd azure-function-deploy && func azure functionapp publish hot-topics-func --python
	@echo "✅ Azure Functions deployment complete."

# Validate devcontainer by listing versions of key tools
devcontainer:
	@echo "Node.js version:" && node --version
	@echo "Terraform version:" && terraform --version
	@echo "Azure CLI version:" && az --version

# Validate Azure Functions app (deploy directory ready)
test-functions:
	cd azure-function-deploy && python -m py_compile GetHotTopics/__init__.py
	@echo "✅ Azure Functions code validated"

# Validate Eleventy static site
site:
	cd site && npm install && npm run build && npm run start

# Validate Terraform setup
infra:
	cd infra && terraform init && terraform validate

# Clean build artifacts
clean:
	cd site && rm -rf node_modules _site
	cd infra && rm -rf .terraform
	cd azure-function-deploy && rm -rf .python_packages __pycache__ GetHotTopics/__pycache__
