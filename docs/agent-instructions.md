# AI Assistant Guidelines

**Created:** August 5, 2025  
**Last Updated:** August 5, 2025

## 📋 Project Context

The AI Content Farm is a production-ready, enterprise-grade content aggregation system with comprehensive security, cost controls, and operational excellence. This document provides guidelines for AI assistants working on the project.

### Current Project Status
- **Production Ready**: Complete system with Azure Functions, Key Vault integration, and security compliance
- **Architecture**: Multi-component design with infrastructure, functions, and documentation
- **Security**: Enterprise-grade with zero HIGH severity findings
- **Deployment**: Automated CI/CD with staging and production environments
- **Documentation**: Comprehensive guides organized in `/docs` with kebab-case naming

## 🎯 Core Principles

### 1. Security First
- **Always** run security scans before suggesting changes
- **Never** hardcode secrets or credentials
- **Require** Key Vault integration for sensitive data
- **Validate** all security scan results before deployment

### 2. Documentation Excellence
- **Use** kebab-case for all filenames (`system-design.md`)
- **Include** date headers in all documentation
- **Organize** documentation by functional area in `/docs`
- **Maintain** cross-references between related documents

### 3. Enterprise Standards
- **Follow** Azure best practices and naming conventions
- **Implement** comprehensive error handling and logging
- **Use** Infrastructure as Code (Terraform) for all resources
- **Ensure** cost estimation before infrastructure changes

### 4. Testing and Validation
- **Test** all functions using HTTP endpoints before timer deployment
- **Validate** Key Vault integration in all environments
- **Verify** security compliance with multi-tool scanning
- **Confirm** cost estimates within acceptable limits

## 🛠️ Development Workflow

### 1. Understanding Project State
Before making any changes:
```bash
# Check current documentation
ls docs/
cat docs/README.md

# Review security status
make security-scan

# Validate current infrastructure
cd infra && terraform validate
```

### 2. Making Changes
Follow this sequence for any modifications:

1. **Research**: Read relevant documentation in `/docs`
2. **Plan**: Consider security and cost implications
3. **Implement**: Make minimal, focused changes
4. **Test**: Use HTTP functions for validation
5. **Scan**: Run security validation
6. **Document**: Update relevant documentation with dates

### 3. Adding New Features
For new functionality:

1. **Architecture Review**: Update `docs/system-design.md`
2. **Security Analysis**: Consider security implications
3. **Cost Impact**: Run `make cost-estimate`
4. **Testing Strategy**: Create testing procedures
5. **Documentation**: Create or update relevant guides

## 📚 Documentation Standards

### File Organization
```
docs/
├── README.md                    # Documentation index
├── system-design.md            # Architecture and design
├── deployment-guide.md         # Operational procedures
├── key-vault-integration.md    # Security and secrets
├── testing-guide.md            # Testing procedures
├── security-policy.md          # Governance framework
├── file-inventory.md           # Project catalog
├── project-log.md              # Development history
├── progress-tracking.md        # Status and milestones
└── security-testing-report.md  # Security validation
```

### Documentation Template
```markdown
# Document Title

**Created:** [Date]  
**Last Updated:** [Date]

## Overview
Brief description of document purpose

## Content sections...

---
*Maintained by the AI Content Farm development team*
```

### Update Requirements
- **Always** update the "Last Updated" date when modifying files
- **Always** maintain cross-references between documents
- **Always** use consistent markdown formatting
- **Always** include practical examples and code snippets

## 🔐 Security Guidelines

### Key Vault Integration
- **All secrets** must be stored in Azure Key Vault
- **Environment isolation** required (dev/staging/production)
- **Access policies** must follow least privilege principle
- **Audit logging** must be enabled for compliance

### Security Scanning Requirements
```bash
# Required before any infrastructure changes
make security-scan

# Must achieve these results:
# - Checkov: All checks passing
# - TFSec: No critical issues  
# - Terrascan: Acceptable compliance level
```

### Credential Management
- **Never** commit credentials to Git
- **Always** use Key Vault for sensitive data
- **Test** credential retrieval in all environments
- **Document** secret rotation procedures

## 💰 Cost Management

### Cost Estimation
- **Required** for all infrastructure changes
- **Use** `make cost-estimate` before deployment
- **Document** cost impact in change descriptions
- **Monitor** actual vs estimated costs

### Resource Optimization
- **Use** consumption plans for Azure Functions
- **Implement** storage lifecycle policies
- **Configure** appropriate monitoring retention
- **Review** resource utilization regularly

## 🧪 Testing Approach

### Function Testing
```bash
# Use HTTP endpoints for testing
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "source": "reddit",
    "topics": ["technology"],
    "limit": 2,
    "credentials": {"source": "keyvault"}
  }' \
  "https://ai-content-staging-func.azurewebsites.net/api/SummaryWomble"
```

### Integration Testing
- **Validate** Key Vault access in functions
- **Test** storage operations and data persistence
- **Verify** monitoring and logging functionality
- **Confirm** error handling and recovery

### Security Testing
- **Run** all security scans before deployment
- **Test** authentication and authorization
- **Validate** secret handling and access
- **Verify** audit logging functionality

## 🚀 Deployment Guidelines

### Environment Strategy
- **Development**: Local testing with environment variables
- **Staging**: Automated deployment for validation
- **Production**: Manual approval with strict security gates

### Deployment Process
1. **Security Validation**: All scans must pass
2. **Cost Estimation**: Verify acceptable cost impact
3. **Key Vault Check**: Ensure secret accessibility
4. **Infrastructure Deploy**: Use Terraform with appropriate variables
5. **Function Deploy**: Use CI/CD pipeline
6. **Post-Deploy Testing**: Validate end-to-end functionality

### Rollback Procedures
- **Document** rollback steps for all changes
- **Test** rollback procedures in staging
- **Maintain** previous version availability
- **Monitor** system health after rollback

## 📊 Monitoring and Maintenance

### Regular Tasks
- **Daily**: Review function execution logs
- **Weekly**: Security scan results analysis
- **Monthly**: Cost analysis and optimization review
- **Quarterly**: Documentation review and updates

### Key Metrics
- **Security**: Zero HIGH severity findings
- **Cost**: Within 110% of estimates
- **Performance**: Function execution under 30 seconds
- **Reliability**: 99.9% successful function executions

### Alerting
- **Security**: Immediate alerts for HIGH severity findings
- **Cost**: Alerts for 120% budget threshold
- **Performance**: Alerts for execution failures
- **Access**: Unusual Key Vault access patterns

## 🔄 Change Management

### Change Approval Process
1. **Security Review**: Validate security implications
2. **Cost Assessment**: Estimate financial impact
3. **Documentation Update**: Update relevant guides
4. **Stakeholder Review**: Get appropriate approvals
5. **Deployment**: Execute with monitoring
6. **Validation**: Confirm successful implementation

### Emergency Changes
- **Security Issues**: Immediate action authorized
- **Cost Overruns**: Rapid mitigation required
- **Service Outages**: Emergency response procedures
- **Data Incidents**: Immediate containment and assessment

## 🎯 Best Practices

### Code Quality
- **Use** consistent naming conventions (kebab-case for files)
- **Include** comprehensive error handling
- **Add** appropriate logging and monitoring
- **Follow** Azure Functions best practices

### Infrastructure
- **Use** Terraform for all Azure resources
- **Tag** resources appropriately for cost tracking
- **Implement** least privilege access policies
- **Enable** diagnostic logging for compliance

### Operations
- **Automate** repetitive tasks with Makefile targets
- **Monitor** system health and performance
- **Maintain** comprehensive documentation
- **Plan** for disaster recovery and business continuity

This document serves as the authoritative guide for AI assistants working on the AI Content Farm project, ensuring consistency, security, and operational excellence across all development activities.
