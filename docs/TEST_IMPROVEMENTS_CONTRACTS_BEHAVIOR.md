# Test Improvements: Contract and Behavior Focus

**Date:** October 16, 2025  
**Context:** Site-publisher test fixes after adding early validation

## Testing Philosophy

Tests should validate **contracts** (inputs/outputs) and **behavior** (what happens), not implementation details.

### What We Test

#### ✅ Contracts (Inputs and Outputs)
- **Input structure**: Function receives BlobServiceClient and Settings
- **Output structure**: Returns DeploymentResult with expected fields
- **Data types**: Correct types for all fields (int, float, List[str])
- **Required fields**: All mandatory fields are present
- **Valid values**: Fields contain sensible values (e.g., duration > 0)

#### ✅ Behavior (What Happens)
- **Success path**: Downloads → Organizes → Builds → Validates → Backs up → Deploys
- **Error handling**: Deployment failures trigger rollback
- **Resilience**: Backup failures don't prevent deployment
- **Validation**: Output is validated before deployment attempt
- **State changes**: Correct functions are called in correct order

#### ❌ Implementation Details (Don't Test These)
- Internal variable names
- Private helper functions
- Exact file paths used internally
- Directory structure specifics
- Logging format or messages

## Test Structure Pattern

Each test follows this structure:

```python
@pytest.mark.asyncio
@patch("security.validate_hugo_output")  # Mock external dependencies
@patch("site_builder.download_markdown_files", new_callable=AsyncMock)
async def test_feature_name(...):
    """
    Brief description of what's being tested.
    
    Contract:
    - Input: Clear description of inputs
    - Output: Clear description of expected outputs
    
    Behavior:
    - What should happen in this scenario
    - Key decisions or paths taken
    - What should NOT happen
    """
    # Arrange - setup mocks to return valid contract data
    mock_result = Mock()
    mock_result.files_uploaded = 10  # Valid contract data
    mock_result.errors = []
    mock_function.return_value = mock_result
    
    # Act - execute the function under test
    result = await function_under_test(inputs)
    
    # Assert - verify contract (output structure and values)
    assert result.files_uploaded == 10, "Should upload expected files"
    assert result.duration_seconds > 0, "Should track time"
    assert len(result.errors) == 0, "Should have no errors"
    
    # Assert - verify behavior (what was called, what wasn't)
    mock_validate.assert_called_once()  # Should validate
    mock_rollback.assert_not_called()  # Should NOT rollback on success
```

## Specific Test Fixes Applied

### 1. Added Validation Mocking

**Problem:** Added early validation in production code, but tests didn't mock it

**Solution:** Mock `security.validate_hugo_output` in all relevant tests
```python
@patch("security.validate_hugo_output")  # Must match the import location
```

**Why:** The validation function is imported with `from security import` inside the function, so we patch it at its source module.

### 2. Enhanced Test Documentation

**Before:**
```python
async def test_build_and_deploy_site_success(...):
    """Test successful end-to-end build and deploy."""
```

**After:**
```python
async def test_build_and_deploy_site_success(...):
    """
    Test successful end-to-end build and deploy.
    
    Contract:
    - Input: BlobServiceClient, Settings
    - Output: DeploymentResult with files_uploaded > 0, no errors
    
    Behavior:
    - Downloads markdown content
    - Organizes content for Hugo
    - Builds site with Hugo
    - Backs up current site
    - Validates Hugo output
    - Deploys to web container
    - Does NOT trigger rollback on success
    """
```

**Why:** Makes test intent crystal clear to future developers

### 3. Improved Assertions

**Before:**
```python
assert result.files_uploaded == 10
assert result.duration_seconds > 0
```

**After:**
```python
# Assert - verify contract
assert result.files_uploaded == 10, "Should upload expected number of files"
assert result.duration_seconds > 0, "Should track execution time"
assert len(result.errors) == 0, "Should have no errors on success"

# Assert - verify behavior
mock_validate.assert_called_once()  # Should validate Hugo output before deployment
mock_rollback.assert_not_called()  # Should NOT rollback on successful deployment
```

**Why:** Clear separation between contract validation and behavior verification, with descriptive failure messages

## Contract Testing Examples

### Testing Success Contract
```python
# Valid output contract
result = await build_and_deploy_site(blob_client, config)
assert isinstance(result, DeploymentResult), "Should return DeploymentResult"
assert result.files_uploaded >= 0, "files_uploaded should be non-negative int"
assert result.duration_seconds > 0, "duration should be positive float"
assert isinstance(result.errors, list), "errors should be a list"
```

### Testing Error Contract
```python
# Error output contract
result = await build_and_deploy_site(blob_client, config)
assert result.files_uploaded == 0, "Should upload 0 files on failure"
assert len(result.errors) > 0, "Should have error messages"
assert all(isinstance(e, str) for e in result.errors), "All errors should be strings"
```

## Behavior Testing Examples

### Testing Happy Path Behavior
```python
# Successful deployment should:
# 1. Call validation BEFORE deployment
# 2. Call deployment if validation passes
# 3. NOT call rollback
mock_validate.assert_called_once()
mock_deploy.assert_called_once()
mock_rollback.assert_not_called()
```

### Testing Error Recovery Behavior
```python
# Failed deployment should:
# 1. Detect 0 files uploaded
# 2. Trigger automatic rollback
# 3. Include rollback message in errors
assert result.files_uploaded == 0, "Deployment failed"
mock_rollback.assert_called_once(), "Should trigger rollback"
assert any("rollback" in e.lower() for e in result.errors), "Should mention rollback"
```

### Testing Resilience Behavior
```python
# Backup failure should:
# 1. Log the error (don't test logging)
# 2. Continue with deployment anyway
# 3. Still succeed overall
assert result.files_uploaded > 0, "Should still deploy despite backup failure"
mock_deploy.assert_called_once(), "Should attempt deployment"
```

## Benefits of This Approach

### For Maintenance
- **Refactoring safe**: Can change implementation without breaking tests
- **Clear failures**: Test failures clearly indicate contract or behavior violations
- **Easy to understand**: New developers quickly understand what code should do

### For Development
- **Design guidance**: Writing contracts first helps design better APIs
- **Documentation**: Tests serve as executable documentation
- **Regression prevention**: Behavior tests catch unintended changes

### For Debugging
- **Precise failures**: "Should upload 10 files but got 0" is clearer than just "AssertionError"
- **Correlation**: Contract failures vs behavior failures indicate different problem types
- **Context**: Docstrings explain WHY test exists and WHAT it validates

## Anti-Patterns to Avoid

### ❌ Testing Implementation Details
```python
# BAD - tests internal variable names
assert result._internal_state == "processed"
assert "hugo_dir" in str(result)
```

### ❌ Over-Mocking
```python
# BAD - mocking too deep into the implementation
@patch("site_builder.Path")
@patch("site_builder.shutil.copytree")
@patch("site_builder.datetime.now")
```

### ❌ Unclear Assertions
```python
# BAD - no context for failure
assert result.files_uploaded == 10
assert len(result.errors) == 0
```

### ❌ Testing Multiple Things
```python
# BAD - one test doing too much
def test_everything():
    # Tests success, failure, rollback, backup, etc.
    # 200 lines of test code
```

## Best Practices

### ✅ One Behavior Per Test
```python
def test_successful_deployment()  # Happy path
def test_deployment_rollback()    # Error recovery
def test_backup_failure_continues() # Resilience
```

### ✅ Descriptive Test Names
```python
# Good naming pattern:
# test_{component}_{scenario}_{expected_outcome}

test_build_and_deploy_site_success()
test_build_and_deploy_site_automatic_rollback()
test_build_and_deploy_site_backup_failure_continues()
```

### ✅ Mock at Boundaries
```python
# Mock external dependencies, not internal helpers
@patch("security.validate_hugo_output")  # External module
@patch("site_builder.download_markdown_files")  # External I/O
# Don't mock: internal helpers, pure functions
```

### ✅ Test Contracts First
```python
# 1. Verify output structure and types
assert isinstance(result, DeploymentResult)
assert isinstance(result.files_uploaded, int)

# 2. Verify output values make sense
assert result.files_uploaded >= 0
assert result.duration_seconds > 0

# 3. Verify behavior
mock_function.assert_called_once()
```

## Results

After applying these principles:
- **63 tests passing** ✅
- **1 test skipped** (environment-specific)
- **Test clarity improved** - clear contracts and behavior documentation
- **Maintenance burden reduced** - implementation changes don't break tests
- **Debugging easier** - failures clearly indicate contract or behavior issues

## Future Improvements

1. **Add property-based tests** using Hypothesis for contract validation
2. **Add contract validation helpers** to reduce boilerplate
3. **Generate contract documentation** from test docstrings
4. **Add behavior sequence diagrams** for complex flows
