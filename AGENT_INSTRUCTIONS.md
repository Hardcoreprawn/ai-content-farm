# Copilot Agent Instructions

- Always check the Project Status and Project log to understand where we are and what to do next.
- Always following our coding standards and rules below. If you cannot, you need to ask for permission.

## Documentation Rules
- **No document sprawl** - use `/docs` folder for detailed documentation
- **One TODO list** - SIMPLE_TASKS.md only, not multiple planning docs
- **Keep it simple** - clear instructions, not performance documents
- **Update what exists** - keep PROJECT_STATUS.md accurate, remove outdated content
- **Strategy/target/steps** - practical approach, not corporate management theater

## Coding Rules
- **Log issues in GitHub** - track problems and solutions
- **Always test changes** - verify before deploying
- **Use specific versions** - pin Terraform, Actions versions; never use 'latest'
- **Update versions manually** - quarterly schedule, test before deploying
- **Move through environments** - dev → staging → production

## Project Context
- AI content farm with automated Reddit → content generation → publishing pipeline
- Azure Functions with OIDC authentication and Terraform infrastructure
- Current focus: MVP → production-ready with testing and reliability

## Key Files
- `SIMPLE_TASKS.md` - current TODO list
- `PROJECT_STATUS.md` - accurate project state
- `/docs/` - detailed documentation
- `/functions/GetHotTopics/` - main Azure Function
- `/infra/` - Terraform infrastructure
- `/scripts/` - deployment and setup utilities

## Common Tasks
- Fix deployments: check OIDC credentials, run pipeline
- Add tests: unit tests for functions, integration tests for pipeline
- Clean infrastructure: consolidate scripts, update Makefile
- Monitor costs: check Azure budgets and Infracost reports

---
_Last updated: August 6, 2025_
