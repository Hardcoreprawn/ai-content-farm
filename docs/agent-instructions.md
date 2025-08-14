# AI Assistant Guidelines

**Created:** August 5, 2025  
**Last Updated:** August 14, 2025

## 🎯 Core Development Principles

### 1. Test-First Development
- **Write tests before code** - Every feature starts with a failing test
- **Small, focused functions** - One responsibility, minimal side effects
- **Fast feedback loops** - Tests run in seconds, not minutes
- **Test at every level** - Unit, integration, and end-to-end

### 2. Incremental Progress
- **Working software on main** - Every commit should be deployable
- **Small chunks** - Changes under 50 lines when possible
- **Functional style** - Pure functions, immutable data, clear inputs/outputs
- **Proven in production** - Each container must work live before moving on

### 3. Security & Quality
- **Secrets in Key Vault** - Never hardcode credentials
- **Run security scans** - Before every merge to main
- **Error handling** - Graceful failures, meaningful logs
- **Documentation** - Update as you build, not after

## 🚀 Development Workflow

### For Every Feature
1. **Write failing test** - Define expected behavior
2. **Minimal implementation** - Make test pass with simplest code
3. **Refactor** - Clean up while tests still pass
4. **Deploy to staging** - Validate in cloud environment
5. **Deploy to production** - Prove it works live
6. **Document** - Update relevant docs with current date

### Container Development Process
```bash
# 1. Create test structure
mkdir containers/my-service/tests
touch containers/my-service/tests/test_main.py

# 2. Write failing test
# 3. Implement minimal solution
# 4. Test locally
docker build containers/my-service
docker run --env-file .env my-service

# 5. Deploy and validate
make deploy-staging
make test-integration
make deploy-production
```

## 📁 Container Structure
Each container follows this pattern:
```
containers/my-service/
├── Dockerfile              # Multi-stage, minimal image
├── requirements.txt        # Pinned dependencies
├── main.py                 # Entry point, minimal logic
├── service.py              # Core business logic
├── config.py               # Environment-based config
├── tests/
│   ├── test_main.py        # Integration tests
│   ├── test_service.py     # Unit tests
│   └── test_config.py      # Config validation
└── README.md               # Usage and deployment docs
```

## 🧪 Testing Strategy

### Test Types
- **Unit Tests**: Pure functions, no external dependencies
- **Integration Tests**: Real Azure services in staging
- **Contract Tests**: API inputs/outputs match expected schemas
- **Smoke Tests**: Basic functionality works in production

### Test Requirements
```python
# Every function must be testable like this:
def test_process_data():
    input_data = {"key": "value"}
    expected = {"processed": True}
    result = process_data(input_data)
    assert result == expected

# Integration tests use real services:
def test_azure_integration():
    client = create_azure_client()
    result = client.process_request(test_data)
    assert result.status_code == 200
```

## 🔧 Container Development Guidelines

### Code Quality
- **Pure functions** where possible - same input, same output
- **Single responsibility** - each function does one thing well
- **Explicit dependencies** - inject config, don't import globals
- **Error boundaries** - catch and handle errors gracefully

### Container Best Practices
- **Minimal base images** - python:3.11-slim or alpine
- **Non-root user** - security by default
- **Health checks** - /health endpoint for monitoring
- **Graceful shutdown** - handle SIGTERM properly

### Azure Integration
- **Key Vault for secrets** - no environment variables for sensitive data
- **Managed identity** - no service principal keys
- **Application Insights** - structured logging with correlation IDs
- **Container platforms** - cost-effective and scalable deployment

## � Container Development Checklist

Before moving to next container:
- [ ] Unit tests pass locally
- [ ] Integration tests pass in staging
- [ ] Container builds and runs
- [ ] Deployed successfully to staging
- [ ] Deployed successfully to production
- [ ] Monitoring and logs working
- [ ] Documentation updated
- [ ] Security scan passes

## 🎯 Current Project Focus

Building content pipeline containers in this order:
1. **content-processor** - Core data transformation
2. **content-enricher** - AI enhancement of content
3. **content-ranker** - Content scoring and ranking
4. **scheduler** - Task orchestration
5. **ssg** - Static site generation

Each container must be **working in production** before starting the next one.

---
*Focus: Small steps, test-first, working software in production*

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
# - Trivy: No critical issues  
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
- **Use** container platforms for cost-effective scaling
- **Implement** storage lifecycle policies
- **Configure** appropriate monitoring retention
- **Review** resource utilization regularly

## 🧪 Testing Approach

### Container API Testing
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
  "https://content-processor.example.com/api/process"
```

### Integration Testing
- **Validate** Key Vault access in containers
- **Test** storage operations and data persistence
- **Verify** monitoring and logging functionality
- **Confirm** error handling and recovery
- **Test** container health endpoints

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
5. **Container Deploy**: Use CI/CD pipeline for container deployment
6. **Post-Deploy Testing**: Validate end-to-end functionality

### Rollback Procedures
- **Document** rollback steps for all changes
- **Test** rollback procedures in staging
- **Maintain** previous version availability
- **Monitor** system health after rollback

## 📊 Monitoring and Maintenance

### Regular Tasks
- **Daily**: Review container execution logs
- **Weekly**: Security scan results analysis
- **Monthly**: Cost analysis and optimization review
- **Quarterly**: Documentation review and updates

### Key Metrics
- **Security**: Zero HIGH severity findings
- **Cost**: Within 110% of estimates
- **Performance**: Container response time under 10 seconds
- **Reliability**: 99.9% successful container executions

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
- **Follow** container development best practices

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
