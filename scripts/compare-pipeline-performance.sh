#!/bin/bash
# Pipeline Performance Comparison Script
# This script helps measure and compare pipeline performance before/after containerization

set -e

echo "🔍 AI Content Farm - Pipeline Performance Analysis"
echo "=================================================="

# GitHub API configuration
REPO="Hardcoreprawn/ai-content-farm"
API_BASE="https://api.github.com/repos/$REPO"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to get workflow runs
get_workflow_runs() {
    local workflow_name="$1"
    local count="${2:-10}"
    
    echo "📊 Fetching recent runs for workflow: $workflow_name"
    
    # Get workflow ID by name
    local workflow_id=$(curl -s "$API_BASE/actions/workflows" | \
        jq -r ".workflows[] | select(.name == \"$workflow_name\") | .id")
    
    if [ "$workflow_id" = "" ] || [ "$workflow_id" = "null" ]; then
        echo "❌ Workflow '$workflow_name' not found"
        return 1
    fi
    
    # Get recent runs
    curl -s "$API_BASE/actions/workflows/$workflow_id/runs?per_page=$count" | \
        jq -r '.workflow_runs[] | select(.conclusion != null) | 
               "\(.run_number),\(.conclusion),\(.created_at),\(.updated_at),\(.html_url)"'
}

# Function to calculate duration in minutes
calculate_duration() {
    local start_time="$1"
    local end_time="$2"
    
    local start_epoch=$(date -d "$start_time" +%s 2>/dev/null || echo "0")
    local end_epoch=$(date -d "$end_time" +%s 2>/dev/null || echo "0")
    
    if [ "$start_epoch" -gt 0 ] && [ "$end_epoch" -gt 0 ]; then
        local duration_seconds=$((end_epoch - start_epoch))
        local duration_minutes=$((duration_seconds / 60))
        echo "$duration_minutes"
    else
        echo "unknown"
    fi
}

# Function to analyze workflow performance
analyze_workflow() {
    local workflow_name="$1"
    local label="$2"
    
    echo ""
    echo -e "${BLUE}📈 Analyzing: $label${NC}"
    echo "----------------------------------------"
    
    local runs_data=$(get_workflow_runs "$workflow_name" 20)
    
    if [ -z "$runs_data" ]; then
        echo "❌ No data available for $workflow_name"
        return 1
    fi
    
    local total_duration=0
    local success_count=0
    local failure_count=0
    local run_count=0
    local durations=()
    
    while IFS=',' read -r run_number conclusion created_at updated_at url; do
        local duration=$(calculate_duration "$created_at" "$updated_at")
        
        if [ "$duration" != "unknown" ]; then
            durations+=($duration)
            total_duration=$((total_duration + duration))
            run_count=$((run_count + 1))
        fi
        
        if [ "$conclusion" = "success" ]; then
            success_count=$((success_count + 1))
        else
            failure_count=$((failure_count + 1))
        fi
        
        # Show recent runs
        if [ $run_count -le 5 ]; then
            local status_color=$GREEN
            if [ "$conclusion" != "success" ]; then
                status_color=$RED
            fi
            echo -e "  Run #$run_number: ${status_color}$conclusion${NC} ($duration min) - $(echo $url | sed 's|.*runs/||')"
        fi
        
    done <<< "$runs_data"
    
    if [ $run_count -gt 0 ]; then
        local avg_duration=$((total_duration / run_count))
        local success_rate=$((success_count * 100 / (success_count + failure_count)))
        
        echo ""
        echo "📊 Performance Summary ($run_count runs analyzed):"
        echo "  Average Duration: ${avg_duration} minutes"
        echo "  Success Rate: ${success_rate}%"
        echo "  Total Runs: $((success_count + failure_count))"
        echo "  Successful: $success_count"
        echo "  Failed: $failure_count"
        
        # Calculate min/max if we have multiple runs
        if [ ${#durations[@]} -gt 1 ]; then
            local min_duration=$(printf '%s\n' "${durations[@]}" | sort -n | head -1)
            local max_duration=$(printf '%s\n' "${durations[@]}" | sort -n | tail -1)
            echo "  Fastest Run: ${min_duration} minutes"
            echo "  Slowest Run: ${max_duration} minutes"
        fi
    else
        echo "❌ No valid duration data available"
    fi
    
    # Return average duration for comparison
    if [ $run_count -gt 0 ]; then
        echo $avg_duration
    else
        echo 0
    fi
}

# Main analysis
echo ""
echo "🏃‍♂️ Comparing Pipeline Performance"
echo "=================================="

# Analyze original pipeline
echo ""
echo -e "${YELLOW}📊 ORIGINAL PIPELINE PERFORMANCE${NC}"
original_avg=$(analyze_workflow "Consolidated CI/CD Pipeline" "Original (Non-Containerized)")

# Analyze containerized pipeline  
echo ""
echo -e "${YELLOW}📊 CONTAINERIZED PIPELINE PERFORMANCE${NC}"
containerized_avg=$(analyze_workflow "Containerized CI/CD Pipeline" "Containerized")

# Performance comparison
echo ""
echo -e "${BLUE}🏆 PERFORMANCE COMPARISON${NC}"
echo "=================================="

if [ "$original_avg" -gt 0 ] && [ "$containerized_avg" -gt 0 ]; then
    local improvement=$((original_avg - containerized_avg))
    local improvement_percent=$((improvement * 100 / original_avg))
    
    echo "📈 Performance Improvement:"
    echo "  Original Average: ${original_avg} minutes"
    echo "  Containerized Average: ${containerized_avg} minutes"
    echo ""
    
    if [ $improvement -gt 0 ]; then
        echo -e "  ${GREEN}✅ Improvement: ${improvement} minutes (${improvement_percent}% faster)${NC}"
        echo "  💰 Time Savings per Pipeline: ${improvement} minutes"
        echo "  💰 Monthly Savings (50 runs): $((improvement * 50)) minutes"
    elif [ $improvement -lt 0 ]; then
        local regression=$((-improvement))
        local regression_percent=$((regression * 100 / original_avg))
        echo -e "  ${RED}❌ Regression: ${regression} minutes (${regression_percent}% slower)${NC}"
    else
        echo -e "  ${YELLOW}➡️  No significant change${NC}"
    fi
else
    echo "⚠️  Insufficient data for comparison"
    if [ "$original_avg" -eq 0 ]; then
        echo "   - No original pipeline data available"
    fi
    if [ "$containerized_avg" -eq 0 ]; then
        echo "   - No containerized pipeline data available"
    fi
fi

# Additional insights
echo ""
echo -e "${BLUE}💡 OPTIMIZATION INSIGHTS${NC}"
echo "=================================="

echo "🚀 Container Strategy Benefits:"
echo "  ✅ Pre-installed tools (no setup time)"
echo "  ✅ Consistent environments across jobs"
echo "  ✅ Parallel execution capabilities"
echo "  ✅ Docker layer caching"
echo "  ✅ Reduced network dependencies"

echo ""
echo "📊 Expected Performance Targets:"
echo "  🎯 Target Pipeline Time: 6-8 minutes"
echo "  🎯 Container Build Time: 3-5 minutes (one-time cost)"
echo "  🎯 Security Scan Stage: <2 minutes"
echo "  🎯 Deployment Stage: <3 minutes"

echo ""
echo "🔍 To monitor pipeline performance:"
echo "  1. Watch GitHub Actions dashboard for execution times"
echo "  2. Monitor container registry for image build frequency"
echo "  3. Track cache hit rates in build logs"
echo "  4. Compare resource usage in GitHub Actions insights"

echo ""
echo "📊 Re-run this script periodically to track performance trends:"
echo "  ./scripts/compare-pipeline-performance.sh"
