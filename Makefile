# Makefile for AI Content Farm Project

.PHONY: help devcontainer site infra clean deploy-functions verify-functions lint-terraform checkov terraform-init terraform-validate terraform-plan terraform-format apply verify destroy security-scan cost-estimate sbom tfsec terrascan collect-topics process-content rank-topics enrich-content publish-articles content-status cleanup-articles

help:
	@echo "Available targets:"
	@echo "  devcontainer     - Validate devcontainer setup (list installed tools)"
	@echo "  site            - Validate Eleventy static site (build and serve)"
	@echo "  infra           - Validate Terraform setup (init & validate)"
	@echo "  verify-functions - Run full verification pipeline for Functions"
	@echo "  deploy-functions - Deploy Azure Functions after verification"
	@echo "  test-womble      - Test the HTTP Summary Womble function"
	@echo "  test-womble-verbose - Test the HTTP Summary Womble with verbose output"
	@echo "  security-scan    - Run comprehensive security scanning (Checkov, TFSec, Terrascan)"
	@echo "  cost-estimate    - Generate cost estimates with Infracost"
	@echo "  sbom             - Generate Software Bill of Materials"
	@echo "  verify          - Run full verification pipeline (security, cost, compliance)"
	@echo "  apply           - Deploy infrastructure after verification"
	@echo "  destroy         - Destroy infrastructure"
	@echo "  clean           - Remove build artifacts"
	@echo ""
	@echo "Environment-specific targets:"
	@echo "  deploy-staging   - Deploy to staging environment (develop branch)"
	@echo "  deploy-production - Deploy to production environment (main branch only)"
	@echo "  test-staging     - Run tests against staging environment"
	@echo "  test-production  - Run tests against production environment"
	@echo "  rollback-staging - Rollback staging deployment"
	@echo "  rollback-production - Rollback production deployment"
	@echo ""
	@echo "Key Vault integration:"
	@echo "  setup-keyvault   - Configure secrets in Azure Key Vault"
	@echo "  get-secrets      - Retrieve secrets from Key Vault for local development"
	@echo "  validate-secrets - Validate Key Vault secret configuration"
	@echo ""
	@echo "Content processing:"
	@echo "  collect-topics   - Run content wombles to collect topics"
	@echo "  process-content  - Run full content processing pipeline"
	@echo "  rank-topics      - Rank collected topics for publishing"
	@echo "  enrich-content   - Enrich ranked topics with research"
	@echo "  publish-articles - Generate markdown articles for site"
	@echo "  content-status   - Show content processing status"
	@echo "  cleanup-articles - Remove duplicate articles from site"
	@echo "  setup-github-secrets - Configure GitHub secrets for Azure auth (deprecated)"
	@echo "  setup-azure-oidc - Setup Azure OIDC for GitHub Actions (recommended)"
	@echo "  bootstrap-azure  - Bootstrap infrastructure with OIDC via Terraform"
	@echo "  setup-azure-sp   - Show Azure Service Principal setup instructions"

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
	~/.local/bin/checkov -d infra --quiet --compact --output cli --output json --output-file-path infra/checkov-results.json
	@echo "🔒 Running Checkov on Azure Functions..."
	~/.local/bin/checkov -d azure-function-deploy --quiet --compact

# Enhanced security scanning with multiple tools
tfsec:
	@echo "🔐 Running TFSec security scanner..."
	@if command -v tfsec >/dev/null 2>&1; then \
		cd infra && tfsec . --format json --out tfsec-results.json --soft-fail; \
		echo "✅ TFSec scan completed"; \
	else \
		echo "⚠️  TFSec not installed. Installing..."; \
		curl -s https://raw.githubusercontent.com/aquasecurity/tfsec/master/scripts/install_linux.sh | bash; \
		cd infra && tfsec . --format json --out tfsec-results.json --soft-fail; \
	fi

terrascan:
	@echo "🔍 Running Terrascan policy scanner..."
	@if command -v terrascan >/dev/null 2>&1; then \
		cd infra && terrascan scan -i terraform --output json > terrascan-results.json || true; \
		echo "✅ Terrascan scan completed"; \
	else \
		echo "⚠️  Terrascan not installed. Installing..."; \
		LATEST_URL=$$(curl -s https://api.github.com/repos/tenable/terrascan/releases/latest | grep -o -E "https://.*Linux_x86_64.tar.gz" | head -1); \
		curl -L "$$LATEST_URL" > terrascan.tar.gz; \
		tar -xf terrascan.tar.gz terrascan && rm terrascan.tar.gz; \
		sudo mv terrascan /usr/local/bin; \
		cd infra && terrascan scan -i terraform --output json > terrascan-results.json || true; \
	fi

# Comprehensive security scan combining all tools
security-scan: checkov tfsec terrascan
	@echo "📊 Generating security scan summary..."
	@echo "🔒 Security Scan Results Summary:" > infra/security-summary.txt
	@echo "=================================" >> infra/security-summary.txt
	@echo "" >> infra/security-summary.txt
	@echo "Checkov Issues:" >> infra/security-summary.txt
	@if [ -f infra/checkov-results.json ]; then \
		jq -r '.summary.failed' infra/checkov-results.json >> infra/security-summary.txt 2>/dev/null || echo "Failed to parse Checkov results" >> infra/security-summary.txt; \
	fi
	@echo "" >> infra/security-summary.txt
	@echo "TFSec Issues:" >> infra/security-summary.txt
	@if [ -f infra/tfsec-results.json ]; then \
		jq -r '.results | length' infra/tfsec-results.json >> infra/security-summary.txt 2>/dev/null || echo "Failed to parse TFSec results" >> infra/security-summary.txt; \
	fi
	@echo "" >> infra/security-summary.txt
	@echo "Terrascan Issues:" >> infra/security-summary.txt
	@if [ -f infra/terrascan-results.json ]; then \
		jq -r '.results.violations | length' infra/terrascan-results.json >> infra/security-summary.txt 2>/dev/null || echo "Failed to parse Terrascan results" >> infra/security-summary.txt; \
	fi
	@echo "📊 Security scan complete. Check infra/security-summary.txt for results"

# Cost estimation with Infracost
cost-estimate:
	@echo "💰 Running cost estimation with Infracost..."
	@if command -v infracost >/dev/null 2>&1; then \
		if [ -z "$$INFRACOST_API_KEY" ]; then \
			echo "🔑 Trying to retrieve Infracost API key from Key Vault..."; \
			export ENVIRONMENT=$${ENVIRONMENT:-staging}; \
			KEYVAULT_NAME=$$(az keyvault list --resource-group "ai-content-farm-$$ENVIRONMENT" --query "[0].name" -o tsv 2>/dev/null || echo ""); \
			if [ -n "$$KEYVAULT_NAME" ]; then \
				export INFRACOST_API_KEY=$$(az keyvault secret show --vault-name "$$KEYVAULT_NAME" --name "infracost-api-key" --query "value" -o tsv 2>/dev/null || echo ""); \
				if [ -n "$$INFRACOST_API_KEY" ] && [ "$$INFRACOST_API_KEY" != "placeholder-get-from-infracost-io" ]; then \
					echo "✅ Using Infracost API key from Key Vault"; \
				else \
					echo "⚠️  Infracost API key not found in Key Vault."; \
					INFRACOST_API_KEY=""; \
				fi; \
			else \
				echo "⚠️  Key Vault not found (infrastructure not deployed yet)."; \
			fi; \
		fi; \
		if [ -z "$$INFRACOST_API_KEY" ]; then \
			echo ""; \
			echo "💡 To set up Infracost API key:"; \
			echo "   1. Get your API key from https://dashboard.infracost.io"; \
			echo "   2. Set it as environment variable: export INFRACOST_API_KEY=your-key"; \
			echo "   3. Or store in Key Vault after deploying: make setup-infracost"; \
			echo ""; \
			echo "❌ Infracost API key required. Skipping cost estimation."; \
		else \
			cd infra && infracost breakdown --path . --format json --out-file infracost-base.json; \
			infracost breakdown --path . --format table; \
			infracost breakdown --path . --format html --out-file infracost-report.html; \
			echo "✅ Cost estimation complete. See infracost-report.html for detailed breakdown"; \
		fi; \
	else \
		echo "⚠️  Infracost not installed. Installing..."; \
		curl -fsSL https://raw.githubusercontent.com/infracost/infracost/master/scripts/install.sh | sh; \
		echo "After installation, set INFRACOST_API_KEY environment variable and retry"; \
	fi

# Setup Infracost API key in Key Vault
setup-infracost:
	@echo "💰 Setting up Infracost API key in Key Vault..."
	@echo "📋 To get an Infracost API key:"
	@echo "   1. Visit https://dashboard.infracost.io"
	@echo "   2. Sign up/login with your email or GitHub"
	@echo "   3. Copy your API key from the settings"
	@echo ""
	@read -p "Enter your Infracost API key: " INFRACOST_KEY; \
	if [ -n "$$INFRACOST_KEY" ]; then \
		export ENVIRONMENT=$${ENVIRONMENT:-staging}; \
		KEYVAULT_NAME=$$(az keyvault list --resource-group "ai-content-farm-$$ENVIRONMENT" --query "[0].name" -o tsv 2>/dev/null || echo ""); \
		if [ -n "$$KEYVAULT_NAME" ]; then \
			az keyvault secret set --vault-name "$$KEYVAULT_NAME" --name "infracost-api-key" --value "$$INFRACOST_KEY" > /dev/null; \
			echo "✅ Infracost API key stored in Key Vault: $$KEYVAULT_NAME"; \
		else \
			echo "❌ Key Vault not found. Please deploy infrastructure first with 'make deploy-staging'"; \
			echo "💡 For now, you can use: export INFRACOST_API_KEY=$$INFRACOST_KEY"; \
		fi; \
	else \
		echo "❌ No API key provided"; \
	fi

# Help users get started with Infracost before deployment
infracost-help:
	@echo "💰 Infracost Setup Guide"
	@echo "======================="
	@echo ""
	@echo "Before deploying infrastructure:"
	@echo "  1. Get API key: https://dashboard.infracost.io"
	@echo "  2. Export key: export INFRACOST_API_KEY=your-key"
	@echo "  3. Test costs: make cost-estimate"
	@echo "  4. Deploy: make deploy-staging"
	@echo ""
	@echo "After deploying infrastructure:"
	@echo "  1. Store in Key Vault: make setup-infracost" 
	@echo "  2. Future cost estimates use Key Vault automatically"
	@echo ""

# Quick setup for existing Infracost API key
setup-infracost-env:
	@echo "🔧 Setting up Infracost API key from environment..."
	@if [ -z "$$INFRACOST_API_KEY" ]; then \
		echo "❌ INFRACOST_API_KEY environment variable not set"; \
		echo "💡 Please set it first: export INFRACOST_API_KEY=your-key"; \
		echo "💡 Or check your existing variables with: env | grep INFRACOST"; \
		exit 1; \
	fi
	@echo "✅ INFRACOST_API_KEY is set (ending in: ...$(shell echo $$INFRACOST_API_KEY | tail -c 5))"
	@echo "🧪 Testing Infracost authentication..."
	@if infracost auth status > /dev/null 2>&1; then \
		echo "✅ Infracost already authenticated"; \
	else \
		echo "🔐 Authenticating with Infracost..."; \
		echo "$$INFRACOST_API_KEY" | infracost configure set api_key; \
	fi
	@echo "✅ Infracost setup complete"

# Check what Infracost-related variables you have
check-infracost-vars:
	@echo "🔍 Checking for Infracost-related environment variables..."
	@env | grep -i infra || echo "No INFRA* variables found"
	@env | grep -i cost || echo "No COST* variables found"
	@if [ -n "$$INFRACOST_API_KEY" ]; then \
		echo "✅ INFRACOST_API_KEY is set (ending in: ...$(shell echo $$INFRACOST_API_KEY | tail -c 5))"; \
	else \
		echo "❌ INFRACOST_API_KEY not set"; \
	fi

# Interactive cost calculator for different usage scenarios
cost-calculator:
	@echo "🧮 Running AI Content Farm cost calculator..."
	@python3 scripts/cost-calculator.py

# Comprehensive cost analysis including calculator and Infracost  
cost-analysis: cost-estimate cost-calculator
	@echo "📊 Complete cost analysis finished"
	@echo "📄 See docs/cost-analysis.md for detailed breakdown"
	@echo "🌐 See infracost-report.html for interactive report"

# Generate Software Bill of Materials (SBOM)
sbom:
	@echo "📋 Generating Software Bill of Materials..."
	@echo "Creating SBOM for Python dependencies..."
	@if command -v syft >/dev/null 2>&1; then \
		cd azure-function-deploy && syft . -o json=sbom-python.json -o table; \
		echo "✅ Python SBOM generated: azure-function-deploy/sbom-python.json"; \
	else \
		echo "⚠️  Syft not installed. Installing..."; \
		curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sudo sh -s -- -b /usr/local/bin; \
		cd azure-function-deploy && syft . -o json=sbom-python.json -o table; \
	fi
	@echo "Creating dependency list for Node.js components..."
	@if [ -f site/package.json ]; then \
		cd site && npm list --json > ../sbom-nodejs.json 2>/dev/null || true; \
		echo "✅ Node.js dependencies listed: sbom-nodejs.json"; \
	fi
	@echo "Creating infrastructure SBOM..."
	@echo "Infrastructure Components:" > infra/sbom-infrastructure.txt
	@echo "=========================" >> infra/sbom-infrastructure.txt
	@cd infra && grep -r "azurerm_" *.tf | cut -d'"' -f2 | sort -u >> sbom-infrastructure.txt
	@echo "✅ Infrastructure SBOM generated: infra/sbom-infrastructure.txt"

lint-terraform: terraform-format terraform-validate

# Full verification pipeline for infrastructure (security, cost, compliance)
verify: terraform-init lint-terraform security-scan cost-estimate sbom terraform-plan
	@echo "📊 Generating comprehensive deployment report..."
	@echo "=== DEPLOYMENT READINESS REPORT ===" > infra/deployment-report.txt
	@echo "Generated: $(shell date)" >> infra/deployment-report.txt
	@echo "" >> infra/deployment-report.txt
	@echo "🔒 SECURITY STATUS:" >> infra/deployment-report.txt
	@if [ -f infra/security-summary.txt ]; then cat infra/security-summary.txt >> infra/deployment-report.txt; fi
	@echo "" >> infra/deployment-report.txt
	@echo "💰 COST ESTIMATION:" >> infra/deployment-report.txt
	@if [ -f infra/infracost-base.json ]; then \
		echo "Monthly cost estimate available in infracost-report.html" >> infra/deployment-report.txt; \
	else \
		echo "Cost estimation not available" >> infra/deployment-report.txt; \
	fi
	@echo "" >> infra/deployment-report.txt
	@echo "📋 SBOM STATUS:" >> infra/deployment-report.txt
	@echo "- Python SBOM: azure-function-deploy/sbom-python.json" >> infra/deployment-report.txt
	@echo "- Infrastructure SBOM: infra/sbom-infrastructure.txt" >> infra/deployment-report.txt
	@if [ -f sbom-nodejs.json ]; then echo "- Node.js SBOM: sbom-nodejs.json" >> infra/deployment-report.txt; fi
	@echo "" >> infra/deployment-report.txt
	@echo "✅ Verification complete. Check infra/deployment-report.txt for full summary."
	@echo "🚀 Infrastructure is ready for deployment."

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
	cd azure-function-deploy && python -m py_compile SummaryWomble/__init__.py
	@echo "✅ Validating function.json files..."
	cd azure-function-deploy/GetHotTopics && python -c "import json; json.load(open('function.json'))"
	cd azure-function-deploy/SummaryWomble && python -c "import json; json.load(open('function.json'))"
	@echo "✅ Checking requirements.txt exists..."
	cd azure-function-deploy && test -f requirements.txt && echo "requirements.txt found" || echo "⚠️  requirements.txt not found"
	@echo "✅ Azure Functions verification complete."

deploy-functions: verify-functions
	@echo "🚀 Deploying Azure Functions..."
	cd azure-function-deploy && func azure functionapp publish hot-topics-func --python
	@echo "✅ Azure Functions deployment complete."

# Test the HTTP Summary Womble function
test-womble:
	@echo "🧪 Testing Summary Womble HTTP function..."
	@echo "📤 Sending test request with technology subreddit only..."
	curl -X POST \
		-H "Content-Type: application/json" \
		-d '{"source": "reddit", "topics": ["technology"], "limit": 5, "credentials": {"source": "keyvault"}}' \
		"https://hot-topics-func.azurewebsites.net/api/SummaryWomble" \
		| jq '.' || echo "⚠️  Response is not valid JSON or jq not available"
	@echo "✅ Test request sent. Check Azure logs for results."

# Test the HTTP Summary Womble function with local curl (more detailed)
test-womble-verbose:
	@echo "🧪 Testing Summary Womble HTTP function (verbose)..."
	@echo "📤 Request payload:"
	@echo '{"source": "reddit", "topics": ["technology", "programming"], "limit": 3, "credentials": {"source": "keyvault"}}' | jq '.'
	@echo "📤 Sending request..."
	curl -v -X POST \
		-H "Content-Type: application/json" \
		-d '{"source": "reddit", "topics": ["technology", "programming"], "limit": 3, "credentials": {"source": "keyvault"}}' \
		"https://hot-topics-func.azurewebsites.net/api/SummaryWomble"

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

# Clean build artifacts and security scan results
clean:
	cd site && rm -rf node_modules _site
	cd infra && rm -rf .terraform
	cd infra && rm -rf *.json *.txt *.html tfsec terrascan
	cd azure-function-deploy && rm -rf .python_packages __pycache__ GetHotTopics/__pycache__ SummaryWomble/__pycache__
	cd azure-function-deploy && rm -f *.json
	rm -f sbom-nodejs.json latest_tech.json
	@echo "🧹 All build artifacts and scan results cleaned"

# Environment-specific deployment targets
deploy-staging: verify-staging
	@echo "🚀 Deploying to staging environment..."
	@if [ "$(shell git branch --show-current)" != "develop" ] && [ ! "$(shell git branch --show-current)" = "feature/"* ]; then \
		echo "❌ Staging deployment only allowed from develop or feature/ branches"; \
		exit 1; \
	fi
	cd infra && terraform workspace select staging || terraform workspace new staging
	cd infra && terraform plan -var-file="staging.tfvars"
	cd infra && terraform apply -auto-approve -var-file="staging.tfvars"
	@echo "✅ Staging infrastructure deployment complete"
	@echo "🔐 Next step: Configure secrets with 'make setup-keyvault'"

# Staging-specific verification (more flexible than full verify)
verify-staging: terraform-init lint-terraform security-scan cost-estimate-optional sbom terraform-plan-staging
	@echo "📊 Staging verification complete"
	@echo "🚀 Infrastructure is ready for staging deployment"

# Optional cost estimation that doesn't fail deployment
cost-estimate-optional:
	@echo "💰 Running optional cost estimation..."
	@if [ -n "$$INFRACOST_API_KEY" ]; then \
		echo "✅ INFRACOST_API_KEY found, running cost estimation"; \
		$(MAKE) cost-estimate; \
	else \
		echo "⚠️  INFRACOST_API_KEY not set, skipping cost estimation"; \
		echo "💡 To enable cost estimation: export INFRACOST_API_KEY=your-key"; \
		echo "💡 Or get your key from: https://dashboard.infracost.io"; \
	fi

# Terraform plan for staging
terraform-plan-staging:
	@echo "📋 Planning Terraform changes for staging..."
	cd infra && terraform plan -var-file="staging.tfvars"

deploy-production: verify
	@echo "🎯 Deploying to production environment..."
	@if [ "$(shell git branch --show-current)" != "main" ]; then \
		echo "❌ Production deployment only allowed from main branch"; \
		exit 1; \
	fi
	@echo "⚠️  This will deploy to PRODUCTION. Continue? [y/N]" && read ans && [ $${ans:-N} = y ]
	cd infra && terraform workspace select production || terraform workspace new production
	cd infra && terraform plan -var="environment=production" -var="resource_prefix=ai-content-prod"
	cd infra && terraform apply -var="environment=production" -var="resource_prefix=ai-content-prod"
	cd azure-function-deploy && func azure functionapp publish hot-topics-func --python
	@echo "✅ Production deployment complete: https://hot-topics-func.azurewebsites.net"

# Environment-specific testing
test-staging:
	@echo "🧪 Testing staging environment..."
	@echo "📤 Testing Summary Womble on staging..."
	curl -f -X POST \
		-H "Content-Type: application/json" \
		-d '{"source": "test", "topics": ["technology"], "limit": 2}' \
		"https://ai-content-staging-func.azurewebsites.net/api/SummaryWomble" \
		| jq '.' || echo "⚠️  Staging test failed"
	@echo "✅ Staging tests complete"

test-production:
	@echo "🧪 Testing production environment..."
	@echo "📤 Testing Summary Womble on production (minimal test)..."
	curl -f -X POST \
		-H "Content-Type: application/json" \
		-d '{"source": "test", "limit": 1}' \
		"https://hot-topics-func.azurewebsites.net/api/SummaryWomble" > /dev/null
	@echo "✅ Production smoke test complete"

# Rollback capabilities
rollback-staging:
	@echo "🔄 Rolling back staging deployment..."
	@echo "⚠️  This will rollback staging to previous state. Continue? [y/N]" && read ans && [ $${ans:-N} = y ]
	cd infra && terraform workspace select staging
	cd infra && terraform apply -auto-approve -refresh-only
	@echo "ℹ️  Manual rollback: Check previous git tags and redeploy from desired commit"

rollback-production:
	@echo "🚨 Rolling back production deployment..."
	@echo "⚠️  This will rollback PRODUCTION. This should only be done in emergencies. Continue? [y/N]" && read ans && [ $${ans:-N} = y ]
	cd infra && terraform workspace select production
	cd infra && terraform apply -auto-approve -refresh-only
	@echo "🚨 EMERGENCY: Manual rollback required - check previous production tags and redeploy"

# Security validation for different environments
security-scan-strict:
	@echo "🔒 Running strict security scan for production..."
	~/.local/bin/checkov -d infra --hard-fail-on HIGH,CRITICAL --quiet --compact
	~/.local/bin/checkov -d azure-function-deploy --hard-fail-on HIGH,CRITICAL --quiet --compact
	cd infra && tfsec . --minimum-severity HIGH
	@echo "✅ Strict security validation passed"

# Key Vault integration targets
setup-keyvault:
	@echo "🔐 Setting up Azure Key Vault secrets..."
	@if [ ! -f scripts/setup-keyvault.sh ]; then \
		echo "❌ Key Vault setup script not found"; \
		exit 1; \
	fi
	@scripts/setup-keyvault.sh

get-secrets:
	@echo "🔍 Retrieving secrets from Azure Key Vault..."
	@echo "Getting Key Vault name from current environment..."
	@KEYVAULT_NAME=$$(az keyvault list --resource-group "ai-content-dev-rg" --query "[0].name" -o tsv 2>/dev/null || echo ""); \
	if [ -z "$$KEYVAULT_NAME" ]; then \
		echo "❌ Key Vault not found. Please deploy infrastructure first."; \
		exit 1; \
	fi; \
	echo "📋 Key Vault: $$KEYVAULT_NAME"; \
	echo "Available secrets:"; \
	az keyvault secret list --vault-name "$$KEYVAULT_NAME" --query "[].name" -o table

validate-secrets:
	@echo "✅ Validating Key Vault secret configuration..."
	@KEYVAULT_NAME=$$(az keyvault list --resource-group "ai-content-dev-rg" --query "[0].name" -o tsv 2>/dev/null || echo ""); \
	if [ -z "$$KEYVAULT_NAME" ]; then \
		echo "❌ Key Vault not found. Please deploy infrastructure first."; \
		exit 1; \
	fi; \
	echo "Checking required secrets in $$KEYVAULT_NAME..."; \
	MISSING_SECRETS=""; \
	for secret in reddit-client-id reddit-client-secret reddit-user-agent infracost-api-key; do \
		if ! az keyvault secret show --vault-name "$$KEYVAULT_NAME" --name "$$secret" >/dev/null 2>&1; then \
			MISSING_SECRETS="$$MISSING_SECRETS $$secret"; \
		else \
			echo "✅ $$secret: Found"; \
		fi; \
	done; \
	if [ -n "$$MISSING_SECRETS" ]; then \
		echo "⚠️  Missing secrets:$$MISSING_SECRETS"; \
		echo "Run 'make setup-keyvault' to configure missing secrets"; \
	else \
		echo "🎉 All required secrets are configured!"; \
	fi

# Content processing targets
collect-topics:
	@echo "🕷️ Running content wombles to collect topics..."
	cd content_wombles && python3 run_all_wombles.py
	@echo "✅ Topic collection complete"

process-content:
	@echo "🏭 Running full content processing pipeline..."
	cd content_processor && python3 -m pip install -r requirements.txt --quiet
	cd content_processor && python3 pipeline.py --mode full --max-articles 5
	@echo "✅ Content processing complete"

rank-topics:
	@echo "📊 Ranking collected topics..."
	cd content_processor && python3 -m pip install -r requirements.txt --quiet
	cd content_processor && python3 pipeline.py --mode rank --hours-back 24 --min-score 0.3
	@echo "✅ Topic ranking complete"

enrich-content:
	@echo "🔍 Enriching topics with research..."
	@if [ -z "$(FILE)" ]; then \
		echo "❌ Please specify input file: make enrich-content FILE=ranked_topics_file.json"; \
		exit 1; \
	fi
	cd content_processor && python3 -m pip install -r requirements.txt --quiet
	cd content_processor && python3 pipeline.py --mode enrich --input-file $(FILE)
	@echo "✅ Content enrichment complete"

publish-articles:
	@echo "📝 Publishing articles to site..."
	@if [ -z "$(FILE)" ]; then \
		echo "❌ Please specify input file: make publish-articles FILE=enriched_topics_file.json"; \
		exit 1; \
	fi
	cd content_processor && python3 -m pip install -r requirements.txt --quiet
	cd content_processor && python3 pipeline.py --mode publish --input-file $(FILE) --max-articles $(or $(MAX_ARTICLES),5)
	@echo "✅ Article publishing complete"

content-status:
	@echo "📈 Content processing status..."
	cd content_processor && python3 -m pip install -r requirements.txt --quiet
	cd content_processor && python3 pipeline.py --mode status

# Cleanup duplicate articles in published content
cleanup-articles:
	@echo "🧹 Cleaning up duplicate articles..."
	cd content_processor && python3 -m pip install -r requirements.txt --quiet
	cd content_processor && python3 content_publisher.py --cleanup-only
	@echo "✅ Cleanup complete!"

# Setup GitHub secrets for Azure authentication  
setup-github-secrets:
	@echo "⚠️  DEPRECATED: Use OIDC setup instead for better security"
	@echo "🔐 Setting up GitHub secrets for Azure authentication..."
	@echo "This will configure the minimal secrets needed for Key Vault integration"
	./scripts/setup-github-secrets.sh

# Setup Azure OIDC for GitHub Actions (recommended)
setup-azure-oidc:
	@echo "🔐 Setting up Azure OIDC for GitHub Actions..."
	@echo "This is the modern, secure approach using managed identity"
	./scripts/setup-azure-oidc.sh

# Bootstrap Azure infrastructure with OIDC (IaC approach)
bootstrap-azure:
	@echo "🚀 Bootstrapping Azure infrastructure with OIDC..."
	@echo "This will create the Azure AD app and infrastructure via Terraform"
	cd infra && terraform init
	cd infra && terraform plan -var-file="staging.tfvars"
	cd infra && terraform apply -var-file="staging.tfvars" -auto-approve
	@echo ""
	@echo "✅ Infrastructure deployed! Now setting GitHub variables:"
	cd infra && terraform output github_variables_setup_command

# Show required Azure service principal setup
setup-azure-sp:
	@echo "🔧 Azure Service Principal Setup"
	@echo "================================="
	@echo ""
	@echo "1. Create a service principal:"
	@echo "   az ad sp create-for-rbac --name 'ai-content-farm-github' \\"
	@echo "     --role contributor \\"
	@echo "     --scopes /subscriptions/YOUR_SUBSCRIPTION_ID"
	@echo ""
	@echo "2. Note down these values for GitHub secrets:"
	@echo "   - appId (ARM_CLIENT_ID)"
	@echo "   - password (ARM_CLIENT_SECRET)"
	@echo "   - tenant (ARM_TENANT_ID)"
	@echo "   - Your subscription ID (ARM_SUBSCRIPTION_ID)"
	@echo ""
	@echo "3. Run: make setup-github-secrets"
	@echo ""
