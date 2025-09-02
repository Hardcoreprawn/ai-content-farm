# Security Scanning Strategy

## Overview

This document outlines our approach to security scanning and how we handle security findings across different workflows.

## Security Scanning Tools

We use a comprehensive security scanning approach with the following tools:

### 1. **Trivy**
- **Purpose**: Infrastructure and container vulnerability scanning
- **Scope**: Dockerfiles, container images, infrastructure configs
- **Severity Levels**: HIGH, CRITICAL

### 2. **Semgrep**
- **Purpose**: Static Application Security Testing (SAST)
- **Scope**: Python code, JavaScript, infrastructure as code
- **Coverage**: Security patterns, best practices, vulnerability detection

### 3. **Checkov**
- **Purpose**: Infrastructure as Code compliance
- **Scope**: Terraform files, cloud configurations
- **Coverage**: Security best practices, compliance standards

### 4. **SBOM Generation**
- **Purpose**: Software Bill of Materials
- **Scope**: All dependencies and packages
- **Coverage**: Dependency tracking and analysis

## Workflow-Specific Configurations

### Main CI/CD Pipeline
- **Security Scan Mode**: Report-only (`fail-on-critical: false`)
- **Rationale**: Allow development to continue while tracking security debt
- **Action**: Issues are reported but don't block deployment
- **Monitoring**: Security findings are uploaded to GitHub Security tab

### Dependabot Auto-merge
- **Security Scan Mode**: Report-only (`fail-on-critical: false`)
- **Rationale**: Dependency updates shouldn't be blocked by existing security issues
- **Action**: Security scan runs but doesn't prevent auto-merge
- **Special Handling**: Security-focused updates are prioritized

## Acceptable Security Exceptions

The following security findings are documented as acceptable for our current environment:

### Infrastructure Exceptions
1. **Azure Storage Service Bypass** (`storage-allow-microsoft-service-bypass`)
   - **Reason**: Required for Container Apps to access storage
   - **Mitigation**: Access controlled via managed identity

2. **Azure Storage Queue Logging** (`storage-queue-services-logging`)
   - **Reason**: We use Service Bus instead of Storage Queues
   - **Mitigation**: Not applicable to our architecture

3. **Key Vault Network Access** (`keyvault-specify-network-acl`)
   - **Reason**: GitHub Actions needs dynamic IP access
   - **Mitigation**: RBAC controls access, temporary development setting

4. **Key Vault Secret Expiration** (`keyvault-ensure-secret-expires`)
   - **Reason**: External secrets managed outside Terraform lifecycle
   - **Mitigation**: Manual rotation process in place

### Container Exceptions
1. **Missing USER directive** (`dockerfile.security.missing-user.missing-user`)
   - **Reason**: Development containers, not production
   - **Mitigation**: Container Apps runs with restricted permissions

### Code Exceptions
1. **Direct Jinja2 Usage** (`direct-use-of-jinja2`)
   - **Reason**: Controlled template generation for static sites
   - **Mitigation**: Input validation and sanitization in place

## Security Debt Management

### Monitoring
- Security findings are tracked in GitHub Security tab
- Regular security reviews scheduled monthly
- Critical findings addressed within 30 days

### Escalation Process
1. **Critical Issues**: Address within 7 days or document exception
2. **High Issues**: Address within 30 days or add to security backlog
3. **Medium/Low Issues**: Include in regular maintenance cycles

## Consistency Guidelines

### Tool Alignment
- Both main CI/CD and Dependabot workflows use the same `./.github/actions/security-scan` action
- Same security tools and configurations across all workflows
- Consistent severity thresholds and exception handling

### Failure Modes
- **Development**: Report security issues but don't block
- **Production**: Enhanced monitoring and alerting
- **Dependabot**: Don't block dependency updates with existing issues

## Future Improvements

1. **Security Gate Integration**: Implement security gates for production deployments
2. **Automated Remediation**: Add automated security fix suggestions
3. **Policy as Code**: Implement OPA policies for security compliance
4. **Continuous Monitoring**: Real-time security monitoring in production

## Documentation Updates

This document should be updated when:
- New security tools are added
- Exception policies change
- New acceptable exceptions are identified
- Workflow configurations are modified

Last Updated: September 2, 2025
