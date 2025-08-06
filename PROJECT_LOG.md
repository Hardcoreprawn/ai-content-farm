---

- Configured devcontainer.json to clone the repository into a Docker volume by default for optimal file I/O performance (especially for Terraform and similar tools).
---

- Removed duplicate devcontainer features for Terraform, Azure CLI, and common-utils from devcontainer.json since all tools are now installed in the Dockerfile. This reduces build time and avoids confusion.
---

## Next steps for Copilot (after devcontainer rebuild)

1. Start the Azure Functions host locally in /functions: `func start`.
2. Test the GetHotTopics endpoint (e.g., with curl or browser) to verify it fetches live Reddit topics.
3. Display or log the output for user review.
4. If successful, proceed to wire up the Eleventy site to consume the function’s output and generate/update a static page.
5. Continue logging all user requests and actions in this file.

# Project Log

This file records all actions taken by GitHub Copilot for the 'Hot Topics Feed' project.

## 2025-07-23 (continued)

- User requested a slimmer, custom devcontainer image to speed up rebuilds and reduce bloat.
- Created a new minimal Dockerfile in .devcontainer based on node:20-slim, installing only Azure Functions Core Tools,
  Azure CLI, Terraform, make, and git.
- Updated devcontainer.json to use the new Dockerfile instead of the Microsoft image.

## 2025-07-23 (linting and best practices)

- User requested that all code and documentation follow good practice and standard linting conventions.
- Added ESLint configuration to /functions for JavaScript linting (eslint:recommended).
- Added markdownlint configuration to project root for markdown linting.
- Committed to following Dockerfile best practices for minimal, secure, and maintainable images.

## 2025-07-23

- Project initialized. Created folders: /infra, /functions, /site.
- Added .devcontainer/devcontainer.json with Node.js, Terraform, Azure CLI, and recommended VS Code extensions.
- Scaffolded minimal Azure Functions app in /functions with sample HTTP-triggered function (GetHotTopics).
- Scaffolded minimal Eleventy static site in /site with index.md and base.njk layout.
- Added Makefile to validate devcontainer, Azure Functions, Eleventy site, and Terraform setup.

---

### Later actions on 2025-07-23

- User requested to fetch hot topics from Reddit (technology subreddits) via Azure Function.
- Updated GetHotTopics function to fetch and aggregate top posts from r/technology, r/programming, r/MachineLearning,
  r/artificial, r/Futurology using Reddit's public API.
- Added node-fetch as a dependency to /functions/package.json.
- Installed node-fetch in /functions.
- User requested to test the function locally before deploying.
- Discovered Azure Functions Core Tools were not installed in the devcontainer.
- User requested to install Azure Functions Core Tools and add to devcontainer config.
- Updated .devcontainer/devcontainer.json to install Azure Functions Core Tools globally via postCreateCommand.
- Reminded user to rebuild the devcontainer to apply the change.
- User requested that all actions and requests be logged to PROJECT_LOG.md as we go.

## 2025-08-06 - Azure AD Application Configuration and Pipeline Fixes

- **Issue**: GitHub Actions pipeline failing due to Azure OIDC service principal permission issues and job dependency mismatches.
- **Root Cause Analysis**: 
  - OIDC service principal (ai-content-farm-github-staging) had insufficient permissions for resource deployment
  - Workflow job names didn't match dependency references
  - Terraform was trying to create new Azure AD application conflicting with existing staging app

- **Major Changes Made**:
  1. **Azure Permissions**: Granted Owner role to OIDC service principal (90d4d3b8-61af-4a9e-bcc8-bcba7a0139b6) for full deployment permissions
  2. **GitHub Workflow**: Fixed all job names and dependencies in `.github/workflows/consolidated-pipeline.yml`
  3. **Terraform Infrastructure Conversion**: Modified `infra/main.tf` and `infra/outputs.tf` to use existing Azure AD application instead of creating new one:
     - Converted `azuread_application.github_actions` resource to `data.azuread_application.github_actions` data source
     - Converted `azuread_service_principal.github_actions` resource to `data.azuread_service_principal.github_actions` data source
     - Updated all federated identity credentials to reference data sources
     - Updated role assignments to use data source references
     - Fixed all output references to use data sources

- **Strategy Adopted**: Ephemeral environments using shared Azure AD app "ai-content-farm-github-staging" to avoid permission propagation delays and reduce maintenance overhead

- **Clean Deployment**: Successfully deleted resource group `ai-content-dev-rg` for clean Terraform deployment

- **Validation**: Terraform configuration validated successfully using `make infra` target

## 2025-08-06 - Pipeline Optimization Analysis

- **Identified Opportunity**: Significant code duplication between GitHub Actions workflow and Makefile
- **Current State Analysis**:
  - Makefile has comprehensive `make verify` target with all security scans, terraform validation, cost estimation
  - GitHub Actions duplicates ~200 lines of tool installation and execution
  - Manual terraform commands scattered throughout workflow jobs
  - Inconsistent tool versions between local dev and CI

- **Proposed Solution**: Refactor GitHub Actions to reuse Makefile targets
  - Replace security-gate job with `make verify`
  - Replace terraform commands with `make infra`, `make apply`, etc.
  - Maintain GitHub Actions-specific features (outputs, artifacts, environment variables)
  - Estimated 60% reduction in workflow complexity

- **Benefits**:
  - Single source of truth for build/deploy logic
  - Easier maintenance and updates
  - Consistent behavior between local development and CI
  - Faster troubleshooting (developers can reproduce CI locally with same commands)

- **Added to Backlog**: SIMPLE_TASKS.md updated with priority pipeline optimization task

## 2025-08-06 - Deployment Pipeline Troubleshooting

- **Issue Identified**: GitHub Actions pipeline failing on Azure AD application data source lookup
- **Root Cause**: Service principal lacks permission to search Azure AD applications by `display_name`
- **Solution Applied**: Modified data source to use `client_id` lookup instead of `display_name`
  - Changed from: `data "azuread_application" "github_actions" { display_name = "ai-content-farm-github-staging" }`
  - Changed to: `data "azuread_application" "github_actions" { client_id = "c5deb409-eb9b-44be-9519-9a24a7dce9d6" }`

- **Testing**: Local terraform validation successful, new pipeline run initiated
- **Next Steps**: Monitor pipeline progress, expect successful deployment to development environment
