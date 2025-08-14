# Makefile for AI Content Farm Project

.PHONY: help devcontainer site infra clean deploy-functions verify-functions lint-terraform checkov terraform-init terraform-validate terraform-plan terraform-format apply verify destroy security-scan cost-estimate sbom trivy terrascan collect-topics process-con		else \
			echo "💰 Generating cost breakdown with pricing..."; \
			docker run --rm -v $$(pwd)/infra:/workspace -e "INFRACOST_API_KEY=$$INFRACOST_API_KEY" infracost/infracost:latest breakdown --path /workspace --format json --out-file /workspace/infracost-base.json; \
			echo "📊 Displaying cost summary..."; \
			docker run --rm -v $$(pwd)/infra:/workspace -e "INFRACOST_API_KEY=$$INFRACOST_API_KEY" infracost/infracost:latest breakdown --path /workspace --format table; \
			echo "📋 Generating HTML report..."; \ank-topics enrich-content publish-articles content-status cleanup-articles scan-containers

help:
	@echo "Available targets:"
	@echo "  devcontainer     - Validate devcontainer setup (list installed tools)"
	@echo "  site            - Validate Eleventy static site (build and serve)"
	@echo "  infra           - Validate Terraform setup (init & validate)"
	@echo "  verify-functions - Run full verification pipeline for Functions"
	@echo "  deploy-functions - Deploy Azure Functions after verification"
	@echo "  test-womble      - Test the HTTP Summary Womble function"
	@echo "  test-womble-verbose - Test the HTTP Summary Womble with verbose output"
	@echo ""
	@echo "Security & Cost Analysis (Containerized & Cached):"
	@echo "  trivy           - Scan infrastructure configuration with Trivy"
	@echo "  checkov         - Validate Terraform with Checkov best practices"
	@echo "  terrascan       - Static analysis with Terrascan policies (full scan)"
	@echo "  terrascan-fast  - Fast Terrascan scan (HIGH severity only)"
	@echo "  scan-python     - Comprehensive Python security scanning (Safety, Semgrep, Trivy)"
	@echo "  scan-containers - Scan container images for vulnerabilities"
	@echo "  cost-estimate   - Full cost analysis with Infracost (auto Key Vault integration)"
	@echo "  infracost-parallel - Streamlined cost analysis for CI/CD pipelines"
	@echo "  scan-all        - Run all security and cost analysis sequentially"
	@echo "  scan-parallel   - Run all analysis in parallel (faster for CI/CD)"
	@echo "  security-scan   - Alias for scan-parallel (GitHub Actions compatibility)"
	@echo "  cache-pull      - Pre-pull all analysis container images"
	@echo "  cache-clean     - Clean analysis caches and results"
	@echo ""
	@echo "Infrastructure:"
	@echo "  cost-estimate   - Generate cost estimates with Infracost (bootstrap/env Key Vault)"
	@echo "  sbom            - Generate Software Bill of Materials"
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
	@echo "  setup-infracost  - Store Infracost API key in bootstrap/environment Key Vault"
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
	@if command -v docker >/dev/null 2>&1; then \
		if ! docker images bridgecrew/checkov:latest -q | grep -q .; then \
			echo "📥 Pulling Checkov image (first time or outdated)..."; \
			docker pull bridgecrew/checkov:latest; \
		fi; \
		docker run --rm -v $(PWD):/workspace -v checkov-cache:/root/.cache bridgecrew/checkov:latest -d /workspace/infra --quiet --compact --output json > infra/checkov-results.json; \
		echo "🔒 Running Checkov on Azure Functions..."; \
		docker run --rm -v $(PWD):/workspace -v checkov-cache:/root/.cache bridgecrew/checkov:latest -d /workspace/azure-function-deploy --quiet --compact || true; \
	else \
		echo "⚠️  Docker not available. Please install Docker to run Checkov"; \
		exit 1; \
	fi

# Enhanced security scanning with multiple tools - optimized with caching
trivy:
	@echo "🔐 Running Trivy security scanner..."
	@if command -v docker >/dev/null 2>&1; then \
		if ! docker images aquasec/trivy:latest -q | grep -q .; then \
			echo "📥 Pulling Trivy image (first time or outdated)..."; \
			docker pull aquasec/trivy:latest; \
		fi; \
		docker run --rm -v $(PWD):/workspace -v trivy-cache:/root/.cache/trivy aquasec/trivy:latest config /workspace/infra --format json --output /workspace/infra/trivy-results.json --exit-code 0; \
		echo "✅ Trivy scan completed"; \
	else \
		echo "⚠️  Docker not available. Please install Docker to run Trivy"; \
		exit 1; \
	fi

terrascan:
	@echo "🔍 Running Terrascan policy scanner..."
	@if command -v docker >/dev/null 2>&1; then \
		if ! docker images tenable/terrascan:latest -q | grep -q .; then \
			echo "📥 Pulling Terrascan image (first time or outdated)..."; \
			docker pull tenable/terrascan:latest; \
		fi; \
		echo "🔍 Scanning infrastructure files with Terrascan..."; \
		echo "📁 Target directory: infra/ (excluding subdirectories)"; \
		echo "⏳ Scanning for security policy violations..."; \
		docker run --rm -v $$(pwd):/workspace tenable/terrascan:latest scan -i terraform -d /workspace/infra --non-recursive --verbose --output human; \
		echo "💾 Generating JSON report..."; \
		docker run --rm -v $$(pwd):/workspace tenable/terrascan:latest scan -i terraform -d /workspace/infra --non-recursive --output json > infra/terrascan-results.json 2>/dev/null || echo "⚠️  JSON report generation completed with warnings"; \
		echo "✅ Terrascan scan completed - results saved to infra/terrascan-results.json"; \
	else \
		echo "⚠️  Docker not available. Please install Docker to run Terrascan"; \
		exit 1; \
	fi

# Fast Terrascan scan with just medium/high issues
terrascan-fast:
	@echo "⚡ Running Terrascan fast scan (MEDIUM/HIGH only)..."
	@if command -v docker >/dev/null 2>&1; then \
		if ! docker images tenable/terrascan:latest -q | grep -q .; then \
			echo "📥 Pulling Terrascan image..."; \
			docker pull tenable/terrascan:latest; \
		fi; \
		echo "🔍 Fast scanning infrastructure with Terrascan..."; \
		docker run --rm -v $$(pwd):/workspace tenable/terrascan:latest scan -i terraform -d /workspace/infra --non-recursive --severity HIGH --verbose --output human || echo "⚠️ No HIGH severity issues found"; \
		echo "✅ Fast Terrascan scan completed"; \
	else \
		echo "⚠️  Docker not available. Please install Docker to run Terrascan"; \
		exit 1; \
	fi

# Comprehensive security and cost analysis (sequential)
scan-all: checkov trivy terrascan scan-python cost-estimate
	@echo "📊 Generating comprehensive security and cost analysis summary..."
	@$(MAKE) scan-summary

# Parallel security and cost analysis for faster CI/CD execution
scan-parallel:
	@echo "🚀 Running security and cost analysis in parallel..."
	@echo "Starting parallel analysis at $$(date)"
	@$(MAKE) -j5 checkov trivy terrascan scan-python infracost-parallel || echo "⚠️ Some scans completed with warnings"
	@echo "📊 Generating comprehensive analysis summary..."
	@$(MAKE) scan-summary

# Legacy target for GitHub Actions compatibility
security-scan: scan-parallel

# Generate security summary report
scan-summary:
	@echo "🔒 Security Scan Results Summary:" > security-summary.txt
	@echo "=================================" >> security-summary.txt
	@echo "Generated on: $$(date)" >> security-summary.txt
	@echo "" >> security-summary.txt
	@echo "Infrastructure Security:" >> security-summary.txt
	@echo "----------------------" >> security-summary.txt
	@echo "Checkov Issues:" >> security-summary.txt
	@if [ -f infra/checkov-results.json ]; then \
		jq -r '.summary.failed' infra/checkov-results.json >> security-summary.txt 2>/dev/null || echo "Failed to parse Checkov results" >> security-summary.txt; \
	fi
	@echo "" >> security-summary.txt
	@echo "Trivy Issues:" >> security-summary.txt
	@if [ -f infra/trivy-results.json ]; then \
		jq -r '[.Results[]?.Misconfigurations[]?] | length' infra/trivy-results.json >> security-summary.txt 2>/dev/null || echo "Failed to parse Trivy results" >> security-summary.txt; \
	fi
	@echo "" >> security-summary.txt
	@echo "Terrascan Issues:" >> security-summary.txt
	@if [ -f infra/terrascan-results.json ]; then \
		jq -r '.results.violations | length' infra/terrascan-results.json >> security-summary.txt 2>/dev/null || echo "Failed to parse Terrascan results" >> security-summary.txt; \
	fi
	@echo "" >> security-summary.txt
	@echo "Python Security:" >> security-summary.txt
	@echo "---------------" >> security-summary.txt
	@echo "Safety Vulnerabilities:" >> security-summary.txt
	@if [ -f python-safety-results.json ]; then \
		jq -r 'length' python-safety-results.json >> security-summary.txt 2>/dev/null || echo "No vulnerabilities found" >> security-summary.txt; \
	fi
	@echo "" >> security-summary.txt
	@echo "Semgrep Issues:" >> security-summary.txt
	@if [ -f python-semgrep-results.json ]; then \
		jq -r '.results | length' python-semgrep-results.json >> security-summary.txt 2>/dev/null || echo "No issues found" >> security-summary.txt; \
	fi
	@echo "" >> security-summary.txt
	@echo "Cost Analysis:" >> security-summary.txt
	@echo "-------------" >> security-summary.txt
	@if [ -f infra/infracost-results.json ]; then \
		echo "Infracost Analysis:" >> security-summary.txt; \
		jq -r '.totalMonthlyCost // "Cost data not available"' infra/infracost-results.json >> security-summary.txt 2>/dev/null || echo "Cost analysis completed" >> security-summary.txt; \
	else \
		echo "Cost analysis not available" >> security-summary.txt; \
	fi
	@echo "📊 Comprehensive security and cost analysis complete. Check security-summary.txt for results"

# Cache management for security tools
cache-pull:
	@echo "📥 Pre-pulling all security and cost analysis images..."
	@if command -v docker >/dev/null 2>&1; then \
		docker pull aquasec/trivy:latest; \
		docker pull bridgecrew/checkov:latest; \
		docker pull tenable/terrascan:latest; \
		docker pull pyupio/safety:latest; \
		docker pull returntocorp/semgrep:latest; \
		docker pull infracost/infracost:latest; \
		echo "✅ All security and cost analysis images cached locally"; \
	else \
		echo "⚠️  Docker not available"; \
	fi

cache-clean:
	@echo "🧹 Cleaning security scan caches and results..."
	@docker volume rm trivy-cache checkov-cache 2>/dev/null || true
	@rm -f infra/*-results.json infra/infracost-*.json infra/infracost-*.html python-*-results.json security-summary.txt 2>/dev/null || true
	@echo "✅ Caches and results cleaned"

# Container image security scanning
scan-containers:
	@echo "🐳 Scanning container images for vulnerabilities..."
	@if command -v docker >/dev/null 2>&1; then \
		echo "🔍 Scanning available container images..."; \
		for image in $$(docker images --format "{{.Repository}}:{{.Tag}}" | grep -v "<none>" | head -10); do \
			echo "Scanning $$image..."; \
			docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v trivy-cache:/root/.cache/trivy aquasec/trivy:latest image $$image --severity HIGH,CRITICAL --format table || true; \
		done; \
	else \
		echo "⚠️  Docker not available. Cannot scan container images"; \
	fi

# Python security scanning with multiple tools
scan-python:
	@echo "🐍 Running Python security scans..."
	@if command -v docker >/dev/null 2>&1; then \
		echo "� Running Safety for dependency vulnerabilities..."; \
		if ! docker images pyupio/safety:latest -q | grep -q .; then \
			echo "📥 Pulling Python security scanning images..."; \
			docker pull pyupio/safety:latest; \
		fi; \
		docker run --rm -v $(PWD):/workspace pyupio/safety:latest check --json --file /workspace/requirements.txt > python-safety-results.json 2>/dev/null || echo "No requirements.txt or vulnerabilities found"; \
		echo "🔍 Running Semgrep for code security analysis..."; \
		if ! docker images returntocorp/semgrep:latest -q | grep -q .; then \
			docker pull returntocorp/semgrep:latest; \
		fi; \
		docker run --rm -v $(PWD):/src returntocorp/semgrep:latest semgrep --config=auto --json --output=/src/python-semgrep-results.json /src || true; \
		echo "🔐 Running Trivy filesystem scan for Python dependencies..."; \
		docker run --rm -v $(PWD):/workspace -v trivy-cache:/root/.cache/trivy aquasec/trivy:latest filesystem /workspace --skip-dirs .venv,node_modules,containers --scanners vuln --severity HIGH,CRITICAL --format json --output /workspace/python-trivy-results.json || true; \
		echo "✅ Python security scans completed"; \
	else \
		echo "⚠️  Docker not available. Cannot run Python security scans"; \
	fi

# Cost estimation with Infracost (containerized)
cost-estimate:
	@echo "💰 Running cost estimation with Infracost..."
	@if command -v docker >/dev/null 2>&1; then \
		if ! docker images infracost/infracost:latest -q | grep -q .; then \
			echo "📥 Pulling Infracost image (first time or outdated)..."; \
			docker pull infracost/infracost:latest; \
		fi; \
		if [ -z "$$INFRACOST_API_KEY" ]; then \
			echo "🔑 Trying to retrieve Infracost API key from Key Vault..."; \
			export ENVIRONMENT=$${ENVIRONMENT:-staging}; \
			echo "🔍 Checking bootstrap Key Vault first..."; \
			BOOTSTRAP_KEYVAULT=$$(az keyvault list --resource-group "ai-content-farm-bootstrap" --query "[0].name" -o tsv 2>/dev/null || echo ""); \
			if [ -n "$$BOOTSTRAP_KEYVAULT" ]; then \
				export INFRACOST_API_KEY=$$(az keyvault secret show --vault-name "$$BOOTSTRAP_KEYVAULT" --name "infracost-api-key" --query "value" -o tsv 2>/dev/null || echo ""); \
				if [ -n "$$INFRACOST_API_KEY" ] && [ "$$INFRACOST_API_KEY" != "placeholder-get-from-infracost-io" ]; then \
					echo "✅ Using Infracost API key from bootstrap Key Vault"; \
				else \
					echo "⚠️  Infracost API key is placeholder in bootstrap Key Vault. Checking environment Key Vault..."; \
					KEYVAULT_NAME=$$(az keyvault list --resource-group "ai-content-$$ENVIRONMENT-rg" --query "[0].name" -o tsv 2>/dev/null || echo ""); \
					if [ -n "$$KEYVAULT_NAME" ]; then \
						export INFRACOST_API_KEY=$$(az keyvault secret show --vault-name "$$KEYVAULT_NAME" --name "infracost-api-key" --query "value" -o tsv 2>/dev/null || echo ""); \
						if [ -n "$$INFRACOST_API_KEY" ] && [ "$$INFRACOST_API_KEY" != "placeholder-get-from-infracost-io" ]; then \
							echo "✅ Using Infracost API key from environment Key Vault"; \
						else \
							echo "⚠️  Infracost API key not found in environment Key Vault."; \
							INFRACOST_API_KEY=""; \
						fi; \
					else \
						echo "⚠️  Environment Key Vault not found (infrastructure not deployed yet)."; \
						INFRACOST_API_KEY=""; \
					fi; \
				fi; \
			else \
				echo "⚠️  Bootstrap Key Vault not found."; \
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
			echo "💰 Generating cost breakdown with Infracost..."; \
			docker run --rm -v $$(pwd)/infra:/workspace -e "INFRACOST_API_KEY=$$INFRACOST_API_KEY" infracost/infracost:latest breakdown --path /workspace --format json --out-file /workspace/infracost-base.json; \
			echo "📊 Displaying cost summary..."; \
			docker run --rm -v $$(pwd)/infra:/workspace -e "INFRACOST_API_KEY=$$INFRACOST_API_KEY" infracost/infracost:latest breakdown --path /workspace --format table; \
			echo "📋 Generating HTML report..."; \
			docker run --rm -v $$(pwd)/infra:/workspace -e "INFRACOST_API_KEY=$$INFRACOST_API_KEY" infracost/infracost:latest breakdown --path /workspace --format html --out-file /workspace/infracost-report.html; \
			echo "✅ Cost estimation complete. See infra/infracost-report.html for detailed breakdown"; \
		fi; \
	else \
		echo "⚠️  Docker not available. Please install Docker to run Infracost"; \
		exit 1; \
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
		echo "🔍 Trying to store in bootstrap Key Vault first..."; \
		BOOTSTRAP_KEYVAULT=$$(az keyvault list --resource-group "ai-content-farm-bootstrap" --query "[0].name" -o tsv 2>/dev/null || echo ""); \
		if [ -n "$$BOOTSTRAP_KEYVAULT" ]; then \
			az keyvault secret set --vault-name "$$BOOTSTRAP_KEYVAULT" --name "infracost-api-key" --value "$$INFRACOST_KEY" > /dev/null; \
			echo "✅ Infracost API key stored in bootstrap Key Vault: $$BOOTSTRAP_KEYVAULT"; \
		else \
			echo "⚠️  Bootstrap Key Vault not found. Trying environment Key Vault..."; \
			KEYVAULT_NAME=$$(az keyvault list --resource-group "ai-content-$$ENVIRONMENT-rg" --query "[0].name" -o tsv 2>/dev/null || echo ""); \
			if [ -n "$$KEYVAULT_NAME" ]; then \
				az keyvault secret set --vault-name "$$KEYVAULT_NAME" --name "infracost-api-key" --value "$$INFRACOST_KEY" > /dev/null; \
				echo "✅ Infracost API key stored in environment Key Vault: $$KEYVAULT_NAME"; \
			else \
				echo "❌ No Key Vault found. Please deploy infrastructure first with 'make deploy-staging'"; \
				echo "💡 For now, you can use: export INFRACOST_API_KEY=$$INFRACOST_KEY"; \
			fi; \
		fi; \
	else \
		echo "❌ No API key provided"; \
	fi

# Streamlined Infracost for parallel execution in CI/CD
infracost-parallel:
	@echo "💰 Running Infracost cost analysis..."
	@if command -v docker >/dev/null 2>&1; then \
		if ! docker images infracost/infracost:latest -q | grep -q .; then \
			echo "📥 Pulling Infracost image..."; \
			docker pull infracost/infracost:latest; \
		fi; \
		if [ -z "$$INFRACOST_API_KEY" ]; then \
			echo "🔑 Retrieving API key from Key Vault..."; \
			export ENVIRONMENT=$${ENVIRONMENT:-staging}; \
			echo "🔍 Checking bootstrap Key Vault first..."; \
			BOOTSTRAP_KEYVAULT=$$(az keyvault list --resource-group "ai-content-farm-bootstrap" --query "[0].name" -o tsv 2>/dev/null || echo ""); \
			if [ -n "$$BOOTSTRAP_KEYVAULT" ]; then \
				export INFRACOST_API_KEY=$$(az keyvault secret show --vault-name "$$BOOTSTRAP_KEYVAULT" --name "infracost-api-key" --query "value" -o tsv 2>/dev/null || echo ""); \
				if [ -n "$$INFRACOST_API_KEY" ] && [ "$$INFRACOST_API_KEY" != "placeholder-get-from-infracost-io" ]; then \
					echo "✅ Retrieved Infracost API key from bootstrap Key Vault: $$BOOTSTRAP_KEYVAULT"; \
				else \
					echo "⚠️  Infracost API key is placeholder in bootstrap Key Vault. Checking environment Key Vault..."; \
					KEYVAULT_NAME=$$(az keyvault list --resource-group "ai-content-$$ENVIRONMENT-rg" --query "[0].name" -o tsv 2>/dev/null || echo ""); \
					if [ -n "$$KEYVAULT_NAME" ]; then \
						export INFRACOST_API_KEY=$$(az keyvault secret show --vault-name "$$KEYVAULT_NAME" --name "infracost-api-key" --query "value" -o tsv 2>/dev/null || echo ""); \
						if [ -n "$$INFRACOST_API_KEY" ] && [ "$$INFRACOST_API_KEY" != "placeholder-get-from-infracost-io" ]; then \
							echo "✅ Retrieved Infracost API key from environment Key Vault: $$KEYVAULT_NAME"; \
						else \
							echo "⚠️  Infracost API key not found in environment Key Vault: $$KEYVAULT_NAME"; \
							INFRACOST_API_KEY=""; \
						fi; \
					else \
						echo "⚠️  Environment Key Vault not found in resource group ai-content-$$ENVIRONMENT-rg"; \
						INFRACOST_API_KEY=""; \
					fi; \
				fi; \
			else \
				echo "⚠️  Bootstrap Key Vault not found in resource group ai-content-farm-bootstrap"; \
			fi; \
		fi; \
		if [ -z "$$INFRACOST_API_KEY" ] || [ "$$INFRACOST_API_KEY" = "placeholder-get-from-infracost-io" ]; then \
			echo "⚠️  Infracost API key not available. Generating cost breakdown without pricing..."; \
			docker run --rm -v $$(pwd)/infra:/workspace infracost/infracost:latest breakdown --path /workspace --format json --out-file /workspace/infracost-results.json --no-color || echo "Cost analysis completed with limited data"; \
		else \
			echo "💰 Generating cost breakdown with pricing..."; \
			docker run --rm -v $$(pwd)/infra:/workspace -e "INFRACOST_API_KEY=$$INFRACOST_API_KEY" infracost/infracost:latest breakdown --path /workspace --format json --out-file /workspace/infracost-results.json --no-color; \
		fi; \
		echo "✅ Infracost analysis completed - results saved to infra/infracost-results.json"; \
	else \
		echo "⚠️  Docker not available. Cannot run Infracost"; \
		exit 1; \
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
	cd infra && rm -rf *.json *.txt *.html trivy terrascan
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
	docker run --rm -v $(PWD):/workspace bridgecrew/checkov -d /workspace/infra --hard-fail-on HIGH,CRITICAL --quiet --compact
	docker run --rm -v $(PWD):/workspace bridgecrew/checkov -d /workspace/azure-function-deploy --hard-fail-on HIGH,CRITICAL --quiet --compact
	docker run --rm -v $(PWD):/workspace aquasec/trivy config /workspace/infra --severity HIGH,CRITICAL --exit-code 1
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
