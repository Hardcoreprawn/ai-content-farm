# AI Content Farm - File Inventory

**Created:** August 5, 2025  
**Last Updated:** August 5, 2025

## 📁 Repository Structure Overview

This document provides a comprehensive catalog of all files in the AI Content Farm project, organized by functional area with detailed descriptions of purpose and relationships.

### 🏗️ Infrastructure (`/infra/`)

#### Core Infrastructure Files
- **`main.tf`** - Core Azure infrastructure definition
  - Azure Function App with managed identity
  - Azure Key Vault with diagnostic logging and access policies
  - Storage Account with blob containers
  - Application Insights for monitoring
  - Resource Group with proper tagging

- **`variables.tf`** - Environment-specific configuration variables
  - Environment identifier (dev/staging/production)
  - Azure region and naming configuration
  - Reddit API credentials (retrieved from Key Vault)
  - Cost and security settings

- **`providers.tf`** - Terraform provider configuration
  - Azure Resource Manager provider
  - Random provider for unique naming
  - Version constraints for consistency

- **`outputs.tf`** - Infrastructure output values
  - Function App URLs and keys
  - Storage account connection strings
  - Key Vault references
  - Resource identifiers for CI/CD

- **`.terraform.lock.hcl`** - Provider version locks for consistency

#### Environment Configuration Files
- **`development.tfvars`** - Development environment variables
- **`staging.tfvars`** - Staging environment configuration
- **`production.tfvars`** - Production environment settings
- **`terraform.tfvars.example`** - Template for environment configuration

#### Security and Compliance Results
- **`checkov-results.json`** - Infrastructure security scan results
- **`tfsec-results.json`** - Terraform security analysis
- **`terrascan-results.json`** - Policy compliance validation
- **`security-summary.txt`** - Consolidated security status

### ⚡ Azure Functions (`/functions/`)

#### Function Host Configuration
- **`host.json`** - Azure Functions runtime configuration
  - Python language worker settings
  - HTTP timeout and routing configuration
  - Extension bundle configuration

- **`local.settings.json`** - Local development settings
  - Azure Storage emulator connection
  - Local environment variables
  - Function runtime configuration

- **`requirements.txt`** - Python dependencies
  - `praw` - Python Reddit API Wrapper
  - `azure-identity` - Azure authentication
  - `azure-keyvault-secrets` - Key Vault integration
  - `azure-storage-blob` - Blob storage operations

#### GetHotTopics Function (Timer-triggered)
- **`GetHotTopics/function.json`** - Timer trigger configuration
  - Daily execution at 10:55 AM
  - UTC timezone configuration
  - Function binding definitions

- **`GetHotTopics/index.js`** - Timer function implementation
  - Calls HTTP Summary Womble internally
  - Logging and error handling
  - Scheduling coordination

#### SummaryWomble Function (HTTP-triggered)
- **`SummaryWomble/function.json`** - HTTP trigger configuration
  - POST method endpoint
  - Authentication level configuration
  - HTTP binding definitions

- **`SummaryWomble/index.js`** - HTTP-callable Reddit data collection
  - Flexible parameter handling
  - Key Vault credentials integration
  - Reddit API data collection and processing
  - Azure Blob Storage integration
  - Comprehensive error handling and logging

### 🌐 Static Site (`/site/`)

#### Site Generator Configuration
- **`package.json`** - Node.js dependencies for 11ty static site generator
  - Eleventy static site generator
  - Development and build scripts
  - Markdown and template processing

- **`src/base.njk`** - Base template for site generation
  - HTML structure and styling
  - Navigation and layout components
  - Responsive design framework

- **`src/index.md`** - Main page content
  - Project overview and description
  - Getting started documentation
  - Feature highlights and links

### 🔐 Security & CI/CD (`/.github/workflows/`)

#### Security Validation Pipeline
- **`security-and-cost-validation.yml`** - Comprehensive security scanning
  - Checkov infrastructure security scanning
  - TFSec Terraform security analysis
  - Terrascan policy compliance validation
  - SBOM generation with Syft
  - Infracost deployment cost estimation

#### Environment Deployment Pipelines
- **`staging-deployment.yml`** - Staging environment deployment
  - Automated deployment on develop/feature branches
  - Key Vault integration with secret retrieval
  - Security gate validation
  - Function app deployment
  - Post-deployment testing

- **`production-deployment.yml`** - Production deployment with approval
  - Manual approval requirement for production
  - Enhanced security validation
  - Blue-green deployment strategy
  - Rollback procedures
  - Comprehensive monitoring setup

### 📋 Build & Deployment (`/`)

#### Build Automation
- **`Makefile`** - Comprehensive build automation
  - **Security Targets**: `security-scan`, `checkov`, `tfsec`, `terrascan`
  - **Cost Management**: `cost-estimate`, `cost-baseline`
  - **SBOM Generation**: `generate-sbom`
  - **Infrastructure**: `deploy-staging`, `deploy-production`
  - **Key Vault**: `setup-keyvault`, `get-secrets`, `validate-secrets`
  - **Development**: `local-setup`, `verify`, `clean`

#### Project Configuration
- **`.gitignore`** - Comprehensive exclusions
  - Terraform state files and backups
  - Security scan results and reports
  - Local development files
  - Build artifacts and logs
  - Environment-specific configurations

### 🛠️ Scripts & Utilities (`/scripts/`)

#### Key Vault Management
- **`setup-keyvault.sh`** - Interactive Key Vault secret configuration
  - Environment selection (dev/staging/production)
  - Automatic Key Vault discovery
  - Interactive secret prompts with validation
  - Error handling and rollback procedures
  - Confirmation and testing workflow

### 📚 Documentation (`/docs/`)

#### Architecture & Design Documentation
- **`README.md`** - Documentation index and navigation
- **`system-design.md`** - Comprehensive architectural documentation
  - High-level system architecture
  - Component relationships and data flow
  - Technology stack and implementation details
  - Security architecture and controls

#### Operational Documentation
- **`deployment-guide.md`** - Step-by-step deployment procedures
  - Environment-specific deployment steps
  - Key Vault integration procedures
  - Security validation and monitoring
  - Troubleshooting and rollback procedures

- **`key-vault-integration.md`** - Secure secrets management guide
  - Key Vault architecture and access policies
  - Secret management and rotation procedures
  - CI/CD integration and automation
  - Security compliance and auditing

#### Testing & Quality Assurance
- **`testing-guide.md`** - Comprehensive testing procedures
  - HTTP function testing with various configurations
  - Authentication and error handling validation
  - Performance and reliability testing
  - Local development and debugging

#### Security & Governance
- **`security-policy.md`** - Complete security and governance framework
  - Security scanning pipeline and requirements
  - Key Vault security controls and compliance
  - Cost governance and monitoring
  - SBOM generation and dependency management
  - Incident response and governance reporting

#### Project Management
- **`project-log.md`** - Development history and major milestones
- **`progress-tracking.md`** - Current status and upcoming objectives
- **`security-testing-report.md`** - Security validation results
- **`agent-instructions.md`** - AI assistant guidelines and best practices
- **`file-inventory.md`** - This comprehensive file catalog

### 🔧 Development Configuration (`/.devcontainer/`)

#### Development Environment
- **`devcontainer.json`** - VS Code development container configuration
  - Ubuntu-based container with all required tools
  - Azure CLI, Terraform, Python, Node.js pre-installed
  - Extensions for development productivity
  - Port forwarding and environment setup

- **`Dockerfile`** - Container image definition
  - Base image and system dependencies
  - Development tools installation
  - User configuration and permissions

### 📊 Generated Reports & Artifacts

#### Security Scan Results
- **`infra/checkov-results.json`** - Infrastructure security findings
- **`infra/tfsec-results.json`** - Terraform security analysis
- **`infra/terrascan-results.json`** - Policy compliance results
- **`infra/security-summary.txt`** - Consolidated security status

#### Cost Management
- **`infra/infracost-report.json`** - Infrastructure cost estimates
- **`infra/cost-baseline.json`** - Historical cost tracking

#### Software Bill of Materials
- **`sbom-functions.json`** - Python dependencies SBOM
- **`sbom-site.json`** - Node.js dependencies SBOM
- **`sbom-combined.json`** - Complete project SBOM

### 🏷️ File Relationships & Dependencies

#### Infrastructure Dependencies
```
main.tf → variables.tf (configuration)
main.tf → providers.tf (Azure provider)
outputs.tf ← main.tf (resource references)
*.tfvars → variables.tf (environment values)
```

#### Function Dependencies
```
host.json → Function runtime configuration
requirements.txt → Python package dependencies
function.json → Individual function configuration
SummaryWomble ← GetHotTopics (internal API call)
```

#### Documentation Dependencies
```
README.md → All documentation (index)
system-design.md → architecture references
deployment-guide.md → infrastructure procedures
testing-guide.md → function validation
security-policy.md → governance framework
```

#### CI/CD Dependencies
```
.github/workflows/* → Makefile targets
staging-deployment.yml → Key Vault integration
production-deployment.yml → Manual approval gates
security-validation.yml → All security tools
```

### 📈 File Maintenance & Ownership

#### Automated Updates
- **Security Results**: Updated with each scan execution
- **Cost Reports**: Generated during infrastructure changes
- **SBOM Files**: Updated when dependencies change
- **Terraform Locks**: Updated when providers change

#### Manual Updates
- **Documentation**: Updated with feature changes
- **Configuration**: Updated for environment changes
- **Scripts**: Updated for process improvements
- **Policies**: Updated for compliance requirements

#### Version Control Strategy
- **Infrastructure**: All Terraform files tracked with state management
- **Functions**: Complete source code and configuration tracked
- **Documentation**: Version controlled with date headers
- **Security**: Scan results archived for compliance history

This file inventory provides complete visibility into the project structure, enabling efficient navigation, maintenance, and understanding of the AI Content Farm codebase.
