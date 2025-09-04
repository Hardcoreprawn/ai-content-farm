#!/bin/bash
set -e

# Content Processor Local Testing Script
# Tests the container locally before Azure deployment

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR" && pwd)"

# Configuration
CONTAINER_NAME="content-processor-test"
LOCAL_PORT=8000
TEST_TIMEOUT=120

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

cleanup() {
    log "Cleaning up test environment..."
    docker stop "$CONTAINER_NAME" 2>/dev/null || true
    docker rm "$CONTAINER_NAME" 2>/dev/null || true
}

# Cleanup on exit
trap cleanup EXIT

main() {
    log "🚀 Starting Content Processor Local Testing"

    # Check Docker is running
    if ! docker info >/dev/null 2>&1; then
        error "Docker is not running. Please start Docker first."
        exit 1
    fi

    # Check if port is available
    if lsof -i :$LOCAL_PORT >/dev/null 2>&1; then
        error "Port $LOCAL_PORT is already in use. Please stop the service or choose a different port."
        exit 1
    fi

    # Build the container
    log "🔨 Building content-processor container..."
    cd "/workspaces/ai-content-farm"  # Build from project root

    if ! docker build -t content-processor:test -f containers/content-processor/Dockerfile .; then
        error "Failed to build container"
        exit 1
    fi
    success "Container built successfully"

    # Start the container
    log "🏃 Starting container on port $LOCAL_PORT..."

    docker run -d \
        --name "$CONTAINER_NAME" \
        -p "$LOCAL_PORT:8000" \
        -e ENVIRONMENT=test \
        -e LOG_LEVEL=DEBUG \
        -e AZURE_OPENAI_ENDPOINT="" \
        -e AZURE_OPENAI_API_KEY="" \
        -e AZURE_OPENAI_API_VERSION="2024-06-01" \
        -e AZURE_SERVICE_BUS_CONNECTION_STRING="" \
        content-processor:test

    # Wait for container to be ready
    log "⏳ Waiting for container to be ready..."

    for i in {1..30}; do
        if curl -s "http://localhost:$LOCAL_PORT/health" >/dev/null 2>&1; then
            success "Container is ready!"
            break
        fi

        if [ $i -eq 30 ]; then
            error "Container failed to start within timeout"
            docker logs "$CONTAINER_NAME"
            exit 1
        fi

        sleep 2
    done

    # Show container logs
    log "📋 Container logs:"
    docker logs "$CONTAINER_NAME" | tail -20

    # Run API validation tests
    log "🔬 Running API validation tests..."

    cd "$SCRIPT_DIR"  # Go back to container directory for validation script

    if python3 validate_api.py --local --local-port "$LOCAL_PORT"; then
        success "All API tests passed!"
    else
        warning "Some API tests failed. Check validation results for details."
    fi

    # Show container status
    log "📊 Container Status:"
    docker stats --no-stream "$CONTAINER_NAME" | grep -v CONTAINER

    # Interactive mode
    echo ""
    log "🎯 Container is running on http://localhost:$LOCAL_PORT"
    log "Available endpoints:"
    echo "  • Health check: http://localhost:$LOCAL_PORT/health"
    echo "  • Status info:  http://localhost:$LOCAL_PORT/status"
    echo "  • API docs:     http://localhost:$LOCAL_PORT/docs"
    echo "  • OpenAPI spec: http://localhost:$LOCAL_PORT/openapi.json"
    echo ""

    read -p "Press Enter to run additional tests, or Ctrl+C to stop..."

    # Test specific endpoints manually
    log "🧪 Testing specific endpoints..."

    echo ""
    echo "=== Health Check ==="
    curl -s "http://localhost:$LOCAL_PORT/health" | python3 -m json.tool

    echo ""
    echo "=== Status Info ==="
    curl -s "http://localhost:$LOCAL_PORT/status" | python3 -m json.tool

    echo ""
    echo "=== Root Endpoint ==="
    curl -s "http://localhost:$LOCAL_PORT/" | python3 -m json.tool

    echo ""
    echo "=== Process Endpoint (Test) ==="
    curl -s -X POST "http://localhost:$LOCAL_PORT/process" \
        -H "Content-Type: application/json" \
        -d '{
            "topic_id": "test-local-001",
            "content": "This is a test content for local validation",
            "metadata": {
                "source": "local_test",
                "timestamp": "'$(date -u +%s)'"
            }
        }' | python3 -m json.tool

    echo ""
    success "Local testing completed!"

    read -p "Container will continue running. Press Enter to stop and cleanup..."
}

# Check dependencies
if ! command -v docker &> /dev/null; then
    error "Docker is required but not installed"
    exit 1
fi

if ! command -v curl &> /dev/null; then
    error "curl is required but not installed"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    error "python3 is required but not installed"
    exit 1
fi

# Run main function
main "$@"
