# Makefile for AI Content Farm Project

.PHONY: help devcontainer site infra clean deploy-functions verify-functions lint-terraform checkov terraform-init terraform-validate terraform-plan terraform-format apply verify destroy security-scan cost-estimate sbom trivy terrascan collect-topics process-content rank-topics enrich-content publish-articles content-status cleanup-articles scan-containers yamllint actionlint lint-workflows lint-actions check-emojis lint-python lint-python-all flake8 black-check black-format isort-check isort-format mypy pylint format-python lint-container lint-all quality-check

help:
	@echo "Available targets:"
	@echo "  devcontainer     - Validate devcontainer setup (list installed tools)"
	@echo "  site            - Validate Eleventy static site (build and serve)"
	@echo "  infra           - Validate Terraform setup (init & validate)"
	@echo "  verify-containers - Run full verification pipeline for Container Apps"
	@echo "  deploy-containers - Deploy Container Apps after verification"
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
	@echo "Code Quality & Linting:"
	@echo "  quality-check    - Run quality checks matching GitHub Actions (smart file detection)"
	@echo "  lint-all         - Run all linting checks (workflows + Python)"
	@echo "  lint-workflows   - Lint GitHub Actions YAML files (yamllint + actionlint)"
	@echo "  lint-python      - Run Python linting (flake8 + black + isort) [shared with CI]"
	@echo "  lint-python-all  - Run all Python checks including types and complexity"
	@echo "  flake8           - Python code style and error checking"
	@echo "  black-check      - Check Python code formatting (no changes)"
	@echo "  black-format     - Auto-format Python code with black"
	@echo "  isort-check      - Check import sorting (no changes)"
	@echo "  isort-format     - Auto-sort Python imports"
	@echo "  mypy             - Python type checking"
	@echo "  pylint           - Python code analysis (complexity)"
	@echo "  format-python    - Auto-format Python code (black + isort)"
	@echo "  lint-container   - Lint specific container: make lint-container CONTAINER=content-generator"
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
	@echo "Formatting Terraform files..."
	cd infra && terraform fmt -recursive

terraform-init:
	@echo "Initializing Terraform..."
	cd infra && terraform init -upgrade

terraform-validate:
	@echo "Validating Terraform configuration..."
	cd infra && terraform validate

terraform-plan:
	@echo "Planning Terraform changes..."
	cd infra && terraform plan

# Workflow linting targets
yamllint:
	@echo "Running yamllint on GitHub Actions..."
	@if command -v docker >/dev/null 2>&1; then \
		docker run --rm -v $(PWD):/workspace cytopia/yamllint:latest -c /workspace/.yamllint.yml /workspace/.github/; \
	else \
		echo "Docker not available, skipping yamllint"; \
	fi

actionlint:
	@echo "Running actionlint on GitHub Actions..."
	@if [ ! -f ./actionlint ]; then \
		echo "Downloading actionlint..."; \
		curl -L -o actionlint.tar.gz https://github.com/rhysd/actionlint/releases/download/v1.7.7/actionlint_1.7.7_linux_amd64.tar.gz; \
		tar --extract --file=actionlint.tar.gz actionlint; \
		rm actionlint.tar.gz; \
	fi
	@./actionlint -color

check-emojis:
	@echo "Checking YAML files for emojis..."
	@./scripts/check-emojis.sh

lint-workflows: yamllint actionlint check-emojis

lint-actions: actionlint
	@echo "Running comprehensive GitHub Actions linting..."
	@echo "✅ ActionLint completed"
	@echo "Running shellcheck on embedded shell scripts..."
	@# Note: actionlint already runs shellcheck on embedded scripts in YAML
	@echo "✅ All GitHub Actions linting completed"

# Python linting targets (using shared script for CI/CD consistency)
lint-python: ## Run all Python linting (flake8 + black + isort)
	@./scripts/code-quality.sh

lint-python-all: ## Run all Python linting including types and complexity
	@./scripts/code-quality.sh --all

flake8: ## Python code style and error checking
	@./scripts/code-quality.sh --linting

black-check: ## Check Python code formatting (no changes)
	@./scripts/code-quality.sh --formatting

black-format: ## Auto-format Python code with black
	@./scripts/code-quality.sh --formatting --fix

isort-check: ## Check import sorting (no changes)
	@./scripts/code-quality.sh --imports

isort-format: ## Auto-sort Python imports
	@./scripts/code-quality.sh --imports --fix

mypy: ## Python type checking
	@./scripts/code-quality.sh --types

pylint: ## Python code analysis (complexity)
	@./scripts/code-quality.sh --complexity

# Python formatting (auto-fix)
format-python: ## Auto-format Python code (black + isort)
	@./scripts/code-quality.sh --fix

# Container-specific linting (using shared script)
lint-container: ## Lint specific container: make lint-container CONTAINER=content-generator
	@if [ -z "$(CONTAINER)" ]; then \
		echo "❌ Usage: make lint-container CONTAINER=container-name"; \
		echo "Available containers: content-collector, content-processor, content-enricher, content-ranker, content-generator, markdown-generator, site-generator"; \
		exit 1; \
	fi
	@if [ ! -d "containers/$(CONTAINER)" ]; then \
		echo "❌ Container 'containers/$(CONTAINER)' not found"; \
		exit 1; \
	fi
	@echo "Linting container: $(CONTAINER)"
	@cd containers/$(CONTAINER) && ../../scripts/code-quality.sh

# Quality checks matching GitHub Actions
quality-check: ## Run the same quality checks as GitHub Actions
	@echo "🔍 Running quality checks (same as GitHub Actions)..."
	@echo "📁 Checking for Python file changes..."
	@if [ -d .git ] && [ -n "$$(git status --porcelain | grep -E '\.(py)$$|requirements.*\.txt$$|pyproject\.toml$$|\.flake8$$|scripts/code-quality\.sh$$')" ]; then \
		echo "🐍 Running Python quality checks..."; \
		./scripts/code-quality.sh; \
	elif [ ! -d .git ]; then \
		echo "🐍 No git repo detected, running Python quality checks..."; \
		./scripts/code-quality.sh; \
	else \
		echo "⏭️  No Python files changed, skipping Python checks"; \
	fi
	@echo "📁 Checking for workflow file changes..."
	@if [ -d .git ] && [ -n "$$(git status --porcelain | grep -E '\.github/(workflows|actions)/.*\.(yml|yaml)$$')" ]; then \
		echo "⚙️  Running workflow quality checks..."; \
		$(MAKE) lint-workflows; \
	elif [ ! -d .git ]; then \
		echo "⚙️  No git repo detected, running workflow quality checks..."; \
		$(MAKE) lint-workflows; \
	else \
		echo "⏭️  No workflow files changed, skipping workflow checks"; \
	fi
	@echo "✅ Quality checks completed (GitHub Actions compatible)"

# Comprehensive linting (always runs everything)
lint-all: lint-workflows lint-python
	@echo "✅ All linting checks completed"

checkov:
	@echo "Running Checkov security scan..."
	@if command -v docker >/dev/null 2>&1; then \
		if ! docker images bridgecrew/checkov:latest -q | grep -q .; then \
			echo "Pulling Checkov image (first time or outdated)..."; \
			docker pull bridgecrew/checkov:latest; \
		fi; \
		docker run --rm -v $(PWD):/workspace -v checkov-cache:/root/.cache bridgecrew/checkov:latest -d /workspace/infra --skip-check CKV_AZURE_165,CKV_AZURE_233,CKV_AZURE_112,CKV_AZURE_247,CKV2_AZURE_22,CKV_AZURE_199,CKV_AZURE_201 --quiet --compact --output json > infra/checkov-results.json; \
		echo "Running Checkov on Container configurations..."; \
		docker run --rm -v $(PWD):/workspace -v checkov-cache:/root/.cache bridgecrew/checkov:latest -d /workspace/containers --quiet --compact || true; \
	else \
		echo "Docker not available. Please install Docker to run Checkov"; \
		exit 1; \
	fi

# Enhanced security scanning with multiple tools - optimized with caching
trivy:
	@echo "🔐 Running Trivy security scanner..."
	@if command -v docker >/dev/null 2>&1; then \
		if ! docker images aquasec/trivy:latest -q | grep -q .; then \
			echo "Pulling Trivy image (first time or outdated)..."; \
			docker pull aquasec/trivy:latest; \
		fi; \
		docker run --rm -v $(PWD):/workspace -v trivy-cache:/root/.cache/trivy aquasec/trivy:latest config /workspace/infra --format json --output /workspace/infra/trivy-results.json --exit-code 0; \
		echo "Trivy scan completed"; \
	else \
		echo "Docker not available. Please install Docker to run Trivy"; \
		exit 1; \
	fi

terrascan:
	@echo "Running Terrascan policy scanner..."
	@if command -v docker >/dev/null 2>&1; then \
		if ! docker images tenable/terrascan:latest -q | grep -q .; then \
			echo "Pulling Terrascan image (first time or outdated)..."; \
			docker pull tenable/terrascan:latest; \
		fi; \
		echo "Scanning infrastructure files with Terrascan..."; \
		echo "📁 Target directory: infra/ (excluding subdirectories)"; \
		echo "⏳ Scanning for security policy violations..."; \
		docker run --rm -v $$(pwd):/workspace tenable/terrascan:latest scan -i terraform -d /workspace/infra --non-recursive --verbose --output human; \
		echo "💾 Generating JSON report..."; \
		docker run --rm -v $$(pwd):/workspace tenable/terrascan:latest scan -i terraform -d /workspace/infra --non-recursive --output json > infra/terrascan-results.json 2>/dev/null || echo "JSON report generation completed with warnings"; \
		echo "Terrascan scan completed - results saved to infra/terrascan-results.json"; \
	else \
		echo "Docker not available. Please install Docker to run Terrascan"; \
		exit 1; \
	fi

# Fast Terrascan scan with just medium/high issues
terrascan-fast:
	@echo "⚡ Running Terrascan fast scan (MEDIUM/HIGH only)..."
	@if command -v docker >/dev/null 2>&1; then \
		if ! docker images tenable/terrascan:latest -q | grep -q .; then \
			echo "Pulling Terrascan image..."; \
			docker pull tenable/terrascan:latest; \
		fi; \
		echo "Fast scanning infrastructure with Terrascan..."; \
		docker run --rm -v $$(pwd):/workspace tenable/terrascan:latest scan -i terraform -d /workspace/infra --non-recursive --severity HIGH --verbose --output human || echo "No HIGH severity issues found"; \
		echo "Fast Terrascan scan completed"; \
	else \
		echo "Docker not available. Please install Docker to run Terrascan"; \
		exit 1; \
	fi

# Comprehensive security and cost analysis (sequential)
scan-all: checkov trivy terrascan scan-python cost-estimate
	@echo "📊 Generating comprehensive security and cost analysis summary..."
	@$(MAKE) scan-summary

# Parallel security and cost analysis for faster CI/CD execution
scan-parallel:
	@echo "Running security and cost analysis in parallel..."
	@echo "Starting parallel analysis at $$(date)"
	@$(MAKE) -j5 checkov trivy terrascan scan-python infracost-parallel || echo "Some scans completed with warnings"
	@echo "📊 Generating comprehensive analysis summary..."
	@$(MAKE) scan-summary

# Legacy target for GitHub Actions compatibility
security-scan: scan-parallel

# Generate security summary report
scan-summary:
	@echo "Security Scan Results Summary:" > security-summary.txt
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
	@if [ -f security-results/semgrep-results.json ]; then \
		jq -r '.results | length' security-results/semgrep-results.json >> security-summary.txt 2>/dev/null || echo "No issues found" >> security-summary.txt; \
	elif [ -f python-semgrep-results.json ]; then \
		jq -r '.results | length' python-semgrep-results.json >> security-summary.txt 2>/dev/null || echo "No issues found" >> security-summary.txt; \
	else \
		echo "No semgrep results found" >> security-summary.txt; \
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
	@echo "Pre-pulling all security and cost analysis images..."
	@if command -v docker >/dev/null 2>&1; then \
		docker pull aquasec/trivy:latest; \
		docker pull bridgecrew/checkov:latest; \
		docker pull tenable/terrascan:latest; \
		docker pull pyupio/safety:latest; \
		docker pull semgrep/semgrep:latest; \
		docker pull infracost/infracost:latest; \
		echo "All security and cost analysis images cached locally"; \
	else \
		echo "Docker not available"; \
	fi

cache-clean:
	@echo "🧹 Cleaning security scan caches and results..."
	@docker volume rm trivy-cache checkov-cache 2>/dev/null || true
	@rm -f infra/*-results.json infra/infracost-*.json infra/infracost-*.html python-*-results.json security-summary.txt 2>/dev/null || true
	@echo "Caches and results cleaned"

# Container image security scanning
scan-containers:
	@echo "🐳 Scanning container images for vulnerabilities..."
	@if command -v docker >/dev/null 2>&1; then \
		echo "Scanning available container images..."; \
		for image in $$(docker images --format "{{.Repository}}:{{.Tag}}" | grep -v "<none>" | head -10); do \
			echo "Scanning $$image..."; \
			docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v trivy-cache:/root/.cache/trivy aquasec/trivy:latest image $$image --severity HIGH,CRITICAL --format table || true; \
		done; \
	else \
		echo "Docker not available. Cannot scan container images"; \
	fi

# Python security scanning with multiple tools
scan-python:
	@echo "🐍 Running Python security scans..."
	@if command -v docker >/dev/null 2>&1; then \
		echo "� Running Safety for dependency vulnerabilities..."; \
		if ! docker images pyupio/safety:latest -q | grep -q .; then \
			echo "Pulling Python security scanning images..."; \
			docker pull pyupio/safety:latest; \
		fi; \
		docker run --rm -v $(PWD):/workspace pyupio/safety:latest check --json --file /workspace/requirements.txt > python-safety-results.json 2>/dev/null || echo "No requirements.txt or vulnerabilities found"; \
		echo "Running Semgrep for code security analysis..."; \
		./scripts/run-semgrep.sh $(PWD) security-results semgrep/semgrep:latest; \
		echo "🔐 Running Trivy filesystem scan for Python dependencies..."; \
		docker run --rm -v $(PWD):/workspace -v trivy-cache:/root/.cache/trivy aquasec/trivy:latest filesystem /workspace --skip-dirs .venv,node_modules,containers --scanners vuln --severity HIGH,CRITICAL --format json --output /workspace/python-trivy-results.json || true; \
		echo "Python security scans completed"; \
	else \
		echo "Docker not available. Cannot run Python security scans"; \
	fi

# Cost estimation with Infracost (containerized)
cost-estimate:
	@echo "💰 Running cost estimation with Infracost..."
	@if command -v docker >/dev/null 2>&1; then \
		if ! docker images infracost/infracost:latest -q | grep -q .; then \
			echo "Pulling Infracost image (first time or outdated)..."; \
			docker pull infracost/infracost:latest; \
		fi; \
		if [ -z "$$INFRACOST_API_KEY" ]; then \
			echo "🔑 Trying to retrieve Infracost API key from Key Vault..."; \
			export ENVIRONMENT=$${ENVIRONMENT:-staging}; \
			echo "Checking bootstrap Key Vault first..."; \
			BOOTSTRAP_KEYVAULT=$$(az keyvault list --resource-group "ai-content-farm-bootstrap" --query "[0].name" -o tsv 2>/dev/null || echo ""); \
			if [ -n "$$BOOTSTRAP_KEYVAULT" ]; then \
				export INFRACOST_API_KEY=$$(az keyvault secret show --vault-name "$$BOOTSTRAP_KEYVAULT" --name "infracost-api-key" --query "value" -o tsv 2>/dev/null || echo ""); \
				if [ -n "$$INFRACOST_API_KEY" ] && [ "$$INFRACOST_API_KEY" != "placeholder-get-from-infracost-io" ]; then \
					echo "Using Infracost API key from bootstrap Key Vault"; \
				else \
					echo "Infracost API key is placeholder in bootstrap Key Vault. Checking environment Key Vault..."; \
					KEYVAULT_NAME=$$(az keyvault list --resource-group "ai-content-$$ENVIRONMENT-rg" --query "[0].name" -o tsv 2>/dev/null || echo ""); \
					if [ -n "$$KEYVAULT_NAME" ]; then \
						export INFRACOST_API_KEY=$$(az keyvault secret show --vault-name "$$KEYVAULT_NAME" --name "infracost-api-key" --query "value" -o tsv 2>/dev/null || echo ""); \
						if [ -n "$$INFRACOST_API_KEY" ] && [ "$$INFRACOST_API_KEY" != "placeholder-get-from-infracost-io" ]; then \
							echo "Using Infracost API key from environment Key Vault"; \
						else \
							echo "Infracost API key not found in environment Key Vault."; \
							INFRACOST_API_KEY=""; \
						fi; \
					else \
						echo "Environment Key Vault not found (infrastructure not deployed yet)."; \
						INFRACOST_API_KEY=""; \
					fi; \
				fi; \
			else \
				echo "Bootstrap Key Vault not found."; \
			fi; \
		fi; \
		if [ -z "$$INFRACOST_API_KEY" ]; then \
			echo ""; \
			echo "To set up Infracost API key:"; \
			echo "   1. Get your API key from https://dashboard.infracost.io"; \
			echo "   2. Set it as environment variable: export INFRACOST_API_KEY=your-key"; \
			echo "   3. Or store in Key Vault after deploying: make setup-infracost"; \
			echo ""; \
			echo "Infracost API key required. Skipping cost estimation."; \
		else \
			echo "💰 Generating cost breakdown with Infracost..."; \
			docker run --rm -v $$(pwd)/infra:/workspace -e "INFRACOST_API_KEY=$$INFRACOST_API_KEY" infracost/infracost:latest breakdown --path /workspace --format json --out-file /workspace/infracost-base.json; \
			echo "📊 Displaying cost summary..."; \
			docker run --rm -v $$(pwd)/infra:/workspace -e "INFRACOST_API_KEY=$$INFRACOST_API_KEY" infracost/infracost:latest breakdown --path /workspace --format table; \
			echo "Generating HTML report..."; \
			docker run --rm -v $$(pwd)/infra:/workspace -e "INFRACOST_API_KEY=$$INFRACOST_API_KEY" infracost/infracost:latest breakdown --path /workspace --format html --out-file /workspace/infracost-report.html; \
			echo "Cost estimation complete. See infra/infracost-report.html for detailed breakdown"; \
		fi; \
	else \
		echo "Docker not available. Please install Docker to run Infracost"; \
		exit 1; \
	fi

# Setup Infracost API key in Key Vault
setup-infracost:
	@echo "💰 Setting up Infracost API key in Key Vault..."
	@echo "To get an Infracost API key:"
	@echo "   1. Visit https://dashboard.infracost.io"
	@echo "   2. Sign up/login with your email or GitHub"
	@echo "   3. Copy your API key from the settings"
	@echo ""
	@read -p "Enter your Infracost API key: " INFRACOST_KEY; \
	if [ -n "$$INFRACOST_KEY" ]; then \
		export ENVIRONMENT=$${ENVIRONMENT:-staging}; \
		echo "Trying to store in bootstrap Key Vault first..."; \
		BOOTSTRAP_KEYVAULT=$$(az keyvault list --resource-group "ai-content-farm-bootstrap" --query "[0].name" -o tsv 2>/dev/null || echo ""); \
		if [ -n "$$BOOTSTRAP_KEYVAULT" ]; then \
			az keyvault secret set --vault-name "$$BOOTSTRAP_KEYVAULT" --name "infracost-api-key" --value "$$INFRACOST_KEY" > /dev/null; \
			echo "Infracost API key stored in bootstrap Key Vault: $$BOOTSTRAP_KEYVAULT"; \
		else \
			echo "Bootstrap Key Vault not found. Trying environment Key Vault..."; \
			KEYVAULT_NAME=$$(az keyvault list --resource-group "ai-content-$$ENVIRONMENT-rg" --query "[0].name" -o tsv 2>/dev/null || echo ""); \
			if [ -n "$$KEYVAULT_NAME" ]; then \
				az keyvault secret set --vault-name "$$KEYVAULT_NAME" --name "infracost-api-key" --value "$$INFRACOST_KEY" > /dev/null; \
				echo "Infracost API key stored in environment Key Vault: $$KEYVAULT_NAME"; \
			else \
				echo "No Key Vault found. Please deploy infrastructure first with 'make deploy-staging'"; \
				echo "For now, you can use: export INFRACOST_API_KEY=$$INFRACOST_KEY"; \
			fi; \
		fi; \
	else \
		echo "No API key provided"; \
	fi

# Streamlined Infracost for parallel execution in CI/CD
infracost-parallel:
	@echo "💰 Running Infracost cost analysis..."
	@if command -v docker >/dev/null 2>&1; then \
		if ! docker images infracost/infracost:latest -q | grep -q .; then \
			echo "Pulling Infracost image..."; \
			docker pull infracost/infracost:latest; \
		fi; \
		if [ -z "$$INFRACOST_API_KEY" ]; then \
			echo "🔑 Retrieving API key from Key Vault..."; \
			export ENVIRONMENT=$${ENVIRONMENT:-staging}; \
			echo "Checking bootstrap Key Vault first..."; \
			BOOTSTRAP_KEYVAULT=$$(az keyvault list --resource-group "ai-content-farm-bootstrap" --query "[0].name" -o tsv 2>/dev/null || echo ""); \
			if [ -n "$$BOOTSTRAP_KEYVAULT" ]; then \
				export INFRACOST_API_KEY=$$(az keyvault secret show --vault-name "$$BOOTSTRAP_KEYVAULT" --name "infracost-api-key" --query "value" -o tsv 2>/dev/null || echo ""); \
				if [ -n "$$INFRACOST_API_KEY" ] && [ "$$INFRACOST_API_KEY" != "placeholder-get-from-infracost-io" ]; then \
					echo "Retrieved Infracost API key from bootstrap Key Vault: $$BOOTSTRAP_KEYVAULT"; \
				else \
					echo "Infracost API key is placeholder in bootstrap Key Vault. Checking environment Key Vault..."; \
					KEYVAULT_NAME=$$(az keyvault list --resource-group "ai-content-$$ENVIRONMENT-rg" --query "[0].name" -o tsv 2>/dev/null || echo ""); \
					if [ -n "$$KEYVAULT_NAME" ]; then \
						export INFRACOST_API_KEY=$$(az keyvault secret show --vault-name "$$KEYVAULT_NAME" --name "infracost-api-key" --query "value" -o tsv 2>/dev/null || echo ""); \
						if [ -n "$$INFRACOST_API_KEY" ] && [ "$$INFRACOST_API_KEY" != "placeholder-get-from-infracost-io" ]; then \
							echo "Retrieved Infracost API key from environment Key Vault: $$KEYVAULT_NAME"; \
						else \
							echo "Infracost API key not found in environment Key Vault: $$KEYVAULT_NAME"; \
							INFRACOST_API_KEY=""; \
						fi; \
					else \
						echo "Environment Key Vault not found in resource group ai-content-$$ENVIRONMENT-rg"; \
						INFRACOST_API_KEY=""; \
					fi; \
				fi; \
			else \
				echo "Bootstrap Key Vault not found in resource group ai-content-farm-bootstrap"; \
			fi; \
		fi; \
		if [ -z "$$INFRACOST_API_KEY" ] || [ "$$INFRACOST_API_KEY" = "placeholder-get-from-infracost-io" ]; then \
			echo "Infracost API key not available. Generating cost breakdown without pricing..."; \
			docker run --rm -v $$(pwd)/infra:/workspace infracost/infracost:latest breakdown --path /workspace --format json --out-file /workspace/infracost-results.json --no-color || echo "Cost analysis completed with limited data"; \
		else \
			echo "💰 Generating cost breakdown with pricing..."; \
			docker run --rm -v $$(pwd)/infra:/workspace -e "INFRACOST_API_KEY=$$INFRACOST_API_KEY" infracost/infracost:latest breakdown --path /workspace --format json --out-file /workspace/infracost-results.json --no-color; \
		fi; \
		echo "Infracost analysis completed - results saved to infra/infracost-results.json"; \
	else \
		echo "Docker not available. Cannot run Infracost"; \
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
	@echo "Setting up Infracost API key from environment..."
	@if [ -z "$$INFRACOST_API_KEY" ]; then \
		echo "INFRACOST_API_KEY environment variable not set"; \
		echo "Please set it first: export INFRACOST_API_KEY=your-key"; \
		echo "Or check your existing variables with: env | grep INFRACOST"; \
		exit 1; \
	fi
	@echo "INFRACOST_API_KEY is set (ending in: ...$(shell echo $$INFRACOST_API_KEY | tail -c 5))"
	@echo "🧪 Testing Infracost authentication..."
	@if infracost auth status > /dev/null 2>&1; then \
		echo "Infracost already authenticated"; \
	else \
		echo "🔐 Authenticating with Infracost..."; \
		echo "$$INFRACOST_API_KEY" | infracost configure set api_key; \
	fi
	@echo "Infracost setup complete"

# Check what Infracost-related variables you have
check-infracost-vars:
	@echo "Checking for Infracost-related environment variables..."
	@env | grep -i infra || echo "No INFRA* variables found"
	@env | grep -i cost || echo "No COST* variables found"
	@if [ -n "$$INFRACOST_API_KEY" ]; then \
		echo "INFRACOST_API_KEY is set (ending in: ...$(shell echo $$INFRACOST_API_KEY | tail -c 5))"; \
	else \
		echo "INFRACOST_API_KEY not set"; \
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
	@echo "Generating Software Bill of Materials..."
	@echo "Creating SBOM for Python dependencies..."
	@mkdir -p output/sbom
	@# Generate SBOM for each container using containerized syft
	@for container in content-collector content-processor content-ranker content-enricher content-generator site-generator markdown-generator collector-scheduler; do \
		echo "Generating SBOM for $$container..."; \
		docker run --rm -v $(PWD):/src anchore/syft:latest \
			/src/containers/$$container \
			-o json=/src/output/sbom/$$container-sbom.json \
			-o table; \
	done
	@# Generate SBOM for shared libs
	@echo "Generating SBOM for shared libs..."
	@docker run --rm -v $(PWD):/src anchore/syft:latest \
		/src/libs \
		-o json=/src/output/sbom/libs-sbom.json \
		-o table
	@echo "Creating infrastructure SBOM..."
	@echo "Infrastructure Components:" > infra/sbom-infrastructure.txt
	@echo "=========================" >> infra/sbom-infrastructure.txt
	@cd infra && grep -r "azurerm_" *.tf | cut -d'"' -f2 | sort -u >> sbom-infrastructure.txt
	@echo "Infrastructure SBOM generated: infra/sbom-infrastructure.txt"
	@echo "Python SBOMs generated in: output/sbom/"
	@echo "Running dependency analysis..."
	@python3 scripts/analyze-dependencies.py

lint-terraform: terraform-format terraform-validate

# Full verification pipeline for infrastructure (security, cost, compliance)
verify: terraform-init lint-terraform security-scan cost-estimate sbom terraform-plan
	@echo "📊 Generating comprehensive deployment report..."
	@echo "=== DEPLOYMENT READINESS REPORT ===" > infra/deployment-report.txt
	@echo "Generated: $(shell date)" >> infra/deployment-report.txt
	@echo "" >> infra/deployment-report.txt
	@echo "SECURITY STATUS:" >> infra/deployment-report.txt
	@if [ -f infra/security-summary.txt ]; then cat infra/security-summary.txt >> infra/deployment-report.txt; fi
	@echo "" >> infra/deployment-report.txt
	@echo "💰 COST ESTIMATION:" >> infra/deployment-report.txt
	@if [ -f infra/infracost-base.json ]; then \
		echo "Monthly cost estimate available in infracost-report.html" >> infra/deployment-report.txt; \
	else \
		echo "Cost estimation not available" >> infra/deployment-report.txt; \
	fi
	@echo "" >> infra/deployment-report.txt
	@echo "SBOM STATUS:" >> infra/deployment-report.txt
	@echo "- Container SBOMs: output/sbom/" >> infra/deployment-report.txt
	@echo "- Infrastructure SBOM: infra/sbom-infrastructure.txt" >> infra/deployment-report.txt
	@if [ -f sbom-nodejs.json ]; then echo "- Node.js SBOM: sbom-nodejs.json" >> infra/deployment-report.txt; fi
	@echo "" >> infra/deployment-report.txt
	@echo "Verification complete. Check infra/deployment-report.txt for full summary."
	@echo "Infrastructure is ready for deployment."

# Deploy infrastructure after verification
apply: verify
	@echo "Deploying infrastructure..."
	cd infra && terraform apply

# Destroy infrastructure
destroy:
	@echo "💥 Destroying infrastructure..."
	cd infra && terraform destroy -auto-approve

# Container Apps targets
verify-containers:
	@echo "Verifying Container Apps deployment..."
	@echo "Checking container configurations..."
	@for dir in containers/*/; do \
		if [ -f "$$dir/Dockerfile" ]; then \
			echo "Validating $$dir..."; \
			docker build --no-cache --dry-run "$$dir" > /dev/null 2>&1 && echo "✅ $$dir Dockerfile valid" || echo "❌ $$dir Dockerfile invalid"; \
		fi; \
	done
	@echo "Container Apps verification complete."

deploy-containers: verify-containers
	@echo "Deploying Container Apps..."
	./scripts/deploy-containers.sh
	@echo "Container Apps deployment complete."

# Test Container Apps endpoints
test-containers:
	@echo "🧪 Testing Container Apps endpoints..."
	@echo "📤 Testing content collector health endpoint..."
	curl -f http://localhost:8001/health || echo "Content collector not responding"
	@echo "📤 Testing content processor health endpoint..."
	curl -f http://localhost:8002/health || echo "Content processor not responding"
	@echo "Container Apps health check complete."

# Validate devcontainer by listing versions of key tools
devcontainer:
	@echo "Node.js version:" && node --version
	@echo "Terraform version:" && terraform --version
	@echo "Azure CLI version:" && az --version

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
	@for dir in containers/*/; do \
		cd "$$dir" && rm -rf __pycache__ .pytest_cache || true; \
	done
	rm -f sbom-nodejs.json latest_tech.json
	@echo "🧹 All build artifacts and scan results cleaned"

# Environment-specific deployment targets
deploy-staging: verify-staging
	@echo "Deploying to staging environment..."
	@if [ "$(shell git branch --show-current)" != "develop" ] && [ ! "$(shell git branch --show-current)" = "feature/"* ]; then \
		echo "Staging deployment only allowed from develop or feature/ branches"; \
		exit 1; \
	fi
	cd infra && terraform workspace select staging || terraform workspace new staging
	cd infra && terraform plan -var-file="staging.tfvars"
	cd infra && terraform apply -auto-approve -var-file="staging.tfvars"
	@echo "Staging infrastructure deployment complete"
	@echo "🔐 Next step: Configure secrets with 'make setup-keyvault'"

# Staging-specific verification (more flexible than full verify)
verify-staging: terraform-init lint-terraform security-scan cost-estimate-optional sbom terraform-plan-staging
	@echo "📊 Staging verification complete"
	@echo "Infrastructure is ready for staging deployment"

# Optional cost estimation that doesn't fail deployment
cost-estimate-optional:
	@echo "💰 Running optional cost estimation..."
	@if [ -n "$$INFRACOST_API_KEY" ]; then \
		echo "INFRACOST_API_KEY found, running cost estimation"; \
		$(MAKE) cost-estimate; \
	else \
		echo "INFRACOST_API_KEY not set, skipping cost estimation"; \
		echo "To enable cost estimation: export INFRACOST_API_KEY=your-key"; \
		echo "Or get your key from: https://dashboard.infracost.io"; \
	fi

# Terraform plan for staging
terraform-plan-staging:
	@echo "Planning Terraform changes for staging..."
	cd infra && terraform plan -var-file="staging.tfvars"

deploy-production: verify
	@echo "Deploying to production environment..."
	@if [ "$(shell git branch --show-current)" != "main" ]; then \
		echo "Production deployment only allowed from main branch"; \
		exit 1; \
	fi
	@echo "This will deploy to PRODUCTION. Continue? [y/N]" && read ans && [ $${ans:-N} = y ]
	cd infra && terraform workspace select production || terraform workspace new production
	cd infra && terraform plan -var="environment=production" -var="resource_prefix=ai-content-prod"
	cd infra && terraform apply -var="environment=production" -var="resource_prefix=ai-content-prod"
	./scripts/deploy-containers.sh production
	@echo "Production deployment complete."

# Environment-specific testing
test-staging:
	@echo "🧪 Testing staging environment..."
	@echo "📤 Testing Container Apps on staging..."
	curl -f "https://ai-content-staging-collector.azurecontainerapps.io/health" > /dev/null && echo "✅ Collector healthy"
	curl -f "https://ai-content-staging-processor.azurecontainerapps.io/health" > /dev/null && echo "✅ Processor healthy"
	@echo "Staging tests complete"

test-production:
	@echo "🧪 Testing production environment..."
	@echo "📤 Testing Container Apps health endpoints..."
	curl -f "https://ai-content-prod-collector.azurecontainerapps.io/health" > /dev/null
	curl -f "https://ai-content-prod-processor.azurecontainerapps.io/health" > /dev/null
	@echo "Production smoke test complete"

# Rollback capabilities
rollback-staging:
	@echo "🔄 Rolling back staging deployment..."
	@echo "This will rollback staging to previous state. Continue? [y/N]" && read ans && [ $${ans:-N} = y ]
	cd infra && terraform workspace select staging
	cd infra && terraform apply -auto-approve -refresh-only
	@echo "Manual rollback: Check previous git tags and redeploy from desired commit"

rollback-production:
	@echo "🚨 Rolling back production deployment..."
	@echo "This will rollback PRODUCTION. This should only be done in emergencies. Continue? [y/N]" && read ans && [ $${ans:-N} = y ]
	cd infra && terraform workspace select production
	cd infra && terraform apply -auto-approve -refresh-only
	@echo "🚨 EMERGENCY: Manual rollback required - check previous production tags and redeploy"

# Security validation for different environments
security-scan-strict:
	@echo "Running strict security scan for production..."
	docker run --rm -v $(PWD):/workspace bridgecrew/checkov -d /workspace/infra --hard-fail-on HIGH,CRITICAL --quiet --compact
	docker run --rm -v $(PWD):/workspace bridgecrew/checkov -d /workspace/containers --hard-fail-on HIGH,CRITICAL --quiet --compact
	docker run --rm -v $(PWD):/workspace aquasec/trivy config /workspace/infra --severity HIGH,CRITICAL --exit-code 1
	@echo "Strict security validation passed"

# Key Vault integration targets
setup-keyvault:
	@echo "🔐 Setting up Azure Key Vault secrets..."
	@if [ ! -f scripts/setup-keyvault.sh ]; then \
		echo "Key Vault setup script not found"; \
		exit 1; \
	fi
	@scripts/setup-keyvault.sh

get-secrets:
	@echo "Retrieving secrets from Azure Key Vault..."
	@echo "Getting Key Vault name from current environment..."
	@KEYVAULT_NAME=$$(az keyvault list --resource-group "ai-content-dev-rg" --query "[0].name" -o tsv 2>/dev/null || echo ""); \
	if [ -z "$$KEYVAULT_NAME" ]; then \
		echo "Key Vault not found. Please deploy infrastructure first."; \
		exit 1; \
	fi; \
	echo "Key Vault: $$KEYVAULT_NAME"; \
	echo "Available secrets:"; \
	az keyvault secret list --vault-name "$$KEYVAULT_NAME" --query "[].name" -o table

validate-secrets:
	@echo "Validating Key Vault secret configuration..."
	@KEYVAULT_NAME=$$(az keyvault list --resource-group "ai-content-dev-rg" --query "[0].name" -o tsv 2>/dev/null || echo ""); \
	if [ -z "$$KEYVAULT_NAME" ]; then \
		echo "Key Vault not found. Please deploy infrastructure first."; \
		exit 1; \
	fi; \
	echo "Checking required secrets in $$KEYVAULT_NAME..."; \
	MISSING_SECRETS=""; \
	for secret in reddit-client-id reddit-client-secret reddit-user-agent infracost-api-key; do \
		if ! az keyvault secret show --vault-name "$$KEYVAULT_NAME" --name "$$secret" >/dev/null 2>&1; then \
			MISSING_SECRETS="$$MISSING_SECRETS $$secret"; \
		else \
			echo "$$secret: Found"; \
		fi; \
	done; \
	if [ -n "$$MISSING_SECRETS" ]; then \
		echo "Missing secrets:$$MISSING_SECRETS"; \
		echo "Run 'make setup-keyvault' to configure missing secrets"; \
	else \
		echo "🎉 All required secrets are configured!"; \
	fi

# Content processing targets
collect-topics:
	@echo "🕷️ Running content wombles to collect topics..."
	cd content_wombles && python3 run_all_wombles.py
	@echo "Topic collection complete"

process-content:
	@echo "🏭 Running full content processing pipeline..."
	cd containers/content-processor && python3 -m pip install -r requirements.txt --quiet
	cd containers/content-processor && python3 pipeline.py --mode full --max-articles 5
	@echo "Content processing complete"

rank-topics:
	@echo "📊 Ranking collected topics..."
	cd containers/content-processor && python3 -m pip install -r requirements.txt --quiet
	cd containers/content-processor && python3 pipeline.py --mode rank --hours-back 24 --min-score 0.3
	@echo "Topic ranking complete"

enrich-content:
	@echo "Enriching topics with research..."
	@if [ -z "$(FILE)" ]; then \
		echo "Please specify input file: make enrich-content FILE=ranked_topics_file.json"; \
		exit 1; \
	fi
	cd containers/content-processor && python3 -m pip install -r requirements.txt --quiet
	cd containers/content-processor && python3 pipeline.py --mode enrich --input-file $(FILE)
	@echo "Content enrichment complete"

publish-articles:
	@echo "Publishing articles to site..."
	@if [ -z "$(FILE)" ]; then \
		echo "Please specify input file: make publish-articles FILE=enriched_topics_file.json"; \
		exit 1; \
	fi
	cd containers/content-processor && python3 -m pip install -r requirements.txt --quiet
	cd containers/content-processor && python3 pipeline.py --mode publish --input-file $(FILE) --max-articles $(or $(MAX_ARTICLES),5)
	@echo "Article publishing complete"

content-status:
	@echo "📈 Content processing status..."
	export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://azurite:10000/devstoreaccount1;" && \
	cd containers/content-processor && python3 -m pip install -r requirements.txt --quiet && \
	python3 main.py --mode status

# Cleanup duplicate articles in published content
cleanup-articles:
	@echo "🧹 Cleaning up duplicate articles..."
	cd content_processor && python3 -m pip install -r requirements.txt --quiet
	cd content_processor && python3 content_publisher.py --cleanup-only
	@echo "Cleanup complete!"
