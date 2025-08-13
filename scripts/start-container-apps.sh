#!/bin/bash

# AI Content Farm - Container Apps Development Startup
# This script builds and runs the Container Apps version of SummaryWomble locally

set -e

echo "🚀 Starting AI Content Farm Container Apps Development"

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if we have the required environment variables
if [ -z "$REDDIT_CLIENT_ID" ]; then
    echo "⚠️  Warning: REDDIT_CLIENT_ID not set. Reddit collection will not work."
fi

if [ -z "$REDDIT_CLIENT_SECRET" ]; then
    echo "⚠️  Warning: REDDIT_CLIENT_SECRET not set. Reddit collection will not work."
fi

if [ -z "$REDDIT_USER_AGENT" ]; then
    echo "⚠️  Warning: REDDIT_USER_AGENT not set. Reddit collection will not work."
fi

echo "📦 Building content processor container..."
docker-compose build

echo "🔧 Starting services..."
docker-compose up -d

echo "⏳ Waiting for services to be ready..."
sleep 10

# Check if the service is healthy
if curl -f http://localhost:8000/health >/dev/null 2>&1; then
    echo "✅ Content Processor API is running at http://localhost:8000"
    echo "📖 API Documentation available at http://localhost:8000/docs"
    echo "🔍 Health check: http://localhost:8000/health"
    echo "📋 SummaryWomble API: http://localhost:8000/api/summary-womble/docs"
    echo ""
    echo "🧪 Test the API:"
    echo "curl -X POST http://localhost:8000/api/summary-womble/process \\"
    echo "  -H 'Content-Type: application/json' \\"
    echo "  -d '{\"source\": \"reddit\", \"targets\": [\"technology\"], \"limit\": 5}'"
    echo ""
    echo "📊 View logs: docker-compose logs -f"
    echo "🛑 Stop services: docker-compose down"
else
    echo "❌ Service failed to start. Check logs:"
    docker-compose logs
    exit 1
fi
