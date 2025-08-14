# Copilot Agent Instructions for AI Content Farm

## Project Overview
This is an **enterprise-grade A#### Event-Driven Integration (Secondary, After REST API):
- **Blob/Timer Triggers**: Optional automation after HTTP endpoint is proven working
- **Pattern**: `EventTrigger` → calls → `HTTP Endpoint` (same business logic)
- **Benefits**: Automatic processing while maintaining manual control and debugging
- **Requirements**: HTTP endpoint must exist first, event trigger calls it internally
- **Example**: `ContentEnricher` blob trigger calls `ContentEnricherManual` HTTP logic

#### Project Structure (Enforced):ntent farm** built on Azure Functions with comprehensive security, cost governance, and compliance controls. The system processes Reddit topics through an automated pipeline: collection → ranking → enrichment → publication.

**Always check README.md and TODO.md first** to understand current status and next priorities.

## Development Philosophy
- **Security-first**: Every change must pass security scanning (Checkov, Trivy, Terrascan)
- **Cost-conscious**: All deployments include cost impact analysis with Infracost
- **Production-ready**: Focus on reliability, monitoring, and maintainability over features
- **Clean architecture**: Event-driven functions with clear separation of concerns
- **Documentation as code**: Keep docs current, concise, and actionable

## AI Agent Working Principles
- **Code Quality First**: Always consider linting, formatting, and best practices
- **Test Integrity**: Never skip or remove tests - fix them to work properly. Tests prove code works.
- **Think Before Acting**: Research and discuss solutions before implementing
- **No Unnatural Acts**: Use tools as designed. If it's not working, reconsider the approach or tool choice
- **Bad News Early**: Stop and explain issues/errors immediately when discovered, then collaborate on resolution
- **Slow is Smooth, Smooth is Fast**: Steady incremental progress over rushed changes. Avoid massive refactors or unexpected diversions without strong justification
- **Incremental & Safe**: Prefer staged rollouts and targeted changes when appropriate
- **Security-Conscious**: Apply principle of least privilege, scope permissions appropriately

## GitHub Issues Workflow
Use GitHub Issues for specific, actionable tasks while keeping TODO.md for high-level roadmap.

### Issue Creation Guidelines
- **Auto-create Issues**: When starting new work phases, create detailed issues based on TODO.md analysis
- **Technical Precision**: Include specific file paths, function names, acceptance criteria
- **Reference Template**: Link to existing working examples (e.g., ContentRanker pattern)
- **Label Appropriately**: Use labels for categorization (function-standardization, content-pipeline, infrastructure)

### Issue Lifecycle Management  
- **Start Work**: Before implementing, check for related issues or create new ones
- **Update Progress**: Add progress comments during implementation
- **Link Commits**: Reference issues in commit messages (`git commit -m "Fix auth pattern - addresses #12"`)
- **Close on Completion**: Close issues when work is complete with summary comment

### Issue Status Keywords
- **When asked to "start work on function standardization"**: Check for existing issues, create if needed
- **When user says "I finished issue #X"**: Close the issue with completion summary, update related issues
- **When user says "update the issues"**: Review current status, close completed items, create new issues for next work

### Standard Issue Template
```markdown
## Description
[Clear description of what needs to be done]

## Acceptance Criteria
- [ ] Specific, testable requirements
- [ ] Technical implementation details
- [ ] Test coverage requirements

## Files to Modify
- `/path/to/file.py` (specific changes needed)

## Reference/Template
Link to existing working examples or documentation

## Related Issues
- Related to #X
- Blocks #Y
```

### Issue Labels to Use
- `function-standardization` - Applying ContentRanker template to other functions
- `content-pipeline` - Building end-to-end content flow
- `infrastructure` - Terraform, CI/CD, Azure resources
- `documentation` - Updates to docs, README, guides
- `bug` - Issues to fix
- `enhancement` - New features or improvements

## Documentation Rules - CRITICAL
- **NO ROOT POLLUTION** - Never create status/log files in project root
- **Use `/docs` folder** for detailed documentation, NOT root directory
- **Single source of truth** - README.md is main entry point, avoid duplicates
- **Temporary files** go in `.temp/` (gitignored) or are deleted after session
- **No session logs** in git - use temporary files or `.github/` for agent notes
- **Consolidate redundancy** - merge duplicate information, don't create new files
- **One TODO list** - TODO.md only, not multiple planning docs
- **No excessive documentation** - prefer working code over documentation theater
- **NO DOC SPRAWL** - Update existing files rather than creating new ones
- **Implementation logs** - Add to existing docs with date prefixes (YYYY-MM-DD)
- **Planning documents** - Use TODO.md, don't create separate planning files

## Coding Standards - CRITICAL

### Line Endings (CRITICAL - Prevents Deployment Failures)
- **ALL files must use Unix line endings (LF) - never CRLF**
- Use `sed -i 's/\r$//' filename` to fix CRLF issues  
- Check with `file filename` (should NOT show "with CRLF line terminators")
- Run `git diff --cached --check` before committing
- This prevents CI/CD deployment failures (recurring critical issue)

### Code Quality Standards
- **Azure Functions REST API Standard**: ALL functions must be proper HTTP REST APIs first
- **Clear API Contracts**: Document all endpoints with inputs, outputs, errors, authentication
- **Standardized Responses**: Use consistent JSON format with status, data, metadata, errors
- **Observable Functions**: Every function must provide health, status, and documentation endpoints
- **Authentication Clarity**: Return 401 with helpful messages, not generic 500 errors
- **Azure Functions Logging**: `az functionapp logs tail` only works for .NET functions, NOT Python
  - For Python functions: Use Azure portal logs or Application Insights queries
  - Python logs are buffered and don't stream in real-time like .NET
- **Keep logs ASCII-clean** - Avoid emojis in logs (makes parsing difficult)
- **Pin all versions** - Never use 'latest' tags; pin Terraform, Actions, package versions
- **Test all changes** - Verify locally before deploying to any environment
- **Functional programming preferred** - Pure functions for thread safety and scalability

### Security & Compliance Requirements
- **Security-first development** - All code must pass security scans before deployment
- **Run comprehensive scanning**: `make security-scan` (Checkov + Trivy + Terrascan)
- **Cost impact analysis** - All infrastructure changes require `make cost-estimate`
- **SBOM generation** - Generate software bill of materials: `make sbom`
- **Environment separation** - strict dev → staging → production promotion
- **Key Vault for secrets** - No hardcoded credentials, use Azure Key Vault integration

### Architecture Patterns

#### Worker/Scheduler Pattern (MANDATORY)
**ALL FUNCTIONS MUST FOLLOW CLEAN WORKER/SCHEDULER SEPARATION**

Our Azure Functions follow a clean architectural pattern that separates concerns:

**Worker Functions** (HTTP endpoints):
- Accept specific input/output blob paths via HTTP POST
- Return immediate acknowledgment response  
- Process asynchronously and write to specified output location
- Can be manually triggered with specific parameters
- Examples: `ContentRanker`, `ContentEnricher`

**Scheduler Functions** (Event-driven):
- Monitor blob containers, timers, or other triggers
- Call worker functions with appropriate parameters  
- Handle event-driven automation of pipeline
- Examples: `TopicRankingScheduler`, `ContentEnrichmentScheduler`

This pattern provides:
- Manual control over any processing step
- Event-driven automation for normal pipeline flow  
- Clear separation of concerns
- Easy testing and debugging
- No confusing duplicate functions with "Manual" suffixes

#### Worker Function API Requirements:
**ALL WORKER FUNCTIONS MUST BE PROPER REST APIs WITH CLEAR CONTRACTS**

- **HTTP-First Design**: Every worker function must have an HTTP endpoint as primary interface
- **Proper REST Semantics**: Use correct HTTP methods, status codes, and response formats  
- **Clear API Contracts**: Document inputs, outputs, authentication, and error responses
- **Observable Operations**: All functions must provide status, health, and progress endpoints
- **Standardized Responses**: Consistent JSON format with status, data, errors, and metadata
- **Authentication Transparency**: Clear error messages for auth failures ("401 Unauthorized - Function key required")
- **Manual Testing Capability**: Every function testable via curl/Postman for debugging
- **No Silent Failures**: Always return meaningful HTTP status codes and error descriptions

#### Required REST Endpoints for Each Function:
```
GET  /api/{function-name}/health     # Health check
POST /api/{function-name}/process    # Main processing endpoint  
GET  /api/{function-name}/status     # Operation status/progress
```

#### Standard Response Format (MANDATORY):
```json
{
  "status": "success|error|processing",
  "message": "Human-readable description of what happened",
  "data": { /* actual response data */ },
  "errors": [ /* detailed error information if applicable */ ],
  "metadata": {
    "timestamp": "2025-08-12T14:30:00Z",
    "function": "FunctionName",
    "execution_time_ms": 1250,
    "version": "1.0.0"
  }
}
```

#### Error Response Requirements:
- **401 Unauthorized**: "Function key required" or "Invalid authentication"
- **400 Bad Request**: "Missing required field: blob_name" 
- **404 Not Found**: "Blob not found: ranked-topics/file.json"
- **500 Internal Error**: Include specific error details and suggested fixes
```
GET  /api/{function-name}/health     # Health check (200/500)
GET  /api/{function-name}/status     # Current status and metrics
POST /api/{function-name}/process    # Main processing endpoint
GET  /api/{function-name}/docs       # API documentation
```

#### Response Format Standard:
```json
{
  "status": "success|error|processing",
  "message": "Human-readable description",
  "data": {...},
  "metadata": {
    "timestamp": "ISO-8601",
    "function": "function-name",
    "version": "1.0.0",
    "execution_time_ms": 1234
  },
  "errors": ["specific error messages"]
}
```

#### Authentication Handling:
- **Clear auth errors**: Return 401 with helpful message, not generic 500
- **Multiple auth methods**: Support both function keys and anonymous for testing
- **Auth documentation**: Clear instructions on how to authenticate

#### Event-Driven Integration (Secondary):
- **HTTP functions can have blob/timer triggers**: But HTTP is primary interface
- **Event handlers call HTTP endpoints**: Timer/blob triggers call HTTP functions internally
- **Benefits**: Testability, debuggability, manual control, clear contracts
- **Trade-offs**: ~2x cost, but essential for production reliability

#### Project Structure (Enforced)
- **Functions** in `/functions/` directory (main application code)
- **Infrastructure** in `/infra/` with bootstrap vs application separation
- **Documentation** in `/docs/` only, not scattered across root
- **Working files** in `.temp/` (gitignored) or deleted after session
- **No over-engineering** - prefer simple solutions that work reliably

## Development Workflow

### Environment Promotion (Strictly Enforced)
- **Development**: Local development and testing
- **Staging**: `develop` branch deployment for integration testing  
- **Production**: `main` branch only, requires manual approval
- **Branch protection**: Production deployment blocked from non-main branches

### Build System (Make-based)
Our Makefile provides comprehensive automation for all development tasks:

#### Core Development Commands
```bash
make help              # Show all available targets
make verify            # Complete pre-deployment validation pipeline
make deploy-staging    # Deploy to staging (develop branch only)
make deploy-production # Deploy to production (main branch only)
make security-scan     # Run Checkov + Trivy + Terrascan security analysis
make cost-estimate     # Generate Infracost impact analysis
make test-staging      # Run integration tests against staging
```

#### Content Processing Pipeline
```bash
make collect-topics    # Run Reddit content collection wombles
make process-content   # Full pipeline: collect → rank → enrich → publish
make rank-topics       # Rank collected topics for publishing priority
make enrich-content    # Research and fact-check topics (requires FILE=)
make publish-articles  # Generate markdown articles (requires FILE=)
make content-status    # Show current pipeline status
```

#### Infrastructure & Security
```bash
make terraform-plan    # Review infrastructure changes
make setup-keyvault    # Configure Azure Key Vault secrets
make validate-secrets  # Verify Key Vault configuration
make clean             # Remove all build artifacts and temp files
```

### Testing Strategy
- **Co-located Tests**: Each function has tests alongside implementation (functions/[Function]/test_*.py)
- **Unit Tests**: Required for all business logic functions (pytest -m unit)
- **Integration Tests**: Automated testing against staging environment (pytest -m integration)
- **Function Tests**: Test complete function behavior with mocks (pytest -m function)
- **Security Testing**: Comprehensive scanning with multiple tools
- **Cost Validation**: Impact analysis for all infrastructure changes
- **End-to-End**: Full pipeline testing from Reddit → published articles
- **Local Execution**: make test, make test-unit, make test-coverage
- **Pipeline Integration**: GitHub Actions with test matrix and reporting
- **Quality Gates**: All tests must pass before deployment

### Deployment Process
1. **Local Development**: Implement and test locally
2. **Security Validation**: `make security-scan` must pass
3. **Cost Analysis**: `make cost-estimate` for infrastructure changes
4. **Infrastructure Drift Check**: Run `terraform plan` to verify no unexpected changes
5. **Staging Deployment**: Deploy to staging for integration testing
6. **Production Approval**: Manual review and approval process
7. **Production Deployment**: Deploy from main branch only

## Infrastructure Efficiency Guidelines

### Preventing Configuration Drift (CRITICAL)
Azure automatically adds properties to resources that must be explicitly defined in Terraform to prevent unnecessary updates on every deployment:

#### Key Vault Secrets
- Always include `content_type = "function-key"` for function keys
- Include Azure's automatic `file-encoding = "utf-8"` tag
- Use `lifecycle.ignore_changes` for properties updated by deployment processes

#### Function Apps
- Explicitly define `APPINSIGHTS_INSTRUMENTATIONKEY` and `APPLICATIONINSIGHTS_CONNECTION_STRING`
- Use lifecycle rules to ignore `WEBSITE_RUN_FROM_PACKAGE` changes during deployments
- Define all app settings that Azure adds automatically

#### Storage Accounts
- Always include explicit `network_rules` block even if using defaults:
  ```hcl
  network_rules {
    default_action = "Allow"
    bypass         = ["AzureServices"]
  }
  ```

#### Null Resources
- Never use `timestamp()` in triggers as it forces replacement on every run
- Only trigger on actual resource changes that require the provisioner to re-run

### Best Practices
- Run `terraform plan` before any deployment to identify drift
- When Azure provider updates introduce new properties, add them to Terraform proactively
- Use `lifecycle.ignore_changes` strategically for Azure-managed properties
- Monitor deployment times - unexpected increases may indicate new drift issues

## Technology Stack & Current Architecture

### Platform & Infrastructure
- **Cloud Platform**: Microsoft Azure (Functions, Key Vault, Storage, Application Insights)
- **Infrastructure as Code**: Terraform with state management and workspace separation
- **Authentication**: OIDC integration for secure credential management
- **Secrets Management**: Azure Key Vault with environment-specific access controls
- **Cost Management**: Infracost integration for all infrastructure changes

### Application Architecture
- **Event-Driven Pipeline**: Timer → HTTP → Blob triggers for content processing
- **Serverless Functions**: Azure Functions with Python runtime
- **Content Flow**: Reddit → Collection → Ranking → Enrichment → Publication
- **Data Storage**: JSON-based intermediate storage with blob triggers
- **Static Site**: Eleventy (11ty) for article publication and site generation

### Current Functions (Production Ready)
- **GetHotTopics**: Timer-triggered (6 hours) Reddit topic collection
- **SummaryWomble**: HTTP-triggered with async job processing system  
- **ContentRanker**: Blob-triggered functional ranking with comprehensive scoring
- **ContentEnricher**: [Next Implementation] - Research and fact-checking
- **ContentPublisher**: [Next Implementation] - Markdown generation with frontmatter

### Development Environment
- **Container**: Dev container with pre-configured tools and dependencies
- **IDE**: VS Code with Azure Functions, Python, and Terraform extensions
- **CLI Tools**: Azure CLI, Terraform, GitHub CLI, Docker CLI pre-installed
- **Security Tools**: Checkov, Trivy, Terrascan for comprehensive scanning
- **Cost Tools**: Infracost for impact analysis and budget governance

## Project Context & Current Focus

### Business Objective
Automated AI content farm that transforms trending Reddit topics into high-quality, SEO-optimized articles for content marketing and traffic generation.

### Current Status: Event-Driven Content Pipeline
- ✅ **Infrastructure**: Terraform-managed Azure resources with OIDC auth
- ✅ **Collection**: Automated Reddit topic harvesting every 6 hours
- ✅ **Processing**: Async job system with comprehensive topic ranking
- ✅ **Security**: Multi-tool scanning pipeline with governance controls
- 🚧 **Enrichment**: Research and fact-checking implementation in progress
- 🚧 **Publication**: Markdown article generation with SEO optimization

### Immediate Priorities (Q3 2025)
1. **Complete ContentEnricher Function**: Implement research and fact-checking
2. **Complete ContentPublisher Function**: Generate SEO-optimized markdown articles
3. **End-to-End Pipeline Testing**: Validate complete Reddit → published flow
4. **Production Hardening**: Monitor performance, costs, and reliability
5. **Content Quality Controls**: Implement editorial review and approval workflows

## Key Files & Directory Structure

### Project Root Files (Single Source of Truth)
- **`README.md`** - MAIN entry point, project overview, quick start guide
- **`TODO.md`** - Simple task list and current priorities only
- **`Makefile`** - Comprehensive build automation (500+ lines, all dev workflows)
- **`.gitignore`** - Comprehensive exclusions for security and build artifacts

### Critical Directories
- **`/functions/`** - Azure Functions application code (main business logic)
- **`/infra/`** - Terraform infrastructure (bootstrap + application separation)
- **`/docs/`** - ALL detailed documentation (system design, deployment guides, etc.)
- **`/content_processor/`** - Local content processing pipeline for development
- **`/content_wombles/`** - Topic collection scripts and utilities
- **`/scripts/`** - Utility scripts for deployment, cleanup, and maintenance
- **`/tests/`** - Unit tests, integration tests, and test fixtures
- **`/output/`** - Generated content and processing results (gitignored)

### Documentation Organization
- **`docs/README.md`** - Documentation index and navigation
- **`docs/system-design.md`** - Architecture and technical design
- **`docs/deployment-guide.md`** - Step-by-step deployment procedures
- **`docs/api-contracts.md`** - Data format specifications for pipeline
- **`docs/security-policy.md`** - Security governance and compliance framework
- **`docs/development-standards.md`** - Critical coding rules (line endings, etc.)

## Issue Automation Triggers
When users use these phrases, automatically interact with GitHub Issues:

### Starting Work
- **"Start function standardization"** → Check/create issues for remaining functions
- **"Begin content pipeline work"** → Create issues for ContentPublisher and end-to-end testing  
- **"Work on infrastructure"** → Create targeted infrastructure improvement issues
- **"Continue: [phase name]"** → Check existing issues in that phase, create if missing

### Progress Updates
- **"Finished issue #X"** → Close issue with completion comment, check for dependent issues
- **"Update the issues"** → Review all open issues, close completed ones, create new ones for next phase
- **"I completed [specific work]"** → Find related issues, close them, update progress

### Status Queries
- **"What issues are open?"** → List current issues by priority/label
- **"What's next?"** → Check open issues, suggest highest priority items
- **"Show me function standardization progress"** → List issues with that label

## Common Tasks - Development Priority Order

### 1. Function Development & Deployment (Highest Priority)
```bash
make verify-functions    # Validate function code and configuration
make deploy-staging     # Deploy to staging for testing
make test-staging       # Run integration tests
make deploy-production  # Deploy to production (main branch only)
```

### 2. Infrastructure & Security (Required for All Changes)
```bash
make security-scan      # Run comprehensive security analysis
make cost-estimate      # Analyze cost impact of changes
make terraform-plan     # Review infrastructure changes
make setup-keyvault     # Configure secrets management
```

### 3. Content Pipeline Management
```bash
make process-content    # Run full content processing pipeline
make content-status     # Monitor pipeline health and status
make cleanup-articles   # Maintain content quality and remove duplicates
```

### 4. Development Environment
```bash
make clean              # Remove build artifacts and temp files
make validate-secrets   # Verify Key Vault configuration
make devcontainer       # Validate development environment setup
```

### 5. Emergency Procedures
```bash
make rollback-staging   # Rollback staging deployment
make rollback-production # EMERGENCY: Rollback production (manual approval)
```

## Quality Gates & Governance

### Pre-Deployment Requirements (All Must Pass)
- ✅ Security scan passes (Checkov + Trivy + Terrascan)
- ✅ Cost impact analysis completed (Infracost)
- ✅ Function code validation (syntax, configuration, dependencies)
- ✅ Infrastructure plan review (Terraform)
- ✅ SBOM generation (Software Bill of Materials)

### Branch Protection Rules
- **main**: Production deployments only, requires pull request review
- **develop**: Staging deployments, integration testing
- **feature/***: Development branches, must merge to develop first

### Cost Governance
- **Infracost required** for all infrastructure changes
- **Monthly budget alerts** configured in Azure
- **Quarterly cost review** and optimization
- **Resource tagging** for cost allocation and tracking

---
_Last updated: August 12, 2025 - Comprehensive development standards and workflow documentation_
