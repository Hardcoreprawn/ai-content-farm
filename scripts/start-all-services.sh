#!/bin/bash

# AI Content Farm - Container Apps Development Startup
# This script builds and runs all Container Apps services locally

set -e

echo "🚀 Starting AI Content Farm Container Apps Development Environment"

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if we have the required environment variables for Reddit
if [ -z "$REDDIT_CLIENT_ID" ]; then
    echo "⚠️  Warning: REDDIT_CLIENT_ID not set. Reddit collection will not work."
    echo "   To fix: export REDDIT_CLIENT_ID=\$(az keyvault secret show --vault-name ai-content-app-kvt0t36m --name reddit-client-id --query 'value' --output tsv)"
fi

if [ -z "$REDDIT_CLIENT_SECRET" ]; then
    echo "⚠️  Warning: REDDIT_CLIENT_SECRET not set. Reddit collection will not work."
    echo "   To fix: export REDDIT_CLIENT_SECRET=\$(az keyvault secret show --vault-name ai-content-app-kvt0t36m --name reddit-client-secret --query 'value' --output tsv)"
fi

if [ -z "$REDDIT_USER_AGENT" ]; then
    echo "⚠️  Warning: REDDIT_USER_AGENT not set. Reddit collection will not work."
    echo "   To fix: export REDDIT_USER_AGENT=\$(az keyvault secret show --vault-name ai-content-app-kvt0t36m --name reddit-user-agent --query 'value' --output tsv)"
fi

echo "📦 Building all container services..."
docker-compose build

echo "🔧 Starting services..."
docker-compose up -d

echo "⏳ Waiting for services to be ready..."
sleep 15

# Check service health
services_healthy=true

# Check Content Processor (SummaryWomble)
if curl -f http://localhost:8000/health >/dev/null 2>&1; then
    echo "✅ Content Processor API is running at http://localhost:8000"
else
    echo "❌ Content Processor API failed to start"
    services_healthy=false
fi

# Check Content Ranker
if curl -f http://localhost:8001/health >/dev/null 2>&1; then
    echo "✅ Content Ranker API is running at http://localhost:8001"
else
    echo "❌ Content Ranker API failed to start"
    services_healthy=false
fi

# Check Azurite (blob storage emulation)
if curl -f http://localhost:10000 >/dev/null 2>&1; then
    echo "✅ Azurite blob storage emulation is running at http://localhost:10000"
else
    echo "❌ Azurite blob storage emulation failed to start"
    services_healthy=false
fi

if [ "$services_healthy" = true ]; then
    echo ""
    echo "🎉 All services are healthy and ready!"
    echo ""
    echo "📖 Service Documentation:"
    echo "   • Content Processor: http://localhost:8000/docs"
    echo "   • Content Ranker: http://localhost:8001/docs"
    echo ""
    echo "🔍 Health Checks:"
    echo "   • Content Processor: http://localhost:8000/health"
    echo "   • Content Ranker: http://localhost:8001/health"
    echo ""
    echo "🧪 Quick API Tests:"
    echo ""
    echo "   # Test content collection:"
    echo "   curl -X POST http://localhost:8000/api/summary-womble/process \\"
    echo "     -H 'Content-Type: application/json' \\"
    echo "     -d '{\"source\": \"reddit\", \"targets\": [\"technology\"], \"limit\": 3}'"
    echo ""
    echo "   # Test content ranking (with sample data):"
    echo "   curl -X POST http://localhost:8001/api/content-ranker/process \\"
    echo "     -H 'Content-Type: application/json' \\"
    echo "     -d '{\"source\": \"reddit\", \"topics\": [{\"title\": \"AI breakthrough\", \"score\": 1000, \"num_comments\": 50, \"created_utc\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}]}'"
    echo ""
    echo "📊 Monitoring:"
    echo "   • View logs: docker-compose logs -f"
    echo "   • View specific service: docker-compose logs -f content-processor"
    echo ""
    echo "🛑 Stop services: docker-compose down"
    echo ""
    echo "🔧 Troubleshooting:"
    echo "   • Rebuild: docker-compose build --no-cache"
    echo "   • Reset storage: docker-compose down -v && docker-compose up -d"
else
    echo ""
    echo "❌ Some services failed to start. Check logs:"
    echo "   docker-compose logs"
    echo ""
    echo "🔧 Try rebuilding:"
    echo "   docker-compose down"
    echo "   docker-compose build --no-cache"
    echo "   docker-compose up -d"
fi
