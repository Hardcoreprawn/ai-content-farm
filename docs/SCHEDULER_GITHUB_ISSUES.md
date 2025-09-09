# Scheduler Phase 1 GitHub Issues

## Issue 1: Create Scheduler Infrastructure
**Label:** `infrastructure`
**Title:** Add Azure Logic App scheduler infrastructure with Terraform

### Description
Create complete Azure Logic App infrastructure for content collection scheduling, including managed identity, storage tables, and RBAC permissions.

### Acceptance Criteria
- [ ] Logic App created with system-assigned managed identity
- [ ] Azure Table Storage tables created (topic configurations, execution history, analytics)
- [ ] RBAC permissions configured for Logic App to call Container Apps
- [ ] Key Vault access policy for scheduler configuration
- [ ] Budget monitoring for scheduler costs (<$2/month)
- [ ] Terraform validation passes (checkov, tflint)

### Files to Modify
- `infra/scheduler.tf` ✅ CREATED - Complete infrastructure definition
- Update `infra/outputs.tf` to include scheduler outputs
- Update terraform plans and validation

### Implementation Notes
- Use system-assigned managed identity for authentication
- Store topic configuration in Azure Table Storage
- Monitor costs with budget alerts
- Follow existing infrastructure patterns

---

## Issue 2: Implement Basic Logic App Workflow  
**Label:** `scheduler`
**Title:** Create basic Logic App workflow for 4-hour content collection

### Description
Implement the core Logic App workflow that triggers every 4 hours, retrieves topic configuration, and calls the content-collector service with managed identity authentication.

### Acceptance Criteria
- [ ] Logic App workflow deploys successfully
- [ ] 4-hour recurrence trigger configured
- [ ] Managed identity authentication to content-collector
- [ ] Topic configuration retrieval from Key Vault
- [ ] Single topic (Technology) collection working
- [ ] Error handling for authentication failures
- [ ] Execution logging to Azure Table Storage

### Files to Create/Modify
- `docs/scheduler/logic-app-workflow.json` ✅ CREATED - Basic workflow
- Create deployment script for Logic App workflow
- Update Logic App resource in Terraform with workflow definition

### Reference/Template
- Content-collector API: `/collect` endpoint with managed identity auth
- Existing managed identity patterns in container_apps.tf

---

## Issue 3: Setup Topic Configuration System
**Label:** `configuration`  
**Title:** Create topic configuration management for scheduler

### Description
Implement the topic configuration system using Azure Table Storage and Key Vault, starting with the Technology topic for MVP validation.

### Acceptance Criteria
- [ ] Topic configuration schema defined and documented
- [ ] Technology topic configuration created in Azure Table Storage
- [ ] Subreddit mappings (technology, programming, MachineLearning, artificial)
- [ ] Collection criteria (min_score: 50, min_comments: 10)
- [ ] Configuration accessible via Logic App
- [ ] Script to initialize topic configurations
- [ ] Validation of topic configuration format

### Files to Create
- `scripts/scheduler/configure-topics.sh` - Topic configuration setup
- `docs/scheduler/topic-configuration.md` - Topic configuration guide
- Update Key Vault secret with initial topic configuration

### Topic Configuration Example
```json
{
  "technology": {
    "display_name": "Technology",
    "schedule": { "frequency_hours": 4, "priority": "high" },
    "sources": {
      "reddit": {
        "subreddits": ["technology", "programming", "MachineLearning", "artificial"],
        "limit": 20, "sort": "hot"
      }
    },
    "criteria": { "min_score": 50, "min_comments": 10 }
  }
}
```

---

## Issue 4: End-to-End Scheduler Testing
**Label:** `testing`
**Title:** Validate complete scheduler → content-collector → content-processor flow

### Description
Test the complete scheduler workflow from Logic App trigger through content collection to content processing, ensuring all authentication and data flow works correctly.

### Acceptance Criteria
- [ ] Logic App triggers successfully (manual and scheduled)
- [ ] Content-collector receives authenticated requests from Logic App
- [ ] Content collection succeeds for Technology topic
- [ ] Content flows to content-processor correctly
- [ ] Execution results logged to Azure Table Storage
- [ ] Cost monitoring shows <$2/month for scheduler components
- [ ] No authentication or authorization errors
- [ ] End-to-end flow documented

### Files to Create
- `scripts/scheduler/test-scheduler.sh` - End-to-end testing script
- `tests/scheduler/test_integration.py` - Scheduler integration tests
- Update documentation with test results

### Testing Steps
1. Deploy scheduler infrastructure with Terraform
2. Configure initial topic in Azure Table Storage
3. Deploy Logic App workflow
4. Trigger manual execution
5. Verify content-collector receives request
6. Confirm content processing succeeds
7. Monitor costs and performance

---

## Issue 5: Scheduler Monitoring and Alerting
**Label:** `monitoring`
**Title:** Implement monitoring and alerting for scheduler operations

### Description
Set up comprehensive monitoring for Logic App executions, content collection success rates, and cost tracking to ensure scheduler operates reliably within budget.

### Acceptance Criteria
- [ ] Logic App execution monitoring in Azure Monitor
- [ ] Collection success/failure rate tracking
- [ ] Cost monitoring with budget alerts
- [ ] Authentication failure alerting
- [ ] Execution history analytics
- [ ] Performance metrics dashboard
- [ ] Monthly cost reporting

### Files to Create
- Update `infra/scheduler.tf` with monitoring resources
- `docs/scheduler/monitoring.md` - Monitoring guide
- Alert rules for failures and cost overruns

### Metrics to Track
- Logic App execution frequency and success rate
- Content-collector response times and success rates
- Monthly scheduler costs vs budget
- Topic collection performance by subreddit

---

## Priority Order
1. **Issue 1** (Infrastructure) - Foundation for everything else
2. **Issue 3** (Configuration) - Needed before workflow can run
3. **Issue 2** (Workflow) - Core scheduling functionality  
4. **Issue 4** (Testing) - Validation of complete flow
5. **Issue 5** (Monitoring) - Production readiness

## Success Metrics for Phase 1
- [ ] Logic App executes every 4 hours with >95% success rate
- [ ] Content-collector receives authenticated requests successfully
- [ ] Technology topic collects 15-20 items per execution
- [ ] Content flows through to content-processor without errors
- [ ] Total scheduler monthly cost < $2
- [ ] No authentication or authorization failures
- [ ] Complete end-to-end flow documented and tested

---

*These issues provide a structured approach to implementing the MVP scheduler while maintaining the existing 3-container architecture and staying within the $30-40/month budget.*
