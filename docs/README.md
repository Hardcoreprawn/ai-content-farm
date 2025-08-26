# AI Content Farm Documentation

This directory contains comprehensive documentation for the AI Content Farm project, organized by category for easy navigation.

## � Documentation Structure

### Core Documentation
- [`SYSTEM_ARCHITECTURE.md`](SYSTEM_ARCHITECTURE.md) - Overall system design and component architecture
- [`QUICK_START_GUIDE.md`](QUICK_START_GUIDE.md) - Get started with the project quickly
- [`IMPLEMENTATION_ROADMAP.md`](IMPLEMENTATION_ROADMAP.md) - Project development roadmap and milestones
- [`DEPENDENCY_MANAGEMENT.md`](DEPENDENCY_MANAGEMENT.md) - Version management using config/shared-versions.toml
- [`content-collector-api.md`](content-collector-api.md) - Content collector service API specification

### 📂 Organized Categories

#### `/development`
Development standards, guidelines, and best practices:
- Container development standards and migration guides
- Commit message guidelines and emoji policies
- Testing strategies and content processor optimization
- Code quality and review guidelines

#### `/cicd`
Continuous integration and deployment workflows:
- GitHub Actions implementation and workflow design
- Dependabot integration and auto-merge configuration
- Pipeline execution logic and validation
- Workflow troubleshooting and best practices

#### `/infrastructure`
Infrastructure setup, deployment, and cloud services:
- Azure OpenAI and Key Vault integration
- Managed identity and authentication setup
- Cost analysis and optimization strategies
- Deployment guides and infrastructure architecture

#### `/security`
Security policies, tools, and remediation:
- Security scanning and vulnerability management
- Security testing reports and exceptions
- Remediation strategies and security tools rationale

#### `/archived`
Historical documentation and completed phase reports:
- Daily development reports
- Completed phase integration summaries
- Legacy documentation for reference

#### `/articles`
Content examples and sample outputs for reference

## 🚀 Quick Navigation

### For Developers
Start with [`QUICK_START_GUIDE.md`](QUICK_START_GUIDE.md), then review:
- [`development/CONTAINER_DEVELOPMENT_STANDARDS.md`](development/CONTAINER_DEVELOPMENT_STANDARDS.md)
- [`DEPENDENCY_MANAGEMENT.md`](DEPENDENCY_MANAGEMENT.md)
- [`development/testing-guide.md`](development/testing-guide.md)

### For DevOps
Review CI/CD and infrastructure documentation:
- [`cicd/GITHUB_ACTIONS_IMPLEMENTATION.md`](cicd/GITHUB_ACTIONS_IMPLEMENTATION.md)
- [`infrastructure/deployment-guide.md`](infrastructure/deployment-guide.md)
- [`infrastructure/AZURE_OPENAI_SETUP.md`](infrastructure/AZURE_OPENAI_SETUP.md)

### For Security
Check security documentation:
- [`security/SECURITY_REMEDIATION_COMPLETE_2025_08_21.md`](security/SECURITY_REMEDIATION_COMPLETE_2025_08_21.md)
- [`security/security-policy.md`](security/security-policy.md)
- [`security/SECURITY_TOOLS_RATIONALE.md`](security/SECURITY_TOOLS_RATIONALE.md)

## 📋 Current Status

The project has completed major dependency standardization and security remediation efforts. All containers now use consistent versioning with compatible release specifiers (`~=`) and separated production/test dependencies.

For the latest project status, see:
- [`VERSION_STANDARDIZATION_SUMMARY.md`](VERSION_STANDARDIZATION_SUMMARY.md)
- [`CLEANUP_SUMMARY.md`](CLEANUP_SUMMARY.md)

## 🔧 Maintenance

This documentation is actively maintained. When adding new documentation:
1. Place files in the appropriate category folder
2. Update this README with links to new files
3. Follow the established naming conventions
4. Include appropriate cross-references
3. **[testing-guide.md](testing-guide.md)** - Ensure quality through testing

### Production Deployment
1. **[deployment-guide.md](deployment-guide.md)** - Deploy to Azure
2. **[security-policy.md](security-policy.md)** - Security checklist
3. **[cost-analysis.md](cost-analysis.md)** - Monitor costs

## 📋 Documentation Standards

- All documentation follows Markdown standards
- Architecture decisions are documented in SYSTEM_ARCHITECTURE.md
- Code examples are tested and validated  
- Documentation is updated with each major system change
- New features require corresponding documentation updates

## 🔄 Maintenance

This documentation is actively maintained and reflects the current state of the system. When making system changes:

1. Update relevant documentation
2. Validate code examples still work
3. Update the IMPLEMENTATION_ROADMAP.md progress
4. Consider if SYSTEM_ARCHITECTURE.md needs updates

---
**Last Updated**: August 19, 2025  
**Next Review**: When implementation roadmap Phase 2D completes
