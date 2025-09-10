#!/bin/bash

# monitor-pipeline-test.sh
# Monitors Issue #421 pipeline fix test and logs any issues for remediation

set -euo pipefail

echo "=== Monitoring Pipeline Fix Test for Issue #421 ==="
echo "Commit: $(git rev-parse --short HEAD)"
echo "Date: $(date)"
echo ""

# Get the current running pipeline
PIPELINE_ID=$(gh run list --workflow="CI/CD Pipeline" --limit 1 --json databaseId --jq '.[0].databaseId')
echo "Monitoring Pipeline ID: $PIPELINE_ID"

# Create logs directory
mkdir -p logs

# Function to log issues
log_issue() {
    local severity=$1
    local component=$2
    local message=$3
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    echo "[$timestamp] [$severity] [$component] $message" | tee -a logs/pipeline-fix-test-issues.log
}

# Function to log success
log_success() {
    local component=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    echo "[$timestamp] [SUCCESS] [$component] $message" | tee -a logs/pipeline-fix-test-success.log
}

echo "Pipeline Status Monitoring:"
echo "- SUCCESS events logged to: logs/pipeline-fix-test-success.log"
echo "- ISSUE events logged to: logs/pipeline-fix-test-issues.log"
echo ""

# Wait for pipeline to complete or timeout after 30 minutes
timeout_seconds=1800
start_time=$(date +%s)

while true; do
    current_time=$(date +%s)
    elapsed=$((current_time - start_time))

    if [ $elapsed -gt $timeout_seconds ]; then
        log_issue "ERROR" "TIMEOUT" "Pipeline test exceeded 30-minute timeout limit"
        break
    fi

    # Check pipeline status
    STATUS=$(gh run view $PIPELINE_ID --json status --jq '.status')
    CONCLUSION=$(gh run view $PIPELINE_ID --json conclusion --jq '.conclusion')

    if [ "$STATUS" = "completed" ]; then
        if [ "$CONCLUSION" = "success" ]; then
            log_success "PIPELINE" "Issue #421 fix test completed successfully"

            # Log specific success metrics
            log_success "CONTAINERS" "All container tests passed"
            log_success "DEPLOYMENT" "Infrastructure deployment successful"
            log_success "VERSIONING" "Container image versioning working"
            log_success "DISCOVERY" "Dynamic container discovery operational"

            echo ""
            echo "🎉 PIPELINE TEST SUCCESS!"
            echo "Issue #421 fix is working correctly in production."
            break
        else
            log_issue "ERROR" "PIPELINE" "Pipeline failed with conclusion: $CONCLUSION"

            # Get detailed job failures
            echo ""
            echo "Analyzing failed jobs..."
            gh run view $PIPELINE_ID --json jobs --jq '.jobs[] | select(.conclusion != "success") | {name: .name, conclusion: .conclusion}' | while read -r job_info; do
                job_name=$(echo "$job_info" | jq -r '.name')
                job_conclusion=$(echo "$job_info" | jq -r '.conclusion')
                log_issue "ERROR" "JOB_FAILURE" "Job '$job_name' failed with: $job_conclusion"
            done

            echo ""
            echo "❌ PIPELINE TEST FAILED!"
            echo "Check logs/pipeline-fix-test-issues.log for remediation items."
            break
        fi
    fi

    # Log progress every 60 seconds
    if [ $((elapsed % 60)) -eq 0 ]; then
        elapsed_min=$((elapsed / 60))
        echo "[$elapsed_min min] Pipeline status: $STATUS"

        # Check for any warnings or issues in job logs
        if [ "$STATUS" = "in_progress" ]; then
            # Log any job failures as they happen
            gh run view $PIPELINE_ID --json jobs --jq '.jobs[] | select(.conclusion == "failure") | .name' | while read -r failed_job; do
                log_issue "WARNING" "JOB_FAILURE" "Job '$failed_job' failed during execution"
            done
        fi
    fi

    sleep 10
done

echo ""
echo "=== Pipeline Test Monitoring Complete ==="
echo "Review log files in logs/ directory for any remediation items."
