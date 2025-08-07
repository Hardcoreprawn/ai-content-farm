# Makefile for AI Content Farm Project - SIMPLIFIED

.PHONY: help clean deploy-functions test-functions bootstrap-apply security-scan

ENVIRONMENT ?= staging

help:
	@echo "AI Content Farm - Simplified Makefile"
	@echo ""
	@echo "🚀 Core Deployment:"
	@echo "  deploy-functions     - Deploy Azure Functions"
	@echo "  test-functions       - Test deployed functions" 
	@echo ""
	@echo "🏗️ Infrastructure:"
	@echo "  bootstrap-apply      - Deploy bootstrap (one-time)"
	@echo "  bootstrap-apply      - Deploy bootstrap (one-time)"
	@echo "  terraform-apply      - Deploy main infrastructure"
	@echo ""
	@echo "🔒 Security:"
	@echo "  security-scan        - Run Checkov security scan"
	@echo ""
	@echo "🧹 Utilities:"
	@echo "  clean               - Remove build artifacts"
	@echo "  check-azure         - Verify Azure access"

deploy-functions:
	@echo "🚀 Deploying Azure Functions..."
	cd functions && func azure functionapp publish ai-content-$(ENVIRONMENT)-func

test-functions:
	@echo "🧪 Testing functions..."
	curl -f https://ai-content-$(ENVIRONMENT)-func.azurewebsites.net/api/GetHotTopics || echo "❌ Function not responding"

bootstrap-apply:
	@echo "🏗️ Deploying bootstrap infrastructure..."
	cd infra/bootstrap && terraform init && terraform apply -var="environment=$(ENVIRONMENT)" -auto-approve

terraform-apply:
	@echo "🔧 Deploying main infrastructure..."
	cd infra && terraform init && terraform apply -var="environment=$(ENVIRONMENT)" -auto-approve

security-scan:
	@echo "🔒 Running security scan..."
	checkov --framework terraform --directory infra/ --quiet

check-azure:
	@echo "🔍 Checking Azure access..."
	az account show --output table

clean:
	@echo "🧹 Cleaning build artifacts..."
	find . -name "*.tfplan" -delete
	find . -name ".terraform" -type d -exec rm -rf {} + 2>/dev/null || true

dev: check-azure deploy-functions test-functions
	@echo "🎯 Development deployment complete!"
