# Terraform Configuration: AUTO_COLLECT_ON_STARTUP

## Change Made

Added `AUTO_COLLECT_ON_STARTUP` environment variable to the content-collector container app in Terraform.

### File Modified
`/workspaces/ai-content-farm/infra/container_app_collector.tf`

### Change
```terraform
# Enable automatic startup collection when KEDA scales container up
env {
  name  = "AUTO_COLLECT_ON_STARTUP"
  value = "true"
}
```

### Location
Added after the `KEDA_CRON_TRIGGER` environment variable in the container template.

### Impact
- **Default behavior**: Startup collection is ENABLED (`"true"`)
- **Container startup**: When KEDA scales up, collection runs automatically
- **Disable if needed**: Change value to `"false"` to disable startup collection
- **HTTP triggers**: Manual HTTP triggers via `/api/collect/trigger` still work regardless

### Integration with KEDA Cron
```
KEDA Schedule: 0 0,8,16 * * * UTC
       ↓
Scale 0 → 1 replica
       ↓
Container starts
       ↓
lifespan() checks AUTO_COLLECT_ON_STARTUP=true
       ↓
Runs startup collection
       ↓
HTTP server ready
       ↓
Cooldown period, KEDA scales 1 → 0
```

## Deployment
The Terraform change will be applied when:
1. Changes are committed to feature branch
2. GitHub Actions runs Terraform plan
3. PR is approved and merged to main
4. CI/CD triggers Terraform apply in production

## Rollback
If startup collection causes issues:
1. Change `value = "true"` to `value = "false"`
2. Apply Terraform
3. Container continues serving manual HTTP triggers

Or temporarily:
```bash
az containerapp update \
  -n ai-content-prod-collector \
  -g ai-content-prod-rg \
  --set-env-vars AUTO_COLLECT_ON_STARTUP=false
```
