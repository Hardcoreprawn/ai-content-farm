#!/bin/bash
"""
Quick Start Script for Event-Driven AI Content Farm

Builds and starts the complete containerized pipeline with static site generation.
"""

set -e

echo "🚀 Starting AI Content Farm - Event-Driven Pipeline"
echo "====================================================="

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        echo "❌ Docker is not running. Please start Docker and try again."
        exit 1
    fi
    echo "✅ Docker is running"
}

# Function to build and start services
start_services() {
    echo ""
    echo "🔧 Building and starting services..."
    
    # Build only the new services (existing ones should be already built)
    echo "📦 Building new containers..."
    docker-compose build ssg markdown-generator markdown-converter
    
    # Start all services
    echo "🚀 Starting all services..."
    docker-compose up -d
    
    echo "✅ Services started"
}

# Function to wait for services to be healthy
wait_for_services() {
    echo ""
    echo "⏳ Waiting for services to be ready..."
    
    services=(
        "localhost:8001|Content Collector"
        "localhost:8002|Content Processor" 
        "localhost:8003|Content Enricher"
        "localhost:8004|Content Ranker"
        "localhost:8005|Static Site Generator"
        "localhost:8006|Markdown Converter"
        "localhost:8007|Markdown Generator"
    )
    
    for service in "${services[@]}"; do
        IFS='|' read -r url name <<< "$service"
        echo -n "   Waiting for $name..."
        
        for i in {1..30}; do
            if curl -s "http://$url/health" > /dev/null 2>&1; then
                echo " ✅ Ready"
                break
            fi
            
            if [ $i -eq 30 ]; then
                echo " ❌ Timeout"
            else
                echo -n "."
                sleep 2
            fi
        done
    done
}

# Function to run the test pipeline
test_pipeline() {
    echo ""
    echo "🧪 Running event-driven pipeline test..."
    
    # Install httpx if not available
    if ! python3 -c "import httpx" 2>/dev/null; then
        echo "📦 Installing required Python packages..."
        pip3 install httpx
    fi
    
    # Run the test
    python3 test_event_driven_pipeline.py
}

# Function to show the results
show_results() {
    echo ""
    echo "🎯 AI Content Farm - Event-Driven Pipeline Started!"
    echo "===================================================="
    echo ""
    echo "🌐 Access Your Generated Website:"
    echo "   📱 Live Website: http://localhost:8005/preview/"
    echo "   🏠 Homepage: http://localhost:8005/preview/index.html"
    echo "   📚 Topics: http://localhost:8005/preview/topics/"
    echo "   📄 Articles: http://localhost:8005/preview/articles/"
    echo "   📡 RSS Feed: http://localhost:8005/preview/feed.xml"
    echo ""
    echo "🔧 Service APIs:"
    echo "   📊 Content Collector: http://localhost:8001/"
    echo "   🔄 Content Processor: http://localhost:8002/"
    echo "   🤖 Content Enricher: http://localhost:8003/"
    echo "   📈 Content Ranker: http://localhost:8004/"
    echo "   🏗️  Static Site Generator: http://localhost:8005/"
    echo "   📝 Markdown Converter: http://localhost:8006/"
    echo "   📄 Markdown Generator: http://localhost:8007/"
    echo ""
    echo "📊 Pipeline Flow:"
    echo "   1️⃣  Collector → Processor → Enricher → Ranker"
    echo "   2️⃣  Ranker → Markdown Generator (auto-triggered)"
    echo "   3️⃣  Markdown Generator → Static Site Generator (auto-triggered)"
    echo "   4️⃣  Website updates automatically!"
    echo ""
    echo "🛠️  Management Commands:"
    echo "   🔍 View logs: docker-compose logs -f [service-name]"
    echo "   🔄 Restart: docker-compose restart [service-name]"
    echo "   🛑 Stop all: docker-compose down"
    echo "   📊 Status: docker-compose ps"
    echo ""
    echo "💡 The pipeline is now event-driven and will automatically:"
    echo "   • Watch for new ranked content"
    echo "   • Generate markdown files"
    echo "   • Create static website"
    echo "   • Update the live site"
    echo ""
    echo "🎉 Your AI Content Farm is ready!"
}

# Main execution
main() {
    check_docker
    start_services
    wait_for_services
    test_pipeline
    show_results
}

# Run main function
main
