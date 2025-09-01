# Copilot Code Scanning Auto-Resolution Configuration

## Overview
This configuration file defines which types of code scanning alerts should be automatically resolved by GitHub Copilot and how they should be handled.

## Auto-Resolution Rules

### Security Fixes (High Priority)
These security issues will be automatically fixed when detected:

- `python.lang.security.insecure-hash-algorithms` - Replace MD5/SHA1 with SHA256
- `python.lang.security.weak-crypto` - Upgrade cryptographic functions
- `python.lang.security.hardcoded-password` - Replace with environment variables
- `python.lang.security.hardcoded-secret` - Replace with secure secret management
- `python.django.security.injection.path-traversal` - Add path validation
- `python.flask.security.injection.path-traversal` - Add path validation
- `python.lang.security.sql-injection` - Add parameterized query protection
- `python.lang.security.subprocess-shell-true` - Disable shell=True where safe

### Infrastructure Security Fixes
- `terraform.azure.security.*` - Apply Azure security best practices
- `yaml.github-actions.security.*` - Pin action versions, add security measures

### Code Quality Fixes (Optional - requires force_resolution=true)
- `python.lang.correctness.unused-import` - Remove unused imports
- `python.lang.correctness.unused-variable` - Add underscore prefix or removal suggestions
- `python.lang.maintainability.todo-comment` - Standardize TODO format
- `python.lang.performance.unnecessary-list-cast` - Optimize performance patterns

## Configuration Options

### Workflow Triggers
- **Schedule**: Daily at 10 AM UTC (after security monitoring)
- **Manual**: Via workflow_dispatch with options:
  - `target_alert_number`: Focus on specific alert
  - `force_resolution`: Enable code quality fixes
  - `max_alerts`: Limit number of alerts processed (default: 5)

### Auto-Resolution Criteria
An alert is considered for auto-resolution if:
1. Rule ID matches one of the patterns above
2. File is in a supported language (Python, YAML, Terraform)
3. Alert severity is not critical (unless force_resolution=true)
4. No manual "do-not-auto-fix" label exists

### Safety Measures
- **Validation**: All fixes undergo syntax and basic functionality validation
- **Pull Requests**: All fixes create PRs for human review before merging
- **Backup**: Original code is preserved and can be restored
- **Labeling**: Auto-fix PRs are clearly labeled for identification
- **Rollback**: Failed fixes create issues for manual attention

## Customization

### Adding New Rule Patterns
To add support for new code scanning rules, update the case statements in:
- `.github/workflows/copilot-code-scanning-resolution.yml` (lines ~80-120)
- `.github/actions/copilot-code-fix/action.yml` (fix application logic)

### Modifying Fix Strategies
Each rule can use one of three strategies:
- `security-fix`: High-priority security improvements
- `code-quality`: Code quality and maintainability improvements  
- `infrastructure-fix`: Infrastructure as Code security improvements

### Language Support
Currently supported languages:
- **Python**: Full security and quality fix support
- **YAML**: GitHub Actions and basic syntax fixes
- **Terraform**: Azure security pattern fixes
- **JavaScript/TypeScript**: Basic syntax validation (can be extended)

## Usage Examples

### Run for Specific Alert
```bash
gh workflow run copilot-code-scanning-resolution.yml \
  -f target_alert_number="123" \
  -f force_resolution="true"
```

### Force Quality Fixes
```bash
gh workflow run copilot-code-scanning-resolution.yml \
  -f force_resolution="true" \
  -f max_alerts="10"
```

## Monitoring and Maintenance

### Review Auto-Fix Results
1. Check created pull requests with label `automated-fix`
2. Review any failed auto-fix issues with label `failed`
3. Monitor security alert trends in GitHub Security tab

### Updating Fix Patterns
- Review weekly: effectiveness of applied fixes
- Monthly: update rule patterns based on new alert types
- Quarterly: enhance fix logic based on manual review patterns

## Security Considerations

### What Gets Auto-Fixed
- ✅ Standard security patterns with well-known solutions
- ✅ Code quality issues that don't affect functionality
- ✅ Infrastructure misconfigurations with clear best practices

### What Requires Manual Review
- ❌ Business logic security issues
- ❌ Complex algorithm security flaws  
- ❌ Cross-file dependency issues
- ❌ Performance-sensitive security changes

### Audit Trail
- All fixes create detailed commit messages
- PR descriptions include full context
- Failed attempts create tracking issues
- All changes are reversible

## Troubleshooting

### Common Issues
1. **Fix validation fails**: Check language-specific syntax validators
2. **No PR created**: Verify GitHub token permissions
3. **Alert not auto-resolved**: Check if rule pattern is supported
4. **Syntax errors after fix**: Review fix logic for the specific rule

### Support
- Check workflow run logs for detailed error messages
- Review created issues for failed auto-fix attempts
- Examine PR descriptions for applied fix context
