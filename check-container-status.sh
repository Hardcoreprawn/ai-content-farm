#!/bin/bash
# Quick container status checker

echo "=== CONTAINER APP STATUS ==="
az containerapp list --resource-group ai-content-prod-rg \
  --query '[].{Name:name, Status:properties.runningStatus, Provisioning:properties.provisioningState}' \
  -o table

echo -e "\n=== REVISION DETAILS FOR EACH CONTAINER ==="
for app in ai-content-prod-collector ai-content-prod-processor ai-content-prod-markdown-gen ai-content-prod-site-publisher; do
  echo -e "\n📦 $app:"
  az containerapp revision list --name $app --resource-group ai-content-prod-rg \
    --query '[].{Revision:name, Active:properties.active, Traffic:properties.trafficWeight, State:properties.runningState, Replicas:properties.replicas, Image:properties.template.containers[0].image, Created:properties.createdTime}' \
    -o table 2>/dev/null | head -10
done

echo -e "\n=== SUMMARY ==="
echo "Collector Status: $(az containerapp show --name ai-content-prod-collector --resource-group ai-content-prod-rg --query 'properties.runningStatus' -o tsv 2>/dev/null)"
echo "Processor Status: $(az containerapp show --name ai-content-prod-processor --resource-group ai-content-prod-rg --query 'properties.runningStatus' -o tsv 2>/dev/null)"
echo "Markdown-Gen Status: $(az containerapp show --name ai-content-prod-markdown-gen --resource-group ai-content-prod-rg --query 'properties.runningStatus' -o tsv 2>/dev/null)"
echo "Site-Publisher Status: $(az containerapp show --name ai-content-prod-site-publisher --resource-group ai-content-prod-rg --query 'properties.runningStatus' -o tsv 2>/dev/null)"
