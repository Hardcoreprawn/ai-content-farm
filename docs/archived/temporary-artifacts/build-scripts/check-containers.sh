#!/bin/bash
# Container status checker - tests all Azure Container Apps

echo "🔍 Azure Container Apps Status Check"
echo "======================================"
echo "Date: $(date)"
echo "Your IP: $(curl -s https://ipinfo.io/ip 2>/dev/null || echo 'unknown')"
echo ""

# Array of container URLs
containers=(
    "ai-content-prod-collector"
    "ai-content-prod-ranker"
    "ai-content-prod-enricher"
    "ai-content-prod-processor"
    "ai-content-prod-markdown-gen"
    "ai-content-prod-scheduler"
    "ai-content-prod-content-gen"
    "ai-content-prod-site-gen"
)

base_url="victoriousbeach-e62a5683.uksouth.azurecontainerapps.io"

for container in "${containers[@]}"; do
    echo -n "📦 $container: "

    # Try health endpoint first, then docs, then root
    for endpoint in "health" "docs" ""; do
        url="https://${container}.${base_url}/${endpoint}"
        response=$(timeout 5 curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)

        if [[ "$response" == "200" ]]; then
            echo "✅ OK ($endpoint)"
            break
        elif [[ "$response" == "404" && "$endpoint" != "" ]]; then
            continue
        else
            if [[ "$endpoint" == "" ]]; then
                if [[ "$response" == "000" ]]; then
                    echo "❌ No response (timeout/unreachable)"
                else
                    echo "⚠️  HTTP $response"
                fi
            fi
        fi
    done
done

echo ""
echo "🌐 Direct URLs (restricted to your IP):"
echo "======================================"
for container in "${containers[@]}"; do
    echo "   https://${container}.${base_url}/"
done
