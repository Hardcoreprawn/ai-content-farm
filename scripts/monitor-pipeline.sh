#!/bin/bash
# Monitor blob pipeline flow in staging environment
# Usage: ./monitor-pipeline.sh

STORAGE_ACCOUNT="hottopicsstoraget0t36m"

echo "🔍 Monitoring Content Pipeline Flow..."
echo "Storage Account: $STORAGE_ACCOUNT"
echo "========================================"

while true; do
    echo -e "\n$(date): Checking pipeline containers..."
    
    # Check hot-topics container
    echo -e "\n📥 HOT-TOPICS (Raw Reddit Data):"
    az storage blob list --container-name hot-topics --account-name $STORAGE_ACCOUNT \
        --query "[].{Name:name, Size:properties.contentLength, Modified:properties.lastModified}" \
        --output table | tail -5
    
    # Check if content-pipeline container exists
    PIPELINE_EXISTS=$(az storage container list --account-name $STORAGE_ACCOUNT \
        --query "[?name=='content-pipeline'].name" --output tsv)
    
    if [ "$PIPELINE_EXISTS" = "content-pipeline" ]; then
        echo -e "\n📊 RANKED-TOPICS (ContentRanker Output):"
        az storage blob list --container-name content-pipeline --prefix ranked-topics/ \
            --account-name $STORAGE_ACCOUNT \
            --query "[].{Name:name, Size:properties.contentLength, Modified:properties.lastModified}" \
            --output table
        
        echo -e "\n🔬 ENRICHED-TOPICS (ContentEnricher Output):"
        az storage blob list --container-name content-pipeline --prefix enriched-topics/ \
            --account-name $STORAGE_ACCOUNT \
            --query "[].{Name:name, Size:properties.contentLength, Modified:properties.lastModified}" \
            --output table
    else
        echo -e "\n⏳ content-pipeline container doesn't exist yet - waiting for ContentRanker to create it..."
    fi
    
    echo -e "\n⏰ Next check in 30 seconds... (Ctrl+C to stop)"
    sleep 30
done
