# Copilot Agent Instructions

- Always check the Project Status and Project log to understand where we are and what to do next.
- Always following our coding standards and rules below. If you cannot, you need to ask for permission.

## Documentation Rules - CRITICAL
- **NO ROOT POLLUTION** - Never create status/log files in project root
- **Use `/docs` folder** for detailed documentation, NOT root directory
- **Single source of truth** - README.md is main entry point, avoid duplicates
- **Temporary files** go in `.temp/` (gitignored) or are deleted after session
- **No session logs** in git - use temporary files or `.github/` for agent notes
- **Consolidate redundancy** - merge duplicate information, don't create new files
- **One TODO list** - TODO.md only, not multiple planning docs
- **No excessive documentation** - prefer working code over documentation theater

## Coding Rules
- **Fix path mismatches immediately** - verify Makefile vs actual file structure
- **Simplify build systems** - Makefiles should be <200 lines, remove unused targets
- **Log issues in GitHub** - track problems and solutions
- **Always test changes** - verify before deploying
- **Use specific versions** - pin Terraform, Actions versions; never use 'latest'
- **Update versions manually** - quarterly schedule, test before deploying
- **Move through environments** - dev → staging → production
- **Function deployment priority** - get working code deployed before optimization

## Project Structure Rules
- **Functions** go in `/functions/` directory (rename from azure-function-deploy if needed)
- **Infrastructure** in `/infra/` with clear bootstrap vs application separation
- **Documentation** in `/docs/` only, not scattered across root
- **Working files** in `.temp/` (gitignored) or deleted after session
- **No over-engineering** - prefer simple solutions that work

## Project Context
- AI content farm with automated Reddit → content generation → publishing pipeline
- Azure Functions with OIDC authentication and Terraform infrastructure
- Current focus: MVP → production-ready with testing and reliability

## Key Files
- `README.md` - SINGLE source of truth and main entry point
- `TODO.md` - simple task list (rename from SIMPLE_TASKS.md)
- `/docs/` - detailed documentation (system design, deployment guides)
- `/functions/` - Azure Functions code (main application)
- `/infra/` - Terraform infrastructure (bootstrap + application)
- `Makefile` - simple build targets (<200 lines), core workflows only

## Common Tasks - Priority Order
1. **Fix function deployment** - correct paths, deploy working code first
2. **Clean documentation** - consolidate root files, move temp files
3. **Simplify Makefile** - remove unused targets, fix path references
4. **Test deployments** - verify OIDC credentials, run pipeline
5. **Add monitoring** - check Azure budgets and function logs

---
_Last updated: August 6, 2025_
