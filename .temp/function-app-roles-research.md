# Function App Deployment Roles Research

## Azure Roles for Function App Deployment

### Option 1: Website Contributor
- **Role**: `Website Contributor`
- **Scope**: Function App or Resource Group
- **Permissions**: Full management of web apps and function apps
- **Pros**: Targeted, principle of least privilege
- **Cons**: Limited to web/function apps only

### Option 2: Contributor  
- **Role**: `Contributor`
- **Scope**: Resource Group or Function App
- **Permissions**: Full management of all resources
- **Pros**: Comprehensive access
- **Cons**: Overly broad permissions

### Option 3: App Service Contributor
- **Role**: `App Service Contributor` 
- **Scope**: Function App or Resource Group
- **Permissions**: Manage app services including deployment
- **Pros**: More targeted than Contributor
- **Cons**: Still broader than Website Contributor

### Option 4: Custom Role (Advanced)
- **Role**: Custom deployment role
- **Permissions**: Specific deployment actions only
- **Pros**: Maximum security
- **Cons**: Complex to maintain

## Recommended Approach
**Website Contributor** at the Function App scope - provides necessary deployment permissions without excessive privileges.

## Implementation Options

### A. Direct Role Assignment (Resource-level)
```terraform
resource "azurerm_role_assignment" "github_actions_function_app_contributor" {
  count = var.github_actions_object_id != "" ? 1 : 0
  
  scope                = azurerm_linux_function_app.main.id
  role_definition_name = "Website Contributor"
  principal_id         = var.github_actions_object_id
}
```

### B. Resource Group Level (if we need broader access)
```terraform 
resource "azurerm_role_assignment" "github_actions_rg_contributor" {
  count = var.github_actions_object_id != "" ? 1 : 0
  
  scope                = azurerm_resource_group.main.id
  role_definition_name = "Website Contributor" 
  principal_id         = var.github_actions_object_id
}
```

## Security Considerations
- Function App scope is more secure than Resource Group scope
- Website Contributor is more secure than full Contributor
- Consider environment-specific controls (staging vs production)
